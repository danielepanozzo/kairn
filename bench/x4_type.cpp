// The experimental four-limb interval rounded upward (experiments/upward4/; bench/x4_data.hpp), backend
// x4. EXPERIMENTAL, NOT VERIFIED, not part of the library. Requires the rounding mode upward set by
// kairn::upward::Scope and the options of docs/concepts/upward.md (GCC and Clang -frounding-math):
// bench/CMakeLists.txt compiles this file with the option of the target kairn::upward (and the flags of
// packed code), and every timed function here holds one Scope around its loop or chain.
//
// Variants: native (the type's operators: the accurate sum, the product "branch", the square by
// branches), sloppy (the sloppy sum, KAIRN_UPWARD4_SUM_SLOPPY's), table, sel2 and, with AVX2, sel4 (the
// forms of the product), sel (the square without branches on the signs) (upward4_forms.hpp), each
// through the same barriers as the operators.
//
// Also the backend x4a: the functions on arrays (upward4_arrays.hpp), add, sub and mul on eight plain
// arrays of kN elements, X and Y (variant native, each function holding its own scope, called from code
// that rounds to nearest), and the loop of the type's operators over the same eight arrays, element by
// element inside one Scope (variant loop), against which they are measured; the arrays placed as
// up_data.hpp says. The reference of each: the same function on copies of its operands read through
// volatile objects. (Here, not in a unit of its own, so that bench/CMakeLists.txt is unchanged: this file
// is compiled with the option of kairn::upward and the flags of packed code, as the functions need.)
#include <kairn/experimental/upward4.hpp>
#include <kairn/experimental/upward4_arrays.hpp>
#include <kairn/experimental/upward4_forms.hpp>
#include <kairn/upward.hpp>

#include <string>
#include <vector>

#include "x4_unit.hpp"

