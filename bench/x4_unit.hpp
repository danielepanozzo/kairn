// The kernels of the benchmark of 1, 2 and 4 limbs (bench/x4_data.hpp), as templates that every unit
// x4_*.cpp instantiates with its type T and an operations class Ops (static add, sub, mul, sqr, one:
// the type's operators, or a form of them). EXPERIMENTAL, NOT VERIFIED. The same template body is the
// timed function (operands as they are) and its reference (operands read through volatile objects,
// accessor VRead), so that the two run the same kernels.
#pragma once

#include <cstring>
#include <string>

#include "x4_data.hpp"

namespace kairn_bench::x4 {

// The operands as they are.
struct Id {
    template <class T>
    KB_X2_INLINE const T& operator()(const T& a) const {
        return a;
    }
};
// The operands through volatile objects: their bytes copied from a volatile view, so that nothing of
// the operand is known to the compiler.
struct VRead {
    template <class T>
    T operator()(const T& a) const {
        T t;
        const volatile unsigned char* p = reinterpret_cast<const volatile unsigned char*>(&a);
        unsigned char* q = reinterpret_cast<unsigned char*>(&t);
        for (std::size_t k = 0; k < sizeof(T); ++k) q[k] = p[k];
        return t;
    }
};

// A value with the operators of Ops (for the expressions of the determinant and Horner).
template <class T, class Ops>
struct W {
    T v;
};
template <class T, class Ops>
KB_X2_INLINE W<T, Ops> operator+(const W<T, Ops>& a, const W<T, Ops>& b) {
    return {Ops::add(a.v, b.v)};
}
template <class T, class Ops>
KB_X2_INLINE W<T, Ops> operator-(const W<T, Ops>& a, const W<T, Ops>& b) {
    return {Ops::sub(a.v, b.v)};
}
template <class T, class Ops>
KB_X2_INLINE W<T, Ops> operator*(const W<T, Ops>& a, const W<T, Ops>& b) {
    return {Ops::mul(a.v, b.v)};
}
template <class T, class Ops, class A>
struct GW {
    const Local<T>& d;
    A a;
    W<T, Ops> x(int j) const { return {a(d.px[j])}; }
    W<T, Ops> y(int j) const { return {a(d.py[j])}; }
    W<T, Ops> z(int j) const { return {a(d.pz[j])}; }
};

enum Kernel { K_ADD, K_SUB, K_MUL, K_MULPOS, K_MULZERO, K_MULRAND, K_SQR, K_SQRRAND, K_SUM, K_PROD, K_PRODRAND, K_DET, K_HORNER_PT, K_HORNER_I, K_NONE };

// The computation of kernel k by Ops, the operands through the accessor a, the results into d's
// result arrays (or d.s for a chain).
template <class T, class Ops, class A>
KB_X2_INLINE void run(int k, const Local<T>& d, A a) {
    using WT = W<T, Ops>;
    switch (k) {
    case K_ADD: KB_X4_EACH(d.z[i] = Ops::add(a(d.x[i]), a(d.y[i]))) break;
    case K_SUB: KB_X4_EACH(d.z[i] = Ops::sub(a(d.x[i]), a(d.y[i]))) break;
    case K_MUL: KB_X4_EACH(d.z[i] = Ops::mul(a(d.x[i]), a(d.y[i]))) break;
    case K_MULPOS: KB_X4_EACH(d.zb[i] = Ops::mul(a(d.xp[i]), a(d.yp[i]))) break;
    case K_MULZERO: KB_X4_EACH(d.zc[i] = Ops::mul(a(d.xz[i]), a(d.yz[i]))) break;
    case K_MULRAND: KB_X4_EACHR(d.zr[i] = Ops::mul(a(d.xr[i]), a(d.yr[i]))) break;
    case K_SQR: KB_X4_EACH(d.z[i] = Ops::sqr(a(d.x[i]))) break;
    case K_SQRRAND: KB_X4_EACHR(d.zr[i] = Ops::sqr(a(d.xr[i]))) break;
    case K_SUM: {
        T s = Ops::zero();
        KB_X4_EACH(s = Ops::add(s, a(d.x[i])))
        d.s = s;
        break;
    }
    case K_PROD: {
        T p = Ops::one();
        KB_X4_EACH(p = Ops::mul(p, a(d.f[i])))
        d.s = p;
        break;
    }
    case K_PRODRAND: {
        T p = Ops::one();
        KB_X4_EACHR(p = Ops::mul(p, a(d.fr[i])))
        d.s = p;
        break;
    }
    case K_DET: {
        const GW<T, Ops, A> q{d, a};
        KB_X4_EACH(d.zd[i] = x2::det3pt_at<WT>(q, i).v)
        break;
    }
    case K_HORNER_PT: {
        WT c[kDeg + 1];
        for (int j = 0; j <= kDeg; ++j) c[j] = WT{a(d.hc[j])};
        KB_X4_EACH(d.zd[i] = x2::horner2(c, WT{a(d.ht[i])}).v)
        break;
    }
    case K_HORNER_I: {
        WT c[kDeg + 1];
        for (int j = 0; j <= kDeg; ++j) c[j] = WT{a(d.hc[j])};
        KB_X4_EACH(d.z[i] = x2::horner2(c, WT{a(d.h[i])}).v)
        break;
    }
    default: break;
    }
}

// The kernel of a name BACKEND/KIND/KERNEL/VARIANT, and its variant.
struct Name {
    int kernel;
    std::string variant;
};
inline Name parse(const char* s) {
    const std::string t = s;
    const std::size_t a = t.find('/'), b = t.find('/', a + 1), c = t.find('/', b + 1);
    const std::string kind = t.substr(a + 1, b - a - 1), kernel = t.substr(b + 1, c - b - 1), variant = t.substr(c + 1);
    int k = K_NONE;
    if (kind == "sum") k = K_SUM;
    else if (kind == "prod") k = kernel == "mulrand" ? K_PRODRAND : K_PROD;
    else if (kernel == "add") k = K_ADD;
    else if (kernel == "sub") k = K_SUB;
    else if (kernel == "mul") k = K_MUL;
    else if (kernel == "mulpos") k = K_MULPOS;
    else if (kernel == "mulzero") k = K_MULZERO;
    else if (kernel == "mulrand") k = K_MULRAND;
    else if (kernel == "sqr") k = K_SQR;
    else if (kernel == "sqrrand") k = K_SQRRAND;
    else if (kernel == "det3pt") k = K_DET;
    else if (kernel == "horner_pt") k = K_HORNER_PT;
    else if (kernel == "horner_i") k = K_HORNER_I;
    return {k, variant};
}
// The results of kernel k from d, through put(const T&, double[8]).
template <class T, class Put>
int read_results(int k, const Data<T>& d, Put put, double* out) {
    const T* r = d.z;
    int n = kN;
    if (k == K_SUM || k == K_PROD || k == K_PRODRAND) {
        put(d.s, out);
        return 1;
    }
    if (k == K_MULPOS) r = d.zb;
    if (k == K_MULZERO) r = d.zc;
    if (k == K_MULRAND || k == K_SQRRAND) r = d.zr, n = kRand;
    if (k == K_DET || k == K_HORNER_PT) r = d.zd;
    for (int i = 0; i < n; ++i) put(r[i], out + 8 * i);
    return n;
}
template <class T>
void clear_results(Data<T>& d) {
    for (T* a : {d.z, d.zb, d.zc, d.zd}) std::memset(static_cast<void*>(a), 0xff, kN * sizeof(T));
    std::memset(static_cast<void*>(d.zr), 0xff, kRand * sizeof(T));
    std::memset(static_cast<void*>(&d.s), 0xff, sizeof(T));
}

}  // namespace kairn_bench::x4

