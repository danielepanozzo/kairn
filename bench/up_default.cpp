// The determinant of coordinate differences (bench/up_data.hpp: det3, the sign filter of an
// orientation test) for the default enclosure types of Kairn, double, backend m2, written for the
// benchmark of the round-up interval, whose own determinant is in up_type.cpp. Ordinary code,
// compiled as m2.cpp, under rounding to nearest. For each type that has -, * and +:
//
//   tp/det3_i1   Interval<double, 1>, on the intervals X, Y, F of m2.cpp
//   tp/det3_i2   Interval<double, 2>, on the intervals of two limbs X2, Y2, F2
//   tp/det3_b1   Ball<double, 1>, on the balls of X, Y, F
//   tp/det3_b2   Ball<double, 2>, on the balls of two limbs of m2.cpp
//   tp/det3_t    double rounded to nearest, on the numbers x, y, f: the floor
//
// with the variants kairn (Kairn's generated kernels on the limbs, up_kernels.hpp: the reference),
// op (the public operators on arrays of the type) and, for det3_t, plain (the operations of
// double). The results go to Raw<double>::out, element after element, as the limbs of the type.
// det3_i1/kairn is checked against the reference of the round-up interval's checks (up_check.cpp);
// each op and plain variant against its kairn variant, byte for byte; the other kairn variants are
// references, as in m2.cpp. The rounding-mode prop det3_i1/fenv_loop is in up_fenv.cpp, the round-up
// interval's det3_i1 in up_type.cpp.
#include <kairn/kairn.hpp>

#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#include "up_kernels.hpp"

namespace {

namespace up = kairn_bench::up;
using kairn_bench::m2::Entry;
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

// The operands as the public types, exactly the stored limbs.
struct DefData {
    I1<double> x1[kN], y1[kN], f1[kN];
    I2<double> x2[kN], y2[kN], f2[kN];
    B1<double> xb1[kN], yb1[kN], fb1[kN];
    B2<double> xb2[kN], yb2[kN], fb2[kN];
};
DefData* g_def = nullptr;

I1<double> i1_at(const double* a, int j) {
    return I1<double>(kairn::detail::kernel_result, E1<double>(a[2 * j]), E1<double>(a[2 * j + 1]));
}
I2<double> i2_at(const double* a, int j) {
    return I2<double>(kairn::detail::kernel_result, E2<double>::from_limbs(a + 4 * j), E2<double>::from_limbs(a + 4 * j + 2));
}
B1<double> b1_at(const double* a, int j) {
    return B1<double>(kairn::detail::kernel_result, E1<double>(a[2 * j]), a[2 * j + 1]);
}
B2<double> b2_at(const double* a, int j) {
    return B2<double>(kairn::detail::kernel_result, E2<double>::from_limbs(a + 3 * j), a[3 * j + 2]);
}

void fill(const Raw<double>& r) {
    if (!g_def) g_def = new DefData();
    for (int i = 0; i < kN; ++i) {
        g_def->x1[i] = i1_at(r.xi, i);
        g_def->y1[i] = i1_at(r.yi, i);
        g_def->f1[i] = i1_at(r.fi, i);
        g_def->x2[i] = i2_at(r.xi2, i);
        g_def->y2[i] = i2_at(r.yi2, i);
        g_def->f2[i] = i2_at(r.fi2, i);
        g_def->xb1[i] = b1_at(r.xb1, i);
        g_def->yb1[i] = b1_at(r.yb1, i);
        g_def->fb1[i] = b1_at(r.fb1, i);
        g_def->xb2[i] = b2_at(r.xb2, i);
        g_def->yb2[i] = b2_at(r.yb2, i);
        g_def->fb2[i] = b2_at(r.fb2, i);
    }
}

// The coordinates of the points: the stored limbs as the types of up_kernels.hpp (variant kairn),
// the public types (op), the numbers (plain, and the kairn variant of the floor).
struct LimbsI1 {
    const Raw<double>& r;
    up::K1<double> at(const double* a, int j) const { return {a[2 * j], a[2 * j + 1]}; }
    up::K1<double> x(int j) const { return at(r.xi, j); }
    up::K1<double> y(int j) const { return at(r.yi, j); }
    up::K1<double> f(int j) const { return at(r.fi, j); }
};
struct LimbsI2 {
    const Raw<double>& r;
    up::K2<double> at(const double* a, int j) const { return {a[4 * j], a[4 * j + 1], a[4 * j + 2], a[4 * j + 3]}; }
    up::K2<double> x(int j) const { return at(r.xi2, j); }
    up::K2<double> y(int j) const { return at(r.yi2, j); }
    up::K2<double> f(int j) const { return at(r.fi2, j); }
};
struct LimbsB1 {
    const Raw<double>& r;
    up::KB1<double> at(const double* a, int j) const { return {a[2 * j], a[2 * j + 1]}; }
    up::KB1<double> x(int j) const { return at(r.xb1, j); }
    up::KB1<double> y(int j) const { return at(r.yb1, j); }
    up::KB1<double> f(int j) const { return at(r.fb1, j); }
};
struct LimbsB2 {
    const Raw<double>& r;
    up::KB2<double> at(const double* a, int j) const { return {a[3 * j], a[3 * j + 1], a[3 * j + 2]}; }
    up::KB2<double> x(int j) const { return at(r.xb2, j); }
    up::KB2<double> y(int j) const { return at(r.yb2, j); }
    up::KB2<double> f(int j) const { return at(r.fb2, j); }
};
struct LimbsT {
    const Raw<double>& r;
    up::KT<double> x(int j) const { return {r.xa[j]}; }
    up::KT<double> y(int j) const { return {r.ya[j]}; }
    up::KT<double> f(int j) const { return {r.fa[j]}; }
};
struct PlainT {
    const Raw<double>& r;
    double x(int j) const { return r.xa[j]; }
    double y(int j) const { return r.ya[j]; }
    double f(int j) const { return r.fa[j]; }
};
template <class I, I (DefData::*X)[kN], I (DefData::*Y)[kN], I (DefData::*F)[kN]>
struct Public {
    const DefData& d;
    const I& x(int j) const { return (d.*X)[j]; }
    const I& y(int j) const { return (d.*Y)[j]; }
    const I& f(int j) const { return (d.*F)[j]; }
};
using PublicI1 = Public<I1<double>, &DefData::x1, &DefData::y1, &DefData::f1>;
using PublicI2 = Public<I2<double>, &DefData::x2, &DefData::y2, &DefData::f2>;
using PublicB1 = Public<B1<double>, &DefData::xb1, &DefData::yb1, &DefData::fb1>;
using PublicB2 = Public<B2<double>, &DefData::xb2, &DefData::yb2, &DefData::fb2>;

bool check_against_kairn(const Entry& e, char* why, std::size_t size);

}  // namespace

