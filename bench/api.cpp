// The timed functions of the public types: arrays of kairn::Expansion<T, 2>, kairn::Ball<T, 2> and
// kairn::Ball<T, 1>, as a client stores them (each number's limbs and radius next to each other),
// with T double (backend api) and float (backend apif). Variants:
//
// - op: the public operator (x + y, x * y, x + a, x * a, -x, kairn::add_fast; X + Y, X * Y, X * a,
//   -X), which calls the generated full kernel;
// - finite: kairn::finite::, which calls the generated core;
// - kairn: the generated core called on the limbs directly, the reference every other variant of
//   the kernel is checked against, bit for bit, on the benchmark inputs;
// - textbook: the JMP17 algorithm of props.hpp on the limbs, the baseline of the 1.2x budget;
// - limb: one operation of T, for the center of a Ball<T, 1>.
//
// Throughput loops z[i] = op(x[i], y[i]) over arrays in L1; chains as in bench.hpp (a running sum,
// a running product of factors near 1, a Horner evaluation). Built with the defaults a client gets
// (KAIRN_CHECKS is 0 under NDEBUG, the fix-up placement of kairn/gen/prelude.hpp).
#include <kairn/kairn.hpp>

#include <cmath>
#include <cstring>

#include "bench.hpp"
#include "props.hpp"

