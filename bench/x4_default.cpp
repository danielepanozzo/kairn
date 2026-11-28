// The default enclosures of Kairn on the operands of the benchmark of 1, 2 and 4 limbs
// (bench/x4_data.hpp), backend x4d: kairn::Interval<double, 1> (variant i1), Ball<double, 1> (b1),
// Interval<double, 2> (i2) and Ball<double, 2> (b2), through their public operators. Ordinary code,
// compiled as m2.cpp, under rounding to nearest. The operands: the intervals of two limbs as they are
// (i2), each bound rounded outward to one limb (i1: the greatest number below the lower bound, the
// least above the upper bound, as the round-up type of one limb has them), the balls enclosing those
// intervals (b1, b2), the points as they are. The default types have no square: no tp/sqr here.
#include <kairn/kairn.hpp>

#include <cmath>

#include "x4_unit.hpp"

namespace {

namespace x4 = kairn_bench::x4;
using I1 = kairn::Interval<double, 1>;
using I2 = kairn::Interval<double, 2>;
using B1 = kairn::Ball<double, 1>;
using B2 = kairn::Ball<double, 2>;
using E1 = kairn::Expansion<double, 1>;

// The one-limb interval around (l0 + l1, h0 + h1) of a canonical two-limb one: RD(l0 + l1) is l0, or
// the number below it where l1 < 0 (|l1| <= ulp(l0) / 2, and at a power of two the gap below is ulp/2,
// so l0 + l1 is at least pred(l0)); RU(h0 + h1) likewise.
I1 outward(const double* p) {
    const double lo = p[1] < 0 ? std::nextafter(p[0], -HUGE_VAL) : p[0];
    const double hi = p[3] > 0 ? std::nextafter(p[2], HUGE_VAL) : p[2];
    return I1(E1(lo), E1(hi));
}
void put_i1(const I1& v, double* o) {
    for (int i = 0; i < 8; ++i) o[i] = 0;
    o[0] = v.lower().limb[0];
    o[4] = v.upper().limb[0];
}
void put_i2(const I2& v, double* o) {
    for (int i = 0; i < 8; ++i) o[i] = 0;
    o[0] = v.lower().limb[0];
    o[1] = v.lower().limb[1];
    o[4] = v.upper().limb[0];
    o[5] = v.upper().limb[1];
}

template <class T>
struct Ops {
    static KB_X2_INLINE T add(const T& a, const T& b) { return a + b; }
    static KB_X2_INLINE T sub(const T& a, const T& b) { return a - b; }
    static KB_X2_INLINE T mul(const T& a, const T& b) { return a * b; }
    static KB_X2_INLINE T sqr(const T& a) { return a * a; }
    static KB_X2_INLINE T zero() { return T(0.0); }
    static KB_X2_INLINE T one() { return T(1.0); }
};

}  // namespace