// The timed function of BACKEND/KIND/KERNEL/VARIANT: the kernel K by operations OPS on the unit's
// data, its pointers in locals, inside the statement SCOPE (a kairn::upward::Scope, or nothing).
#define KB_X4_FN(SUF, KIND, KERNEL, VAR, K, OPS, SCOPE)                                            \
    extern "C" KB_NOINLINE void kb_##SUF##_##KIND##_##KERNEL##__##VAR(void*) {                     \
        const ::kairn_bench::x4::Local<T> d = ::kairn_bench::x4::local(*g);                        \
        SCOPE;                                                                                     \
        ::kairn_bench::x4::run<T, OPS>(::kairn_bench::x4::K, d, ::kairn_bench::x4::Id{});          \
    }
#define KB_X4_ROW(B, SUF, KIND, KERNEL, VAR, K, OPS, SCOPE)                                        \
    {B "/" #KIND "/" #KERNEL "/" #VAR, kb_##SUF##_##KIND##_##KERNEL##__##VAR, 64, 1,               \
     (::kairn_bench::x4::K == ::kairn_bench::x4::K_MULRAND || ::kairn_bench::x4::K == ::kairn_bench::x4::K_PRODRAND || \
      ::kairn_bench::x4::K == ::kairn_bench::x4::K_SQRRAND)                                         \
         ? ::kairn_bench::x4::kRand : ::kairn_bench::x4::kN,                                        \
     0, 0, ::kairn_bench::x4::check},
