// The floor of the benchmark of 1, 2 and 4 limbs (bench/x4_data.hpp): plain double arithmetic, backend
// x4f, variant double, on the same operands (each interval's upper bound's first limb, the points as
// they are). Ordinary code, compiled as m2.cpp, under rounding to nearest. Not an enclosure: its
// results are checked only against their reference, bit for bit.
#include "x4_unit.hpp"

namespace {

namespace x4 = kairn_bench::x4;
using T = double;

struct Ops {
    static KB_X2_INLINE T add(T a, T b) { return a + b; }
    static KB_X2_INLINE T sub(T a, T b) { return a - b; }
    static KB_X2_INLINE T mul(T a, T b) { return a * b; }
    static KB_X2_INLINE T sqr(T a) { return a * a; }
    static KB_X2_INLINE T zero() { return 0.0; }
    static KB_X2_INLINE T one() { return 1.0; }
};

x4::Data<T>* g = nullptr;

void fill() {
    if (!g) g = new x4::Data<T>();
    x4::fill(*g, [](const double* p) { return p[2]; }, [](double t) { return t; });
}
void clear() { x4::clear_results(*g); }
void put(const T& v, double* o) {
    for (int i = 0; i < 8; ++i) o[i] = 0;
    o[0] = v;
    o[4] = v;
}
int read(const char* name, double* out) { return x4::read_results(x4::parse(name).kernel, *g, put, out); }
int reference(const char* name, double* out) {
    const x4::Local<T> d = x4::local(*g);
    x4::run<T, Ops>(x4::parse(name).kernel, d, x4::VRead{});
    return read(name, out);
}

x4::Unit unit{"x4f", nullptr, false, fill, clear, read, reference, nullptr, nullptr};
[[maybe_unused]] const bool unit_registered = (unit.next = x4::units, x4::units = &unit, true);

}  // namespace

#define KB_X4F_LIST(X)                                                                             \
    X("x4f", x4f, tp, add, double, K_ADD, Ops, (void)0)                                            \
    X("x4f", x4f, tp, sub, double, K_SUB, Ops, (void)0)                                            \
    X("x4f", x4f, tp, mul, double, K_MUL, Ops, (void)0)                                            \
    X("x4f", x4f, tp, mulrand, double, K_MULRAND, Ops, (void)0)                                    \
    X("x4f", x4f, tp, sqr, double, K_SQR, Ops, (void)0)                                            \
    X("x4f", x4f, sum, add, double, K_SUM, Ops, (void)0)                                           \
    X("x4f", x4f, prod, mul, double, K_PROD, Ops, (void)0)                                         \
    X("x4f", x4f, tp, det3pt, double, K_DET, Ops, (void)0)                                         \
    X("x4f", x4f, tp, horner_pt, double, K_HORNER_PT, Ops, (void)0)                                \
    X("x4f", x4f, tp, horner_i, double, K_HORNER_I, Ops, (void)0)

#define KB_X4F_DEF(B, SUF, KIND, KERNEL, VAR, K, OPS, SCOPE) KB_X4_FN(SUF, KIND, KERNEL, VAR, K, OPS, SCOPE)
KB_X4F_LIST(KB_X4F_DEF)

namespace {
const kairn_bench::m2::Entry table[] = {
    KB_X4F_LIST(KB_X4_ROW)
    {nullptr, nullptr, 0, 0, 0, 0, 0, nullptr},
};
kairn_bench::m2::TableLink link{table, nullptr};
[[maybe_unused]] const bool registered =
    (link.next = kairn_bench::m2::m2_extra_tables, kairn_bench::m2::m2_extra_tables = &link, true);
}  // namespace
