// The experimental two-limb interval rounded upward (experiments/upward2/; bench/x2_data.hpp),
// backend x2, and the one-limb kairn::upward::Interval<double> on the same points, backend x2u.
// EXPERIMENTAL, NOT VERIFIED, not part of the library. Requires the rounding mode upward set by
// kairn::upward::Scope and the options of docs/concepts/upward.md (GCC and Clang -frounding-math):
// bench/CMakeLists.txt compiles this file with the option of the target kairn::upward (and the flags
// of packed code), and every timed function here holds one Scope around its loop or chain.
//
// Arrays of the type, filled outside the timed functions (native storage), placed as up_data.hpp
// says. Variants: native (the type's operators), the forms of the product (sel2, eight, table,
// branch, sel4: experiments/upward2/README.md) and of the sum (lean, sloppy) through the same
// barriers as the operators. Each function has a reference: the same computation by the same
// kernels on operands read through volatile objects, which its results must equal bit for bit.
#include <kairn/experimental/upward2.hpp>
#include <kairn/upward.hpp>

#include <cstring>
#include <new>
#include <string>

#include "up_data.hpp"
#include "x2_data.hpp"

namespace {

namespace x2 = kairn_bench::x2;
namespace up = kairn_bench::up;
namespace u2 = kairn::experimental::upward2;
namespace d2 = kairn::experimental::upward2::detail;
namespace ku = kairn::upward;
using kairn_bench::m2::Entry;
using kairn_bench::m2::kDeg;
using kairn_bench::m2::kN;
using U = u2::Interval;
using U1 = ku::Interval<double>;

// --- The forms, as operators of a wrapper type --------------------------------------------------------

enum Form { NATIVE, SEL2, EIGHT, TABLE, BRANCH, SEL4, LEAN, SLOPPY };

template <int F>
KB_X2_INLINE U mulf(const U& x, const U& y) {
    if constexpr (F == NATIVE || F == LEAN || F == SLOPPY) {
        return x * y;
    } else {
        d2::R a = x.r_, b = y.r_;
        d2::pin(a);
        d2::bar(b);
        d2::R z;
        if constexpr (F == SEL2) z = d2::mul_sel2(a, b);
        else if constexpr (F == EIGHT) z = d2::mul_eight(a, b);
        else if constexpr (F == TABLE) z = d2::mul_table(a, b);
        else if constexpr (F == BRANCH) z = d2::mul_branch(a, b);
        else {
#if KAIRN_UPWARD2_AVX2
            z = d2::mul_sel4(a, b);
#else
            z = d2::mul_sel2(a, b);
#endif
        }
        d2::bar(z);
        return U(z);
    }
}
template <int F>
KB_X2_INLINE U addf(const U& x, const U& y) {
    if constexpr (F == LEAN || F == SLOPPY) {
        d2::R a = x.r_, b = y.r_;
        d2::pin(a);
        d2::bar(b);
        d2::R z = F == LEAN ? d2::add_r<d2::SumForm::lean>(a, b) : d2::add_r<d2::SumForm::sloppy>(a, b);
        d2::bar(z);
        return U(z);
    } else {
        return x + y;
    }
}
template <int F>
struct UF {
    U v;
};
template <int F>
KB_X2_INLINE UF<F> operator+(const UF<F>& a, const UF<F>& b) { return {addf<F>(a.v, b.v)}; }
template <int F>
KB_X2_INLINE UF<F> operator-(const UF<F>& a, const UF<F>& b) { return {a.v - b.v}; }
template <int F>
KB_X2_INLINE UF<F> operator*(const UF<F>& a, const UF<F>& b) { return {mulf<F>(a.v, b.v)}; }

// --- The operands ---------------------------------------------------------------------------------------

U from_default(const double* p) {
    ku::Scope scope;
    return u2::from_interval(kairn::Interval<double, 2>::from_limbs(p));
}

using x2::kRand;
struct TypeData {
    up::Placed a{kN * sizeof(U)}, b{kN * sizeof(U)}, c{kN * sizeof(U)}, r{kRand * sizeof(U)};
    U* xr = arr(r, 0, kRand);
    U* yr = arr(r, 1, kRand);
    U* zr = arr(r, 8, kRand);
    U* x = arr(a, 0);
    U* y = arr(a, 1);
    U* f = arr(a, 2);
    U* h = arr(a, 3);
    U* z = arr(a, 8);
    U* xp = arr(b, 0);
    U* yp = arr(b, 1);
    U* xz = arr(b, 4);
    U* yz = arr(b, 5);
    U* zb = arr(b, 8);
    U* zc = arr(b, 10);
    U* px = arr(c, 0);
    U* py = arr(c, 1);
    U* pz = arr(c, 2);
    U* ht = arr(c, 3);
    U* zd = arr(c, 8);
    U1* qx = arr1(c, 4);
    U1* qy = arr1(c, 5);
    U1* qz = arr1(c, 6);
    U1* qt = arr1(c, 7);
    U1* zq = arr1(c, 10);
    U hc[kDeg + 1];
    U1 hc1[kDeg + 1];
    U s;
    static U* arr(const up::Placed& p, int k, int n = kN) {
        U* q = p.at<U>(k);
        for (int i = 0; i < n; ++i) new (q + i) U();
        return q;
    }
    static U1* arr1(const up::Placed& p, int k) {
        U1* q = p.at<U1>(k);
        for (int i = 0; i < kN; ++i) new (q + i) U1();
        return q;
    }
};
TypeData* g = nullptr;

void fill() {
    if (!g) g = new TypeData();
    const x2::Ops& o = x2::ops();
    for (int i = 0; i < kN; ++i) {
        g->x[i] = from_default(o.x + 4 * i);
        g->y[i] = from_default(o.y + 4 * i);
        g->f[i] = from_default(o.f + 4 * i);
        g->h[i] = from_default(o.h + 4 * i);
        g->xp[i] = from_default(o.xp + 4 * i);
        g->yp[i] = from_default(o.yp + 4 * i);
        g->xz[i] = from_default(o.xz + 4 * i);
        g->yz[i] = from_default(o.yz + 4 * i);
        g->px[i] = U(o.px[i]);
        g->py[i] = U(o.py[i]);
        g->pz[i] = U(o.pz[i]);
        g->ht[i] = U(o.ht[i]);
        g->qx[i] = U1(o.px[i]);
        g->qy[i] = U1(o.py[i]);
        g->qz[i] = U1(o.pz[i]);
        g->qt[i] = U1(o.ht[i]);
    }
    for (int k = 0; k <= kDeg; ++k) {
        g->hc[k] = U(o.hc[k]);
        g->hc1[k] = U1(o.hc[k]);
    }
    for (int j = 0; j < kRand; ++j) {
        g->xr[j] = from_default(o.xr + 4 * j);
        g->yr[j] = from_default(o.yr + 4 * j);
    }
}
void clear() {
    std::memset(static_cast<void*>(g->zr), 0xff, kRand * sizeof(U));
    for (U* a : {g->z, g->zb, g->zc, g->zd}) std::memset(static_cast<void*>(a), 0xff, kN * sizeof(U));
    std::memset(static_cast<void*>(g->zq), 0xff, kN * sizeof(U1));
    std::memset(static_cast<void*>(&g->s), 0xff, sizeof(U));
}

// The argument of the next dependent Horner evaluation: h with z (a zero computed from the previous
// result, unknown to the compiler) added to its heads: exact, the same interval.
KB_X2_INLINE U arg(const U& h, double z) {
    double p[4];
    h.to_limbs(p);
    p[0] += z;
    p[1] += z;
    return U::from_limbs(p);
}
KB_X2_INLINE double zero_of(const U& p) {
    double q[4];
    p.to_limbs(q);
    return q[0] * 0.0;
}

// Point coordinates of the type with a form, and of the one-limb type.
template <int F>
struct G3 {
    const TypeData& d;
    UF<F> x(int j) const { return {d.px[j]}; }
    UF<F> y(int j) const { return {d.py[j]}; }
    UF<F> z(int j) const { return {d.pz[j]}; }
};
struct G1 {
    const TypeData& d;
    const U1& x(int j) const { return d.qx[j]; }
    const U1& y(int j) const { return d.qy[j]; }
    const U1& z(int j) const { return d.qz[j]; }
};

}  // namespace