namespace {

namespace x4 = kairn_bench::x4;
namespace u4 = kairn::experimental::upward4;
namespace d4 = kairn::experimental::upward4::detail;
namespace ku = kairn::upward;
using T = u4::Interval;

enum Form { SLOPPY, TABLE, SEL2, SEL4 };
template <int F>
KB_X2_INLINE T mulf(const T& x, const T& y) {
    d4::R4 a = x.r_, b = y.r_;
    d4::pin(a);
    d4::bar(b);
    d4::R4 z;
    if constexpr (F == TABLE) z = d4::mul_table(a, b);
#if KAIRN_UPWARD2_AVX2
    else if constexpr (F == SEL4) z = d4::mul_sel4(a, b);
#endif
    else z = d4::mul_sel2(a, b);
    d4::bar(z);
    return T(z);
}
KB_X2_INLINE T sqr_sel(const T& x) {
    d4::R4 a = x.r_;
    d4::pin(a);
    d4::R4 z = d4::sqr_sel(a);
    d4::bar(z);
    return T(z);
}
KB_X2_INLINE T add_sloppy(const T& x, const T& y) {
    d4::R4 a = x.r_, b = y.r_;
    d4::pin(a);
    d4::bar(b);
    d4::R4 z = d4::add_sloppy_r(a, b);
    d4::bar(z);
    return T(z);
}
struct Native {
    static KB_X2_INLINE T add(const T& a, const T& b) { return a + b; }
    static KB_X2_INLINE T sub(const T& a, const T& b) { return a - b; }
    static KB_X2_INLINE T mul(const T& a, const T& b) { return a * b; }
    static KB_X2_INLINE T sqr(const T& a) { return u4::sqr(a); }
    static KB_X2_INLINE T zero() { return T(); }
    static KB_X2_INLINE T one() { return T(1.0); }
};
struct Sloppy : Native {
    static KB_X2_INLINE T add(const T& a, const T& b) { return add_sloppy(a, b); }
    static KB_X2_INLINE T sub(const T& a, const T& b) { return add_sloppy(a, -b); }
};
template <int F>
struct MulForm : Native {
    static KB_X2_INLINE T mul(const T& a, const T& b) { return mulf<F>(a, b); }
};
using Table = MulForm<TABLE>;
using Sel2 = MulForm<SEL2>;
using Sel4 = MulForm<SEL4>;
struct SqrSel : Native {
    static KB_X2_INLINE T sqr(const T& a) { return sqr_sel(a); }
};

x4::Data<T>* g = nullptr;

void fill() {
    if (!g) g = new x4::Data<T>();
    x4::fill(
        *g,
        [](const double* p) {
            const kairn::Interval<double, 2> k = kairn::Interval<double, 2>::from_limbs(p);   // before the scope
            ku::Scope scope;
            return u4::from_interval(k);
        },
        [](double t) { return T(t); });
}
void clear() { x4::clear_results(*g); }
void put(const T& v, double* o) {
    double p[8];
    v.to_limbs(p);   // u0 n0 u1 n1 u2 n2 u3 n3: lower -(n0 + n1 + n2 + n3), upper u0 + u1 + u2 + u3
    for (int i = 0; i < 4; ++i) {
        o[i] = -p[2 * i + 1];
        o[4 + i] = p[2 * i];
    }
}
int read(const char* name, double* out) { return x4::read_results(x4::parse(name).kernel, *g, put, out); }

template <class Ops>
void ref_run(int k) {
    const x4::Local<T> d = x4::local(*g);
    ku::Scope scope;
    x4::run<T, Ops>(k, d, x4::VRead{});
}
int reference(const char* name, double* out) {
    const x4::Name n = x4::parse(name);
    if (n.variant == "sloppy") ref_run<Sloppy>(n.kernel);
    else if (n.variant == "table") ref_run<Table>(n.kernel);
    else if (n.variant == "sel2") ref_run<Sel2>(n.kernel);
    else if (n.variant == "sel4") ref_run<Sel4>(n.kernel);
    else if (n.variant == "sel") ref_run<SqrSel>(n.kernel);
    else ref_run<Native>(n.kernel);
    return read(name, out);
}
template <class Ops>
T step_of(int k, const T& s, int j) {
    ku::Scope scope;
    if (k == x4::K_SUM) return Ops::add(s, g->x[j]);
    return Ops::mul(s, k == x4::K_PRODRAND ? g->fr[j] : g->f[j]);
}
bool step(const char* name, const double* before, int k, double* after) {
    const x4::Name n = x4::parse(name);
    double p[8];
    for (int i = 0; i < 4; ++i) {
        p[2 * i] = before[4 + i];
        p[2 * i + 1] = -before[i];
    }
    const T s = T::from_limbs(p);
    T r;
    if (n.variant == "sloppy") r = step_of<Sloppy>(n.kernel, s, k);
    else if (n.variant == "table") r = step_of<Table>(n.kernel, s, k);
    else if (n.variant == "sel2") r = step_of<Sel2>(n.kernel, s, k);
    else if (n.variant == "sel4") r = step_of<Sel4>(n.kernel, s, k);
    else r = step_of<Native>(n.kernel, s, k);
    put(r, after);
    return true;
}

x4::Unit unit{"x4", nullptr, true, fill, clear, read, reference, step, nullptr};
[[maybe_unused]] const bool unit_registered = (unit.next = x4::units, x4::units = &unit, true);

// --- The functions on arrays: backend x4a ------------------------------------------------------------------

using kairn_bench::m2::kN;
struct ArrData {
    kairn_bench::up::Placed a{kN * sizeof(double)}, b{kN * sizeof(double)}, c{kN * sizeof(double)};
    double* x[8];   // u0..u3, n0..n3
    double* y[8];
    double* z[8];
    ArrData() {
        for (int k = 0; k < 8; ++k) {
            x[k] = a.at<double>(k);
            y[k] = b.at<double>(k);
            z[k] = c.at<double>(k);
        }
    }
};
ArrData* ga = nullptr;

u4::View<const double> cv(double* const* p, std::size_t n = kN) { return {{p[0], p[1], p[2], p[3]}, {p[4], p[5], p[6], p[7]}, n}; }
u4::View<double> mv(double* const* p, std::size_t n = kN) { return {{p[0], p[1], p[2], p[3]}, {p[4], p[5], p[6], p[7]}, n}; }

void fill_one(const double* d, double* const* p, int i) {
    const kairn::Interval<double, 2> k = kairn::Interval<double, 2>::from_limbs(d);   // before the scope
    ku::Scope scope;
    const T v = u4::from_interval(k);
    double q[8];
    v.to_limbs(q);   // u0 n0 u1 n1 u2 n2 u3 n3
    for (int j = 0; j < 4; ++j) {
        p[j][i] = q[2 * j];
        p[4 + j][i] = q[2 * j + 1];
    }
}
void afill() {
    if (!ga) ga = new ArrData();
    const kairn_bench::x2::Ops& o = kairn_bench::x2::ops();
    for (int i = 0; i < kN; ++i) {
        fill_one(o.x + 4 * i, ga->x, i);
        fill_one(o.y + 4 * i, ga->y, i);
    }
}
void aclear() {
    for (double* p : ga->z) std::memset(p, 0xff, kN * sizeof(double));
}
// Element i of eight arrays as 8 numbers: lower -(n0 + n1 + n2 + n3), upper u0 + u1 + u2 + u3.
void aput(double* const* p, int i, double* o) {
    for (int j = 0; j < 4; ++j) {
        o[j] = -p[4 + j][i];
        o[4 + j] = p[j][i];
    }
}
int aread(const char*, double* out) {
    for (int i = 0; i < kN; ++i) aput(ga->z, i, out + 8 * i);
    return kN;
}
// The loop of the type's operators over eight arrays, element by element, inside one Scope.
template <int K>
KB_X2_INLINE void loop_ops(const u4::View<double>& z, const u4::View<const double>& x, const u4::View<const double>& y) {
    ku::Scope scope;
    for (std::size_t k = 0; k < z.size; ++k) {
        const T p = d4::element(x, k), q = d4::element(y, k);
        d4::put(z, k, K == x4::K_ADD ? p + q : K == x4::K_SUB ? p - q : p * q);
    }
}
template <int K>
void arrays_of(const std::string& variant, const u4::View<double>& z, const u4::View<const double>& x, const u4::View<const double>& y) {
    if (variant == "loop") loop_ops<K>(z, x, y);
    else if (K == x4::K_ADD) u4::add(z, x, y);
    else if (K == x4::K_SUB) u4::sub(z, x, y);
    else u4::mul(z, x, y);
}
int areference(const char* name, double* out) {
    std::vector<double> buf(24 * kN);
    double* xs[8];
    double* ys[8];
    double* zs[8];
    for (int k = 0; k < 8; ++k) {
        xs[k] = buf.data() + k * kN;
        ys[k] = buf.data() + (8 + k) * kN;
        zs[k] = buf.data() + (16 + k) * kN;
        const volatile double* vx = ga->x[k];
        const volatile double* vy = ga->y[k];
        for (int i = 0; i < kN; ++i) {
            xs[k][i] = vx[i];
            ys[k][i] = vy[i];
        }
    }
    const x4::Name n = x4::parse(name);
    if (n.kernel == x4::K_ADD) arrays_of<x4::K_ADD>(n.variant, mv(zs), cv(xs), cv(ys));
    else if (n.kernel == x4::K_SUB) arrays_of<x4::K_SUB>(n.variant, mv(zs), cv(xs), cv(ys));
    else arrays_of<x4::K_MUL>(n.variant, mv(zs), cv(xs), cv(ys));
    for (int i = 0; i < kN; ++i) aput(zs, i, out + 8 * i);
    return kN;
}

x4::Unit aunit{"x4a", nullptr, true, afill, aclear, aread, areference, nullptr, nullptr};
[[maybe_unused]] const bool aunit_registered = (aunit.next = x4::units, x4::units = &aunit, true);

}  // namespace

