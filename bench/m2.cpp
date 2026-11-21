// The timed functions of Milestone 2 that use Kairn (bench/m2_data.hpp says what each translation
// unit of the benchmark does), for double limbs (backend m2) and float limbs (m2f):
//
// 1. The building blocks of kairn/blocks.hpp: the sums, differences and products rounded down and
//    up, next_up, next_down, radd, rmul, two_sum, two_prod; the floors add, sub, mul (one plain
//    operation of T).
// 2. Interval<T, 1>: + - *, negation, hull, intersection, midpoint and radius, split, the
//    conversions to and from Ball<T, 1>; the floors pair_add_1, pair_sub_1, pair_mul_1 (two plain
//    operations of T), plain4_mul_1 (the four products and their least and greatest, rounded to
//    nearest), plain_midrad_1, plain_bounds_1; and Ball<T, 1> for the same operations.
// 3. Interval<T, 2>: + - *, hull, intersection; the floors pair_add_2, pair_sub_2, pair_mul_2
//    (the operation of Expansion<T, 2> done twice) and plain4_mul_2; and Ball<T, 2>.
// 4. A Horner evaluation of a polynomial of degree 8 on intervals and balls of one and two limbs,
//    on a number of T and of two limbs; and its tightness (m2_tightness_json).
// 5. The additions to Ball: lower_as and upper_as, from_interval, the narrowing of two limbs to
//    one, half and ldexp, next to the ordinary scaling by the same power of two.
// 6. kairn::rational, small and large terms, one and two limbs, and its check.
//
// Variants: kairn, the generated kernel called on the limbs, the reference; op, the public operation
// as a client writes it, on arrays of the public types; plain, the same values computed with the
// operations of T (a floor, or for the floors the reference's other spelling); flat, the public
// operation in a function that the compiler is asked to inline everything into (the product of
// intervals of two limbs is an ordinary function, not forced inline); nextafter, std::nextafter.
// Built with the defaults a client gets (KAIRN_CHECKS is 0 under NDEBUG).
#include <kairn/kairn.hpp>

#include <algorithm>
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
using kairn_bench::m2::Entry;
using kairn_bench::m2::kDeg;
using kairn_bench::m2::kN;
using kairn_bench::m2::Raw;
using namespace kairn_bench::m2;   // the regions

template <class T>
using E1 = kairn::Expansion<T, 1>;
template <class T>
using E2 = kairn::Expansion<T, 2>;
template <class T>
using I1 = kairn::Interval<T, 1>;
template <class T>
using I2 = kairn::Interval<T, 2>;
template <class T>
using B1 = kairn::Ball<T, 1>;
template <class T>
using B2 = kairn::Ball<T, 2>;

template <class T>
struct Data {
    Raw<T> raw;   // first: m2_fenv.cpp sees this structure as a Raw<T>
    // Operands as the public types: the same numbers as raw.
    I1<T> x1[kN], y1[kN], f1[kN], w1[kN];
    I2<T> x2[kN], y2[kN], f2[kN], w2[kN];
    B1<T> xb1[kN], yb1[kN], fb1[kN];
    B2<T> xb2[kN], yb2[kN], fb2[kN];
    // The Horner polynomial's coefficients as each type, and its arguments.
    I1<T> hc1[kDeg + 1];
    I2<T> hc2[kDeg + 1];
    B1<T> hcb1[kDeg + 1];
    B2<T> hcb2[kDeg + 1];
    E2<T> hce2[kDeg + 1];
    I1<T> hx1[kN];
    I2<T> hx2[kN];
    B1<T> hxb1[kN];
    B2<T> hxb2[kN];
    E2<T> hxe2[kN];
    // Results of kairn::rational, the input of the timing of is_rational_result.
    kairn::Constant<E2<T>> pq2[kN];
    // Outputs.
    I1<T> zi1[kN];
    I2<T> zi2[kN];
    B1<T> zb1[kN];
    B2<T> zb2[kN];
    E2<T> ze2[kN];
    kairn::Split<I1<T>> zsp[kN];
    kairn::SumAndError<T> zse[kN];
    kairn::ProductAndError<T> zpe[kN];
    I1<T> ci1;
    I2<T> ci2;
    B1<T> cb1;
    B2<T> cb2;
    E2<T> ce2;
    kairn::Constant<E1<T>> zq1[kN];
    kairn::Constant<E2<T>> zq2[kN];
};

static_assert(std::is_standard_layout_v<Data<double>> && std::is_standard_layout_v<Data<float>>,
              "m2_fenv.cpp reads Data<T> as its first member, Raw<T>");
static_assert(sizeof(I1<double>) == 2 * sizeof(double) && sizeof(I2<double>) == 4 * sizeof(double) &&
                  sizeof(B1<double>) == 2 * sizeof(double) && sizeof(B2<double>) == 3 * sizeof(double) &&
                  sizeof(kairn::Split<I1<double>>) == 4 * sizeof(double) && sizeof(I2<float>) == 4 * sizeof(float) &&
                  sizeof(B2<float>) == 3 * sizeof(float),
              "the public types are their limbs, in order");

Data<double>* g64 = nullptr;
Data<float>* g32 = nullptr;

using kairn_bench::util::Rng;

// --- Inputs -------------------------------------------------------------------------------------

// +-[1, 2) 2^k with k in [kmin, kmax]. One draw per statement, so that every compiler sees the same
// numbers.
template <class T>
T one(Rng& g, int kmin, int kmax) {
    const double s = g.sign();
    const double m = 1.0 + g.u01();
    const int k = g.range(kmin, kmax);
    return T(s * std::ldexp(m, k));
}
template <class T>
T factor(Rng& g) {
    const double v = g.sym();
    return T(std::exp2(0.25 * v));
}
// A normalized pair of T near h, with a second limb about u |h|.
template <class T>
E2<T> two_limbs(Rng& g, T h) {
    const double v = g.sym();
    const T b = T(double(h) * v * std::ldexp(1.0, -std::numeric_limits<T>::digits));
    T s, e;
    kg::fast_two_sum(h, b, s, e);
    const T limbs[2] = {s, e};
    return E2<T>::from_limbs(limbs);
}
// [c - w, c + w] with w = |c| 2^-rel (1/2 to 1 of it), in plain arithmetic: two numbers of T.
template <class T>
I1<T> interval_around(Rng& g, T c, int rel) {
    const double v = g.u01();
    const T w = T(std::fabs(double(c)) * std::ldexp(0.5 + 0.5 * v, -rel));
    const T lo = c - w, hi = c + w;
    return I1<T>(E1<T>(lo), E1<T>(hi));
}
// The same with a center of two limbs, the bounds computed by Expansion<T, 2>.
template <class T>
I2<T> interval_around2(Rng& g, const E2<T>& c, int rel) {
    const double v = g.u01();
    const T w = T(std::fabs(double(c.limb[0])) * std::ldexp(0.5 + 0.5 * v, -rel));
    const E2<T> lo = c - E2<T>(w), hi = c + E2<T>(w);
    return I2<T>(lo, hi);
}

template <class T>
void put(T* o, int i, const I1<T>& x) {
    o[2 * i] = x.lower().limb[0];
    o[2 * i + 1] = x.upper().limb[0];
}
template <class T>
void put(T* o, int i, const I2<T>& x) {
    o[4 * i] = x.lower().limb[0];
    o[4 * i + 1] = x.lower().limb[1];
    o[4 * i + 2] = x.upper().limb[0];
    o[4 * i + 3] = x.upper().limb[1];
}
template <class T>
void put(T* o, int i, const B1<T>& x) {
    o[2 * i] = x.center().limb[0];
    o[2 * i + 1] = x.radius();
}
template <class T>
void put(T* o, int i, const B2<T>& x) {
    o[3 * i] = x.center().limb[0];
    o[3 * i + 1] = x.center().limb[1];
    o[3 * i + 2] = x.radius();
}
template <class T>
void put(T* o, int i, const E2<T>& x) {
    o[2 * i] = x.limb[0];
    o[2 * i + 1] = x.limb[1];
}

// The Chebyshev polynomial T8 = 128 x^8 - 256 x^6 + 160 x^4 - 32 x^2 + 1, from degree 0 up: exact
// coefficients, so that every width below comes from the arithmetic and the dependency, and a range
// that is known exactly (cos 8t on [-1, 1]).
constexpr double kT8[kDeg + 1] = {1, 0, -32, 0, 160, 0, -256, 0, 128};

// The half-width of an argument of the Horner benchmark, relative: 2^-30 for double, 2^-12 for
// float (the "narrow" regime of the tightness, m2_tightness_json).
template <class T>
constexpr int narrow_rel() {
    return sizeof(T) == 8 ? 30 : 12;
}

template <class T>
void fill(Data<T>& d, std::uint64_t seed) {
    Rng g{seed};
    Raw<T>& r = d.raw;
    const int rel1 = sizeof(T) == 8 ? 30 : 12;   // half-width of an interval of one limb, relative
    const int rel2 = sizeof(T) == 8 ? 80 : 40;   // of two limbs, and the radii of balls of two limbs
    for (int i = 0; i < kN; ++i) {
        r.xa[i] = one<T>(g, -8, 8);
        r.ya[i] = one<T>(g, -8, 8);
        r.fa[i] = factor<T>(g);
        r.ua[i] = std::fabs(one<T>(g, -8, 8));
        r.na[i] = g.range(-8, 8);
        r.pa[i] = T(std::ldexp(1.0, r.na[i]));
        r.sn[i] = (i & 1) ? 1 : -1;
        r.sa[i] = T(std::ldexp(1.0, r.sn[i]));

        d.x1[i] = interval_around<T>(g, one<T>(g, -8, 8), rel1);
        d.y1[i] = interval_around<T>(g, one<T>(g, -8, 8), rel1);
        d.f1[i] = interval_around<T>(g, factor<T>(g), rel1);
        {   // W overlaps X: from its midpoint to beyond its upper bound
            const T lo = d.x1[i].lower().limb[0], hi = d.x1[i].upper().limb[0];
            d.w1[i] = I1<T>(E1<T>(lo + (hi - lo) / 2), E1<T>(hi + (hi - lo)));
        }
        const E2<T> cx = two_limbs<T>(g, one<T>(g, -8, 8)), cy = two_limbs<T>(g, one<T>(g, -8, 8));
        const E2<T> cf = two_limbs<T>(g, factor<T>(g));
        d.x2[i] = interval_around2<T>(g, cx, rel2);
        d.y2[i] = interval_around2<T>(g, cy, rel2);
        d.f2[i] = interval_around2<T>(g, cf, rel2);
        {
            const E2<T> lo = d.x2[i].lower(), hi = d.x2[i].upper();
            const E2<T> mid = kairn::half(lo + hi);
            d.w2[i] = I2<T>(mid, hi + (hi - lo));
        }
        d.xb1[i] = B1<T>(d.x1[i]);
        d.yb1[i] = B1<T>(d.y1[i]);
        d.fb1[i] = B1<T>(d.f1[i]);
        const auto radius = [&](const E2<T>& c) {
            const double v = g.u01();
            return T(std::fabs(double(c.limb[0])) * std::ldexp(0.5 + 0.5 * v, -rel2));
        };
        d.xb2[i] = B2<T>(cx, radius(cx));
        d.yb2[i] = B2<T>(cy, radius(cy));
        d.fb2[i] = B2<T>(cf, radius(cf));

        put(r.xi, i, d.x1[i]);
        put(r.yi, i, d.y1[i]);
        put(r.fi, i, d.f1[i]);
        put(r.wi, i, d.w1[i]);
        put(r.xi2, i, d.x2[i]);
        put(r.yi2, i, d.y2[i]);
        put(r.fi2, i, d.f2[i]);
        put(r.wi2, i, d.w2[i]);
        put(r.xb1, i, d.xb1[i]);
        put(r.yb1, i, d.yb1[i]);
        put(r.fb1, i, d.fb1[i]);
        put(r.xb2, i, d.xb2[i]);
        put(r.yb2, i, d.yb2[i]);
        put(r.fb2, i, d.fb2[i]);
        put(r.xe2, i, d.x2[i].lower());
        put(r.ye2, i, d.y2[i].lower());
        put(r.fe2, i, d.f2[i].lower());
        for (int k = 0; k < 2; ++k) {
            r.sxi[k][i] = r.xi[2 * i + k];
            r.syi[k][i] = r.yi[2 * i + k];
            r.sxb1[k][i] = r.xb1[2 * i + k];
            r.syb1[k][i] = r.yb1[2 * i + k];
        }
        for (int k = 0; k < 4; ++k) {
            r.sxi2[k][i] = r.xi2[4 * i + k];
            r.syi2[k][i] = r.yi2[4 * i + k];
        }
        for (int k = 0; k < 3; ++k) {
            r.sxb2[k][i] = r.xb2[3 * i + k];
            r.syb2[k][i] = r.yb2[3 * i + k];
        }

        // Fractions.
        r.qns[i] = g.range(-1000, 1000);
        r.qds[i] = g.range(1, 1000) * ((g.next() & 1) ? 1 : -1);
        r.qnl[i] = (long long)g.next();
        do {
            r.qdl[i] = (long long)g.next();
        } while (r.qdl[i] == 0);
    }
    // The Horner polynomial and its arguments: narrow sets around points of [-1, 1].
    for (int k = 0; k <= kDeg; ++k) {
        const T c = T(kT8[k]);
        r.hc[k] = c;
        d.hc1[k] = I1<T>(c);
        d.hc2[k] = I2<T>(c);
        d.hcb1[k] = B1<T>(c);
        d.hcb2[k] = B2<T>(c);
        d.hce2[k] = E2<T>(c);
    }
    for (int i = 0; i < kN; ++i) {
        const T x = T(g.sym());
        const double v = g.u01();
        const T w = T(std::max(std::fabs(double(x)), 0.0625) * std::ldexp(0.5 + 0.5 * v, -narrow_rel<T>()));
        const T lo = x - w, hi = x + w;
        d.hx1[i] = I1<T>(E1<T>(lo), E1<T>(hi));
        d.hx2[i] = I2<T>(E2<T>(lo), E2<T>(hi));
        d.hxb1[i] = B1<T>(d.hx1[i]);
        d.hxb2[i] = B2<T>::from_interval(lo, hi);
        d.hxe2[i] = E2<T>(x);
        put(r.hi1, i, d.hx1[i]);
        put(r.hi2, i, d.hx2[i]);
        put(r.hb1, i, d.hxb1[i]);
        put(r.hb2, i, d.hxb2[i]);
        r.ht[i] = x;
        put(r.he2, i, d.hxe2[i]);
    }
    for (int i = 0; i < kN; ++i) d.pq2[i] = kairn::rational<E2<T>>(r.qnl[i], r.qdl[i]);
}

