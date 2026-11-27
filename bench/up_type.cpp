// The round-up interval kairn::upward::Interval<T>, one interval per register (bench/up_data.hpp),
// for double (backend upw) and float (upwf), and the cost of its scopes (backend upws). Requires the
// rounding mode upward set by kairn::upward::Scope and the options of docs/concepts/upward.md (GCC
// and Clang -frounding-math, MSVC /fp:strict): bench/CMakeLists.txt compiles this file with the
// option of the target kairn::upward, and every function here that rounds holds a Scope or runs
// inside one.
//
// The type: loops of sums, differences and products (KIND tp), a chain of sums and one of products
// (sum, prod), Horner (tp, and lat: dependent evaluations), the determinant of coordinate
// differences (tp/det3_i1), each timed function holding one Scope around its loop or chain, as a
// program holds one around a region of many operations. Two layouts:
// - native: arrays of kairn::upward::Interval<T> filled outside the timed function, the results to
//   such an array;
// - conv: arrays of the default kairn::Interval<T, 1>, (lower, upper) in memory, each operand
//   converted in the loop (kairn::upward::Interval<T>(x), upward_from_interval_1) and each result
//   back (to_interval(), upward_to_interval_1): what the conversions cost a program that keeps the
//   default layout;
// and native_x16, the loop of native 16 times inside one Scope (the scope's share of a call 1/16th;
// for a chain, the chain 16 times as long: 16 kN steps over the elements again).
// The conversions alone, tp/from_interval_1/op and tp/to_interval_1/op, are loops without a scope
// (they are exact, in every mode).
//
// The scopes (upws/call/KERNEL/VARIANT, double, time per call): a non-inlined function that holds
// a scope around one operation, called kN times: scope_add_1 (a kairn::upward::Scope around one sum
// of the type), regscope_add_1 (the register-only scope that each function on arrays holds,
// kairn::upward::detail::RegisterScope, around the same sum), nearest_add_1 (a
// kairn::upward::NearestScope around one sum of the default Interval<double, 1>). VARIANT change:
// the scope changes the mode (called from code that rounds to nearest; nearest_add_1 from inside an
// upward Scope); nested: it changes nothing (scope_add_1 and regscope_add_1 inside an outer Scope,
// nearest_add_1 from code that rounds to nearest); none: the same call without the scope
// (scope_add_1/none inside an outer Scope, for both upward scopes; nearest_add_1/none from code
// that rounds to nearest). The cost of a scope is the time of a call with it minus none.
#include <kairn/kairn.hpp>
#include <kairn/upward.hpp>

#include <cstring>
#include <new>
#include <string>

#include "up_data.hpp"