// --- The timed functions ------------------------------------------------------------------------------

#define KB_EACH(...)                                                                               \
    for (int i = 0; i < kN; ++i) {                                                                 \
        __VA_ARGS__;                                                                               \
    }

// X(B, SUF, KIND, KERNEL, VAR, BODY...)
#define KB_X2_FORMS(X, KERNEL, XA, YA, ZA)                                                         \
    X("x2", x2, tp, KERNEL, sel2, KB_EACH(g->ZA[i] = mulf<SEL2>(g->XA[i], g->YA[i])))               \
    X("x2", x2, tp, KERNEL, eight, KB_EACH(g->ZA[i] = mulf<EIGHT>(g->XA[i], g->YA[i])))             \
    X("x2", x2, tp, KERNEL, table, KB_EACH(g->ZA[i] = mulf<TABLE>(g->XA[i], g->YA[i])))             \
    X("x2", x2, tp, KERNEL, branch, KB_EACH(g->ZA[i] = mulf<BRANCH>(g->XA[i], g->YA[i])))           \
    X("x2", x2, tp, KERNEL, sel4, KB_EACH(g->ZA[i] = mulf<SEL4>(g->XA[i], g->YA[i])))
#define KB_X2_CHAINS(X, VAR, F)                                                                    \
    X("x2", x2, prod, interval_mul_2, VAR, U p(1.0); KB_EACH(p = mulf<F>(p, g->f[i])) g->s = p;)