template <class T>
Data<T>& data_of();
template <>
Data<double>& data_of<double>() {
    return *g64;
}
template <>
Data<float>& data_of<float>() {
    return *g32;
}

template <class T>
unsigned char* region_of(Data<T>& d, int region, std::size_t& bytes) {
    auto at = [&](auto& x) {
        bytes = sizeof x;
        return reinterpret_cast<unsigned char*>(&x);
    };
    switch (region) {
        case R_OUT: return at(d.raw.out);
        case R_COUT: return at(d.raw.cout);
        case R_SOUT: return at(d.raw.sout);
        case R_I1: return at(d.zi1);
        case R_I2: return at(d.zi2);
        case R_B1: return at(d.zb1);
        case R_B2: return at(d.zb2);
        case R_E2: return at(d.ze2);
        case R_SPLIT: return at(d.zsp);
        case R_SE: return at(d.zse);
        case R_PE: return at(d.zpe);
        case R_CI1: return at(d.ci1);
        case R_CI2: return at(d.ci2);
        case R_CB1: return at(d.cb1);
        case R_CB2: return at(d.cb2);
        case R_CE2: return at(d.ce2);
        case R_Q1: return at(d.zq1);
        case R_Q2: return at(d.zq2);
        default: bytes = 0; return nullptr;
    }
}

// --- Generic forms of the timed operations ------------------------------------------------------

// Horner, as a client writes it for an interval, a ball or a number: p = c8; p = p x + ck.
template <class X, class C>
KAIRN_GEN_FORCEINLINE X horner(const C* c, const X& x) {
    X p = c[kDeg];
    for (int k = kDeg - 1; k >= 0; --k) p = p * x + c[k];
    return p;
}

// The generated kernels, on the limbs.
template <class T>
KAIRN_GEN_FORCEINLINE void k_horner_i1(const T* c, T xl, T xu, T& pl, T& pu) {
    pl = c[kDeg];
    pu = c[kDeg];
    for (int k = kDeg - 1; k >= 0; --k) {
        T ml, mu;
        kg::interval_mul_1(pl, pu, xl, xu, ml, mu);
        kg::interval_add_1(ml, mu, c[k], c[k], pl, pu);
    }
}
template <class T>
KAIRN_GEN_FORCEINLINE void k_horner_i2(const T* c, const T* x, T* p) {
    p[0] = c[kDeg];
    p[1] = T(0);
    p[2] = c[kDeg];
    p[3] = T(0);
    for (int k = kDeg - 1; k >= 0; --k) {
        T m[4];
        kg::interval_mul_2(p[0], p[1], p[2], p[3], x[0], x[1], x[2], x[3], m[0], m[1], m[2], m[3]);
        kg::interval_add_2(m[0], m[1], m[2], m[3], c[k], T(0), c[k], T(0), p[0], p[1], p[2], p[3]);
    }
}
template <class T>
KAIRN_GEN_FORCEINLINE void k_horner_b1(const T* c, T xc, T xr, T& pc, T& pr) {
    pc = c[kDeg];
    pr = T(0);
    for (int k = kDeg - 1; k >= 0; --k) {
        T mc, mr;
        kg::ball_mul_1_full(pc, pr, xc, xr, mc, mr);
        kg::ball_add_1_full(mc, mr, c[k], T(0), pc, pr);
    }
}
template <class T>
KAIRN_GEN_FORCEINLINE void k_horner_b2(const T* c, const T* x, T* p) {
    p[0] = c[kDeg];
    p[1] = T(0);
    p[2] = T(0);
    for (int k = kDeg - 1; k >= 0; --k) {
        T m[3];
        kg::ball_mul_2_full(p[0], p[1], p[2], x[0], x[1], x[2], m[0], m[1], m[2]);
        kg::ball_add_2_full(m[0], m[1], m[2], c[k], T(0), T(0), p[0], p[1], p[2]);
    }
}
template <class T>
KAIRN_GEN_FORCEINLINE void k_horner_e2(const T* c, const T* x, T* p) {
    p[0] = c[kDeg];
    p[1] = T(0);
    for (int k = kDeg - 1; k >= 0; --k) {
        T m0, m1;
        kg::mul_2_2_full(p[0], p[1], x[0], x[1], m0, m1);
        kg::add_2_2_full(m0, m1, c[k], T(0), p[0], p[1]);
    }
}
template <class T>
KAIRN_GEN_FORCEINLINE T k_horner_t(const T* c, T x) {
    T p = c[kDeg];
    for (int k = kDeg - 1; k >= 0; --k) {
        T m;
        kg::mul_1_1(p, x, m);
        kg::add_1_1(m, c[k], p);
    }
    return p;
}
template <class T>
KAIRN_GEN_FORCEINLINE T p_horner_t(const T* c, T x) {
    T p = c[kDeg];
    for (int k = kDeg - 1; k >= 0; --k) p = p * x + c[k];
    return p;
}

// The least and the greatest of four values, as the kernels choose them (lt and select).
template <class T>
KAIRN_GEN_FORCEINLINE T min4(T a, T b, T c, T e) {
    const T p = b < a ? b : a;
    const T q = e < c ? e : c;
    return q < p ? q : p;
}
template <class T>
KAIRN_GEN_FORCEINLINE T max4(T a, T b, T c, T e) {
    const T p = a < b ? b : a;
    const T q = c < e ? e : c;
    return p < q ? q : p;
}
template <class T>
KAIRN_GEN_FORCEINLINE void k_plain4_mul_1(T xl, T xu, T yl, T yu, T& l, T& h) {
    T p1, p2, p3, p4;
    kg::mul_1_1(xl, yl, p1);
    kg::mul_1_1(xl, yu, p2);
    kg::mul_1_1(xu, yl, p3);
    kg::mul_1_1(xu, yu, p4);
    l = min4(p1, p2, p3, p4);
    h = max4(p1, p2, p3, p4);
}
template <class T>
KAIRN_GEN_FORCEINLINE void p_plain4_mul_1(T xl, T xu, T yl, T yu, T& l, T& h) {
    const T p1 = xl * yl, p2 = xl * yu, p3 = xu * yl, p4 = xu * yu;
    l = min4(p1, p2, p3, p4);
    h = max4(p1, p2, p3, p4);
}
// The same on two limbs: the four products of Expansion<T, 2> and their least and greatest.
template <class T>
KAIRN_GEN_FORCEINLINE void k_plain4_mul_2(const T* x, const T* y, T* z) {
    T p[4][2];
    kg::mul_2_2_full(x[0], x[1], y[0], y[1], p[0][0], p[0][1]);
    kg::mul_2_2_full(x[0], x[1], y[2], y[3], p[1][0], p[1][1]);
    kg::mul_2_2_full(x[2], x[3], y[0], y[1], p[2][0], p[2][1]);
    kg::mul_2_2_full(x[2], x[3], y[2], y[3], p[3][0], p[3][1]);
    auto less = [](const T* a, const T* b) {
        bool m = false;
        kg::lt_2_2(a[0], a[1], b[0], b[1], m);
        return m;
    };
    const T* a = less(p[1], p[0]) ? p[1] : p[0];
    const T* b = less(p[3], p[2]) ? p[3] : p[2];
    const T* lo = less(b, a) ? b : a;
    const T* c = less(p[0], p[1]) ? p[1] : p[0];
    const T* e = less(p[2], p[3]) ? p[3] : p[2];
    const T* hi = less(c, e) ? e : c;
    z[0] = lo[0];
    z[1] = lo[1];
    z[2] = hi[0];
    z[3] = hi[1];
}
template <class T>
KAIRN_GEN_FORCEINLINE void o_plain4_mul_2(const I2<T>& x, const I2<T>& y, T* z) {
    const E2<T> p1 = x.lower() * y.lower(), p2 = x.lower() * y.upper(), p3 = x.upper() * y.lower(),
                p4 = x.upper() * y.upper();
    const E2<T>& a = p2 < p1 ? p2 : p1;
    const E2<T>& b = p4 < p3 ? p4 : p3;
    const E2<T>& lo = b < a ? b : a;
    const E2<T>& c = p1 < p2 ? p2 : p1;
    const E2<T>& e = p3 < p4 ? p4 : p3;
    const E2<T>& hi = c < e ? e : c;
    z[0] = lo.limb[0];
    z[1] = lo.limb[1];
    z[2] = hi.limb[0];
    z[3] = hi.limb[1];
}

// The latency of an evaluation: the argument of the next is made to depend on the result of this
// one by adding z = (a bound of the result) * 0, which is a zero, to its leading limbs. That costs
// one product and one or two additions per evaluation, on top of the evaluation's own chain.
template <class T>
KAIRN_GEN_FORCEINLINE I1<T> arg_i1(const I1<T>& x, T z) {
    return I1<T>(kairn::detail::kernel_result, E1<T>(x.lower().limb[0] + z), E1<T>(x.upper().limb[0] + z));
}
template <class T>
KAIRN_GEN_FORCEINLINE I2<T> arg_i2(const I2<T>& x, T z) {
    E2<T> lo = x.lower(), hi = x.upper();
    lo.limb[0] = lo.limb[0] + z;
    hi.limb[0] = hi.limb[0] + z;
    return I2<T>(kairn::detail::kernel_result, lo, hi);
}
template <class T>
KAIRN_GEN_FORCEINLINE B1<T> arg_b1(const B1<T>& x, T z) {
    return B1<T>(kairn::detail::kernel_result, E1<T>(x.center().limb[0] + z), x.radius());
}
template <class T>
KAIRN_GEN_FORCEINLINE B2<T> arg_b2(const B2<T>& x, T z) {
    E2<T> c = x.center();
    c.limb[0] = c.limb[0] + z;
    return B2<T>(kairn::detail::kernel_result, c, x.radius());
}
template <class T>
KAIRN_GEN_FORCEINLINE E2<T> arg_e2(const E2<T>& x, T z) {
    E2<T> c = x;
    c.limb[0] = c.limb[0] + z;
    return c;
}

}  // namespace