namespace {

namespace ku = kairn::upward;
namespace up = kairn_bench::up;
using kairn_bench::m2::Entry;
using kairn_bench::m2::kDeg;
using kairn_bench::m2::kN;
using kairn_bench::m2::Raw;

template <class T>
using U = ku::Interval<T>;
template <class T>
using I1 = kairn::Interval<T, 1>;
template <class T>
using E1 = kairn::Expansion<T, 1>;

// The operands and results of one limb type: X, Y, F, the Horner arguments H and coefficients C
// (points of T8, m2.cpp), as the type and as the default type. The arrays of kN elements are placed
// as up_data.hpp says (Placed): the type's read in the slots 0 to 3 and written in slot 8, the
// default's read in the slots 4 to 7 and written in slot 10.
template <class T, class V>
V* placed_array(const up::Placed& p, int k) {
    V* a = p.at<V>(k);
    for (int i = 0; i < kN; ++i) new (a + i) V();
    return a;
}
template <class T>
struct TypeData {
    up::Placed place{kN * sizeof(I1<T>) > kN * sizeof(U<T>) ? kN * sizeof(I1<T>) : kN * sizeof(U<T>)};
    U<T>* x = placed_array<T, U<T>>(place, 0);
    U<T>* y = placed_array<T, U<T>>(place, 1);
    U<T>* f = placed_array<T, U<T>>(place, 2);
    U<T>* h = placed_array<T, U<T>>(place, 3);
    U<T>* z = placed_array<T, U<T>>(place, 8);
    I1<T>* x1 = placed_array<T, I1<T>>(place, 4);
    I1<T>* y1 = placed_array<T, I1<T>>(place, 5);
    I1<T>* f1 = placed_array<T, I1<T>>(place, 6);
    I1<T>* h1 = placed_array<T, I1<T>>(place, 7);
    I1<T>* z1 = placed_array<T, I1<T>>(place, 10);
    U<T> c[kDeg + 1];
    U<T> s;
    I1<T> c1[kDeg + 1];
    I1<T> s1;
};
TypeData<double>* g64 = nullptr;
TypeData<float>* g32 = nullptr;

template <class T>
TypeData<T>& data();
template <>
TypeData<double>& data<double>() {
    return *g64;
}
template <>
TypeData<float>& data<float>() {
    return *g32;
}

// The default interval of the stored bounds a[2 j], a[2 j + 1], exactly those numbers.
template <class T>
I1<T> stored(const T* a, int j) {
    return I1<T>(kairn::detail::kernel_result, E1<T>(a[2 * j]), E1<T>(a[2 * j + 1]));
}

template <class T>
void fill(TypeData<T>*& p, const Raw<T>& r) {
    if (!p) p = new TypeData<T>();
    TypeData<T>& d = *p;
    for (int i = 0; i < kN; ++i) {
        d.x1[i] = stored(r.xi, i);
        d.y1[i] = stored(r.yi, i);
        d.f1[i] = stored(r.fi, i);
        d.h1[i] = stored(r.hi1, i);
        d.x[i] = U<T>(d.x1[i]);
        d.y[i] = U<T>(d.y1[i]);
        d.f[i] = U<T>(d.f1[i]);
        d.h[i] = U<T>(d.h1[i]);
    }
    for (int k = 0; k <= kDeg; ++k) {
        d.c1[k] = I1<T>(r.hc[k]);
        d.c[k] = U<T>(d.c1[k]);
    }
}

template <class T>
void clear_t(TypeData<T>& d) {
    std::memset(static_cast<void*>(d.z), 0xff, kN * sizeof(U<T>));
    std::memset(static_cast<void*>(&d.s), 0xff, sizeof d.s);
    std::memset(static_cast<void*>(d.z1), 0xff, kN * sizeof(I1<T>));
    std::memset(static_cast<void*>(&d.s1), 0xff, sizeof d.s1);
}
void clear(int bits) {
    if (bits == 32)
        clear_t(*g32);
    else
        clear_t(*g64);
}

// The bounds of a result, (lower, upper): -n and u of the type's stored pair, or the default's.
template <class T>
void put(const U<T>& v, T* o) {
    T p[2];
    v.to_limbs(p);
    o[0] = -p[1];
    o[1] = p[0];
}
template <class T>
void put(const I1<T>& v, T* o) {
    o[0] = v.lower().limb[0];
    o[1] = v.upper().limb[0];
}

// The results of entry e: in the type's arrays (native, the upward scopes, from_interval_1) or in
// the default's (conv, nearest_add_1, to_interval_1); a chain one interval.
template <class T>
int read_t(const Entry& e, T* o) {
    const TypeData<T>& d = data<T>();
    const std::string name = e.name;
    const bool chain = name.find("/sum/") != std::string::npos || name.find("/prod/") != std::string::npos ||
                       name.find("/lat/") != std::string::npos;
    const bool def = name.find("/conv") != std::string::npos || name.find("nearest_add_1") != std::string::npos ||
                     name.find("to_interval_1") != std::string::npos;
    if (chain) {
        if (def)
            put(d.s1, o);
        else
            put(d.s, o);
        return 1;
    }
    for (int i = 0; i < kN; ++i) {
        if (def)
            put(d.z1[i], o + 2 * i);
        else
            put(d.z[i], o + 2 * i);
    }
    return kN;
}
int read(const Entry& e, void* lohi) {
    return e.bits == 32 ? read_t(e, static_cast<float*>(lohi)) : read_t(e, static_cast<double*>(lohi));
}

bool check(const Entry& e, char* why, std::size_t size) {
    const void* raw = kairn_bench::m2::m2_data(e.bits);
    if (e.bits == 32)
        fill(g32, *static_cast<const Raw<float>*>(raw));
    else
        fill(g64, *static_cast<const Raw<double>*>(raw));
    return up::run_and_check(e, clear, read, why, size);
}

// The coordinates of the determinant's points: the type's arrays, or the default's converted.
template <class T>
struct Native {
    const TypeData<T>& d;
    const U<T>& x(int j) const { return d.x[j]; }
    const U<T>& y(int j) const { return d.y[j]; }
    const U<T>& f(int j) const { return d.f[j]; }
};
template <class T>
struct Converted {
    const TypeData<T>& d;
    U<T> x(int j) const { return U<T>(d.x1[j]); }
    U<T> y(int j) const { return U<T>(d.y1[j]); }
    U<T> f(int j) const { return U<T>(d.f1[j]); }
};

}  // namespace