// One block per type: the data, the unit's functions, the timed functions and their table.
#define KB_X4D_BLOCK(NS, TYPE, VAR, CI, PUT, STEP)                                                 \
    namespace NS {                                                                                 \
    using T = TYPE;                                                                                \
    x4::Data<T>* g = nullptr;                                                                      \
    void fill() {                                                                                  \
        if (!g) g = new x4::Data<T>();                                                             \
        x4::fill(*g, CI, [](double t) { return T(t); });                                           \
    }                                                                                              \
    void clear() { x4::clear_results(*g); }                                                        \
    int read(const char* name, double* out) { return x4::read_results(x4::parse(name).kernel, *g, PUT, out); } \
    int reference(const char* name, double* out) {                                                 \
        const x4::Local<T> d = x4::local(*g);                                                      \
        x4::run<T, Ops<T>>(x4::parse(name).kernel, d, x4::VRead{});                                \
        return read(name, out);                                                                    \
    }                                                                                              \
    bool step(const char* name, const double* before, int k, double* after) {                      \
        const x4::Name n = x4::parse(name);                                                        \
        T s;                                                                                       \
        if (!STEP(before, s)) return false;                                                        \
        const T r = n.kernel == x4::K_SUM ? Ops<T>::add(s, g->x[k])                                \
                                          : Ops<T>::mul(s, n.kernel == x4::K_PRODRAND ? g->fr[k] : g->f[k]); \
        PUT(r, after);                                                                             \
        return true;                                                                               \
    }                                                                                              \
    x4::Unit unit{"x4d", #VAR, true, fill, clear, read, reference, step, nullptr};                       \
    KB_X4_FN(x4d, tp, add, VAR, K_ADD, Ops<T>, (void)0)                                            \
    KB_X4_FN(x4d, tp, sub, VAR, K_SUB, Ops<T>, (void)0)                                            \
    KB_X4_FN(x4d, tp, mul, VAR, K_MUL, Ops<T>, (void)0)                                            \
    KB_X4_FN(x4d, tp, mulpos, VAR, K_MULPOS, Ops<T>, (void)0)                                      \
    KB_X4_FN(x4d, tp, mulzero, VAR, K_MULZERO, Ops<T>, (void)0)                                    \
    KB_X4_FN(x4d, tp, mulrand, VAR, K_MULRAND, Ops<T>, (void)0)                                    \
    KB_X4_FN(x4d, sum, add, VAR, K_SUM, Ops<T>, (void)0)                                           \
    KB_X4_FN(x4d, prod, mul, VAR, K_PROD, Ops<T>, (void)0)                                         \
    KB_X4_FN(x4d, prod, mulrand, VAR, K_PRODRAND, Ops<T>, (void)0)                                 \
    KB_X4_FN(x4d, tp, det3pt, VAR, K_DET, Ops<T>, (void)0)                                         \
    KB_X4_FN(x4d, tp, horner_pt, VAR, K_HORNER_PT, Ops<T>, (void)0)                                \
    KB_X4_FN(x4d, tp, horner_i, VAR, K_HORNER_I, Ops<T>, (void)0)                                  \
    const kairn_bench::m2::Entry table[] = {                                                       \
        KB_X4_ROW("x4d", x4d, tp, add, VAR, K_ADD, Ops<T>, 0)                                      \
        KB_X4_ROW("x4d", x4d, tp, sub, VAR, K_SUB, Ops<T>, 0)                                      \
        KB_X4_ROW("x4d", x4d, tp, mul, VAR, K_MUL, Ops<T>, 0)                                      \
        KB_X4_ROW("x4d", x4d, tp, mulpos, VAR, K_MULPOS, Ops<T>, 0)                                \
        KB_X4_ROW("x4d", x4d, tp, mulzero, VAR, K_MULZERO, Ops<T>, 0)                              \
        KB_X4_ROW("x4d", x4d, tp, mulrand, VAR, K_MULRAND, Ops<T>, 0)                              \
        KB_X4_ROW("x4d", x4d, sum, add, VAR, K_SUM, Ops<T>, 0)                                     \
        KB_X4_ROW("x4d", x4d, prod, mul, VAR, K_PROD, Ops<T>, 0)                                   \
        KB_X4_ROW("x4d", x4d, prod, mulrand, VAR, K_PRODRAND, Ops<T>, 0)                           \
        KB_X4_ROW("x4d", x4d, tp, det3pt, VAR, K_DET, Ops<T>, 0)                                   \
        KB_X4_ROW("x4d", x4d, tp, horner_pt, VAR, K_HORNER_PT, Ops<T>, 0)                          \
        KB_X4_ROW("x4d", x4d, tp, horner_i, VAR, K_HORNER_I, Ops<T>, 0)                            \
        {nullptr, nullptr, 0, 0, 0, 0, 0, nullptr},                                                \
    };                                                                                             \
    kairn_bench::m2::TableLink link{table, nullptr};                                               \
    [[maybe_unused]] const bool registered = (unit.next = x4::units, x4::units = &unit,             \
                                             link.next = kairn_bench::m2::m2_extra_tables,          \
                                             kairn_bench::m2::m2_extra_tables = &link, true);       \
    }

namespace {
bool step_i1(const double* b, I1& s) {
    s = I1(E1(b[0]), E1(b[4]));
    return true;
}
bool step_i2(const double* b, I2& s) {
    const double p[4] = {b[0], b[1], b[4], b[5]};
    s = I2::from_limbs(p);
    return true;
}
template <class T>
bool no_step(const double*, T&) {
    return false;
}
}  // namespace

KB_X4D_BLOCK(x4d_i1, I1, i1, [](const double* p) { return outward(p); }, put_i1, step_i1)
KB_X4D_BLOCK(x4d_i2, I2, i2, [](const double* p) { return I2::from_limbs(p); }, put_i2, step_i2)
KB_X4D_BLOCK(x4d_b1, B1, b1, [](const double* p) { return B1(outward(p)); }, [](const B1& v, double* o) { put_i1(I1(v), o); }, no_step<B1>)
KB_X4D_BLOCK(x4d_b2, B2, b2, [](const double* p) { return B2(I2::from_limbs(p)); }, [](const B2& v, double* o) { put_i2(I2(v), o); }, no_step<B2>)