#define KB_X2_DETS(X, VAR, F)                                                                      \
    X("x2", x2, tp, det3pt, VAR, const G3<F> q{*g}; KB_EACH(g->zd[i] = x2::det3pt_at<UF<F>>(q, i).v))
#define KB_X2_LIST(X)                                                                              \
    X("x2", x2, tp, interval_add_2, native, KB_EACH(g->z[i] = g->x[i] + g->y[i]))                  \
    X("x2", x2, tp, interval_add_2, lean, KB_EACH(g->z[i] = addf<LEAN>(g->x[i], g->y[i])))          \
    X("x2", x2, tp, interval_add_2, sloppy, KB_EACH(g->z[i] = addf<SLOPPY>(g->x[i], g->y[i])))      \
    X("x2", x2, tp, interval_sub_2, native, KB_EACH(g->z[i] = g->x[i] - g->y[i]))                  \
    X("x2", x2, tp, interval_mul_2, native, KB_EACH(g->z[i] = g->x[i] * g->y[i]))                  \
    KB_X2_FORMS(X, interval_mul_2, x, y, z)                                                        \
    KB_X2_FORMS(X, interval_mul_2pos, xp, yp, zb)                                                  \
    KB_X2_FORMS(X, interval_mul_2zero, xz, yz, zc)                                                 \
    X("x2", x2, tp, sqr_2, native, KB_EACH(g->z[i] = u2::sqr(g->x[i])))                            \
    X("x2", x2, sum, interval_add_2, native, U s; KB_EACH(s = s + g->x[i]) g->s = s;)              \
    X("x2", x2, sum, interval_add_2, lean, U s; KB_EACH(s = addf<LEAN>(s, g->x[i])) g->s = s;)     \
    X("x2", x2, sum, interval_add_2, sloppy, U s; KB_EACH(s = addf<SLOPPY>(s, g->x[i])) g->s = s;) \
    X("x2", x2, prod, interval_mul_2, native, U p(1.0); KB_EACH(p = p * g->f[i]) g->s = p;)        \
    KB_X2_CHAINS(X, sel2, SEL2)                                                                    \
    KB_X2_CHAINS(X, eight, EIGHT)                                                                  \
    KB_X2_CHAINS(X, table, TABLE)                                                                  \
    KB_X2_CHAINS(X, branch, BRANCH)                                                                \
    KB_X2_CHAINS(X, sel4, SEL4)                                                                    \
    X("x2", x2, tp, horner_i2, native, KB_EACH(g->z[i] = x2::horner2(g->hc, g->h[i])))             \
    X("x2", x2, lat, horner_i2, native, double zz = 0; U p;                                        \
      KB_EACH(p = x2::horner2(g->hc, arg(g->h[i], zz)); zz = zero_of(p)) g->s = p;)                \
    X("x2", x2, tp, horner_pt, native, KB_EACH(g->zd[i] = x2::horner2(g->hc, g->ht[i])))           \
    X("x2", x2, tp, det3pt, native, const G3<NATIVE> q{*g};                                        \
      KB_EACH(g->zd[i] = x2::det3pt_at<UF<NATIVE>>(q, i).v))                                       \
    KB_X2_DETS(X, sel2, SEL2)                                                                      \
    KB_X2_DETS(X, eight, EIGHT)                                                                    \
    KB_X2_DETS(X, branch, BRANCH)                                                                  \
    KB_X2_DETS(X, sel4, SEL4)                                                                      \
    X("x2u", x2u, tp, det3pt, u1, const G1 q{*g}; KB_EACH(g->zq[i] = x2::det3pt_at<U1>(q, i)))     \
    X("x2u", x2u, tp, horner_pt, u1, KB_EACH(g->zq[i] = up::horner(g->hc1, g->qt[i])))