// --- The calls of the scopes ----------------------------------------------------------------------
//
// External linkage, not inlined, not specialized (noipa with GCC): the call is what a program makes
// to a function of its own that holds a scope.
extern "C" KB_UP_NOIPA void kb_upws_one_none(const U<double>* x, const U<double>* y, U<double>* z) noexcept {
    *z = *x + *y;
}
extern "C" KB_UP_NOIPA void kb_upws_one_scope(const U<double>* x, const U<double>* y, U<double>* z) noexcept {
    ku::Scope scope;
    *z = *x + *y;
}
extern "C" KB_UP_NOIPA void kb_upws_one_regscope(const U<double>* x, const U<double>* y, U<double>* z) noexcept {
    ku::detail::RegisterScope scope;
    *z = *x + *y;
}
extern "C" KB_UP_NOIPA void kb_upws_one_default(const I1<double>* x, const I1<double>* y, I1<double>* z) noexcept {
    *z = *x + *y;
}
extern "C" KB_UP_NOIPA void kb_upws_one_nearest(const I1<double>* x, const I1<double>* y, I1<double>* z) noexcept {
    ku::NearestScope nearest;
    *z = *x + *y;
}

// --- The timed functions ------------------------------------------------------------------------

#define KB_EACH(...)                                                                               \
    for (int i = 0; i < kN; ++i) {                                                                 \
        __VA_ARGS__;                                                                               \
    }
#define KB_PASSES(...)                                                                             \
    for (int pass = 0; pass < up::kPasses; ++pass) {                                               \
        __VA_ARGS__;                                                                               \
        KB_UP_FENCE();                                                                             \
    }
// An operand of the default layout, converted.
#define CV(A) U<T>(d.A[i])

// X(B, SUF, T, KIND, KERNEL, VARIANT, OPS, BODY...): one timed function, OPS operations per call.
#define KB_TYPE_LIST(X, B, SUF, T)                                                                 \
    X(B, SUF, T, tp, interval_add_1, native, kN, ku::Scope scope; KB_EACH(d.z[i] = d.x[i] + d.y[i]))  \
    X(B, SUF, T, tp, interval_add_1, conv, kN, ku::Scope scope; KB_EACH(d.z1[i] = (CV(x1) + CV(y1)).to_interval())) \
    X(B, SUF, T, tp, interval_mul_1, native, kN, ku::Scope scope; KB_EACH(d.z[i] = d.x[i] * d.y[i]))  \
    X(B, SUF, T, tp, interval_mul_1, conv, kN, ku::Scope scope; KB_EACH(d.z1[i] = (CV(x1) * CV(y1)).to_interval()))