extern "C" KB_NOINLINE void kb_x4a_tp_add__native(void*) { u4::add(mv(ga->z), cv(ga->x), cv(ga->y)); }
extern "C" KB_NOINLINE void kb_x4a_tp_sub__native(void*) { u4::sub(mv(ga->z), cv(ga->x), cv(ga->y)); }
extern "C" KB_NOINLINE void kb_x4a_tp_mul__native(void*) { u4::mul(mv(ga->z), cv(ga->x), cv(ga->y)); }
extern "C" KB_NOINLINE void kb_x4a_tp_add__loop(void*) { loop_ops<x4::K_ADD>(mv(ga->z), cv(ga->x), cv(ga->y)); }
extern "C" KB_NOINLINE void kb_x4a_tp_sub__loop(void*) { loop_ops<x4::K_SUB>(mv(ga->z), cv(ga->x), cv(ga->y)); }
extern "C" KB_NOINLINE void kb_x4a_tp_mul__loop(void*) { loop_ops<x4::K_MUL>(mv(ga->z), cv(ga->x), cv(ga->y)); }

#define KB_SCOPE ku::Scope scope
#define KB_X4_TYPE_LIST(X)                                                                         \
    X("x4", x4, tp, add, native, K_ADD, Native, KB_SCOPE)                                          \
    X("x4", x4, tp, add, sloppy, K_ADD, Sloppy, KB_SCOPE)                                          \
    X("x4", x4, tp, sub, native, K_SUB, Native, KB_SCOPE)                                          \
    X("x4", x4, tp, mul, native, K_MUL, Native, KB_SCOPE)                                          \
    X("x4", x4, tp, mul, table, K_MUL, Table, KB_SCOPE)                                            \
    X("x4", x4, tp, mul, sel2, K_MUL, Sel2, KB_SCOPE)                                              \
    X("x4", x4, tp, mulpos, native, K_MULPOS, Native, KB_SCOPE)                                    \
    X("x4", x4, tp, mulpos, table, K_MULPOS, Table, KB_SCOPE)                                      \
    X("x4", x4, tp, mulpos, sel2, K_MULPOS, Sel2, KB_SCOPE)                                        \
    X("x4", x4, tp, mulzero, native, K_MULZERO, Native, KB_SCOPE)                                  \
    X("x4", x4, tp, mulzero, table, K_MULZERO, Table, KB_SCOPE)                                    \
    X("x4", x4, tp, mulzero, sel2, K_MULZERO, Sel2, KB_SCOPE)                                      \
    X("x4", x4, tp, mulrand, native, K_MULRAND, Native, KB_SCOPE)                                  \
    X("x4", x4, tp, mulrand, table, K_MULRAND, Table, KB_SCOPE)                                    \
    X("x4", x4, tp, mulrand, sel2, K_MULRAND, Sel2, KB_SCOPE)                                      \
    X("x4", x4, tp, sqr, native, K_SQR, Native, KB_SCOPE)                                          \
    X("x4", x4, tp, sqr, sel, K_SQR, SqrSel, KB_SCOPE)                                             \
    X("x4", x4, tp, sqrrand, native, K_SQRRAND, Native, KB_SCOPE)                                  \
    X("x4", x4, tp, sqrrand, sel, K_SQRRAND, SqrSel, KB_SCOPE)                                     \
    X("x4", x4, sum, add, native, K_SUM, Native, KB_SCOPE)                                         \
    X("x4", x4, sum, add, sloppy, K_SUM, Sloppy, KB_SCOPE)                                         \
    X("x4", x4, prod, mul, native, K_PROD, Native, KB_SCOPE)                                       \
    X("x4", x4, prod, mul, table, K_PROD, Table, KB_SCOPE)                                         \
    X("x4", x4, prod, mul, sel2, K_PROD, Sel2, KB_SCOPE)                                           \
    X("x4", x4, prod, mulrand, native, K_PRODRAND, Native, KB_SCOPE)                               \
    X("x4", x4, prod, mulrand, table, K_PRODRAND, Table, KB_SCOPE)                                 \
    X("x4", x4, prod, mulrand, sel2, K_PRODRAND, Sel2, KB_SCOPE)                                   \
    X("x4", x4, tp, det3pt, native, K_DET, Native, KB_SCOPE)                                       \
    X("x4", x4, tp, det3pt, sloppy, K_DET, Sloppy, KB_SCOPE)                                       \
    X("x4", x4, tp, det3pt, table, K_DET, Table, KB_SCOPE)                                         \
    X("x4", x4, tp, det3pt, sel2, K_DET, Sel2, KB_SCOPE)                                           \
    X("x4", x4, tp, horner_pt, native, K_HORNER_PT, Native, KB_SCOPE)                              \
    X("x4", x4, tp, horner_i, native, K_HORNER_I, Native, KB_SCOPE)                                \
    X("x4", x4, tp, horner_i, sloppy, K_HORNER_I, Sloppy, KB_SCOPE)