#define KB_X2_DEF(B, SUF, KIND, KERNEL, VAR, ...)                                                  \
    extern "C" KB_NOINLINE void kb_##SUF##_##KIND##_##KERNEL##__##VAR(void*) {                     \
        ku::Scope scope;                                                                           \
        __VA_ARGS__                                                                                \
    }
KB_X2_LIST(KB_X2_DEF)

// The products of random signs, kRand per call.
#define KB_EACHR(...)                                                                              \
    for (int i = 0; i < kRand; ++i) {                                                              \
        __VA_ARGS__;                                                                               \
    }
#define KB_X2_RAND(X)                                                                              \
    X("x2", x2, tp, interval_mul_2rand, sel2, KB_EACHR(g->zr[i] = mulf<SEL2>(g->xr[i], g->yr[i])))  \
    X("x2", x2, tp, interval_mul_2rand, eight, KB_EACHR(g->zr[i] = mulf<EIGHT>(g->xr[i], g->yr[i]))) \
    X("x2", x2, tp, interval_mul_2rand, table, KB_EACHR(g->zr[i] = mulf<TABLE>(g->xr[i], g->yr[i]))) \
    X("x2", x2, tp, interval_mul_2rand, branch, KB_EACHR(g->zr[i] = mulf<BRANCH>(g->xr[i], g->yr[i]))) \
    X("x2", x2, tp, interval_mul_2rand, sel4, KB_EACHR(g->zr[i] = mulf<SEL4>(g->xr[i], g->yr[i])))
KB_X2_RAND(KB_X2_DEF)

// --- The references: the same computations on operands read through volatile objects ---------------