// The cost of a call next to a body: a function with the signature of interval_mul_2 (eight limbs
// in, four out through references) and almost no body, called and not inlined (variant plain of
// the kernel call_8_4), against the same copies written inline (variant kairn). External linkage,
// and noipa with GCC, so that no compiler removes or specializes a parameter.
#if defined(__GNUC__) && !defined(__clang__)
#define KB_NOIPA __attribute__((noipa))
#else
#define KB_NOIPA KB_NOINLINE
#endif
KB_NOIPA void kb_m2_call_8_4(double xl0, double xl1, double, double, double, double, double yu0, double yu1,
                             double& zl0, double& zl1, double& zu0, double& zu1) noexcept {
    zl0 = xl0;
    zl1 = xl1;
    zu0 = yu0;
    zu1 = yu1;
}
KB_NOIPA void kb_m2_call_8_4(float xl0, float xl1, float, float, float, float, float yu0, float yu1, float& zl0,
                             float& zl1, float& zu0, float& zu1) noexcept {
    zl0 = xl0;
    zl1 = xl1;
    zu0 = yu0;
    zu1 = yu1;
}
namespace {
template <class T>
KAIRN_GEN_FORCEINLINE void inline_8_4(T xl0, T xl1, T, T, T, T, T yu0, T yu1, T& zl0, T& zl1, T& zu0, T& zu1) noexcept {
    zl0 = xl0;
    zl1 = xl1;
    zu0 = yu0;
    zu1 = yu1;
}
}  // namespace

// --- The timed functions ------------------------------------------------------------------------

#if defined(__GNUC__)
#define KB_FLATTEN __attribute__((flatten))
#else
#define KB_FLATTEN
#endif
#define KB_ATTR_kairn
#define KB_ATTR_op
#define KB_ATTR_plain
#define KB_ATTR_nextafter
#define KB_ATTR_flat KB_FLATTEN

#define KB_EACH(...)                                                                               \
    for (int i = 0; i < kN; ++i) {                                                                 \
        __VA_ARGS__;                                                                               \
    }

// Shorthands for the operands of element i.
#define XL r.xi[2 * i]
#define XU r.xi[2 * i + 1]
#define YL r.yi[2 * i]
#define YU r.yi[2 * i + 1]
#define WL r.wi[2 * i]
#define WU r.wi[2 * i + 1]
#define FL r.fi[2 * i]
#define FU r.fi[2 * i + 1]
#define OUT2 r.out[2 * i], r.out[2 * i + 1]
#define OUT3 r.out[3 * i], r.out[3 * i + 1], r.out[3 * i + 2]
#define OUT4 r.out[4 * i], r.out[4 * i + 1], r.out[4 * i + 2], r.out[4 * i + 3]
#define X2(A) A[4 * i], A[4 * i + 1], A[4 * i + 2], A[4 * i + 3]
#define B1R(A) A[2 * i], A[2 * i + 1]
#define B2R(A) A[3 * i], A[3 * i + 1], A[3 * i + 2]