#define KB_TYPE_LIST_DOUBLE(X, B, SUF, T)                                                          \
    KB_TYPE_LIST(X, B, SUF, T)                                                                     \
    X(B, SUF, T, tp, interval_add_1, native_x16, up::kPasses * kN, ku::Scope scope;                   \
      KB_PASSES(KB_EACH(d.z[i] = d.x[i] + d.y[i])))                                                \
    X(B, SUF, T, tp, interval_mul_1, native_x16, up::kPasses * kN, ku::Scope scope;                   \
      KB_PASSES(KB_EACH(d.z[i] = d.x[i] * d.y[i])))                                                \
    X(B, SUF, T, tp, interval_sub_1, native, kN, ku::Scope scope; KB_EACH(d.z[i] = d.x[i] - d.y[i]))  \
    X(B, SUF, T, tp, interval_sub_1, conv, kN, ku::Scope scope; KB_EACH(d.z1[i] = (CV(x1) - CV(y1)).to_interval())) \
    X(B, SUF, T, tp, interval_sub_1, native_x16, up::kPasses * kN, ku::Scope scope;                   \
      KB_PASSES(KB_EACH(d.z[i] = d.x[i] - d.y[i])))                                                \
    X(B, SUF, T, sum, interval_add_1, native, kN, ku::Scope scope; U<T> s; KB_EACH(s = s + d.x[i]) d.s = s;) \
    X(B, SUF, T, sum, interval_add_1, native_x16, up::kPasses * kN, ku::Scope scope; U<T> s;          \
      for (int pass = 0; pass < up::kPasses; ++pass) KB_EACH(s = s + d.x[i]) d.s = s;)             \
    X(B, SUF, T, prod, interval_mul_1, native_x16, up::kPasses * kN, ku::Scope scope; U<T> p(T(1));   \
      for (int pass = 0; pass < up::kPasses; ++pass) KB_EACH(p = p * d.f[i]) d.s = p;)             \
    X(B, SUF, T, sum, interval_add_1, conv, kN, ku::Scope scope; U<T> s; KB_EACH(s = s + CV(x1)) d.s1 = s.to_interval();) \
    X(B, SUF, T, prod, interval_mul_1, native, kN, ku::Scope scope; U<T> p(T(1)); KB_EACH(p = p * d.f[i]) d.s = p;) \
    X(B, SUF, T, prod, interval_mul_1, conv, kN, ku::Scope scope; U<T> p(T(1)); KB_EACH(p = p * CV(f1))  \
      d.s1 = p.to_interval();)                                                                     \
    X(B, SUF, T, tp, horner_i1, native, kN, ku::Scope scope; KB_EACH(d.z[i] = up::horner(d.c, d.h[i]))) \
    X(B, SUF, T, tp, horner_i1, conv, kN, ku::Scope scope; U<T> c[kDeg + 1];                          \
      for (int k = 0; k <= kDeg; ++k) c[k] = U<T>(d.c1[k]);                                        \
      KB_EACH(d.z1[i] = up::horner(c, CV(h1)).to_interval()))                                      \
    X(B, SUF, T, lat, horner_i1, native, kN, ku::Scope scope; T zz = 0; U<T> p;                       \
      KB_EACH(p = up::horner(d.c, d.h[i] + zz); zz = p.upper() * T(0)) d.s = p;)                   \
    X(B, SUF, T, lat, horner_i1, conv, kN, ku::Scope scope; U<T> c[kDeg + 1];                         \
      for (int k = 0; k <= kDeg; ++k) c[k] = U<T>(d.c1[k]);                                        \
      T zz = 0; U<T> p; KB_EACH(p = up::horner(c, CV(h1) + zz); zz = p.upper() * T(0)) d.s1 = p.to_interval();) \
    X(B, SUF, T, tp, det3_i1, native, kN, ku::Scope scope; const Native<T> g{d};                      \
      KB_EACH(d.z[i] = up::det3_at<U<T>>(g, i)))                                                   \
    X(B, SUF, T, tp, det3_i1, conv, kN, ku::Scope scope; const Converted<T> g{d};                     \
      KB_EACH(d.z1[i] = up::det3_at<U<T>>(g, i).to_interval()))                                    \
    X(B, SUF, T, tp, from_interval_1, op, kN, KB_EACH(d.z[i] = CV(x1)))                            \
    X(B, SUF, T, tp, to_interval_1, op, kN, KB_EACH(d.z1[i] = d.x[i].to_interval()))