namespace {

namespace kg = kairn::gen;
namespace tb = kairn_bench::textbook;
using kairn::Ball;
using kairn::Expansion;

constexpr int kN = 256;

template <class T>
struct Data {
    using E2 = Expansion<T, 2>;
    using B2 = Ball<T, 2>;
    using B1 = Ball<T, 1>;
    int n = kN;
    // Operands: x, y (throughput, and x the summands of a chain), f (factors near 1), c (Horner
    // coefficients), h (Horner argument); the same numbers as two-limb numbers, as balls of two
    // limbs, as balls of one limb (the leading limb) and as one limb.
    E2 x[kN], y[kN], f[kN], c[kN];
    E2 h;
    B2 xb[kN], yb[kN], fb[kN], cb[kN];
    B2 hb;
    B1 xb1[kN], yb1[kN], fb1[kN], cb1[kN];
    B1 hb1;
    T xa[kN], ya[kN], fa[kN], ca[kN];
    T ha;
    // Outputs, from z on: api_clear and api_output use the bytes from z to the end.
    E2 z[kN];
    B2 zb[kN];
    B1 zb1[kN];
    T za[kN];
    E2 ze;
    B2 zbe;
    B1 zb1e;
    T zae;
};

Data<double>* g64 = nullptr;
Data<float>* g32 = nullptr;

struct Rng {
    std::uint64_t s;
    std::uint64_t next() {   // splitmix64, as in main.cpp
        std::uint64_t z = (s += 0x9e3779b97f4a7c15u);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9u;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebu;
        return z ^ (z >> 31);
    }
    double u01() { return double(next() >> 11) * 0x1p-53; }
    double sym() { return 2.0 * u01() - 1.0; }
    int range(int lo, int hi) { return lo + int(next() % std::uint64_t(hi - lo + 1)); }
    double sign() { return (next() & 1) ? -1.0 : 1.0; }
};

// A normalized pair of T with |h| in [2^kmin, 2^(kmax+1)) and |l| about u |h|, and a radius
// about 2^-rad |h|. One draw per statement, so that every compiler sees the same inputs.
template <class T>
struct Num {
    T h, l, r;
};
template <class T>
Num<T> number(Rng& g, int kmin, int kmax, int rad) {
    const double s = g.sign();
    const double m = 1.0 + g.u01();
    const T a = T(s * std::ldexp(m, g.range(kmin, kmax)));
    const double v = g.sym();
    const T b = T(double(a) * v * std::ldexp(1.0, -std::numeric_limits<T>::digits));
    T h, l;
    kg::fast_two_sum(a, b, h, l);
    const double w = 0.5 + 0.5 * g.u01();
    return {h, l, T(std::fabs(double(h)) * std::ldexp(w, -rad))};
}
template <class T>
Num<T> factor(Rng& g, int rad) {
    const T a = T(std::exp2(0.25 * g.sym()));
    const double v = g.sym();
    const T b = T(double(a) * v * std::ldexp(1.0, -std::numeric_limits<T>::digits));
    T h, l;
    kg::fast_two_sum(a, b, h, l);
    const double w = 0.5 + 0.5 * g.u01();
    return {h, l, T(double(h) * std::ldexp(w, -rad))};
}

template <class T>
void fill(Data<T>& d, std::uint64_t seed) {
    Rng g{seed};
    // Radii about 2^-80 of the centers for double, 2^-40 for float: far above the rounding error
    // of a two-limb center, far below the center.
    const int rad = sizeof(T) == 8 ? 80 : 40;
    auto set = [&](const Num<T>& v, Expansion<T, 2>& e, Ball<T, 2>& b, Ball<T, 1>& b1, T& a) {
        const T limbs[2] = {v.h, v.l};
        e = Expansion<T, 2>::from_limbs(limbs);
        b = Ball<T, 2>(e, v.r);
        b1 = Ball<T, 1>(Expansion<T, 1>(v.h), v.r);
        a = v.h;
    };
    for (int i = 0; i < kN; ++i) {
        set(number<T>(g, -8, 8, rad), d.x[i], d.xb[i], d.xb1[i], d.xa[i]);
        set(number<T>(g, -8, 8, rad), d.y[i], d.yb[i], d.yb1[i], d.ya[i]);
        set(factor<T>(g, rad), d.f[i], d.fb[i], d.fb1[i], d.fa[i]);
        set(number<T>(g, -2, 2, rad), d.c[i], d.cb[i], d.cb1[i], d.ca[i]);
    }
    const T hh = T(0.75 + 0.125 * g.u01());
    const double v = g.sym();
    Num<T> hv;
    kg::fast_two_sum(hh, T(double(hh) * v * std::ldexp(1.0, -std::numeric_limits<T>::digits)), hv.h, hv.l);
    hv.r = T(double(hv.h) * std::ldexp(1.0, -rad));
    set(hv, d.h, d.hb, d.hb1, d.ha);
}

template <class T>
unsigned char* out_begin(Data<T>& d) {
    return reinterpret_cast<unsigned char*>(&d.z);
}
template <class T>
std::size_t out_size(Data<T>& d) {
    return std::size_t(reinterpret_cast<unsigned char*>(&d + 1) - out_begin(d));
}

// --- The operations, by variant -----------------------------------------------------------------

// The generated cores on the limbs of the public types (variant kairn).
template <class T>
KAIRN_GEN_FORCEINLINE Expansion<T, 2> e2(T h, T l) {
    Expansion<T, 2> z;
    z.limb[0] = h;
    z.limb[1] = l;
    return z;
}
template <class T>
KAIRN_GEN_FORCEINLINE Expansion<T, 2> k_add(const Expansion<T, 2>& x, const Expansion<T, 2>& y) {
    T h, l;
    kg::add_2_2(x.limb[0], x.limb[1], y.limb[0], y.limb[1], h, l);
    return e2(h, l);
}
template <class T>
KAIRN_GEN_FORCEINLINE Expansion<T, 2> k_add_fast(const Expansion<T, 2>& x, const Expansion<T, 2>& y) {
    T h, l;
    kg::add_fast_2_2(x.limb[0], x.limb[1], y.limb[0], y.limb[1], h, l);
    return e2(h, l);
}
template <class T>
KAIRN_GEN_FORCEINLINE Expansion<T, 2> k_add(const Expansion<T, 2>& x, T a) {
    T h, l;
    kg::add_2_1(x.limb[0], x.limb[1], a, h, l);
    return e2(h, l);
}
template <class T>
KAIRN_GEN_FORCEINLINE Expansion<T, 2> k_mul(const Expansion<T, 2>& x, const Expansion<T, 2>& y) {
    T h, l;
    kg::mul_2_2(x.limb[0], x.limb[1], y.limb[0], y.limb[1], h, l);
    return e2(h, l);
}
template <class T>
KAIRN_GEN_FORCEINLINE Expansion<T, 2> k_mul(const Expansion<T, 2>& x, T a) {
    T h, l;
    kg::mul_2_1(x.limb[0], x.limb[1], a, h, l);
    return e2(h, l);
}
template <class T>
KAIRN_GEN_FORCEINLINE Expansion<T, 2> k_neg(const Expansion<T, 2>& x) {
    T h, l;
    kg::neg_2(x.limb[0], x.limb[1], h, l);
    return e2(h, l);
}

// Balls: the core's center and radius, through the constructor that keeps them as they are; the
// same one the public operators use for a kernel's result.
template <class T>
KAIRN_GEN_FORCEINLINE Ball<T, 2> b2(T c0, T c1, T r) {
    return Ball<T, 2>(kairn::detail::kernel_result, e2(c0, c1), r);
}
template <class T>
KAIRN_GEN_FORCEINLINE Ball<T, 1> b1(T c, T r) {
    return Ball<T, 1>(kairn::detail::kernel_result, Expansion<T, 1>(c), r);
}
template <class T>
KAIRN_GEN_FORCEINLINE Ball<T, 2> k_add(const Ball<T, 2>& x, const Ball<T, 2>& y) {
    T c0, c1, r;
    kg::ball_add_2(x.center().limb[0], x.center().limb[1], x.radius(), y.center().limb[0], y.center().limb[1], y.radius(),
                   c0, c1, r);
    return b2(c0, c1, r);
}
template <class T>
KAIRN_GEN_FORCEINLINE Ball<T, 2> k_mul(const Ball<T, 2>& x, const Ball<T, 2>& y) {
    T c0, c1, r;
    kg::ball_mul_2(x.center().limb[0], x.center().limb[1], x.radius(), y.center().limb[0], y.center().limb[1], y.radius(),
                   c0, c1, r);
    return b2(c0, c1, r);
}
template <class T>
KAIRN_GEN_FORCEINLINE Ball<T, 2> k_mul(const Ball<T, 2>& x, T a) {
    T c0, c1, r;
    kg::ball_scale_2(x.center().limb[0], x.center().limb[1], x.radius(), a, c0, c1, r);
    return b2(c0, c1, r);
}
template <class T>
KAIRN_GEN_FORCEINLINE Ball<T, 2> k_neg(const Ball<T, 2>& x) {
    T c0, c1, r;
    kg::ball_neg_2(x.center().limb[0], x.center().limb[1], x.radius(), c0, c1, r);
    return b2(c0, c1, r);
}
template <class T>
KAIRN_GEN_FORCEINLINE Ball<T, 1> k_add(const Ball<T, 1>& x, const Ball<T, 1>& y) {
    T c, r;
    kg::ball_add_1(x.center().limb[0], x.radius(), y.center().limb[0], y.radius(), c, r);
    return b1(c, r);
}
template <class T>
KAIRN_GEN_FORCEINLINE Ball<T, 1> k_mul(const Ball<T, 1>& x, const Ball<T, 1>& y) {
    T c, r;
    kg::ball_mul_1(x.center().limb[0], x.radius(), y.center().limb[0], y.radius(), c, r);
    return b1(c, r);
}
template <class T>
KAIRN_GEN_FORCEINLINE Ball<T, 1> k_mul(const Ball<T, 1>& x, T a) {
    T c, r;
    kg::ball_scale_1(x.center().limb[0], x.radius(), a, c, r);
    return b1(c, r);
}
template <class T>
KAIRN_GEN_FORCEINLINE Ball<T, 1> k_neg(const Ball<T, 1>& x) {
    T c, r;
    kg::ball_neg_1(x.center().limb[0], x.radius(), c, r);
    return b1(c, r);
}
template <class T>
KAIRN_GEN_FORCEINLINE T k_add(T a, T b) {
    T s;
    kg::add_1_1(a, b, s);
    return s;
}
template <class T>
KAIRN_GEN_FORCEINLINE T k_mul(T a, T b) {
    T p;
    kg::mul_1_1(a, b, p);
    return p;
}
template <class T>
KAIRN_GEN_FORCEINLINE T k_neg(T a) {
    return -a;
}

// The textbook algorithms on the limbs.
template <class T>
KAIRN_GEN_FORCEINLINE Expansion<T, 2> t_add(const Expansion<T, 2>& x, const Expansion<T, 2>& y) {
    T h, l;
    tb::accurate_dw_plus_dw(x.limb[0], x.limb[1], y.limb[0], y.limb[1], h, l);
    return e2(h, l);
}
template <class T>
KAIRN_GEN_FORCEINLINE Expansion<T, 2> t_add_fast(const Expansion<T, 2>& x, const Expansion<T, 2>& y) {
    T h, l;
    tb::sloppy_dw_plus_dw(x.limb[0], x.limb[1], y.limb[0], y.limb[1], h, l);
    return e2(h, l);
}
template <class T>
KAIRN_GEN_FORCEINLINE Expansion<T, 2> t_add(const Expansion<T, 2>& x, T a) {
    T h, l;
    tb::dw_plus_fp(x.limb[0], x.limb[1], a, h, l);
    return e2(h, l);
}
template <class T>
KAIRN_GEN_FORCEINLINE Expansion<T, 2> t_mul(const Expansion<T, 2>& x, const Expansion<T, 2>& y) {
    T h, l;
    tb::dw_times_dw3(x.limb[0], x.limb[1], y.limb[0], y.limb[1], h, l);
    return e2(h, l);
}
template <class T>
KAIRN_GEN_FORCEINLINE Expansion<T, 2> t_mul(const Expansion<T, 2>& x, T a) {
    T h, l;
    tb::dw_times_fp3(x.limb[0], x.limb[1], a, h, l);
    return e2(h, l);
}

// The public operations, written as a client writes them.
template <class X, class Y>
KAIRN_GEN_FORCEINLINE auto o_add(const X& x, const Y& y) {
    return x + y;
}
template <class X, class Y>
KAIRN_GEN_FORCEINLINE auto o_mul(const X& x, const Y& y) {
    return x * y;
}
template <class X>
KAIRN_GEN_FORCEINLINE auto o_neg(const X& x) {
    return -x;
}
template <class T>
KAIRN_GEN_FORCEINLINE Expansion<T, 2> o_add_fast(const Expansion<T, 2>& x, const Expansion<T, 2>& y) {
    return kairn::add_fast(x, y);
}
template <class X, class Y>
KAIRN_GEN_FORCEINLINE auto f_add(const X& x, const Y& y) {
    return kairn::finite::add(x, y);
}
template <class X, class Y>
KAIRN_GEN_FORCEINLINE auto f_mul(const X& x, const Y& y) {
    return kairn::finite::mul(x, y);
}
template <class T>
KAIRN_GEN_FORCEINLINE Expansion<T, 2> f_add_fast(const Expansion<T, 2>& x, const Expansion<T, 2>& y) {
    return kairn::finite::add_fast(x, y);
}
template <class T>
KAIRN_GEN_FORCEINLINE T l_add(T a, T b) {
    return a + b;
}
template <class T>
KAIRN_GEN_FORCEINLINE T l_mul(T a, T b) {
    return a * b;
}

}  // namespace