#if KAIRN_UPWARD2_AVX2
#define KB_X4_AVX2_LIST(X)                                                                         \
    X("x4", x4, tp, mul, sel4, K_MUL, Sel4, KB_SCOPE)                                              \
    X("x4", x4, tp, mulpos, sel4, K_MULPOS, Sel4, KB_SCOPE)                                        \
    X("x4", x4, tp, mulzero, sel4, K_MULZERO, Sel4, KB_SCOPE)                                      \
    X("x4", x4, tp, mulrand, sel4, K_MULRAND, Sel4, KB_SCOPE)                                      \
    X("x4", x4, prod, mul, sel4, K_PROD, Sel4, KB_SCOPE)                                           \
    X("x4", x4, prod, mulrand, sel4, K_PRODRAND, Sel4, KB_SCOPE)                                   \
    X("x4", x4, tp, det3pt, sel4, K_DET, Sel4, KB_SCOPE)
#else
#define KB_X4_AVX2_LIST(X)
#endif

#define KB_X4_DEF(B, SUF, KIND, KERNEL, VAR, K, OPS, SCOPE) KB_X4_FN(SUF, KIND, KERNEL, VAR, K, OPS, SCOPE)
KB_X4_TYPE_LIST(KB_X4_DEF)
KB_X4_AVX2_LIST(KB_X4_DEF)

