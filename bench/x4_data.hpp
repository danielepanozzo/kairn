// The benchmark of 1, 2 and 4 limbs (experiments/upward4/README.md, which says how to build and run
// it): what the units x4_*.cpp share. EXPERIMENTAL, NOT VERIFIED, not part of the library. Requires
// the rounding mode upward set by kairn::upward::Scope and the options of docs/concepts/upward.md (GCC
// and Clang -frounding-math): the units of the round-up types (x4_type.cpp, x4_one.cpp) are compiled
// with the option of the target kairn::upward and every timed function there holds one Scope; the
// default types (x4_default.cpp) and plain double (x4_floor.cpp) are compiled as a client compiles them.
// This header includes no Kairn header.
//
// Every unit times the same operands, the two-limb experiment's (bench/x2_data.hpp, x2::ops()), each
// converted to the unit's type outside the timed functions: the intervals X, Y, F, H, XP, YP, XZ, YZ,
// XR, YR, FR (exactly for the types of two limbs and more; rounded outward to one limb for the types
// of one limb) and the points px, py, pz, ht, hc (exact doubles). Element i of a loop of a binary
// operation is X[i] op Y[i]; element i of the determinant is x2::det3pt_at on the points i to i + 3.
//
// The functions, BACKEND/KIND/KERNEL/VARIANT (every backend the same kernels where it has them): tp/add,
// tp/sub, tp/mul, tp/mulpos (one sign), tp/mulzero (around zero), tp/mulrand (random signs, kRand per
// call), tp/sqr, sum/add (a chain of sums), prod/mul and prod/mulrand (chains of products), tp/det3pt
// (on points), tp/horner_pt (on points), tp/horner_i (on intervals). Backends: x4 (the four-limb type;
// variants native and the forms), x4u (kairn::upward::Interval<double>, variant u1), x4d (the default
// types: i1 Interval<double, 1>, b1 Ball<double, 1>, i2 Interval<double, 2>, b2 Ball<double, 2>), x4f
// (plain double, variant double: the floor), x4a (the four-limb functions on arrays). The two-limb
// round-up type is the backend x2 (x2_type.cpp) on the same operands.
#pragma once

#include <cstddef>
#include <new>

#include "up_data.hpp"
#include "x2_data.hpp"

