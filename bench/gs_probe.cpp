// Which functions that use Kairn's types get MSVC's /GS stack cookie (bench/README.md, "MSVC's
// stack cookie"; bench/gs_probe.py compiles this file and reads the disassembly). The same shapes
// of code for double, Expansion<double, 1>, Expansion<double, 2>, Ball<double, 1> and
// Ball<double, 2>, written with the public operators, each a non-inlined function with C linkage:
//
// - ret_add, ret_mul: one operation on operands passed by reference, the result returned by value
//   (C++ linkage: MSVC does not let a function with C linkage return a class);
// - add, mul: the same, the result stored through a pointer;
// - tp_add, tp_mul: a loop of independent operations over arrays, z[i] = x[i] op y[i];
// - sum, prod: a dependent chain, s = s op x[i];
// - dot: s = s + x[i] * y[i];
// - axpy: y[i] = a * x[i] + y[i];
// - horner: r = r * h + c[i], over a std::array of eight coefficients.
//
// GS_PLAIN adds the same shapes for plain structures that hold the same members as Expansion and
// Ball, and for kairn_gs::Wrap<K>, a class template with nothing but an array member, to compare
// with (gs_probe.py, "isolate").
#include <kairn/kairn.hpp>

#include <array>
#include <cstddef>

#if defined(_MSC_VER) && !defined(__clang__)
#define GS_NOINLINE __declspec(noinline)
#else
#define GS_NOINLINE __attribute__((noinline))
#endif

using D = double;
using E1 = kairn::Expansion<double, 1>;
using E2 = kairn::Expansion<double, 2>;
using B1 = kairn::Ball<double, 1>;
using B2 = kairn::Ball<double, 2>;

#define GS_SHAPES(TAG, X, A)                                                                        \
    GS_NOINLINE X gs_##TAG##_ret_add(const X& x, const X& y) { return x + y; }                     \
    GS_NOINLINE X gs_##TAG##_ret_mul(const X& x, const X& y) { return x * y; }                     \
    extern "C" GS_NOINLINE void gs_##TAG##_add(const X& x, const X& y, X* z) { *z = x + y; }       \
    extern "C" GS_NOINLINE void gs_##TAG##_mul(const X& x, const X& y, X* z) { *z = x * y; }       \
    extern "C" GS_NOINLINE void gs_##TAG##_tp_add(const X* x, const X* y, X* z, std::size_t n) {   \
        for (std::size_t i = 0; i < n; ++i) z[i] = x[i] + y[i];                                    \
    }                                                                                               \
    extern "C" GS_NOINLINE void gs_##TAG##_tp_mul(const X* x, const X* y, X* z, std::size_t n) {   \
        for (std::size_t i = 0; i < n; ++i) z[i] = x[i] * y[i];                                    \
    }                                                                                               \
    extern "C" GS_NOINLINE void gs_##TAG##_sum(const X* x, std::size_t n, X* out) {                \
        X s{};                                                                                      \
        for (std::size_t i = 0; i < n; ++i) s = s + x[i];                                          \
        *out = s;                                                                                   \
    }                                                                                               \
    extern "C" GS_NOINLINE void gs_##TAG##_prod(const X* x, std::size_t n, X* out) {               \
        X s = x[0];                                                                                 \
        for (std::size_t i = 1; i < n; ++i) s = s * x[i];                                          \
        *out = s;                                                                                   \
    }                                                                                               \
    extern "C" GS_NOINLINE void gs_##TAG##_dot(const X* x, const X* y, std::size_t n, X* out) {    \
        X s{};                                                                                      \
        for (std::size_t i = 0; i < n; ++i) s = s + x[i] * y[i];                                   \
        *out = s;                                                                                   \
    }                                                                                               \
    extern "C" GS_NOINLINE void gs_##TAG##_axpy(A a, const X* x, X* y, std::size_t n) {            \
        for (std::size_t i = 0; i < n; ++i) y[i] = a * x[i] + y[i];                                \
    }                                                                                               \
    extern "C" GS_NOINLINE void gs_##TAG##_horner(const std::array<X, 8>& c, A h, X* out) {        \
        X r = c[7];                                                                                 \
        for (int i = 6; i >= 0; --i) r = r * h + c[i];                                             \
        *out = r;                                                                                   \
    }

GS_SHAPES(double, D, D)
GS_SHAPES(e1, E1, E1)
GS_SHAPES(e2, E2, E2)
GS_SHAPES(b1, B1, B1)
GS_SHAPES(b2, B2, B2)

#if defined(GS_PLAIN)
// The same members as Expansion<double, K> and Ball<double, K>, in plain structures whose
// operations are plain double arithmetic: what /GS does with the layout alone.
struct P1 {
    double limb[1] = {};
};
struct P2 {
    double limb[2] = {};
};
struct PB2 {
    P2 c{};
    double r = 0;
};
inline P1 operator+(const P1& x, const P1& y) { return {{x.limb[0] + y.limb[0]}}; }
inline P1 operator*(const P1& x, const P1& y) { return {{x.limb[0] * y.limb[0]}}; }
inline P2 operator+(const P2& x, const P2& y) { return {{x.limb[0] + y.limb[0], x.limb[1] + y.limb[1]}}; }
inline P2 operator*(const P2& x, const P2& y) { return {{x.limb[0] * y.limb[0], x.limb[1] * y.limb[1]}}; }
inline PB2 operator+(const PB2& x, const PB2& y) { return {x.c + y.c, x.r + y.r}; }
inline PB2 operator*(const PB2& x, const PB2& y) { return {x.c * y.c, x.r * y.r}; }
GS_SHAPES(p1, P1, P1)
GS_SHAPES(p2, P2, P2)
GS_SHAPES(pb2, PB2, PB2)
#endif