// --- The timed functions ------------------------------------------------------------------------

#define KB_EACH(...)                                                                               \
    for (int i = 0; i < kN; ++i) {                                                                 \
        __VA_ARGS__;                                                                               \
    }
#define DET(G, I) up::det3_at<I>(G, i)

// X(KERNEL, VARIANT, VALUES, CHECK, BODY...)
#define KB_DEFAULT_LIST(X)                                                                         \
    X(det3_i1, kairn, 2 * kN, up::check_raw_out, const LimbsI1 g{r};                               \
      KB_EACH(const up::K1<double> z = DET(g, up::K1<double>); r.out[2 * i] = z.l; r.out[2 * i + 1] = z.u)) \
    X(det3_i1, op, 2 * kN, check_against_kairn, const PublicI1 g{*kb_d};                           \
      KB_EACH(const I1<double> z = DET(g, I1<double>); r.out[2 * i] = z.lower().limb[0];           \
              r.out[2 * i + 1] = z.upper().limb[0]))                                               \
    X(det3_i2, kairn, 4 * kN, nullptr, const LimbsI2 g{r};                                         \
      KB_EACH(const up::K2<double> z = DET(g, up::K2<double>); r.out[4 * i] = z.l0; r.out[4 * i + 1] = z.l1; \
              r.out[4 * i + 2] = z.h0; r.out[4 * i + 3] = z.h1))                                   \
    X(det3_i2, op, 4 * kN, check_against_kairn, const PublicI2 g{*kb_d};                           \
      KB_EACH(const I2<double> z = DET(g, I2<double>); r.out[4 * i] = z.lower().limb[0];           \
              r.out[4 * i + 1] = z.lower().limb[1]; r.out[4 * i + 2] = z.upper().limb[0];          \
              r.out[4 * i + 3] = z.upper().limb[1]))                                               \
    X(det3_b1, kairn, 2 * kN, nullptr, const LimbsB1 g{r};                                         \
      KB_EACH(const up::KB1<double> z = DET(g, up::KB1<double>); r.out[2 * i] = z.c; r.out[2 * i + 1] = z.r)) \
    X(det3_b1, op, 2 * kN, check_against_kairn, const PublicB1 g{*kb_d};                           \
      KB_EACH(const B1<double> z = DET(g, B1<double>); r.out[2 * i] = z.center().limb[0];          \
              r.out[2 * i + 1] = z.radius()))                                                      \
    X(det3_b2, kairn, 3 * kN, nullptr, const LimbsB2 g{r};                                         \
      KB_EACH(const up::KB2<double> z = DET(g, up::KB2<double>); r.out[3 * i] = z.c0; r.out[3 * i + 1] = z.c1; \
              r.out[3 * i + 2] = z.r))                                                             \
    X(det3_b2, op, 3 * kN, check_against_kairn, const PublicB2 g{*kb_d};                           \
      KB_EACH(const B2<double> z = DET(g, B2<double>); r.out[3 * i] = z.center().limb[0];          \
              r.out[3 * i + 1] = z.center().limb[1]; r.out[3 * i + 2] = z.radius()))               \
    X(det3_t, kairn, kN, nullptr, const LimbsT g{r}; KB_EACH(r.out[i] = DET(g, up::KT<double>).v)) \
    X(det3_t, plain, kN, check_against_kairn, const PlainT g{r}; KB_EACH(r.out[i] = DET(g, double)))