namespace kairn_bench::x4 {

using m2::Entry;
using m2::kDeg;
using m2::kN;
using x2::kRand;
namespace up = kairn_bench::up;

// One unit of timed functions, which registers itself before main: what the check needs.
struct Unit {
    const char* backend;
    // The variant of its functions, or nullptr for every variant of the backend (the units of x4d hold
    // one type each, its variant).
    const char* variant;
    // Whether its results are enclosures (all but the floor, plain double).
    bool encloses;
    void (*fill)();
    void (*clear)();
    // The results of entry `name` after it ran, 8 numbers per element: the lower bound as the exact sum
    // l0 + l1 + l2 + l3 and the upper bound h0 + h1 + h2 + h3 (unused numbers zero); the number of
    // elements.
    int (*read)(const char* name, double* out);
    // The same computation through operands read from volatile objects, by the same kernels (the
    // reference of a timed function, bit for bit), or nullptr; the number of elements.
    int (*reference)(const char* name, double* out);
    // A chain step by step: the state after step k from the state before it (8 numbers each, as read
    // gives them), by the same kernel; false where the state cannot be rebuilt from its bounds (a ball).
    bool (*step)(const char* name, const double* before, int k, double* after);
    Unit* next;
};
extern Unit* units;   // constant-initialized, in x4_check.cpp

// The check of every function of these units (x4_check.cpp): before it is timed.
bool check(const Entry& e, char* why, std::size_t size);

// The arrays of one type T, placed as up_data.hpp says, filled from x2::ops() by the unit's conversions.
template <class T>
struct Data {
    up::Placed a{kN * sizeof(T)}, b{kN * sizeof(T)}, c{kN * sizeof(T)}, r{kRand * sizeof(T)};
    T* x = arr(a, 0);
    T* y = arr(a, 1);
    T* f = arr(a, 2);
    T* h = arr(a, 3);
    T* z = arr(a, 8);
    T* xp = arr(b, 0);
    T* yp = arr(b, 1);
    T* xz = arr(b, 4);
    T* yz = arr(b, 5);
    T* zb = arr(b, 8);
    T* zc = arr(b, 10);
    T* px = arr(c, 0);
    T* py = arr(c, 1);
    T* pz = arr(c, 2);
    T* ht = arr(c, 3);
    T* zd = arr(c, 8);
    T* xr = arr(r, 0, kRand);
    T* yr = arr(r, 1, kRand);
    T* fr = arr(r, 2, kRand);
    T* zr = arr(r, 8, kRand);
    T hc[kDeg + 1];
    T s;
    static T* arr(const up::Placed& p, int k, int n = kN) {
        T* q = p.at<T>(k);
        for (int i = 0; i < n; ++i) new (q + i) T();
        return q;
    }
};
// What a timed function reaches, held in its locals as a program holds the pointers of its arrays
// (the repair of docs/developer/results/bench-upward.md, "What changed", made from the start here).
template <class T>
struct Local {
    T *x, *y, *f, *h, *z, *xp, *yp, *xz, *yz, *zb, *zc, *px, *py, *pz, *ht, *zd, *xr, *yr, *fr, *zr;
    const T* hc;
    T& s;
};
template <class T>
Local<T> local(Data<T>& d) {
    return {d.x, d.y,  d.f,  d.h,  d.z,  d.xp, d.yp, d.xz, d.yz, d.zb, d.zc,
            d.px, d.py, d.pz, d.ht, d.zd, d.xr, d.yr, d.fr, d.zr, d.hc, d.s};
}
// Fills the arrays: ci(p) the type of the interval p = (l0, l1, h0, h1), cp(t) of the number t.
template <class T, class CI, class CP>
void fill(Data<T>& d, CI ci, CP cp) {
    const x2::Ops& o = x2::ops();
    for (int i = 0; i < kN; ++i) {
        d.x[i] = ci(o.x + 4 * i);
        d.y[i] = ci(o.y + 4 * i);
        d.f[i] = ci(o.f + 4 * i);
        d.h[i] = ci(o.h + 4 * i);
        d.xp[i] = ci(o.xp + 4 * i);
        d.yp[i] = ci(o.yp + 4 * i);
        d.xz[i] = ci(o.xz + 4 * i);
        d.yz[i] = ci(o.yz + 4 * i);
        d.px[i] = cp(o.px[i]);
        d.py[i] = cp(o.py[i]);
        d.pz[i] = cp(o.pz[i]);
        d.ht[i] = cp(o.ht[i]);
    }
    for (int k = 0; k <= kDeg; ++k) d.hc[k] = cp(o.hc[k]);
    for (int j = 0; j < kRand; ++j) {
        d.xr[j] = ci(o.xr + 4 * j);
        d.yr[j] = ci(o.yr + 4 * j);
        d.fr[j] = ci(o.fr + 4 * j);
    }
}
// The point coordinates of the determinant.
template <class T>
struct G3 {
    const Local<T>& d;
    const T& x(int j) const { return d.px[j]; }
    const T& y(int j) const { return d.py[j]; }
    const T& z(int j) const { return d.pz[j]; }
};

// The functions of a backend: X(KIND, KERNEL, VAR, OPS, BODY...), BODY using `d` (a Local<T>), the
// operators of the type or the wrapper OP (a type with the operators of a form), and the constructor
// ONE (the number 1 of the type), for an enclosure type with a square SQR.
#define KB_X4_EACH(...)                                                                            \
    for (int i = 0; i < kN; ++i) {                                                                 \
        __VA_ARGS__;                                                                               \
    }
#define KB_X4_EACHR(...)                                                                           \
    for (int i = 0; i < kRand; ++i) {                                                              \
        __VA_ARGS__;                                                                               \
    }

// The result arrays of each kernel.
inline const char* const kKernels[] = {"add", "sub", "mul", "mulpos", "mulzero", "mulrand", "sqr", "det3pt", "horner_pt", "horner_i"};

}  // namespace kairn_bench::x4