namespace {
const kairn_bench::m2::Entry table[] = {
    KB_X4_TYPE_LIST(KB_X4_ROW)
    KB_X4_AVX2_LIST(KB_X4_ROW)
    {"x4a/tp/add/native", kb_x4a_tp_add__native, 64, 1, kN, 0, 0, kairn_bench::x4::check},
    {"x4a/tp/sub/native", kb_x4a_tp_sub__native, 64, 1, kN, 0, 0, kairn_bench::x4::check},
    {"x4a/tp/mul/native", kb_x4a_tp_mul__native, 64, 1, kN, 0, 0, kairn_bench::x4::check},
    {"x4a/tp/add/loop", kb_x4a_tp_add__loop, 64, 1, kN, 0, 0, kairn_bench::x4::check},
    {"x4a/tp/sub/loop", kb_x4a_tp_sub__loop, 64, 1, kN, 0, 0, kairn_bench::x4::check},
    {"x4a/tp/mul/loop", kb_x4a_tp_mul__loop, 64, 1, kN, 0, 0, kairn_bench::x4::check},
    {nullptr, nullptr, 0, 0, 0, 0, 0, nullptr},
};
kairn_bench::m2::TableLink link{table, nullptr};
[[maybe_unused]] const bool registered =
    (link.next = kairn_bench::m2::m2_extra_tables, kairn_bench::m2::m2_extra_tables = &link, true);
}  // namespace