#define KB_DEF(KERNEL, VAR, VALUES, CHECK, ...)                                                    \
    extern "C" KB_NOINLINE void kb_m2_64_tp_##KERNEL##__##VAR(void* kb_data) {                     \
        [[maybe_unused]] Raw<double>& r = *static_cast<Raw<double>*>(kb_data);                     \
        [[maybe_unused]] const DefData* kb_d = g_def;                                                  \
        __VA_ARGS__                                                                                \
    }
#define KB_ROW(KERNEL, VAR, VALUES, CHECK, ...)                                                    \
    {"m2/tp/" #KERNEL "/" #VAR, kb_m2_64_tp_##KERNEL##__##VAR, 64, 1, kN, R_OUT, VALUES, CHECK},

KB_DEFAULT_LIST(KB_DEF)

namespace {

const Entry table[] = {
    KB_DEFAULT_LIST(KB_ROW)
    {nullptr, nullptr, 0, 0, 0, 0, 0, nullptr},
};

std::vector<unsigned char> run_out(const Entry& e) {
    kairn_bench::m2::m2_clear(64);
    e.fn(kairn_bench::m2::m2_data(64));
    std::size_t bytes = 0;
    const unsigned char* p = kairn_bench::m2::m2_region(64, R_OUT, &bytes);
    const std::size_t n = std::size_t(e.values) * sizeof(double);
    return p && n <= bytes ? std::vector<unsigned char>(p, p + n) : std::vector<unsigned char>();
}

// An op or plain variant against the kairn variant of its kernel, byte for byte (m2_main.cpp's
// check, with the operands of this file filled first).
bool check_against_kairn(const Entry& e, char* why, std::size_t size) {
    fill(*static_cast<const Raw<double>*>(kairn_bench::m2::m2_data(64)));
    std::string ref = e.name;
    ref = ref.substr(0, ref.rfind('/')) + "/kairn";
    const Entry* k = nullptr;
    for (const Entry* t = table; t->name; ++t)
        if (ref == t->name) k = t;
    if (!k || k->values != e.values) {
        std::snprintf(why, size, "no reference %s", ref.c_str());
        return false;
    }
    const std::vector<unsigned char> want = run_out(*k), got = run_out(e);
    if (want.empty() || got.size() != want.size()) {
        std::snprintf(why, size, "no outputs");
        return false;
    }
    for (std::size_t i = 0; i < got.size(); i += sizeof(double))
        if (std::memcmp(got.data() + i, want.data() + i, sizeof(double)) != 0) {
            double a, b;
            std::memcpy(&a, got.data() + i, sizeof a);
            std::memcpy(&b, want.data() + i, sizeof b);
            std::snprintf(why, size, "value %zu: %a != %a", i / sizeof(double), a, b);
            return false;
        }
    std::fprintf(stderr, "up check: %s: %d values equal to %s, byte for byte\n", e.name, e.values, ref.c_str());
    return true;
}

kairn_bench::m2::TableLink link{table, nullptr};
[[maybe_unused]] const bool registered =
    (link.next = kairn_bench::m2::m2_extra_tables, kairn_bench::m2::m2_extra_tables = &link, true);

}  // namespace
