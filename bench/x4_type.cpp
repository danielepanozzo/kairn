// The experimental four-limb interval rounded upward (experiments/upward4/; bench/x4_data.hpp), backend
// x4. EXPERIMENTAL, NOT VERIFIED, not part of the library. Requires the rounding mode upward set by
// kairn::upward::Scope and the options of docs/concepts/upward.md (GCC and Clang -frounding-math):
// bench/CMakeLists.txt compiles this file with the option of the target kairn::upward (and the flags of
// packed code), and every timed function here holds one Scope around its loop or chain.
//
// Variants: native (the type's operators: the accurate sum, the product "branch"), sloppy (the sloppy
// sum, KAIRN_UPWARD4_SUM_SLOPPY's), table, sel2 and, with AVX2, sel4 (the forms of the product,
// upward4_forms.hpp), each through the same barriers as the operators.
#include <kairn/experimental/upward4.hpp>
#include <kairn/experimental/upward4_forms.hpp>
#include <kairn/upward.hpp>

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

}  // namespace

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
    {nullptr, nullptr, 0, 0, 0, 0, 0, nullptr},
};
kairn_bench::m2::TableLink link{table, nullptr};
[[maybe_unused]] const bool registered =
    (link.next = kairn_bench::m2::m2_extra_tables, kairn_bench::m2::m2_extra_tables = &link, true);
}  // namespace