// X(B, SUF, T, KIND, KERNEL, VARIANT, REGION, VALUES, CHECK, BODY...): one timed function.
#define KB_LIST(X, B, SUF, T)                                                                      \
    /* 1. Building blocks: loops */                                                                \
    X(B, SUF, T, tp, add_down, kairn, R_OUT, kN, nullptr, KB_EACH(kg::add_down_1(r.xa[i], r.ya[i], r.out[i]))) \
    X(B, SUF, T, tp, add_down, op, R_OUT, kN, nullptr, KB_EACH(r.out[i] = kairn::add_down(r.xa[i], r.ya[i]))) \
    X(B, SUF, T, tp, add_up, kairn, R_OUT, kN, nullptr, KB_EACH(kg::add_up_1(r.xa[i], r.ya[i], r.out[i]))) \
    X(B, SUF, T, tp, add_up, op, R_OUT, kN, nullptr, KB_EACH(r.out[i] = kairn::add_up(r.xa[i], r.ya[i]))) \
    X(B, SUF, T, tp, sub_down, kairn, R_OUT, kN, nullptr, KB_EACH(kg::sub_down_1(r.xa[i], r.ya[i], r.out[i]))) \
    X(B, SUF, T, tp, sub_down, op, R_OUT, kN, nullptr, KB_EACH(r.out[i] = kairn::sub_down(r.xa[i], r.ya[i]))) \
    X(B, SUF, T, tp, sub_up, kairn, R_OUT, kN, nullptr, KB_EACH(kg::sub_up_1(r.xa[i], r.ya[i], r.out[i]))) \
    X(B, SUF, T, tp, sub_up, op, R_OUT, kN, nullptr, KB_EACH(r.out[i] = kairn::sub_up(r.xa[i], r.ya[i]))) \
    X(B, SUF, T, tp, mul_down, kairn, R_OUT, kN, nullptr, KB_EACH(kg::mul_down_1(r.xa[i], r.ya[i], r.out[i]))) \
    X(B, SUF, T, tp, mul_down, op, R_OUT, kN, nullptr, KB_EACH(r.out[i] = kairn::mul_down(r.xa[i], r.ya[i]))) \
    X(B, SUF, T, tp, mul_up, kairn, R_OUT, kN, nullptr, KB_EACH(kg::mul_up_1(r.xa[i], r.ya[i], r.out[i]))) \
    X(B, SUF, T, tp, mul_up, op, R_OUT, kN, nullptr, KB_EACH(r.out[i] = kairn::mul_up(r.xa[i], r.ya[i]))) \
    X(B, SUF, T, tp, next_up, kairn, R_OUT, kN, nullptr, KB_EACH(kg::next_up(r.xa[i], r.out[i])))      \
    X(B, SUF, T, tp, next_up, op, R_OUT, kN, nullptr, KB_EACH(r.out[i] = kairn::next_up(r.xa[i])))     \
    X(B, SUF, T, tp, next_up, nextafter, R_OUT, kN, nullptr,                                       \
      KB_EACH(r.out[i] = std::nextafter(r.xa[i], std::numeric_limits<T>::infinity())))             \
    X(B, SUF, T, tp, next_down, kairn, R_OUT, kN, nullptr, KB_EACH(kg::next_down(r.xa[i], r.out[i])))  \
    X(B, SUF, T, tp, next_down, op, R_OUT, kN, nullptr, KB_EACH(r.out[i] = kairn::next_down(r.xa[i]))) \
    X(B, SUF, T, tp, next_down, nextafter, R_OUT, kN, nullptr,                                     \
      KB_EACH(r.out[i] = std::nextafter(r.xa[i], -std::numeric_limits<T>::infinity())))            \
    X(B, SUF, T, tp, radd, kairn, R_OUT, kN, nullptr, KB_EACH(kg::radd(r.ua[i], r.fa[i], r.out[i]))) \
    X(B, SUF, T, tp, radd, op, R_OUT, kN, nullptr, KB_EACH(r.out[i] = kairn::radd(r.ua[i], r.fa[i]))) \
    X(B, SUF, T, tp, rmul, kairn, R_OUT, kN, nullptr, KB_EACH(kg::rmul(r.ua[i], r.fa[i], r.out[i]))) \
    X(B, SUF, T, tp, rmul, op, R_OUT, kN, nullptr, KB_EACH(r.out[i] = kairn::rmul(r.ua[i], r.fa[i]))) \
    X(B, SUF, T, tp, two_sum, kairn, R_OUT, 2 * kN, nullptr, KB_EACH(kg::two_sum(r.xa[i], r.ya[i], OUT2))) \
    X(B, SUF, T, tp, two_sum, op, R_SE, 2 * kN, nullptr, KB_EACH(d.zse[i] = kairn::two_sum(r.xa[i], r.ya[i]))) \
    X(B, SUF, T, tp, two_prod, kairn, R_OUT, 2 * kN, nullptr, KB_EACH(kg::two_prod(r.xa[i], r.ya[i], OUT2))) \
    X(B, SUF, T, tp, two_prod, op, R_PE, 2 * kN, nullptr, KB_EACH(d.zpe[i] = kairn::two_prod(r.xa[i], r.ya[i]))) \
    X(B, SUF, T, tp, add, kairn, R_OUT, kN, nullptr, KB_EACH(kg::add_1_1(r.xa[i], r.ya[i], r.out[i]))) \
    X(B, SUF, T, tp, add, plain, R_OUT, kN, nullptr, KB_EACH(r.out[i] = r.xa[i] + r.ya[i]))         \
    X(B, SUF, T, tp, sub, kairn, R_OUT, kN, nullptr, KB_EACH(kg::sub_1_1(r.xa[i], r.ya[i], r.out[i]))) \
    X(B, SUF, T, tp, sub, plain, R_OUT, kN, nullptr, KB_EACH(r.out[i] = r.xa[i] - r.ya[i]))         \
    X(B, SUF, T, tp, mul, kairn, R_OUT, kN, nullptr, KB_EACH(kg::mul_1_1(r.xa[i], r.ya[i], r.out[i]))) \
    X(B, SUF, T, tp, mul, plain, R_OUT, kN, nullptr, KB_EACH(r.out[i] = r.xa[i] * r.ya[i]))         \
    /* 1. Building blocks: chains */                                                               \
    X(B, SUF, T, sum, add_down, kairn, R_COUT, 1, nullptr, T s = 0; KB_EACH(kg::add_down_1(s, r.xa[i], s)) r.cout[0] = s;) \
    X(B, SUF, T, sum, add_down, op, R_COUT, 1, nullptr, T s = 0; KB_EACH(s = kairn::add_down(s, r.xa[i])) r.cout[0] = s;) \
    X(B, SUF, T, sum, add_up, kairn, R_COUT, 1, nullptr, T s = 0; KB_EACH(kg::add_up_1(s, r.xa[i], s)) r.cout[0] = s;) \
    X(B, SUF, T, sum, add_up, op, R_COUT, 1, nullptr, T s = 0; KB_EACH(s = kairn::add_up(s, r.xa[i])) r.cout[0] = s;) \
    X(B, SUF, T, prod, mul_down, kairn, R_COUT, 1, nullptr, T p = 1; KB_EACH(kg::mul_down_1(p, r.fa[i], p)) r.cout[0] = p;) \
    X(B, SUF, T, prod, mul_down, op, R_COUT, 1, nullptr, T p = 1; KB_EACH(p = kairn::mul_down(p, r.fa[i])) r.cout[0] = p;) \
    X(B, SUF, T, prod, mul_up, kairn, R_COUT, 1, nullptr, T p = 1; KB_EACH(kg::mul_up_1(p, r.fa[i], p)) r.cout[0] = p;) \
    X(B, SUF, T, prod, mul_up, op, R_COUT, 1, nullptr, T p = 1; KB_EACH(p = kairn::mul_up(p, r.fa[i])) r.cout[0] = p;) \
    X(B, SUF, T, step, next_up, kairn, R_COUT, 1, nullptr, T s = r.xa[0]; KB_EACH(kg::next_up(s, s)) r.cout[0] = s;) \
    X(B, SUF, T, step, next_up, op, R_COUT, 1, nullptr, T s = r.xa[0]; KB_EACH(s = kairn::next_up(s)) r.cout[0] = s;) \
    X(B, SUF, T, step, next_up, nextafter, R_COUT, 1, nullptr, T s = r.xa[0];                      \
      KB_EACH(s = std::nextafter(s, std::numeric_limits<T>::infinity())) r.cout[0] = s;)            \
    X(B, SUF, T, sum, radd, kairn, R_COUT, 1, nullptr, T s = 0; KB_EACH(kg::radd(s, r.ua[i], s)) r.cout[0] = s;) \
    X(B, SUF, T, sum, radd, op, R_COUT, 1, nullptr, T s = 0; KB_EACH(s = kairn::radd(s, r.ua[i])) r.cout[0] = s;) \
    X(B, SUF, T, prod, rmul, kairn, R_COUT, 1, nullptr, T p = 1; KB_EACH(kg::rmul(p, r.fa[i], p)) r.cout[0] = p;) \
    X(B, SUF, T, prod, rmul, op, R_COUT, 1, nullptr, T p = 1; KB_EACH(p = kairn::rmul(p, r.fa[i])) r.cout[0] = p;) \
    X(B, SUF, T, sum, two_sum, kairn, R_COUT, 2, nullptr, T s = 0, c = 0;                          \
      KB_EACH(T e; kg::two_sum(s, r.xa[i], s, e); c = c + e) r.cout[0] = s; r.cout[1] = c;)         \
    X(B, SUF, T, sum, two_sum, op, R_COUT, 2, nullptr, T s = 0, c = 0;                             \
      KB_EACH(const auto q = kairn::two_sum(s, r.xa[i]); s = q.sum; c = c + q.error) r.cout[0] = s; r.cout[1] = c;) \
    X(B, SUF, T, prod, two_prod, kairn, R_COUT, 2, nullptr, T p = 1, c = 0;                        \
      KB_EACH(T e; kg::two_prod(p, r.fa[i], p, e); c = c + e) r.cout[0] = p; r.cout[1] = c;)        \
    X(B, SUF, T, prod, two_prod, op, R_COUT, 2, nullptr, T p = 1, c = 0;                           \
      KB_EACH(const auto q = kairn::two_prod(p, r.fa[i]); p = q.product; c = c + q.error) r.cout[0] = p; r.cout[1] = c;) \
    X(B, SUF, T, sum, add, kairn, R_COUT, 1, nullptr, T s = 0; KB_EACH(kg::add_1_1(s, r.xa[i], s)) r.cout[0] = s;) \
    X(B, SUF, T, sum, add, plain, R_COUT, 1, nullptr, T s = 0; KB_EACH(s = s + r.xa[i]) r.cout[0] = s;) \
    X(B, SUF, T, prod, mul, kairn, R_COUT, 1, nullptr, T p = 1; KB_EACH(kg::mul_1_1(p, r.fa[i], p)) r.cout[0] = p;) \
    X(B, SUF, T, prod, mul, plain, R_COUT, 1, nullptr, T p = 1; KB_EACH(p = p * r.fa[i]) r.cout[0] = p;) \
    /* 2. Interval<T, 1>: loops */                                                                 \
    X(B, SUF, T, tp, interval_add_1, kairn, R_OUT, 2 * kN, nullptr, KB_EACH(kg::interval_add_1(XL, XU, YL, YU, OUT2))) \
    X(B, SUF, T, tp, interval_add_1, op, R_I1, 2 * kN, nullptr, KB_EACH(d.zi1[i] = d.x1[i] + d.y1[i])) \
    X(B, SUF, T, tp, interval_sub_1, kairn, R_OUT, 2 * kN, nullptr, KB_EACH(kg::interval_sub_1(XL, XU, YL, YU, OUT2))) \
    X(B, SUF, T, tp, interval_sub_1, op, R_I1, 2 * kN, nullptr, KB_EACH(d.zi1[i] = d.x1[i] - d.y1[i])) \
    X(B, SUF, T, tp, interval_mul_1, kairn, R_OUT, 2 * kN, nullptr, KB_EACH(kg::interval_mul_1(XL, XU, YL, YU, OUT2))) \
    X(B, SUF, T, tp, interval_mul_1, op, R_I1, 2 * kN, nullptr, KB_EACH(d.zi1[i] = d.x1[i] * d.y1[i])) \
    X(B, SUF, T, tp, interval_neg_1, kairn, R_OUT, 2 * kN, nullptr, KB_EACH(kg::interval_neg_1(XL, XU, OUT2))) \
    X(B, SUF, T, tp, interval_neg_1, op, R_I1, 2 * kN, nullptr, KB_EACH(d.zi1[i] = -d.x1[i]))      \
    X(B, SUF, T, tp, interval_neg_1, plain, R_OUT, 2 * kN, nullptr, KB_EACH(r.out[2 * i] = -XU; r.out[2 * i + 1] = -XL)) \
    X(B, SUF, T, tp, interval_hull_1, kairn, R_OUT, 2 * kN, nullptr, KB_EACH(kg::interval_hull_1(XL, XU, WL, WU, OUT2))) \
    X(B, SUF, T, tp, interval_hull_1, op, R_I1, 2 * kN, nullptr, KB_EACH(d.zi1[i] = d.x1[i].hull(d.w1[i]))) \
    X(B, SUF, T, tp, interval_hull_1, plain, R_OUT, 2 * kN, nullptr,                               \
      KB_EACH(r.out[2 * i] = WL < XL ? WL : XL; r.out[2 * i + 1] = XU < WU ? WU : XU))               \
    X(B, SUF, T, tp, interval_intersection_1, kairn, R_OUT, 2 * kN, nullptr,                       \
      KB_EACH(kg::interval_intersection_1(XL, XU, WL, WU, OUT2)))                                  \
    X(B, SUF, T, tp, interval_intersection_1, op, R_I1, 2 * kN, nullptr, KB_EACH(d.zi1[i] = d.x1[i].intersection(d.w1[i]))) \
    X(B, SUF, T, tp, interval_intersection_1, plain, R_OUT, 2 * kN, nullptr,                       \
      KB_EACH(const T l = XL < WL ? WL : XL; const T h = WU < XU ? WU : XU; const bool e = h < l;   \
              r.out[2 * i] = e ? std::numeric_limits<T>::infinity() : l;                           \
              r.out[2 * i + 1] = e ? -std::numeric_limits<T>::infinity() : h))                     \
    X(B, SUF, T, tp, interval_midrad_1, kairn, R_OUT, 2 * kN, nullptr, KB_EACH(kg::interval_mid_rad_1(XL, XU, OUT2))) \
    X(B, SUF, T, tp, interval_midrad_1, op, R_OUT, 2 * kN, nullptr,                                \
      KB_EACH(r.out[2 * i] = d.x1[i].midpoint().limb[0]; r.out[2 * i + 1] = d.x1[i].radius()))     \
    X(B, SUF, T, tp, interval_split_1, kairn, R_OUT, 4 * kN, nullptr, KB_EACH(kg::interval_split_1(XL, XU, OUT4))) \
    X(B, SUF, T, tp, interval_split_1, op, R_SPLIT, 4 * kN, nullptr, KB_EACH(d.zsp[i] = d.x1[i].split())) \
    X(B, SUF, T, tp, interval_to_ball_1, kairn, R_OUT, 2 * kN, nullptr, KB_EACH(kg::interval_to_ball_1(XL, XU, OUT2))) \
    X(B, SUF, T, tp, interval_to_ball_1, op, R_B1, 2 * kN, nullptr, KB_EACH(d.zb1[i] = B1<T>(d.x1[i]))) \
    X(B, SUF, T, tp, ball_to_interval_1, kairn, R_OUT, 2 * kN, nullptr,                            \
      KB_EACH(kg::ball_to_interval_1(B1R(r.xb1), OUT2)))                                           \
    X(B, SUF, T, tp, ball_to_interval_1, op, R_I1, 2 * kN, nullptr, KB_EACH(d.zi1[i] = I1<T>(d.xb1[i]))) \
    X(B, SUF, T, tp, pair_add_1, kairn, R_OUT, 2 * kN, nullptr,                                    \
      KB_EACH(kg::add_1_1(XL, YL, r.out[2 * i]); kg::add_1_1(XU, YU, r.out[2 * i + 1])))           \
    X(B, SUF, T, tp, pair_add_1, plain, R_OUT, 2 * kN, nullptr, KB_EACH(r.out[2 * i] = XL + YL; r.out[2 * i + 1] = XU + YU)) \
    X(B, SUF, T, tp, pair_sub_1, kairn, R_OUT, 2 * kN, nullptr,                                    \
      KB_EACH(kg::sub_1_1(XL, YU, r.out[2 * i]); kg::sub_1_1(XU, YL, r.out[2 * i + 1])))           \
    X(B, SUF, T, tp, pair_sub_1, plain, R_OUT, 2 * kN, nullptr, KB_EACH(r.out[2 * i] = XL - YU; r.out[2 * i + 1] = XU - YL)) \
    X(B, SUF, T, tp, pair_mul_1, kairn, R_OUT, 2 * kN, nullptr,                                    \
      KB_EACH(kg::mul_1_1(XL, YL, r.out[2 * i]); kg::mul_1_1(XU, YU, r.out[2 * i + 1])))           \
    X(B, SUF, T, tp, pair_mul_1, plain, R_OUT, 2 * kN, nullptr, KB_EACH(r.out[2 * i] = XL * YL; r.out[2 * i + 1] = XU * YU)) \
    X(B, SUF, T, tp, plain4_mul_1, kairn, R_OUT, 2 * kN, nullptr, KB_EACH(k_plain4_mul_1(XL, XU, YL, YU, OUT2))) \
    X(B, SUF, T, tp, plain4_mul_1, plain, R_OUT, 2 * kN, nullptr, KB_EACH(p_plain4_mul_1(XL, XU, YL, YU, OUT2))) \
    X(B, SUF, T, tp, plain_midrad_1, kairn, R_OUT, 2 * kN, nullptr,                                \
      KB_EACH(T s, e; kg::add_1_1(XL, XU, s); kg::mul_1_1(s, T(0.5), r.out[2 * i]); kg::sub_1_1(XU, XL, e); \
              kg::mul_1_1(e, T(0.5), r.out[2 * i + 1])))                                           \
    X(B, SUF, T, tp, plain_midrad_1, plain, R_OUT, 2 * kN, nullptr,                                \
      KB_EACH(r.out[2 * i] = (XL + XU) * T(0.5); r.out[2 * i + 1] = (XU - XL) * T(0.5)))            \
    X(B, SUF, T, tp, plain_bounds_1, kairn, R_OUT, 2 * kN, nullptr,                                \
      KB_EACH(kg::sub_1_1(r.xb1[2 * i], r.xb1[2 * i + 1], r.out[2 * i]);                           \
              kg::add_1_1(r.xb1[2 * i], r.xb1[2 * i + 1], r.out[2 * i + 1])))                       \
    X(B, SUF, T, tp, plain_bounds_1, plain, R_OUT, 2 * kN, nullptr,                                \
      KB_EACH(r.out[2 * i] = r.xb1[2 * i] - r.xb1[2 * i + 1]; r.out[2 * i + 1] = r.xb1[2 * i] + r.xb1[2 * i + 1])) \
    X(B, SUF, T, tp, ball_add_1, kairn, R_OUT, 2 * kN, nullptr, KB_EACH(kg::ball_add_1_full(B1R(r.xb1), B1R(r.yb1), OUT2))) \
    X(B, SUF, T, tp, ball_add_1, op, R_B1, 2 * kN, nullptr, KB_EACH(d.zb1[i] = d.xb1[i] + d.yb1[i])) \
    X(B, SUF, T, tp, ball_sub_1, kairn, R_OUT, 2 * kN, nullptr, KB_EACH(kg::ball_sub_1_full(B1R(r.xb1), B1R(r.yb1), OUT2))) \
    X(B, SUF, T, tp, ball_sub_1, op, R_B1, 2 * kN, nullptr, KB_EACH(d.zb1[i] = d.xb1[i] - d.yb1[i])) \
    X(B, SUF, T, tp, ball_mul_1, kairn, R_OUT, 2 * kN, nullptr, KB_EACH(kg::ball_mul_1_full(B1R(r.xb1), B1R(r.yb1), OUT2))) \
    X(B, SUF, T, tp, ball_mul_1, op, R_B1, 2 * kN, nullptr, KB_EACH(d.zb1[i] = d.xb1[i] * d.yb1[i])) \
    /* 2. Interval<T, 1>: chains */                                                                \
    X(B, SUF, T, sum, interval_add_1, kairn, R_COUT, 2, nullptr, T sl = 0, su = 0;                 \
      KB_EACH(kg::interval_add_1(sl, su, XL, XU, sl, su)) r.cout[0] = sl; r.cout[1] = su;)          \
    X(B, SUF, T, sum, interval_add_1, op, R_CI1, 2, nullptr, I1<T> s; KB_EACH(s = s + d.x1[i]) d.ci1 = s;) \
    X(B, SUF, T, prod, interval_mul_1, kairn, R_COUT, 2, nullptr, T pl = 1, pu = 1;                \
      KB_EACH(kg::interval_mul_1(pl, pu, FL, FU, pl, pu)) r.cout[0] = pl; r.cout[1] = pu;)          \
    X(B, SUF, T, prod, interval_mul_1, op, R_CI1, 2, nullptr, I1<T> p(T(1)); KB_EACH(p = p * d.f1[i]) d.ci1 = p;) \
    X(B, SUF, T, sum, ball_add_1, kairn, R_COUT, 2, nullptr, T sc = 0, sr = 0;                     \
      KB_EACH(kg::ball_add_1_full(sc, sr, B1R(r.xb1), sc, sr)) r.cout[0] = sc; r.cout[1] = sr;)     \
    X(B, SUF, T, sum, ball_add_1, op, R_CB1, 2, nullptr, B1<T> s; KB_EACH(s = s + d.xb1[i]) d.cb1 = s;) \
    X(B, SUF, T, prod, ball_mul_1, kairn, R_COUT, 2, nullptr, T pc = 1, pr = 0;                    \
      KB_EACH(kg::ball_mul_1_full(pc, pr, B1R(r.fb1), pc, pr)) r.cout[0] = pc; r.cout[1] = pr;)     \
    X(B, SUF, T, prod, ball_mul_1, op, R_CB1, 2, nullptr, B1<T> p(T(1)); KB_EACH(p = p * d.fb1[i]) d.cb1 = p;) \
    X(B, SUF, T, sum, pair_add_1, kairn, R_COUT, 2, nullptr, T sl = 0, su = 0;                     \
      KB_EACH(kg::add_1_1(sl, XL, sl); kg::add_1_1(su, XU, su)) r.cout[0] = sl; r.cout[1] = su;)    \
    X(B, SUF, T, sum, pair_add_1, plain, R_COUT, 2, nullptr, T sl = 0, su = 0;                     \
      KB_EACH(sl = sl + XL; su = su + XU) r.cout[0] = sl; r.cout[1] = su;)                         \
    X(B, SUF, T, prod, pair_mul_1, kairn, R_COUT, 2, nullptr, T pl = 1, pu = 1;                    \
      KB_EACH(kg::mul_1_1(pl, FL, pl); kg::mul_1_1(pu, FU, pu)) r.cout[0] = pl; r.cout[1] = pu;)    \
    X(B, SUF, T, prod, pair_mul_1, plain, R_COUT, 2, nullptr, T pl = 1, pu = 1;                    \
      KB_EACH(pl = pl * FL; pu = pu * FU) r.cout[0] = pl; r.cout[1] = pu;)                         \
    X(B, SUF, T, prod, plain4_mul_1, kairn, R_COUT, 2, nullptr, T pl = 1, pu = 1;                  \
      KB_EACH(k_plain4_mul_1(pl, pu, FL, FU, pl, pu)) r.cout[0] = pl; r.cout[1] = pu;)              \
    X(B, SUF, T, prod, plain4_mul_1, plain, R_COUT, 2, nullptr, T pl = 1, pu = 1;                  \
      KB_EACH(p_plain4_mul_1(pl, pu, FL, FU, pl, pu)) r.cout[0] = pl; r.cout[1] = pu;)              \
    /* 3. Interval<T, 2>: loops */                                                                 \
    X(B, SUF, T, tp, interval_add_2, kairn, R_OUT, 4 * kN, nullptr, KB_EACH(kg::interval_add_2(X2(r.xi2), X2(r.yi2), OUT4))) \
    X(B, SUF, T, tp, interval_add_2, op, R_I2, 4 * kN, nullptr, KB_EACH(d.zi2[i] = d.x2[i] + d.y2[i])) \
    X(B, SUF, T, tp, interval_sub_2, kairn, R_OUT, 4 * kN, nullptr, KB_EACH(kg::interval_sub_2(X2(r.xi2), X2(r.yi2), OUT4))) \
    X(B, SUF, T, tp, interval_sub_2, op, R_I2, 4 * kN, nullptr, KB_EACH(d.zi2[i] = d.x2[i] - d.y2[i])) \
    X(B, SUF, T, tp, interval_mul_2, kairn, R_OUT, 4 * kN, nullptr, KB_EACH(kg::interval_mul_2(X2(r.xi2), X2(r.yi2), OUT4))) \
    X(B, SUF, T, tp, interval_mul_2, op, R_I2, 4 * kN, nullptr, KB_EACH(d.zi2[i] = d.x2[i] * d.y2[i])) \
    X(B, SUF, T, tp, interval_mul_2, flat, R_I2, 4 * kN, nullptr, KB_EACH(d.zi2[i] = d.x2[i] * d.y2[i])) \
    X(B, SUF, T, tp, call_8_4, kairn, R_OUT, 4 * kN, nullptr, KB_EACH(inline_8_4(X2(r.xi2), X2(r.yi2), OUT4))) \
    X(B, SUF, T, tp, call_8_4, plain, R_OUT, 4 * kN, nullptr, KB_EACH(kb_m2_call_8_4(X2(r.xi2), X2(r.yi2), OUT4))) \
    X(B, SUF, T, tp, interval_hull_2, kairn, R_OUT, 4 * kN, nullptr, KB_EACH(kg::interval_hull_2(X2(r.xi2), X2(r.wi2), OUT4))) \
    X(B, SUF, T, tp, interval_hull_2, op, R_I2, 4 * kN, nullptr, KB_EACH(d.zi2[i] = d.x2[i].hull(d.w2[i]))) \
    X(B, SUF, T, tp, interval_intersection_2, kairn, R_OUT, 4 * kN, nullptr,                       \
      KB_EACH(kg::interval_intersection_2(X2(r.xi2), X2(r.wi2), OUT4)))                            \
    X(B, SUF, T, tp, interval_intersection_2, op, R_I2, 4 * kN, nullptr, KB_EACH(d.zi2[i] = d.x2[i].intersection(d.w2[i]))) \
    X(B, SUF, T, tp, pair_add_2, kairn, R_OUT, 4 * kN, nullptr,                                    \
      KB_EACH(kg::add_2_2_full(r.xi2[4 * i], r.xi2[4 * i + 1], r.yi2[4 * i], r.yi2[4 * i + 1], r.out[4 * i], r.out[4 * i + 1]); \
              kg::add_2_2_full(r.xi2[4 * i + 2], r.xi2[4 * i + 3], r.yi2[4 * i + 2], r.yi2[4 * i + 3], r.out[4 * i + 2], r.out[4 * i + 3]))) \
    X(B, SUF, T, tp, pair_add_2, op, R_OUT, 4 * kN, nullptr,                                       \
      KB_EACH(const E2<T> l = d.x2[i].lower() + d.y2[i].lower(); const E2<T> h = d.x2[i].upper() + d.y2[i].upper(); \
              r.out[4 * i] = l.limb[0]; r.out[4 * i + 1] = l.limb[1]; r.out[4 * i + 2] = h.limb[0]; r.out[4 * i + 3] = h.limb[1])) \
    X(B, SUF, T, tp, pair_sub_2, kairn, R_OUT, 4 * kN, nullptr,                                    \
      KB_EACH(kg::sub_2_2_full(r.xi2[4 * i], r.xi2[4 * i + 1], r.yi2[4 * i + 2], r.yi2[4 * i + 3], r.out[4 * i], r.out[4 * i + 1]); \
              kg::sub_2_2_full(r.xi2[4 * i + 2], r.xi2[4 * i + 3], r.yi2[4 * i], r.yi2[4 * i + 1], r.out[4 * i + 2], r.out[4 * i + 3]))) \
    X(B, SUF, T, tp, pair_sub_2, op, R_OUT, 4 * kN, nullptr,                                       \
      KB_EACH(const E2<T> l = d.x2[i].lower() - d.y2[i].upper(); const E2<T> h = d.x2[i].upper() - d.y2[i].lower(); \
              r.out[4 * i] = l.limb[0]; r.out[4 * i + 1] = l.limb[1]; r.out[4 * i + 2] = h.limb[0]; r.out[4 * i + 3] = h.limb[1])) \
    X(B, SUF, T, tp, pair_mul_2, kairn, R_OUT, 4 * kN, nullptr,                                    \
      KB_EACH(kg::mul_2_2_full(r.xi2[4 * i], r.xi2[4 * i + 1], r.yi2[4 * i], r.yi2[4 * i + 1], r.out[4 * i], r.out[4 * i + 1]); \
              kg::mul_2_2_full(r.xi2[4 * i + 2], r.xi2[4 * i + 3], r.yi2[4 * i + 2], r.yi2[4 * i + 3], r.out[4 * i + 2], r.out[4 * i + 3]))) \
    X(B, SUF, T, tp, pair_mul_2, op, R_OUT, 4 * kN, nullptr,                                       \
      KB_EACH(const E2<T> l = d.x2[i].lower() * d.y2[i].lower(); const E2<T> h = d.x2[i].upper() * d.y2[i].upper(); \
              r.out[4 * i] = l.limb[0]; r.out[4 * i + 1] = l.limb[1]; r.out[4 * i + 2] = h.limb[0]; r.out[4 * i + 3] = h.limb[1])) \
    X(B, SUF, T, tp, plain4_mul_2, kairn, R_OUT, 4 * kN, nullptr, KB_EACH(k_plain4_mul_2(r.xi2 + 4 * i, r.yi2 + 4 * i, r.out + 4 * i))) \
    X(B, SUF, T, tp, plain4_mul_2, op, R_OUT, 4 * kN, nullptr, KB_EACH(o_plain4_mul_2(d.x2[i], d.y2[i], r.out + 4 * i))) \
    X(B, SUF, T, tp, ball_add_2, kairn, R_OUT, 3 * kN, nullptr, KB_EACH(kg::ball_add_2_full(B2R(r.xb2), B2R(r.yb2), OUT3))) \
    X(B, SUF, T, tp, ball_add_2, op, R_B2, 3 * kN, nullptr, KB_EACH(d.zb2[i] = d.xb2[i] + d.yb2[i])) \
    X(B, SUF, T, tp, ball_sub_2, kairn, R_OUT, 3 * kN, nullptr, KB_EACH(kg::ball_sub_2_full(B2R(r.xb2), B2R(r.yb2), OUT3))) \
    X(B, SUF, T, tp, ball_sub_2, op, R_B2, 3 * kN, nullptr, KB_EACH(d.zb2[i] = d.xb2[i] - d.yb2[i])) \
    X(B, SUF, T, tp, ball_mul_2, kairn, R_OUT, 3 * kN, nullptr, KB_EACH(kg::ball_mul_2_full(B2R(r.xb2), B2R(r.yb2), OUT3))) \
    X(B, SUF, T, tp, ball_mul_2, op, R_B2, 3 * kN, nullptr, KB_EACH(d.zb2[i] = d.xb2[i] * d.yb2[i])) \
    /* 3. Interval<T, 2>: chains */                                                                \
    X(B, SUF, T, sum, interval_add_2, kairn, R_COUT, 4, nullptr, T s[4] = {0, 0, 0, 0};            \
      KB_EACH(kg::interval_add_2(s[0], s[1], s[2], s[3], X2(r.xi2), s[0], s[1], s[2], s[3]))       \
      for (int k = 0; k < 4; ++k) r.cout[k] = s[k];)                                               \
    X(B, SUF, T, sum, interval_add_2, op, R_CI2, 4, nullptr, I2<T> s; KB_EACH(s = s + d.x2[i]) d.ci2 = s;) \
    X(B, SUF, T, prod, interval_mul_2, kairn, R_COUT, 4, nullptr, T p[4] = {1, 0, 1, 0};           \
      KB_EACH(kg::interval_mul_2(p[0], p[1], p[2], p[3], X2(r.fi2), p[0], p[1], p[2], p[3]))       \
      for (int k = 0; k < 4; ++k) r.cout[k] = p[k];)                                               \
    X(B, SUF, T, prod, interval_mul_2, op, R_CI2, 4, nullptr, I2<T> p(T(1)); KB_EACH(p = p * d.f2[i]) d.ci2 = p;) \
    X(B, SUF, T, prod, call_8_4, kairn, R_COUT, 4, nullptr, T p[4] = {1, 0, 1, 0};                 \
      KB_EACH(inline_8_4(p[0], p[1], p[2], p[3], X2(r.fi2), p[0], p[1], p[2], p[3]))               \
      for (int k = 0; k < 4; ++k) r.cout[k] = p[k];)                                               \
    X(B, SUF, T, prod, call_8_4, plain, R_COUT, 4, nullptr, T p[4] = {1, 0, 1, 0};                 \
      KB_EACH(kb_m2_call_8_4(p[0], p[1], p[2], p[3], X2(r.fi2), p[0], p[1], p[2], p[3]))           \
      for (int k = 0; k < 4; ++k) r.cout[k] = p[k];)                                               \
    X(B, SUF, T, prod, interval_mul_2, flat, R_CI2, 4, nullptr, I2<T> p(T(1)); KB_EACH(p = p * d.f2[i]) d.ci2 = p;) \
    X(B, SUF, T, sum, ball_add_2, kairn, R_COUT, 3, nullptr, T s[3] = {0, 0, 0};                   \
      KB_EACH(kg::ball_add_2_full(s[0], s[1], s[2], B2R(r.xb2), s[0], s[1], s[2])) for (int k = 0; k < 3; ++k) r.cout[k] = s[k];) \
    X(B, SUF, T, sum, ball_add_2, op, R_CB2, 3, nullptr, B2<T> s; KB_EACH(s = s + d.xb2[i]) d.cb2 = s;) \
    X(B, SUF, T, prod, ball_mul_2, kairn, R_COUT, 3, nullptr, T p[3] = {1, 0, 0};                  \
      KB_EACH(kg::ball_mul_2_full(p[0], p[1], p[2], B2R(r.fb2), p[0], p[1], p[2])) for (int k = 0; k < 3; ++k) r.cout[k] = p[k];) \
    X(B, SUF, T, prod, ball_mul_2, op, R_CB2, 3, nullptr, B2<T> p(T(1)); KB_EACH(p = p * d.fb2[i]) d.cb2 = p;) \
    X(B, SUF, T, sum, pair_add_2, kairn, R_COUT, 4, nullptr, T s[4] = {0, 0, 0, 0};                \
      KB_EACH(kg::add_2_2_full(s[0], s[1], r.xi2[4 * i], r.xi2[4 * i + 1], s[0], s[1]);            \
              kg::add_2_2_full(s[2], s[3], r.xi2[4 * i + 2], r.xi2[4 * i + 3], s[2], s[3]))         \
      for (int k = 0; k < 4; ++k) r.cout[k] = s[k];)                                               \
    X(B, SUF, T, sum, pair_add_2, op, R_COUT, 4, nullptr, E2<T> l, h;                              \
      KB_EACH(l = l + d.x2[i].lower(); h = h + d.x2[i].upper())                                    \
      r.cout[0] = l.limb[0]; r.cout[1] = l.limb[1]; r.cout[2] = h.limb[0]; r.cout[3] = h.limb[1];)  \
    X(B, SUF, T, prod, pair_mul_2, kairn, R_COUT, 4, nullptr, T p[4] = {1, 0, 1, 0};               \
      KB_EACH(kg::mul_2_2_full(p[0], p[1], r.fi2[4 * i], r.fi2[4 * i + 1], p[0], p[1]);            \
              kg::mul_2_2_full(p[2], p[3], r.fi2[4 * i + 2], r.fi2[4 * i + 3], p[2], p[3]))         \
      for (int k = 0; k < 4; ++k) r.cout[k] = p[k];)                                               \
    X(B, SUF, T, prod, pair_mul_2, op, R_COUT, 4, nullptr, E2<T> l(T(1)), h(T(1));                 \
      KB_EACH(l = l * d.f2[i].lower(); h = h * d.f2[i].upper())                                    \
      r.cout[0] = l.limb[0]; r.cout[1] = l.limb[1]; r.cout[2] = h.limb[0]; r.cout[3] = h.limb[1];)  \
    /* 4. Horner: loops of independent evaluations */                                              \
    X(B, SUF, T, tp, horner_i1, kairn, R_OUT, 2 * kN, nullptr,                                     \
      KB_EACH(k_horner_i1(r.hc, r.hi1[2 * i], r.hi1[2 * i + 1], OUT2)))                            \
    X(B, SUF, T, tp, horner_i1, op, R_I1, 2 * kN, nullptr, KB_EACH(d.zi1[i] = horner(d.hc1, d.hx1[i]))) \
    X(B, SUF, T, tp, horner_i2, kairn, R_OUT, 4 * kN, nullptr, KB_EACH(k_horner_i2(r.hc, r.hi2 + 4 * i, r.out + 4 * i))) \
    X(B, SUF, T, tp, horner_i2, op, R_I2, 4 * kN, nullptr, KB_EACH(d.zi2[i] = horner(d.hc2, d.hx2[i]))) \
    X(B, SUF, T, tp, horner_i2, flat, R_I2, 4 * kN, nullptr, KB_EACH(d.zi2[i] = horner(d.hc2, d.hx2[i]))) \
    X(B, SUF, T, tp, horner_b1, kairn, R_OUT, 2 * kN, nullptr,                                     \
      KB_EACH(k_horner_b1(r.hc, r.hb1[2 * i], r.hb1[2 * i + 1], OUT2)))                            \
    X(B, SUF, T, tp, horner_b1, op, R_B1, 2 * kN, nullptr, KB_EACH(d.zb1[i] = horner(d.hcb1, d.hxb1[i]))) \
    X(B, SUF, T, tp, horner_b2, kairn, R_OUT, 3 * kN, nullptr, KB_EACH(k_horner_b2(r.hc, r.hb2 + 3 * i, r.out + 3 * i))) \
    X(B, SUF, T, tp, horner_b2, op, R_B2, 3 * kN, nullptr, KB_EACH(d.zb2[i] = horner(d.hcb2, d.hxb2[i]))) \
    X(B, SUF, T, tp, horner_e2, kairn, R_OUT, 2 * kN, nullptr, KB_EACH(k_horner_e2(r.hc, r.he2 + 2 * i, r.out + 2 * i))) \
    X(B, SUF, T, tp, horner_e2, op, R_E2, 2 * kN, nullptr, KB_EACH(d.ze2[i] = horner(d.hce2, d.hxe2[i]))) \
    X(B, SUF, T, tp, horner_t, kairn, R_OUT, kN, nullptr, KB_EACH(r.out[i] = k_horner_t(r.hc, r.ht[i]))) \
    X(B, SUF, T, tp, horner_t, plain, R_OUT, kN, nullptr, KB_EACH(r.out[i] = p_horner_t(r.hc, r.ht[i]))) \
    /* 4. Horner: dependent evaluations (z, a zero, carries the dependency) */                    \
    X(B, SUF, T, lat, horner_i1, kairn, R_COUT, 2, nullptr, T z = 0, pl = 0, pu = 0;               \
      KB_EACH(k_horner_i1(r.hc, r.hi1[2 * i] + z, r.hi1[2 * i + 1] + z, pl, pu); z = pl * T(0))      \
      r.cout[0] = pl; r.cout[1] = pu;)                                                             \
    X(B, SUF, T, lat, horner_i1, op, R_CI1, 2, nullptr, T z = 0; I1<T> p;                          \
      KB_EACH(p = horner(d.hc1, arg_i1(d.hx1[i], z)); z = p.lower().limb[0] * T(0)) d.ci1 = p;)     \
    X(B, SUF, T, lat, horner_i2, kairn, R_COUT, 4, nullptr, T z = 0, p[4] = {0, 0, 0, 0};          \
      KB_EACH(T a[4] = {r.hi2[4 * i] + z, r.hi2[4 * i + 1], r.hi2[4 * i + 2] + z, r.hi2[4 * i + 3]}; \
              k_horner_i2(r.hc, a, p); z = p[0] * T(0)) for (int k = 0; k < 4; ++k) r.cout[k] = p[k];) \
    X(B, SUF, T, lat, horner_i2, op, R_CI2, 4, nullptr, T z = 0; I2<T> p;                          \
      KB_EACH(p = horner(d.hc2, arg_i2(d.hx2[i], z)); z = p.lower().limb[0] * T(0)) d.ci2 = p;)     \
    X(B, SUF, T, lat, horner_i2, flat, R_CI2, 4, nullptr, T z = 0; I2<T> p;                        \
      KB_EACH(p = horner(d.hc2, arg_i2(d.hx2[i], z)); z = p.lower().limb[0] * T(0)) d.ci2 = p;)     \
    X(B, SUF, T, lat, horner_b1, kairn, R_COUT, 2, nullptr, T z = 0, pc = 0, pr = 0;               \
      KB_EACH(k_horner_b1(r.hc, r.hb1[2 * i] + z, r.hb1[2 * i + 1], pc, pr); z = pc * T(0))         \
      r.cout[0] = pc; r.cout[1] = pr;)                                                             \
    X(B, SUF, T, lat, horner_b1, op, R_CB1, 2, nullptr, T z = 0; B1<T> p;                          \
      KB_EACH(p = horner(d.hcb1, arg_b1(d.hxb1[i], z)); z = p.center().limb[0] * T(0)) d.cb1 = p;)  \
    X(B, SUF, T, lat, horner_b2, kairn, R_COUT, 3, nullptr, T z = 0, p[3] = {0, 0, 0};             \
      KB_EACH(T a[3] = {r.hb2[3 * i] + z, r.hb2[3 * i + 1], r.hb2[3 * i + 2]};                      \
              k_horner_b2(r.hc, a, p); z = p[0] * T(0)) for (int k = 0; k < 3; ++k) r.cout[k] = p[k];) \
    X(B, SUF, T, lat, horner_b2, op, R_CB2, 3, nullptr, T z = 0; B2<T> p;                          \
      KB_EACH(p = horner(d.hcb2, arg_b2(d.hxb2[i], z)); z = p.center().limb[0] * T(0)) d.cb2 = p;)  \
    X(B, SUF, T, lat, horner_e2, kairn, R_COUT, 2, nullptr, T z = 0, p[2] = {0, 0};                \
      KB_EACH(T a[2] = {r.he2[2 * i] + z, r.he2[2 * i + 1]}; k_horner_e2(r.hc, a, p); z = p[0] * T(0)) \
      r.cout[0] = p[0]; r.cout[1] = p[1];)                                                         \
    X(B, SUF, T, lat, horner_e2, op, R_CE2, 2, nullptr, T z = 0; E2<T> p;                          \
      KB_EACH(p = horner(d.hce2, arg_e2(d.hxe2[i], z)); z = p.limb[0] * T(0)) d.ce2 = p;)           \
    X(B, SUF, T, lat, horner_t, kairn, R_COUT, 1, nullptr, T z = 0, p = 0;                         \
      KB_EACH(p = k_horner_t(r.hc, r.ht[i] + z); z = p * T(0)) r.cout[0] = p;)                     \
    X(B, SUF, T, lat, horner_t, plain, R_COUT, 1, nullptr, T z = 0, p = 0;                         \
      KB_EACH(p = p_horner_t(r.hc, r.ht[i] + z); z = p * T(0)) r.cout[0] = p;)                     \
    /* 5. The additions to Ball */                                                                 \
    X(B, SUF, T, tp, ball_bounds_1, kairn, R_OUT, 2 * kN, nullptr,                                 \
      KB_EACH(kg::ball_lower_as_1(B1R(r.xb1), r.out[2 * i]); kg::ball_upper_as_1(B1R(r.xb1), r.out[2 * i + 1]))) \
    X(B, SUF, T, tp, ball_bounds_1, op, R_OUT, 2 * kN, nullptr,                                    \
      KB_EACH(r.out[2 * i] = d.xb1[i].template lower_as<T>(); r.out[2 * i + 1] = d.xb1[i].template upper_as<T>())) \
    X(B, SUF, T, tp, ball_bounds_2, kairn, R_OUT, 2 * kN, nullptr,                                 \
      KB_EACH(kg::ball_lower_as_2(B2R(r.xb2), r.out[2 * i]); kg::ball_upper_as_2(B2R(r.xb2), r.out[2 * i + 1]))) \
    X(B, SUF, T, tp, ball_bounds_2, op, R_OUT, 2 * kN, nullptr,                                    \
      KB_EACH(r.out[2 * i] = d.xb2[i].template lower_as<T>(); r.out[2 * i + 1] = d.xb2[i].template upper_as<T>())) \
    X(B, SUF, T, tp, plain_bounds_2, kairn, R_OUT, 2 * kN, nullptr,                                \
      KB_EACH(kg::sub_1_1(r.xb2[3 * i], r.xb2[3 * i + 2], r.out[2 * i]);                           \
              kg::add_1_1(r.xb2[3 * i], r.xb2[3 * i + 2], r.out[2 * i + 1])))                       \
    X(B, SUF, T, tp, plain_bounds_2, plain, R_OUT, 2 * kN, nullptr,                                \
      KB_EACH(r.out[2 * i] = r.xb2[3 * i] - r.xb2[3 * i + 2]; r.out[2 * i + 1] = r.xb2[3 * i] + r.xb2[3 * i + 2])) \
    X(B, SUF, T, tp, ball_from_interval_2, kairn, R_OUT, 3 * kN, nullptr, KB_EACH(kg::ball_from_interval_2(XL, XU, OUT3))) \
    X(B, SUF, T, tp, ball_from_interval_2, op, R_B2, 3 * kN, nullptr, KB_EACH(d.zb2[i] = B2<T>::from_interval(XL, XU))) \
    X(B, SUF, T, tp, ball_narrow_2_1, kairn, R_OUT, 2 * kN, nullptr, KB_EACH(kg::ball_narrow_2_1(B2R(r.xb2), OUT2))) \
    X(B, SUF, T, tp, ball_narrow_2_1, op, R_B1, 2 * kN, nullptr, KB_EACH(d.zb1[i] = B1<T>(d.xb2[i]))) \
    X(B, SUF, T, tp, plain_narrow_2_1, kairn, R_OUT, 2 * kN, nullptr,                              \
      KB_EACH(r.out[2 * i] = r.xb2[3 * i]; kg::add_1_1(r.xb2[3 * i + 2], std::fabs(r.xb2[3 * i + 1]), r.out[2 * i + 1]))) \
    X(B, SUF, T, tp, plain_narrow_2_1, plain, R_OUT, 2 * kN, nullptr,                              \
      KB_EACH(r.out[2 * i] = r.xb2[3 * i]; r.out[2 * i + 1] = r.xb2[3 * i + 2] + std::fabs(r.xb2[3 * i + 1]))) \
    X(B, SUF, T, tp, ball_half_1, kairn, R_OUT, 2 * kN, nullptr, KB_EACH(kg::ball_mul_pow2_1_full(B1R(r.xb1), T(0.5), OUT2))) \
    X(B, SUF, T, tp, ball_half_1, op, R_B1, 2 * kN, nullptr, KB_EACH(d.zb1[i] = kairn::half(d.xb1[i]))) \
    X(B, SUF, T, tp, ball_half_2, kairn, R_OUT, 3 * kN, nullptr, KB_EACH(kg::ball_mul_pow2_2_full(B2R(r.xb2), T(0.5), OUT3))) \
    X(B, SUF, T, tp, ball_half_2, op, R_B2, 3 * kN, nullptr, KB_EACH(d.zb2[i] = kairn::half(d.xb2[i]))) \
    X(B, SUF, T, tp, ball_scale_half_1, kairn, R_OUT, 2 * kN, nullptr, KB_EACH(kg::ball_scale_1_full(B1R(r.xb1), T(0.5), OUT2))) \
    X(B, SUF, T, tp, ball_scale_half_1, op, R_B1, 2 * kN, nullptr, KB_EACH(d.zb1[i] = d.xb1[i] * T(0.5))) \
    X(B, SUF, T, tp, ball_scale_half_2, kairn, R_OUT, 3 * kN, nullptr, KB_EACH(kg::ball_scale_2_full(B2R(r.xb2), T(0.5), OUT3))) \
    X(B, SUF, T, tp, ball_scale_half_2, op, R_B2, 3 * kN, nullptr, KB_EACH(d.zb2[i] = d.xb2[i] * T(0.5))) \
    X(B, SUF, T, tp, ball_ldexp_1, kairn, R_OUT, 2 * kN, nullptr, KB_EACH(kg::ball_mul_pow2_1_full(B1R(r.xb1), r.pa[i], OUT2))) \
    X(B, SUF, T, tp, ball_ldexp_1, op, R_B1, 2 * kN, nullptr, KB_EACH(d.zb1[i] = kairn::ldexp(d.xb1[i], r.na[i]))) \
    X(B, SUF, T, tp, ball_ldexp_2, kairn, R_OUT, 3 * kN, nullptr, KB_EACH(kg::ball_mul_pow2_2_full(B2R(r.xb2), r.pa[i], OUT3))) \
    X(B, SUF, T, tp, ball_ldexp_2, op, R_B2, 3 * kN, nullptr, KB_EACH(d.zb2[i] = kairn::ldexp(d.xb2[i], r.na[i]))) \
    X(B, SUF, T, tp, ball_scale_pow2_1, kairn, R_OUT, 2 * kN, nullptr, KB_EACH(kg::ball_scale_1_full(B1R(r.xb1), r.pa[i], OUT2))) \
    X(B, SUF, T, tp, ball_scale_pow2_1, op, R_B1, 2 * kN, nullptr, KB_EACH(d.zb1[i] = d.xb1[i] * r.pa[i])) \
    X(B, SUF, T, tp, ball_scale_pow2_2, kairn, R_OUT, 3 * kN, nullptr, KB_EACH(kg::ball_scale_2_full(B2R(r.xb2), r.pa[i], OUT3))) \
    X(B, SUF, T, tp, ball_scale_pow2_2, op, R_B2, 3 * kN, nullptr, KB_EACH(d.zb2[i] = d.xb2[i] * r.pa[i])) \
    X(B, SUF, T, prod, ball_ldexp_1, kairn, R_COUT, 2, nullptr, T pc = r.xb1[0], pr = r.xb1[1];    \
      KB_EACH(kg::ball_mul_pow2_1_full(pc, pr, r.sa[i], pc, pr)) r.cout[0] = pc; r.cout[1] = pr;)   \
    X(B, SUF, T, prod, ball_ldexp_1, op, R_CB1, 2, nullptr, B1<T> p = d.xb1[0];                    \
      KB_EACH(p = kairn::ldexp(p, r.sn[i])) d.cb1 = p;)                                            \
    X(B, SUF, T, prod, ball_ldexp_2, kairn, R_COUT, 3, nullptr, T p[3] = {r.xb2[0], r.xb2[1], r.xb2[2]}; \
      KB_EACH(kg::ball_mul_pow2_2_full(p[0], p[1], p[2], r.sa[i], p[0], p[1], p[2]))               \
      for (int k = 0; k < 3; ++k) r.cout[k] = p[k];)                                               \
    X(B, SUF, T, prod, ball_ldexp_2, op, R_CB2, 3, nullptr, B2<T> p = d.xb2[0];                    \
      KB_EACH(p = kairn::ldexp(p, r.sn[i])) d.cb2 = p;)                                            \
    X(B, SUF, T, prod, ball_scale_pow2_1, kairn, R_COUT, 2, nullptr, T pc = r.xb1[0], pr = r.xb1[1]; \
      KB_EACH(kg::ball_scale_1_full(pc, pr, r.sa[i], pc, pr)) r.cout[0] = pc; r.cout[1] = pr;)      \
    X(B, SUF, T, prod, ball_scale_pow2_1, op, R_CB1, 2, nullptr, B1<T> p = d.xb1[0];               \
      KB_EACH(p = p * r.sa[i]) d.cb1 = p;)                                                         \
    X(B, SUF, T, prod, ball_scale_pow2_2, kairn, R_COUT, 3, nullptr, T p[3] = {r.xb2[0], r.xb2[1], r.xb2[2]}; \
      KB_EACH(kg::ball_scale_2_full(p[0], p[1], p[2], r.sa[i], p[0], p[1], p[2]))                  \
      for (int k = 0; k < 3; ++k) r.cout[k] = p[k];)                                               \
    X(B, SUF, T, prod, ball_scale_pow2_2, op, R_CB2, 3, nullptr, B2<T> p = d.xb2[0];               \
      KB_EACH(p = p * r.sa[i]) d.cb2 = p;)                                                         \
    /* 6. kairn::rational */                                                                       \
    X(B, SUF, T, tp, rational_1_small, op, R_Q1, 0, &check_hook,                                   \
      KB_EACH(d.zq1[i] = kairn::rational<E1<T>>(r.qns[i], r.qds[i])))                              \
    X(B, SUF, T, tp, rational_1_large, op, R_Q1, 0, &check_hook,                                   \
      KB_EACH(d.zq1[i] = kairn::rational<E1<T>>(r.qnl[i], r.qdl[i])))                              \
    X(B, SUF, T, tp, rational_2_small, op, R_Q2, 0, &check_hook,                                   \
      KB_EACH(d.zq2[i] = kairn::rational<E2<T>>(r.qns[i], r.qds[i])))                              \
    X(B, SUF, T, tp, rational_2_large, op, R_Q2, 0, &check_hook,                                   \
      KB_EACH(d.zq2[i] = kairn::rational<E2<T>>(r.qnl[i], r.qdl[i])))                              \
    X(B, SUF, T, tp, rational_check_2_large, op, R_COUT, 0, &check_hook, int ok = 0;               \
      KB_EACH(ok += kairn::is_rational_result(d.pq2[i], r.qnl[i], r.qdl[i])) r.cout[0] = T(ok);)    \
    X(B, SUF, T, tp, divide_large, plain, R_OUT, 0, &check_hook, KB_EACH(r.out[i] = T(r.qnl[i]) / T(r.qdl[i])))