// --- The timed functions ------------------------------------------------------------------------

// Throughput: OUT[i] = FN(A[i], B[i]) or FN(A[i]); chains: S = FN(S, A[i]) from START, and Horner
// S = ADD(MUL(S, H), C[i]) from 0 with H of type HTYPE.
#define KB_A_TP2(NAME, T, OUT, FN, A, B)                                                           \
    extern "C" KB_NOINLINE void NAME(void* p) {                                                    \
        Data<T>& d = *static_cast<Data<T>*>(p);                                                    \
        const int n = d.n;                                                                         \
        for (int i = 0; i < n; ++i) d.OUT[i] = FN(d.A[i], d.B[i]);                                 \
    }
#define KB_A_TP1(NAME, T, OUT, FN, A)                                                              \
    extern "C" KB_NOINLINE void NAME(void* p) {                                                    \
        Data<T>& d = *static_cast<Data<T>*>(p);                                                    \
        const int n = d.n;                                                                         \
        for (int i = 0; i < n; ++i) d.OUT[i] = FN(d.A[i]);                                         \
    }
#define KB_A_CHAIN(NAME, T, OUT, TYPE, START, FN, A)                                               \
    extern "C" KB_NOINLINE void NAME(void* p) {                                                    \
        Data<T>& d = *static_cast<Data<T>*>(p);                                                    \
        const int n = d.n;                                                                         \
        TYPE s = START;                                                                            \
        for (int i = 0; i < n; ++i) s = FN(s, d.A[i]);                                             \
        d.OUT = s;                                                                                 \
    }