#define KB_SCOPE_LIST(X, B, SUF, T)                                                                \
    X(B, SUF, T, call, scope_add_1, none, kN, ku::Scope scope; KB_EACH(kb_upws_one_none(&d.x[i], &d.y[i], &d.z[i]))) \
    X(B, SUF, T, call, scope_add_1, change, kN, KB_EACH(kb_upws_one_scope(&d.x[i], &d.y[i], &d.z[i]))) \
    X(B, SUF, T, call, scope_add_1, nested, kN, ku::Scope scope; KB_EACH(kb_upws_one_scope(&d.x[i], &d.y[i], &d.z[i]))) \
    X(B, SUF, T, call, regscope_add_1, change, kN, KB_EACH(kb_upws_one_regscope(&d.x[i], &d.y[i], &d.z[i]))) \
    X(B, SUF, T, call, regscope_add_1, nested, kN, ku::Scope scope;                                   \
      KB_EACH(kb_upws_one_regscope(&d.x[i], &d.y[i], &d.z[i])))                                    \
    X(B, SUF, T, call, nearest_add_1, none, kN, KB_EACH(kb_upws_one_default(&d.x1[i], &d.y1[i], &d.z1[i]))) \
    X(B, SUF, T, call, nearest_add_1, change, kN, ku::Scope scope;                                    \
      KB_EACH(kb_upws_one_nearest(&d.x1[i], &d.y1[i], &d.z1[i])))                                  \
    X(B, SUF, T, call, nearest_add_1, nested, kN, KB_EACH(kb_upws_one_nearest(&d.x1[i], &d.y1[i], &d.z1[i])))

#define KB_DEF(B, SUF, TYPE, KIND, KERNEL, VAR, OPS, ...)                                          \
    extern "C" KB_NOINLINE void kb_##SUF##_##KIND##_##KERNEL##__##VAR(void*) {                     \
        using T = TYPE;                                                                            \
        [[maybe_unused]] TypeData<T>& d = data<T>();                                               \
        __VA_ARGS__                                                                                \
    }
#define KB_ROW(B, SUF, T, KIND, KERNEL, VAR, OPS, ...)                                             \
    {B "/" #KIND "/" #KERNEL "/" #VAR, kb_##SUF##_##KIND##_##KERNEL##__##VAR, int(8 * sizeof(T)), 1, OPS, 0, 0, check},

KB_TYPE_LIST_DOUBLE(KB_DEF, "upw", upw, double)
KB_TYPE_LIST(KB_DEF, "upwf", upwf, float)
KB_SCOPE_LIST(KB_DEF, "upws", upws, double)

namespace {
const Entry table[] = {
    KB_TYPE_LIST_DOUBLE(KB_ROW, "upw", upw, double)
    KB_TYPE_LIST(KB_ROW, "upwf", upwf, float)
    KB_SCOPE_LIST(KB_ROW, "upws", upws, double)
    {nullptr, nullptr, 0, 0, 0, 0, 0, nullptr},
};
kairn_bench::m2::TableLink link{table, nullptr};
[[maybe_unused]] const bool registered =
    (link.next = kairn_bench::m2::m2_extra_tables, kairn_bench::m2::m2_extra_tables = &link, true);
}  // namespace