namespace {
bool check_hook(const Entry& e, char* why, std::size_t size);
}

// The generated scalar kernels on one array per limb, binary64 (backend m2s): the references of
// the packed code (m2_packed.cpp, m2_fenv_packed.cpp), and its scalar comparison.
#define SX(K) r.sxi[K][i]
#define SY(K) r.syi[K][i]
#define SX2(K) r.sxi2[K][i]
#define SY2(K) r.syi2[K][i]
#define SO(K) r.sout[K][i]
#define KB_SLIST(X, B, SUF, T)                                                                     \
    X(B, SUF, T, tp, add_down_1, kairn, R_SOUT, kN, nullptr, KB_EACH(kg::add_down_1(r.xa[i], r.ya[i], SO(0)))) \
    X(B, SUF, T, tp, add_up_1, kairn, R_SOUT, kN, nullptr, KB_EACH(kg::add_up_1(r.xa[i], r.ya[i], SO(0)))) \
    X(B, SUF, T, tp, mul_down_1, kairn, R_SOUT, kN, nullptr, KB_EACH(kg::mul_down_1(r.xa[i], r.ya[i], SO(0)))) \
    X(B, SUF, T, tp, mul_up_1, kairn, R_SOUT, kN, nullptr, KB_EACH(kg::mul_up_1(r.xa[i], r.ya[i], SO(0)))) \
    X(B, SUF, T, tp, next_up, kairn, R_SOUT, kN, nullptr, KB_EACH(kg::next_up(r.xa[i], SO(0))))   \
    X(B, SUF, T, tp, add, kairn, R_SOUT, kN, nullptr, KB_EACH(kg::add_1_1(r.xa[i], r.ya[i], SO(0)))) \
    X(B, SUF, T, tp, mul, kairn, R_SOUT, kN, nullptr, KB_EACH(kg::mul_1_1(r.xa[i], r.ya[i], SO(0)))) \
    X(B, SUF, T, tp, interval_add_1, kairn, R_SOUT, 2 * kN, nullptr,                               \
      KB_EACH(kg::interval_add_1(SX(0), SX(1), SY(0), SY(1), SO(0), SO(1))))                       \
    X(B, SUF, T, tp, interval_mul_1, kairn, R_SOUT, 2 * kN, nullptr,                               \
      KB_EACH(kg::interval_mul_1(SX(0), SX(1), SY(0), SY(1), SO(0), SO(1))))                       \
    X(B, SUF, T, tp, interval_add_2, kairn, R_SOUT, 4 * kN, nullptr,                               \
      KB_EACH(kg::interval_add_2(SX2(0), SX2(1), SX2(2), SX2(3), SY2(0), SY2(1), SY2(2), SY2(3), SO(0), SO(1), SO(2), SO(3)))) \
    X(B, SUF, T, tp, interval_mul_2, kairn, R_SOUT, 4 * kN, nullptr,                               \
      KB_EACH(kg::interval_mul_2(SX2(0), SX2(1), SX2(2), SX2(3), SY2(0), SY2(1), SY2(2), SY2(3), SO(0), SO(1), SO(2), SO(3)))) \
    X(B, SUF, T, tp, ball_add_1, kairn, R_SOUT, 2 * kN, nullptr,                                   \
      KB_EACH(kg::ball_add_1_full(r.sxb1[0][i], r.sxb1[1][i], r.syb1[0][i], r.syb1[1][i], SO(0), SO(1)))) \
    X(B, SUF, T, tp, ball_mul_1, kairn, R_SOUT, 2 * kN, nullptr,                                   \
      KB_EACH(kg::ball_mul_1_full(r.sxb1[0][i], r.sxb1[1][i], r.syb1[0][i], r.syb1[1][i], SO(0), SO(1)))) \
    X(B, SUF, T, tp, ball_add_2, kairn, R_SOUT, 3 * kN, nullptr,                                   \
      KB_EACH(kg::ball_add_2_full(r.sxb2[0][i], r.sxb2[1][i], r.sxb2[2][i], r.syb2[0][i], r.syb2[1][i], r.syb2[2][i], SO(0), SO(1), SO(2)))) \
    X(B, SUF, T, tp, ball_mul_2, kairn, R_SOUT, 3 * kN, nullptr,                                   \
      KB_EACH(kg::ball_mul_2_full(r.sxb2[0][i], r.sxb2[1][i], r.sxb2[2][i], r.syb2[0][i], r.syb2[1][i], r.syb2[2][i], SO(0), SO(1), SO(2))))