namespace {

U vread(const U& a) {
    const volatile double* q = reinterpret_cast<const volatile double*>(&a);
    double t[4] = {q[0], q[1], q[2], q[3]};
    return U::from_limbs(t);
}
U1 vread1(const U1& a) {
    double t[2];
    a.to_limbs(t);
    volatile double v0 = t[0], v1 = t[1];
    t[0] = v0;
    t[1] = v1;
    return U1::from_limbs(t);
}
template <int F>
struct VG3 {
    const TypeData& d;
    UF<F> x(int j) const { return {vread(d.px[j])}; }
    UF<F> y(int j) const { return {vread(d.py[j])}; }
    UF<F> z(int j) const { return {vread(d.pz[j])}; }
};
struct VG1 {
    const TypeData& d;
    U1 x(int j) const { return vread1(d.qx[j]); }
    U1 y(int j) const { return vread1(d.qy[j]); }
    U1 z(int j) const { return vread1(d.qz[j]); }
};

void put(const U& v, double* o) {
    double p[4];
    v.to_limbs(p);   // (uh, nh, ul, nl): the bounds are -(nh + nl) and uh + ul, exactly
    o[0] = -p[1];
    o[1] = -p[3];
    o[2] = p[0];
    o[3] = p[2];
}
void put1(const U1& v, double* o) {
    double p[2];
    v.to_limbs(p);   // (u, n)
    o[0] = -p[1];
    o[1] = 0;
    o[2] = p[0];
    o[3] = 0;
}

struct Name {
    std::string backend, kind, kernel, variant;
};
Name split(const char* s) {
    Name n;
    std::string t = s, part[4];
    std::size_t at = 0;
    for (int k = 0; k < 4; ++k) {
        const std::size_t slash = k < 3 ? t.find('/', at) : std::string::npos;
        part[k] = t.substr(at, slash == std::string::npos ? std::string::npos : slash - at);
        at = slash + 1;
    }
    return {part[0], part[1], part[2], part[3]};
}
int form_of(const std::string& v) {
    if (v == "sel2") return SEL2;
    if (v == "eight") return EIGHT;
    if (v == "table") return TABLE;
    if (v == "branch") return BRANCH;
    if (v == "sel4") return SEL4;
    if (v == "lean") return LEAN;
    if (v == "sloppy") return SLOPPY;
    return NATIVE;
}

template <int F>
U vmul(const U& a, const U& b) { return mulf<F>(vread(a), vread(b)); }
U vmul_form(int f, const U& a, const U& b) {
    switch (f) {
    case SEL2: return vmul<SEL2>(a, b);
    case EIGHT: return vmul<EIGHT>(a, b);
    case TABLE: return vmul<TABLE>(a, b);
    case BRANCH: return vmul<BRANCH>(a, b);
    case SEL4: return vmul<SEL4>(a, b);
    default: return vmul<NATIVE>(a, b);
    }
}
U vadd_form(int f, const U& a, const U& b) {
    if (f == LEAN) return addf<LEAN>(vread(a), vread(b));
    if (f == SLOPPY) return addf<SLOPPY>(vread(a), vread(b));
    return vread(a) + vread(b);
}
template <int F>
U vdet(int i) {
    const VG3<F> q{*g};
    return x2::det3pt_at<UF<F>>(q, i).v;
}

int reference(const char* name, double* out) {
    const Name n = split(name);
    const int f = form_of(n.variant);
    ku::Scope scope;
    if (n.backend == "x2u") {
        const VG1 q{*g};
        for (int i = 0; i < kN; ++i) {
            if (n.kernel == "det3pt") put1(x2::det3pt_at<U1>(q, i), out + 4 * i);
            else put1(up::horner(g->hc1, vread1(g->qt[i])), out + 4 * i);
        }
        return kN;
    }
    if (n.kind == "tp") {
        const U *xa = g->x, *ya = g->y;
        int count = kN;
        if (n.kernel == "interval_mul_2pos") xa = g->xp, ya = g->yp;
        if (n.kernel == "interval_mul_2zero") xa = g->xz, ya = g->yz;
        if (n.kernel == "interval_mul_2rand") xa = g->xr, ya = g->yr, count = kRand;
        for (int i = 0; i < count; ++i) {
            U r;
            if (n.kernel == "interval_add_2") r = vadd_form(f, xa[i], ya[i]);
            else if (n.kernel == "interval_sub_2") r = vread(xa[i]) - vread(ya[i]);
            else if (n.kernel == "sqr_2") r = u2::sqr(vread(xa[i]));
            else if (n.kernel == "horner_i2") r = x2::horner2(g->hc, vread(g->h[i]));
            else if (n.kernel == "horner_pt") r = x2::horner2(g->hc, vread(g->ht[i]));
            else if (n.kernel == "det3pt") {
                switch (f) {
                case SEL2: r = vdet<SEL2>(i); break;
                case EIGHT: r = vdet<EIGHT>(i); break;
                case BRANCH: r = vdet<BRANCH>(i); break;
                case SEL4: r = vdet<SEL4>(i); break;
                default: r = vdet<NATIVE>(i); break;
                }
            } else r = vmul_form(f, xa[i], ya[i]);
            put(r, out + 4 * i);
        }
        return count;
    }
    U s;
    if (n.kind == "sum") {
        for (int i = 0; i < kN; ++i) s = vadd_form(f, s, g->x[i]);
    } else if (n.kind == "prod") {
        s = U(1.0);
        for (int i = 0; i < kN; ++i) s = vmul_form(f, s, g->f[i]);
    } else {   // lat/horner_i2
        double zz = 0;
        for (int i = 0; i < kN; ++i) {
            s = x2::horner2(g->hc, arg(vread(g->h[i]), zz));
            zz = zero_of(s);
        }
    }
    put(s, out);
    return 1;
}

int read(const char* name, double* out) {
    const Name n = split(name);
    if (n.backend == "x2u") {
        for (int i = 0; i < kN; ++i) put1(g->zq[i], out + 4 * i);
        return kN;
    }
    if (n.kind != "tp") {
        put(g->s, out);
        return 1;
    }
    const U* r = g->z;
    int count = kN;
    if (n.kernel == "interval_mul_2pos") r = g->zb;
    if (n.kernel == "interval_mul_2zero") r = g->zc;
    if (n.kernel == "interval_mul_2rand") r = g->zr, count = kRand;
    if (n.kernel == "horner_pt" || n.kernel == "det3pt") r = g->zd;
    for (int i = 0; i < count; ++i) put(r[i], out + 4 * i);
    return count;
}

// A step of a chain: (l0, l1, h0, h1) of the state, as put() wrote it, back to the type exactly.
void step(const char* name, const double* before, int k, double* after) {
    const Name n = split(name);
    const int f = form_of(n.variant);
    const double p[4] = {before[2], -before[0], before[3], -before[1]};
    const U s = U::from_limbs(p);
    ku::Scope scope;
    U r = n.kind == "sum" ? vadd_form(f, s, g->x[k]) : vmul_form(f, s, g->f[k]);
    put(r, after);
}

x2::Unit unit{"x2", fill, clear, read, reference, step, nullptr};
x2::Unit unit_u{"x2u", fill, clear, read, reference, nullptr, nullptr};
[[maybe_unused]] const bool unit_registered =
    (unit.next = x2::units, x2::units = &unit, unit_u.next = x2::units, x2::units = &unit_u, true);

#define KB_X2_ROW(B, SUF, KIND, KERNEL, VAR, ...)                                                  \
    {B "/" #KIND "/" #KERNEL "/" #VAR, kb_##SUF##_##KIND##_##KERNEL##__##VAR, 64, 1, kN, 0, 0, x2::check},
#define KB_X2_ROWR(B, SUF, KIND, KERNEL, VAR, ...)                                                 \
    {B "/" #KIND "/" #KERNEL "/" #VAR, kb_##SUF##_##KIND##_##KERNEL##__##VAR, 64, 1, kRand, 0, 0, x2::check},
const Entry table[] = {
    KB_X2_LIST(KB_X2_ROW)
    KB_X2_RAND(KB_X2_ROWR)
    {nullptr, nullptr, 0, 0, 0, 0, 0, nullptr},
};
kairn_bench::m2::TableLink link{table, nullptr};
[[maybe_unused]] const bool registered =
    (link.next = kairn_bench::m2::m2_extra_tables, kairn_bench::m2::m2_extra_tables = &link, true);

}  // namespace
