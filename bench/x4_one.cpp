// kairn::upward::Interval<double>, the one-limb round-up interval of the library, on the operands of
// the benchmark of 1, 2 and 4 limbs (bench/x4_data.hpp), backend x4u, variant u1: each interval of two
// limbs rounded outward to one (the first limbs of its four-limb conversion: the tightest numbers below
// and above its bounds). Requires the rounding mode upward set by kairn::upward::Scope and the options of
// docs/concepts/upward.md: compiled with the option of the target kairn::upward, every timed function
// holding one Scope. The type has no square: no tp/sqr here.
#include <kairn/experimental/upward4.hpp>
#include <kairn/upward.hpp>

#include "x4_unit.hpp"

namespace {

namespace x4 = kairn_bench::x4;
namespace u4 = kairn::experimental::upward4;
namespace ku = kairn::upward;
using T = ku::Interval<double>;

struct Ops {
    static KB_X2_INLINE T add(const T& a, const T& b) { return a + b; }
    static KB_X2_INLINE T sub(const T& a, const T& b) { return a - b; }
    static KB_X2_INLINE T mul(const T& a, const T& b) { return a * b; }
    static KB_X2_INLINE T sqr(const T& a) { return a * a; }
    static KB_X2_INLINE T zero() { return T(0.0); }
    static KB_X2_INLINE T one() { return T(1.0); }
};

x4::Data<T>* g = nullptr;

void fill() {
    if (!g) g = new x4::Data<T>();
    x4::fill(
        *g,
        [](const double* p) {
            const kairn::Interval<double, 2> k = kairn::Interval<double, 2>::from_limbs(p);
            u4::Interval q;
            {
                ku::Scope scope;
                q = u4::from_interval(k);
            }
            return u4::to_upward1(q);
        },
        [](double t) { return T(t); });
}
void clear() { x4::clear_results(*g); }
void put(const T& v, double* o) {
    double p[2];
    v.to_limbs(p);   // (u, n)
    for (int i = 0; i < 8; ++i) o[i] = 0;
    o[0] = -p[1];
    o[4] = p[0];
}
int read(const char* name, double* out) { return x4::read_results(x4::parse(name).kernel, *g, put, out); }
int reference(const char* name, double* out) {
    const x4::Name n = x4::parse(name);
    {
        const x4::Local<T> d = x4::local(*g);
        ku::Scope scope;
        x4::run<T, Ops>(n.kernel, d, x4::VRead{});
    }
    return read(name, out);
}
bool step(const char* name, const double* before, int k, double* after) {
    const x4::Name n = x4::parse(name);
    const double p[2] = {before[4], -before[0]};
    const T s = T::from_limbs(p);
    T r;
    {
        ku::Scope scope;
        r = n.kernel == x4::K_SUM ? Ops::add(s, g->x[k]) : Ops::mul(s, n.kernel == x4::K_PRODRAND ? g->fr[k] : g->f[k]);
    }
    put(r, after);
    return true;
}

x4::Unit unit{"x4u", nullptr, true, fill, clear, read, reference, step, nullptr};
[[maybe_unused]] const bool unit_registered = (unit.next = x4::units, x4::units = &unit, true);

}  // namespace

#define KB_SCOPE ku::Scope scope
#define KB_X4U_LIST(X)                                                                             \
    X("x4u", x4u, tp, add, u1, K_ADD, Ops, KB_SCOPE)                                               \
    X("x4u", x4u, tp, sub, u1, K_SUB, Ops, KB_SCOPE)                                               \
    X("x4u", x4u, tp, mul, u1, K_MUL, Ops, KB_SCOPE)                                               \
    X("x4u", x4u, tp, mulpos, u1, K_MULPOS, Ops, KB_SCOPE)                                         \
    X("x4u", x4u, tp, mulzero, u1, K_MULZERO, Ops, KB_SCOPE)                                       \
    X("x4u", x4u, tp, mulrand, u1, K_MULRAND, Ops, KB_SCOPE)                                       \
    X("x4u", x4u, sum, add, u1, K_SUM, Ops, KB_SCOPE)                                              \
    X("x4u", x4u, prod, mul, u1, K_PROD, Ops, KB_SCOPE)                                            \
    X("x4u", x4u, prod, mulrand, u1, K_PRODRAND, Ops, KB_SCOPE)                                    \
    X("x4u", x4u, tp, det3pt, u1, K_DET, Ops, KB_SCOPE)                                            \
    X("x4u", x4u, tp, horner_pt, u1, K_HORNER_PT, Ops, KB_SCOPE)                                   \
    X("x4u", x4u, tp, horner_i, u1, K_HORNER_I, Ops, KB_SCOPE)

#define KB_X4U_DEF(B, SUF, KIND, KERNEL, VAR, K, OPS, SCOPE) KB_X4_FN(SUF, KIND, KERNEL, VAR, K, OPS, SCOPE)
KB_X4U_LIST(KB_X4U_DEF)

namespace {
const kairn_bench::m2::Entry table[] = {
    KB_X4U_LIST(KB_X4_ROW)
    {nullptr, nullptr, 0, 0, 0, 0, 0, nullptr},
};
kairn_bench::m2::TableLink link{table, nullptr};
[[maybe_unused]] const bool registered =
    (link.next = kairn_bench::m2::m2_extra_tables, kairn_bench::m2::m2_extra_tables = &link, true);
}  // namespace