#define KB_DEF(B, SUF, T, KIND, KERNEL, VAR, REGION, VALUES, CHECK, ...)                           \
    extern "C" KB_NOINLINE KB_ATTR_##VAR void kb_m2_##SUF##_##KIND##_##KERNEL##__##VAR(void* kb_data) {  \
        [[maybe_unused]] Data<T>& d = *static_cast<Data<T>*>(kb_data);                                   \
        [[maybe_unused]] Raw<T>& r = d.raw;                                                        \
        __VA_ARGS__                                                                                \
    }
#define KB_ROW(B, SUF, T, KIND, KERNEL, VAR, REGION, VALUES, CHECK, ...)                           \
    {B "/" #KIND "/" #KERNEL "/" #VAR, kb_m2_##SUF##_##KIND##_##KERNEL##__##VAR, int(8 * sizeof(T)), 1, kN, REGION, VALUES, CHECK},

KB_LIST(KB_DEF, "m2", 64, double)
KB_LIST(KB_DEF, "m2f", 32, float)
KB_SLIST(KB_DEF, "m2s", s64, double)

namespace kairn_bench::m2 {

const Entry m2_entries[] = {
    KB_LIST(KB_ROW, "m2", 64, double)
    KB_LIST(KB_ROW, "m2f", 32, float)
    KB_SLIST(KB_ROW, "m2s", s64, double)
    {nullptr, nullptr, 0, 0, 0, 0, 0, nullptr},
};

void m2_setup(std::uint64_t seed) {
    if (!g64) g64 = new Data<double>();
    if (!g32) g32 = new Data<float>();
    fill(*g64, seed);
    fill(*g32, seed);
}

void* m2_data(int bits) { return bits == 32 ? static_cast<void*>(g32) : static_cast<void*>(g64); }

void m2_clear(int bits) {
    for (int k = 0; k < R_COUNT; ++k) {
        std::size_t n = 0;
        unsigned char* p = bits == 32 ? region_of(*g32, k, n) : region_of(*g64, k, n);
        if (p) std::memset(p, 0xff, n);
    }
}

const unsigned char* m2_region(int bits, int region, std::size_t* bytes) {
    return bits == 32 ? region_of(*g32, region, *bytes) : region_of(*g64, region, *bytes);
}

// The same directed results as m2_wide_fenv, from Kairn's building blocks, and rounded to nearest.
template <class T>
static void wide_kairn(int op, int n, const T* a, const T* b, T* out, T* rn) {
    for (int i = 0; i < n; ++i) {
        switch (op) {
            case 0: out[i] = kairn::add_down(a[i], b[i]); rn[i] = a[i] + b[i]; break;
            case 1: out[i] = kairn::add_up(a[i], b[i]); rn[i] = a[i] + b[i]; break;
            case 2: out[i] = kairn::sub_down(a[i], b[i]); rn[i] = a[i] - b[i]; break;
            case 3: out[i] = kairn::sub_up(a[i], b[i]); rn[i] = a[i] - b[i]; break;
            case 4: out[i] = kairn::mul_down(a[i], b[i]); rn[i] = a[i] * b[i]; break;
            default: out[i] = kairn::mul_up(a[i], b[i]); rn[i] = a[i] * b[i]; break;
        }
    }
}

void m2_wide_kairn(int bits, int op, int n, const void* a, const void* b, void* out, void* rn) {
    if (bits == 32)
        wide_kairn(op, n, static_cast<const float*>(a), static_cast<const float*>(b), static_cast<float*>(out),
                   static_cast<float*>(rn));
    else
        wide_kairn(op, n, static_cast<const double*>(a), static_cast<const double*>(b), static_cast<double*>(out),
                   static_cast<double*>(rn));
}

}  // namespace kairn_bench::m2

namespace {

// The entries checked otherwise than against a reference: kairn::rational by
// kairn::is_rational_result on every result; is_rational_result by every result being accepted; the
// plain division by its own recomputation.
template <class T>
bool check_rational(const Entry& e, char* why, std::size_t size) {
    Data<T>& d = data_of<T>();
    Raw<T>& r = d.raw;
    const std::string name = e.name;
    kairn_bench::m2::m2_clear(e.bits);
    e.fn(&d);
    const bool large = name.find("large") != std::string::npos;
    const long long* num = large ? r.qnl : r.qns;
    const long long* den = large ? r.qdl : r.qds;
    for (int i = 0; i < kN; ++i) {
        bool ok = true;
        if (name.find("rational_check") != std::string::npos) {
            ok = r.cout[0] == T(kN);
        } else if (name.find("divide") != std::string::npos) {
            ok = r.out[i] == T(num[i]) / T(den[i]);
        } else if (name.find("rational_1") != std::string::npos) {
            ok = kairn::is_rational_result(d.zq1[i], num[i], den[i]);
        } else {
            ok = kairn::is_rational_result(d.zq2[i], num[i], den[i]);
        }
        if (!ok) {
            std::snprintf(why, size, "element %d (%lld / %lld) refused", i, num[i], den[i]);
            return false;
        }
    }
    return true;
}

bool check_hook(const Entry& e, char* why, std::size_t size) {
    return e.bits == 32 ? check_rational<float>(e, why, size) : check_rational<double>(e, why, size);
}

// --- Tightness of the Horner evaluation ---------------------------------------------------------

using D2 = kairn::Expansion<double, 2>;

D2 d2_of(double h, double l) {
    const double limbs[2] = {h, l};
    return D2::from_limbs(limbs);
}
// T8 at x, in two-limb arithmetic: within a few units of 2^-104 of the sum of the magnitudes of its
// terms (at most 577 on [-1, 1]).
D2 t8(const D2& x) {
    D2 p(kT8[kDeg]);
    for (int k = kDeg - 1; k >= 0; --k) p = p * x + D2(kT8[k]);
    return p;
}
double to_d(const D2& x) { return x.limb[0] + x.limb[1]; }

struct Stat {
    std::vector<double> v;
    void add(double a) { v.push_back(a); }
    double q(double p) const { return kairn_bench::util::quantile(v, p); }
};

template <class T>
void tightness_of(std::string& out, bool& first) {
    using kairn_bench::util::num;
    struct Regime {
        const char* name;
        int rel;   // half-width relative to max(|x|, 1/16): 0 a point, -1 the wide sets (1/32 absolute)
    };
    // A point; a value known to a few units in its last place (2^-50 relative for double, 2^-21
    // for float); the narrow sets of the timed Horner evaluation; and wide sets, as a search has.
    const Regime regimes[4] = {{"point", 0}, {"ulp", sizeof(T) == 8 ? 50 : 21}, {"narrow", narrow_rel<T>()}, {"wide", -1}};
    I1<T> hc1[kDeg + 1];
    I2<T> hc2[kDeg + 1];
    B1<T> hcb1[kDeg + 1];
    B2<T> hcb2[kDeg + 1];
    T hc[kDeg + 1];
    for (int k = 0; k <= kDeg; ++k) {
        hc[k] = T(kT8[k]);
        hc1[k] = I1<T>(hc[k]);
        hc2[k] = I2<T>(hc[k]);
        hcb1[k] = B1<T>(hc[k]);
        hcb2[k] = B2<T>(hc[k]);
    }
    const double pi = 3.14159265358979323846;
    for (const Regime& reg : regimes) {
        Rng g{20261121};
        Stat ratio[4], width[4], range_width;
        Stat plain_error;
        int not_contained[4] = {0, 0, 0, 0};
        const char* names[4] = {"Interval<T, 1>", "Interval<T, 2>", "Ball<T, 1>", "Ball<T, 2>"};
        for (int i = 0; i < kN; ++i) {
            const T x = T(g.sym());
            const double v = g.u01();
            T lo = x, hi = x;
            if (reg.rel > 0) {
                const T w = T(std::max(std::fabs(double(x)), 0.0625) * std::ldexp(0.5 + 0.5 * v, -reg.rel));
                lo = x - w;
                hi = x + w;
            } else if (reg.rel < 0) {
                lo = std::max(T(-1), T(x - T(1.0 / 32)));
                hi = std::min(T(1), T(x + T(1.0 / 32)));
            }
            // The exact range: T8 at the bounds, and its extrema +-1 at cos(k pi / 8) inside.
            const D2 a = D2(double(lo)), b = D2(double(hi));
            D2 pa = t8(a), pb = t8(b);
            D2 mn = pa < pb ? pa : pb, mx = pa < pb ? pb : pa;
            for (int k = 1; k < 8; ++k) {
                const double c = std::cos(k * pi / 8);
                if (double(lo) < c && c < double(hi)) {
                    const D2 e((k & 1) ? -1.0 : 1.0);
                    if (e < mn) mn = e;
                    if (mx < e) mx = e;
                }
            }
            const double rw = to_d(mx - mn);
            const double scale = reg.rel == 0 ? std::fabs(to_d(pa)) : rw;
            range_width.add(rw);
            // The tolerance of the containment test: the error of the two-limb reference.
            const double tol = 0x1p-95 * 600;
            const I1<T> xi = I1<T>(E1<T>(lo), E1<T>(hi));
            const I2<T> xi2 = I2<T>(E2<T>(lo), E2<T>(hi));
            const B1<T> xb(xi);
            const B2<T> xb2 = B2<T>::from_interval(lo, hi);
            const I1<T> z1 = horner(hc1, xi);
            const I2<T> z2 = horner(hc2, xi2);
            const B1<T> zb = horner(hcb1, xb);
            const B2<T> zb2 = horner(hcb2, xb2);
            double lo_of[4], hi_of[4], w[4];
            lo_of[0] = double(z1.lower().limb[0]);
            hi_of[0] = double(z1.upper().limb[0]);
            w[0] = to_d(D2(double(z1.upper().limb[0])) - D2(double(z1.lower().limb[0])));
            const D2 l2 = d2_of(double(z2.lower().limb[0]), 0) + D2(double(z2.lower().limb[1]));
            const D2 h2 = d2_of(double(z2.upper().limb[0]), 0) + D2(double(z2.upper().limb[1]));
            lo_of[1] = to_d(l2);
            hi_of[1] = to_d(h2);
            w[1] = to_d(h2 - l2);
            const D2 cb = D2(double(zb.center().limb[0]));
            lo_of[2] = to_d(cb - D2(double(zb.radius())));
            hi_of[2] = to_d(cb + D2(double(zb.radius())));
            w[2] = 2.0 * double(zb.radius());
            const D2 cb2 = d2_of(double(zb2.center().limb[0]), 0) + D2(double(zb2.center().limb[1]));
            lo_of[3] = to_d(cb2 - D2(double(zb2.radius())));
            hi_of[3] = to_d(cb2 + D2(double(zb2.radius())));
            w[3] = 2.0 * double(zb2.radius());
            for (int t = 0; t < 4; ++t) {
                if (lo_of[t] > to_d(mn) + tol || hi_of[t] < to_d(mx) - tol) ++not_contained[t];
                width[t].add(w[t]);
                ratio[t].add(scale > 0 ? w[t] / scale : 0.0);
            }
            if (reg.rel == 0) plain_error.add(std::fabs(double(p_horner_t(hc, x)) - to_d(pa)) / scale);
        }
        for (int t = 0; t < 4; ++t) {
            std::string type = names[t];
            type.replace(type.find('T'), 1, sizeof(T) == 8 ? "double" : "float");
            out += std::string(first ? "" : ",\n") + "    {\"bits\": " + std::to_string(8 * sizeof(T)) +
                   ", \"regime\": \"" + reg.name + "\", \"type\": \"" + type + "\", \"arguments\": " +
                   std::to_string(kN) + ", \"not_contained\": " + std::to_string(not_contained[t]) +
                   ", \"ratio_min\": " + num(ratio[t].q(0)) + ", \"ratio_median\": " + num(ratio[t].q(0.5)) +
                   ", \"ratio_p90\": " + num(ratio[t].q(0.9)) + ", \"ratio_max\": " + num(ratio[t].q(1)) + ", \"width_median\": " + num(width[t].q(0.5)) +
                   ", \"range_width_median\": " + num(range_width.q(0.5)) +
                   (reg.rel == 0 ? ", \"ratio_of\": \"|p(x)|\", \"plain_error_median\": " + num(plain_error.q(0.5)) +
                                       ", \"plain_error_max\": " + num(plain_error.q(1))
                                 : std::string(", \"ratio_of\": \"the width of the exact range\"")) +
                   "}";
            first = false;
        }
    }
}

}  // namespace

namespace kairn_bench::m2 {

std::string m2_tightness_json() {
    std::string out = "[\n";
    bool first = true;
    tightness_of<double>(out, first);
    tightness_of<float>(out, first);
    out += "\n  ]";
    return out;
}

}  // namespace kairn_bench::m2