#define KB_A_HORNER(NAME, T, OUT, TYPE, HTYPE, MUL, ADD, H, C)                                     \
    extern "C" KB_NOINLINE void NAME(void* p) {                                                    \
        Data<T>& d = *static_cast<Data<T>*>(p);                                                    \
        const int n = d.n;                                                                         \
        const HTYPE h = d.H;                                                                       \
        TYPE s{};                                                                                  \
        for (int i = 0; i < n; ++i) s = ADD(MUL(s, h), d.C[i]);                                    \
        d.OUT = s;                                                                                 \
    }

// Every function of one limb type: SUF is the suffix of the C names, T the limb type.
#define KB_A_ALL(SUF, T)                                                                           \
    KB_A_TP2(kb_a##SUF##_tp_add_2_2__kairn, T, z, k_add<T>, x, y)                                  \
    KB_A_TP2(kb_a##SUF##_tp_add_2_2__op, T, z, o_add, x, y)                                        \
    KB_A_TP2(kb_a##SUF##_tp_add_2_2__finite, T, z, f_add, x, y)                                    \
    KB_A_TP2(kb_a##SUF##_tp_add_2_2__textbook, T, z, t_add<T>, x, y)                               \
    KB_A_TP2(kb_a##SUF##_tp_add_fast_2_2__kairn, T, z, k_add_fast<T>, x, y)                        \
    KB_A_TP2(kb_a##SUF##_tp_add_fast_2_2__op, T, z, o_add_fast<T>, x, y)                           \
    KB_A_TP2(kb_a##SUF##_tp_add_fast_2_2__finite, T, z, f_add_fast<T>, x, y)                       \
    KB_A_TP2(kb_a##SUF##_tp_add_fast_2_2__textbook, T, z, t_add_fast<T>, x, y)                     \
    KB_A_TP2(kb_a##SUF##_tp_add_2_1__kairn, T, z, k_add<T>, x, ya)                                 \
    KB_A_TP2(kb_a##SUF##_tp_add_2_1__op, T, z, o_add, x, ya)                                       \
    KB_A_TP2(kb_a##SUF##_tp_add_2_1__finite, T, z, f_add, x, ya)                                   \
    KB_A_TP2(kb_a##SUF##_tp_add_2_1__textbook, T, z, t_add<T>, x, ya)                              \
    KB_A_TP2(kb_a##SUF##_tp_mul_2_2__kairn, T, z, k_mul<T>, x, y)                                  \
    KB_A_TP2(kb_a##SUF##_tp_mul_2_2__op, T, z, o_mul, x, y)                                        \
    KB_A_TP2(kb_a##SUF##_tp_mul_2_2__finite, T, z, f_mul, x, y)                                    \
    KB_A_TP2(kb_a##SUF##_tp_mul_2_2__textbook, T, z, t_mul<T>, x, y)                               \
    KB_A_TP2(kb_a##SUF##_tp_mul_2_1__kairn, T, z, k_mul<T>, x, ya)                                 \
    KB_A_TP2(kb_a##SUF##_tp_mul_2_1__op, T, z, o_mul, x, ya)                                       \
    KB_A_TP2(kb_a##SUF##_tp_mul_2_1__finite, T, z, f_mul, x, ya)                                   \
    KB_A_TP2(kb_a##SUF##_tp_mul_2_1__textbook, T, z, t_mul<T>, x, ya)                              \
    KB_A_TP1(kb_a##SUF##_tp_neg_2__kairn, T, z, k_neg<T>, x)                                       \
    KB_A_TP1(kb_a##SUF##_tp_neg_2__op, T, z, o_neg, x)                                             \
    KB_A_TP2(kb_a##SUF##_tp_ball_add_2__kairn, T, zb, k_add<T>, xb, yb)                            \
    KB_A_TP2(kb_a##SUF##_tp_ball_add_2__op, T, zb, o_add, xb, yb)                                  \
    KB_A_TP2(kb_a##SUF##_tp_ball_mul_2__kairn, T, zb, k_mul<T>, xb, yb)                            \
    KB_A_TP2(kb_a##SUF##_tp_ball_mul_2__op, T, zb, o_mul, xb, yb)                                  \
    KB_A_TP2(kb_a##SUF##_tp_ball_scale_2__kairn, T, zb, k_mul<T>, xb, ya)                          \
    KB_A_TP2(kb_a##SUF##_tp_ball_scale_2__op, T, zb, o_mul, xb, ya)                                \
    KB_A_TP1(kb_a##SUF##_tp_ball_neg_2__kairn, T, zb, k_neg<T>, xb)                                \
    KB_A_TP1(kb_a##SUF##_tp_ball_neg_2__op, T, zb, o_neg, xb)                                      \
    KB_A_TP2(kb_a##SUF##_tp_ball_add_1__kairn, T, zb1, k_add<T>, xb1, yb1)                         \
    KB_A_TP2(kb_a##SUF##_tp_ball_add_1__op, T, zb1, o_add, xb1, yb1)                               \
    KB_A_TP2(kb_a##SUF##_tp_ball_mul_1__kairn, T, zb1, k_mul<T>, xb1, yb1)                         \
    KB_A_TP2(kb_a##SUF##_tp_ball_mul_1__op, T, zb1, o_mul, xb1, yb1)                               \
    KB_A_TP2(kb_a##SUF##_tp_ball_scale_1__kairn, T, zb1, k_mul<T>, xb1, ya)                        \
    KB_A_TP2(kb_a##SUF##_tp_ball_scale_1__op, T, zb1, o_mul, xb1, ya)                              \
    KB_A_TP1(kb_a##SUF##_tp_ball_neg_1__kairn, T, zb1, k_neg<T>, xb1)                              \
    KB_A_TP1(kb_a##SUF##_tp_ball_neg_1__op, T, zb1, o_neg, xb1)                                    \
    KB_A_TP2(kb_a##SUF##_tp_add_1_1__kairn, T, za, k_add<T>, xa, ya)                               \
    KB_A_TP2(kb_a##SUF##_tp_add_1_1__limb, T, za, l_add<T>, xa, ya)                                \
    KB_A_TP2(kb_a##SUF##_tp_mul_1_1__kairn, T, za, k_mul<T>, xa, ya)                               \
    KB_A_TP2(kb_a##SUF##_tp_mul_1_1__limb, T, za, l_mul<T>, xa, ya)                                \
    KB_A_TP1(kb_a##SUF##_tp_neg_1__kairn, T, za, k_neg<T>, xa)                                     \
                                                                                                   \
    KB_A_CHAIN(kb_a##SUF##_sum_add_2_2__kairn, T, ze, Expansion<T KB_COMMA 2>, {}, k_add<T>, x)    \
    KB_A_CHAIN(kb_a##SUF##_sum_add_2_2__op, T, ze, Expansion<T KB_COMMA 2>, {}, o_add, x)          \
    KB_A_CHAIN(kb_a##SUF##_sum_add_2_2__finite, T, ze, Expansion<T KB_COMMA 2>, {}, f_add, x)      \
    KB_A_CHAIN(kb_a##SUF##_sum_add_2_2__textbook, T, ze, Expansion<T KB_COMMA 2>, {}, t_add<T>, x) \
    KB_A_CHAIN(kb_a##SUF##_sum_add_fast_2_2__kairn, T, ze, Expansion<T KB_COMMA 2>, {}, k_add_fast<T>, x) \
    KB_A_CHAIN(kb_a##SUF##_sum_add_fast_2_2__op, T, ze, Expansion<T KB_COMMA 2>, {}, o_add_fast<T>, x) \
    KB_A_CHAIN(kb_a##SUF##_sum_add_fast_2_2__finite, T, ze, Expansion<T KB_COMMA 2>, {}, f_add_fast<T>, x) \
    KB_A_CHAIN(kb_a##SUF##_sum_add_fast_2_2__textbook, T, ze, Expansion<T KB_COMMA 2>, {}, t_add_fast<T>, x) \
    KB_A_CHAIN(kb_a##SUF##_sum_add_2_1__kairn, T, ze, Expansion<T KB_COMMA 2>, {}, k_add<T>, xa)   \
    KB_A_CHAIN(kb_a##SUF##_sum_add_2_1__op, T, ze, Expansion<T KB_COMMA 2>, {}, o_add, xa)         \
    KB_A_CHAIN(kb_a##SUF##_sum_add_2_1__finite, T, ze, Expansion<T KB_COMMA 2>, {}, f_add, xa)     \
    KB_A_CHAIN(kb_a##SUF##_sum_add_2_1__textbook, T, ze, Expansion<T KB_COMMA 2>, {}, t_add<T>, xa) \
    KB_A_CHAIN(kb_a##SUF##_sum_ball_add_2__kairn, T, zbe, Ball<T KB_COMMA 2>, {}, k_add<T>, xb)    \
    KB_A_CHAIN(kb_a##SUF##_sum_ball_add_2__op, T, zbe, Ball<T KB_COMMA 2>, {}, o_add, xb)          \
    KB_A_CHAIN(kb_a##SUF##_sum_ball_add_1__kairn, T, zb1e, Ball<T KB_COMMA 1>, {}, k_add<T>, xb1)  \
    KB_A_CHAIN(kb_a##SUF##_sum_ball_add_1__op, T, zb1e, Ball<T KB_COMMA 1>, {}, o_add, xb1)        \
    KB_A_CHAIN(kb_a##SUF##_sum_add_1_1__kairn, T, zae, T, T(0), k_add<T>, xa)                      \
    KB_A_CHAIN(kb_a##SUF##_sum_add_1_1__limb, T, zae, T, T(0), l_add<T>, xa)                       \
                                                                                                   \
    KB_A_CHAIN(kb_a##SUF##_prod_mul_2_2__kairn, T, ze, Expansion<T KB_COMMA 2>, d.h, k_mul<T>, f)  \
    KB_A_CHAIN(kb_a##SUF##_prod_mul_2_2__op, T, ze, Expansion<T KB_COMMA 2>, d.h, o_mul, f)        \
    KB_A_CHAIN(kb_a##SUF##_prod_mul_2_2__finite, T, ze, Expansion<T KB_COMMA 2>, d.h, f_mul, f)    \
    KB_A_CHAIN(kb_a##SUF##_prod_mul_2_2__textbook, T, ze, Expansion<T KB_COMMA 2>, d.h, t_mul<T>, f) \
    KB_A_CHAIN(kb_a##SUF##_prod_mul_2_1__kairn, T, ze, Expansion<T KB_COMMA 2>, d.h, k_mul<T>, fa) \
    KB_A_CHAIN(kb_a##SUF##_prod_mul_2_1__op, T, ze, Expansion<T KB_COMMA 2>, d.h, o_mul, fa)       \
    KB_A_CHAIN(kb_a##SUF##_prod_mul_2_1__finite, T, ze, Expansion<T KB_COMMA 2>, d.h, f_mul, fa)   \
    KB_A_CHAIN(kb_a##SUF##_prod_mul_2_1__textbook, T, ze, Expansion<T KB_COMMA 2>, d.h, t_mul<T>, fa) \
    KB_A_CHAIN(kb_a##SUF##_prod_ball_mul_2__kairn, T, zbe, Ball<T KB_COMMA 2>, d.hb, k_mul<T>, fb) \
    KB_A_CHAIN(kb_a##SUF##_prod_ball_mul_2__op, T, zbe, Ball<T KB_COMMA 2>, d.hb, o_mul, fb)       \
    KB_A_CHAIN(kb_a##SUF##_prod_ball_scale_2__kairn, T, zbe, Ball<T KB_COMMA 2>, d.hb, k_mul<T>, fa) \
    KB_A_CHAIN(kb_a##SUF##_prod_ball_scale_2__op, T, zbe, Ball<T KB_COMMA 2>, d.hb, o_mul, fa)     \
    KB_A_CHAIN(kb_a##SUF##_prod_ball_mul_1__kairn, T, zb1e, Ball<T KB_COMMA 1>, d.hb1, k_mul<T>, fb1) \
    KB_A_CHAIN(kb_a##SUF##_prod_ball_mul_1__op, T, zb1e, Ball<T KB_COMMA 1>, d.hb1, o_mul, fb1)    \
    KB_A_CHAIN(kb_a##SUF##_prod_ball_scale_1__kairn, T, zb1e, Ball<T KB_COMMA 1>, d.hb1, k_mul<T>, fa) \
    KB_A_CHAIN(kb_a##SUF##_prod_ball_scale_1__op, T, zb1e, Ball<T KB_COMMA 1>, d.hb1, o_mul, fa)   \
    KB_A_CHAIN(kb_a##SUF##_prod_mul_1_1__kairn, T, zae, T, d.ha, k_mul<T>, fa)                     \
    KB_A_CHAIN(kb_a##SUF##_prod_mul_1_1__limb, T, zae, T, d.ha, l_mul<T>, fa)                      \
                                                                                                   \
    KB_A_HORNER(kb_a##SUF##_horner_2__kairn, T, ze, Expansion<T KB_COMMA 2>, Expansion<T KB_COMMA 2>, k_mul<T>, k_add<T>, h, c) \
    KB_A_HORNER(kb_a##SUF##_horner_2__op, T, ze, Expansion<T KB_COMMA 2>, Expansion<T KB_COMMA 2>, o_mul, o_add, h, c)      \
    KB_A_HORNER(kb_a##SUF##_horner_2__finite, T, ze, Expansion<T KB_COMMA 2>, Expansion<T KB_COMMA 2>, f_mul, f_add, h, c)  \
    KB_A_HORNER(kb_a##SUF##_horner_2__textbook, T, ze, Expansion<T KB_COMMA 2>, Expansion<T KB_COMMA 2>, t_mul<T>, t_add<T>, h, c) \
    KB_A_HORNER(kb_a##SUF##_horner_21__kairn, T, ze, Expansion<T KB_COMMA 2>, T, k_mul<T>, k_add<T>, ha, ca) \
    KB_A_HORNER(kb_a##SUF##_horner_21__op, T, ze, Expansion<T KB_COMMA 2>, T, o_mul, o_add, ha, ca)   \
    KB_A_HORNER(kb_a##SUF##_horner_21__finite, T, ze, Expansion<T KB_COMMA 2>, T, f_mul, f_add, ha, ca) \
    KB_A_HORNER(kb_a##SUF##_horner_21__textbook, T, ze, Expansion<T KB_COMMA 2>, T, t_mul<T>, t_add<T>, ha, ca) \
    KB_A_HORNER(kb_a##SUF##_horner_ball_2__kairn, T, zbe, Ball<T KB_COMMA 2>, Ball<T KB_COMMA 2>, k_mul<T>, k_add<T>, hb, cb) \
    KB_A_HORNER(kb_a##SUF##_horner_ball_2__op, T, zbe, Ball<T KB_COMMA 2>, Ball<T KB_COMMA 2>, o_mul, o_add, hb, cb)   \
    KB_A_HORNER(kb_a##SUF##_horner_ball_1__kairn, T, zb1e, Ball<T KB_COMMA 1>, Ball<T KB_COMMA 1>, k_mul<T>, k_add<T>, hb1, cb1) \
    KB_A_HORNER(kb_a##SUF##_horner_ball_1__op, T, zb1e, Ball<T KB_COMMA 1>, Ball<T KB_COMMA 1>, o_mul, o_add, hb1, cb1) \
    KB_A_HORNER(kb_a##SUF##_horner_1__kairn, T, zae, T, T, k_mul<T>, k_add<T>, ha, ca)                \
    KB_A_HORNER(kb_a##SUF##_horner_1__limb, T, zae, T, T, l_mul<T>, l_add<T>, ha, ca)

#define KB_COMMA ,

KB_A_ALL(64, double)
KB_A_ALL(32, float)

// --- The table ----------------------------------------------------------------------------------

#define KB_E(B, BITS, SUF, KIND, KERNEL, CNAME, VARIANT)                                           \
    {B "/" KIND "/" KERNEL "/" #VARIANT, 1, nullptr, nullptr, kb_a##SUF##_##CNAME##__##VARIANT, BITS},

#define KB_A_TABLE(B, BITS, SUF)                                                                   \
    KB_E(B, BITS, SUF, "tp", "add_2_2", tp_add_2_2, kairn)                                         \
    KB_E(B, BITS, SUF, "tp", "add_2_2", tp_add_2_2, op)                                            \
    KB_E(B, BITS, SUF, "tp", "add_2_2", tp_add_2_2, finite)                                        \
    KB_E(B, BITS, SUF, "tp", "add_2_2", tp_add_2_2, textbook)                                      \
    KB_E(B, BITS, SUF, "tp", "add_fast_2_2", tp_add_fast_2_2, kairn)                               \
    KB_E(B, BITS, SUF, "tp", "add_fast_2_2", tp_add_fast_2_2, op)                                  \
    KB_E(B, BITS, SUF, "tp", "add_fast_2_2", tp_add_fast_2_2, finite)                              \
    KB_E(B, BITS, SUF, "tp", "add_fast_2_2", tp_add_fast_2_2, textbook)                            \
    KB_E(B, BITS, SUF, "tp", "add_2_1", tp_add_2_1, kairn)                                         \
    KB_E(B, BITS, SUF, "tp", "add_2_1", tp_add_2_1, op)                                            \
    KB_E(B, BITS, SUF, "tp", "add_2_1", tp_add_2_1, finite)                                        \
    KB_E(B, BITS, SUF, "tp", "add_2_1", tp_add_2_1, textbook)                                      \
    KB_E(B, BITS, SUF, "tp", "mul_2_2", tp_mul_2_2, kairn)                                         \
    KB_E(B, BITS, SUF, "tp", "mul_2_2", tp_mul_2_2, op)                                            \
    KB_E(B, BITS, SUF, "tp", "mul_2_2", tp_mul_2_2, finite)                                        \
    KB_E(B, BITS, SUF, "tp", "mul_2_2", tp_mul_2_2, textbook)                                      \
    KB_E(B, BITS, SUF, "tp", "mul_2_1", tp_mul_2_1, kairn)                                         \
    KB_E(B, BITS, SUF, "tp", "mul_2_1", tp_mul_2_1, op)                                            \
    KB_E(B, BITS, SUF, "tp", "mul_2_1", tp_mul_2_1, finite)                                        \
    KB_E(B, BITS, SUF, "tp", "mul_2_1", tp_mul_2_1, textbook)                                      \
    KB_E(B, BITS, SUF, "tp", "neg_2", tp_neg_2, kairn)                                             \
    KB_E(B, BITS, SUF, "tp", "neg_2", tp_neg_2, op)                                                \
    KB_E(B, BITS, SUF, "tp", "ball_add_2", tp_ball_add_2, kairn)                                   \
    KB_E(B, BITS, SUF, "tp", "ball_add_2", tp_ball_add_2, op)                                      \
    KB_E(B, BITS, SUF, "tp", "ball_mul_2", tp_ball_mul_2, kairn)                                   \
    KB_E(B, BITS, SUF, "tp", "ball_mul_2", tp_ball_mul_2, op)                                      \
    KB_E(B, BITS, SUF, "tp", "ball_scale_2", tp_ball_scale_2, kairn)                               \
    KB_E(B, BITS, SUF, "tp", "ball_scale_2", tp_ball_scale_2, op)                                  \
    KB_E(B, BITS, SUF, "tp", "ball_neg_2", tp_ball_neg_2, kairn)                                   \
    KB_E(B, BITS, SUF, "tp", "ball_neg_2", tp_ball_neg_2, op)                                      \
    KB_E(B, BITS, SUF, "tp", "ball_add_1", tp_ball_add_1, kairn)                                   \
    KB_E(B, BITS, SUF, "tp", "ball_add_1", tp_ball_add_1, op)                                      \
    KB_E(B, BITS, SUF, "tp", "ball_mul_1", tp_ball_mul_1, kairn)                                   \
    KB_E(B, BITS, SUF, "tp", "ball_mul_1", tp_ball_mul_1, op)                                      \
    KB_E(B, BITS, SUF, "tp", "ball_scale_1", tp_ball_scale_1, kairn)                               \
    KB_E(B, BITS, SUF, "tp", "ball_scale_1", tp_ball_scale_1, op)                                  \
    KB_E(B, BITS, SUF, "tp", "ball_neg_1", tp_ball_neg_1, kairn)                                   \
    KB_E(B, BITS, SUF, "tp", "ball_neg_1", tp_ball_neg_1, op)                                      \
    KB_E(B, BITS, SUF, "tp", "add_1_1", tp_add_1_1, kairn)                                         \
    KB_E(B, BITS, SUF, "tp", "add_1_1", tp_add_1_1, limb)                                          \
    KB_E(B, BITS, SUF, "tp", "mul_1_1", tp_mul_1_1, kairn)                                         \
    KB_E(B, BITS, SUF, "tp", "mul_1_1", tp_mul_1_1, limb)                                          \
    KB_E(B, BITS, SUF, "tp", "neg_1", tp_neg_1, kairn)                                             \
    KB_E(B, BITS, SUF, "sum", "add_2_2", sum_add_2_2, kairn)                                       \
    KB_E(B, BITS, SUF, "sum", "add_2_2", sum_add_2_2, op)                                          \
    KB_E(B, BITS, SUF, "sum", "add_2_2", sum_add_2_2, finite)                                      \
    KB_E(B, BITS, SUF, "sum", "add_2_2", sum_add_2_2, textbook)                                    \
    KB_E(B, BITS, SUF, "sum", "add_fast_2_2", sum_add_fast_2_2, kairn)                             \
    KB_E(B, BITS, SUF, "sum", "add_fast_2_2", sum_add_fast_2_2, op)                                \
    KB_E(B, BITS, SUF, "sum", "add_fast_2_2", sum_add_fast_2_2, finite)                            \
    KB_E(B, BITS, SUF, "sum", "add_fast_2_2", sum_add_fast_2_2, textbook)                          \
    KB_E(B, BITS, SUF, "sum", "add_2_1", sum_add_2_1, kairn)                                       \
    KB_E(B, BITS, SUF, "sum", "add_2_1", sum_add_2_1, op)                                          \
    KB_E(B, BITS, SUF, "sum", "add_2_1", sum_add_2_1, finite)                                      \
    KB_E(B, BITS, SUF, "sum", "add_2_1", sum_add_2_1, textbook)                                    \
    KB_E(B, BITS, SUF, "sum", "ball_add_2", sum_ball_add_2, kairn)                                 \
    KB_E(B, BITS, SUF, "sum", "ball_add_2", sum_ball_add_2, op)                                    \
    KB_E(B, BITS, SUF, "sum", "ball_add_1", sum_ball_add_1, kairn)                                 \
    KB_E(B, BITS, SUF, "sum", "ball_add_1", sum_ball_add_1, op)                                    \
    KB_E(B, BITS, SUF, "sum", "add_1_1", sum_add_1_1, kairn)                                       \
    KB_E(B, BITS, SUF, "sum", "add_1_1", sum_add_1_1, limb)                                        \
    KB_E(B, BITS, SUF, "prod", "mul_2_2", prod_mul_2_2, kairn)                                     \
    KB_E(B, BITS, SUF, "prod", "mul_2_2", prod_mul_2_2, op)                                        \
    KB_E(B, BITS, SUF, "prod", "mul_2_2", prod_mul_2_2, finite)                                    \
    KB_E(B, BITS, SUF, "prod", "mul_2_2", prod_mul_2_2, textbook)                                  \
    KB_E(B, BITS, SUF, "prod", "mul_2_1", prod_mul_2_1, kairn)                                     \
    KB_E(B, BITS, SUF, "prod", "mul_2_1", prod_mul_2_1, op)                                        \
    KB_E(B, BITS, SUF, "prod", "mul_2_1", prod_mul_2_1, finite)                                    \
    KB_E(B, BITS, SUF, "prod", "mul_2_1", prod_mul_2_1, textbook)                                  \
    KB_E(B, BITS, SUF, "prod", "ball_mul_2", prod_ball_mul_2, kairn)                               \
    KB_E(B, BITS, SUF, "prod", "ball_mul_2", prod_ball_mul_2, op)                                  \
    KB_E(B, BITS, SUF, "prod", "ball_scale_2", prod_ball_scale_2, kairn)                           \
    KB_E(B, BITS, SUF, "prod", "ball_scale_2", prod_ball_scale_2, op)                              \
    KB_E(B, BITS, SUF, "prod", "ball_mul_1", prod_ball_mul_1, kairn)                               \
    KB_E(B, BITS, SUF, "prod", "ball_mul_1", prod_ball_mul_1, op)                                  \
    KB_E(B, BITS, SUF, "prod", "ball_scale_1", prod_ball_scale_1, kairn)                           \
    KB_E(B, BITS, SUF, "prod", "ball_scale_1", prod_ball_scale_1, op)                              \
    KB_E(B, BITS, SUF, "prod", "mul_1_1", prod_mul_1_1, kairn)                                     \
    KB_E(B, BITS, SUF, "prod", "mul_1_1", prod_mul_1_1, limb)                                      \
    KB_E(B, BITS, SUF, "horner", "mul_2_2+add_2_2", horner_2, kairn)                               \
    KB_E(B, BITS, SUF, "horner", "mul_2_2+add_2_2", horner_2, op)                                  \
    KB_E(B, BITS, SUF, "horner", "mul_2_2+add_2_2", horner_2, finite)                              \
    KB_E(B, BITS, SUF, "horner", "mul_2_2+add_2_2", horner_2, textbook)                            \
    KB_E(B, BITS, SUF, "horner", "mul_2_1+add_2_1", horner_21, kairn)                              \
    KB_E(B, BITS, SUF, "horner", "mul_2_1+add_2_1", horner_21, op)                                 \
    KB_E(B, BITS, SUF, "horner", "mul_2_1+add_2_1", horner_21, finite)                             \
    KB_E(B, BITS, SUF, "horner", "mul_2_1+add_2_1", horner_21, textbook)                           \
    KB_E(B, BITS, SUF, "horner", "ball_mul_2+ball_add_2", horner_ball_2, kairn)                    \
    KB_E(B, BITS, SUF, "horner", "ball_mul_2+ball_add_2", horner_ball_2, op)                       \
    KB_E(B, BITS, SUF, "horner", "ball_mul_1+ball_add_1", horner_ball_1, kairn)                    \
    KB_E(B, BITS, SUF, "horner", "ball_mul_1+ball_add_1", horner_ball_1, op)                       \
    KB_E(B, BITS, SUF, "horner", "mul_1_1+add_1_1", horner_1, kairn)                               \
    KB_E(B, BITS, SUF, "horner", "mul_1_1+add_1_1", horner_1, limb)

namespace kairn_bench {

const Entry api_entries[] = {
    KB_A_TABLE("api", 64, 64)
    KB_A_TABLE("apif", 32, 32)
    {nullptr, 0, nullptr, nullptr, nullptr, 0},
};

void api_setup(std::uint64_t seed) {
    if (!g64) g64 = new Data<double>();
    if (!g32) g32 = new Data<float>();
    fill(*g64, seed);
    fill(*g32, seed);
}

void* api_data(int bits) { return bits == 32 ? static_cast<void*>(g32) : static_cast<void*>(g64); }

void api_clear(int bits) {
    if (bits == 32)
        std::memset(out_begin(*g32), 0xff, out_size(*g32));
    else
        std::memset(out_begin(*g64), 0xff, out_size(*g64));
}

const unsigned char* api_output(int bits, std::size_t* size) {
    if (bits == 32) {
        *size = out_size(*g32);
        return out_begin(*g32);
    }
    *size = out_size(*g64);
    return out_begin(*g64);
}

}  // namespace kairn_bench
