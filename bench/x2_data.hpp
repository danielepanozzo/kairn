// The benchmark of the experimental two-limb interval rounded upward (experiments/upward2/README.md;
// bench/README.md, "The two-limb interval rounded upward"): what the units x2_*.cpp share.
// EXPERIMENTAL, NOT VERIFIED, not part of the library. Requires the rounding mode upward set by
// kairn::upward::Scope and the options of docs/concepts/upward.md (GCC and Clang -frounding-math):
// the unit of the type (x2_type.cpp) is compiled with the option of the target kairn::upward and
// every timed function there holds a Scope; the prototype's unit (x2_proto.cpp) is compiled as
// m2_fenv.cpp, with the mode set by std::fesetround around each loop; the default types
// (x2_default.cpp) are compiled as a client compiles them. This header includes no Kairn header.
//
// Every unit times the same operands, made once from the benchmark's data (Raw<double> of m2.cpp):
// - X2, Y2, F2, H2: the intervals of two limbs xi2, yi2, fi2 (factors near 1, for the chain of
//   products) and hi2 (the Horner arguments), as (l0, l1, h0, h1);
// - XP, YP: X2 and Y2 made positive (each negative interval negated): the products of one sign;
// - XZ, YZ: intervals around zero, [-|a|, |b|] from bounds of X2 and Y2: every one contains zero;
// - the points (px, py, pz) = (xi[2 i], yi[2 i], fi[2 i]) (exact doubles) of the determinant;
// - HT: the Horner arguments as numbers (ht), for the widths of Horner on points; the coefficients hc;
// - XR, YR: below.
// Element i of a loop of a binary operation is X[i] op Y[i]. Element i of the determinant is
// det3pt(a, b, c, d) with a, b, c, d the points i, i + 1, i + 2, i + 3 (mod kN).
#pragma once

#include <cstddef>

#include "m2_data.hpp"

#if defined(_MSC_VER) && !defined(__clang__)
#define KB_X2_INLINE __forceinline
#else
#define KB_X2_INLINE inline __attribute__((always_inline))
#endif

namespace kairn_bench::x2 {

using m2::Entry;
using m2::kDeg;
using m2::kN;
using m2::Raw;

// XR, YR: kRand products whose signs are random and do not repeat within a call (X2 and Y2 with
// signs from a hash of the index), for the forms of the product with branches, whose signs the
// predictors could learn over the 256 elements of the other loops repeated call after call.
inline constexpr int kRand = 4096;
struct Ops {
    double x[4 * kN], y[4 * kN], f[4 * kN], h[4 * kN];
    double xp[4 * kN], yp[4 * kN], xz[4 * kN], yz[4 * kN];
    double px[kN], py[kN], pz[kN], ht[kN];
    double hc[kDeg + 1];
    double xr[4 * kRand], yr[4 * kRand];
};
// The operands, made from the benchmark's data the first time (x2_check.cpp).
const Ops& ops();

// The determinant of coordinate differences on points, the orientation filter of three
// dimensions, expanded along its first row; every type evaluates this expression, in this order.
template <class I>
KB_X2_INLINE I det3pt(const I& ax, const I& ay, const I& az, const I& bx, const I& by, const I& bz, const I& cx,
                      const I& cy, const I& cz, const I& dx, const I& dy, const I& dz) {
    const I adx = ax - dx, ady = ay - dy, adz = az - dz;
    const I bdx = bx - dx, bdy = by - dy, bdz = bz - dz;
    const I cdx = cx - dx, cdy = cy - dy, cdz = cz - dz;
    return adx * (bdy * cdz - bdz * cdy) + bdx * (cdy * adz - cdz * ady) + cdx * (ady * bdz - adz * bdy);
}
// Element i of the determinant, the coordinates given by g: g.x(j), g.y(j), g.z(j) of point j.
template <class I, class G>
KB_X2_INLINE I det3pt_at(const G& g, int i) {
    const int a = i, b = (i + 1) % kN, c = (i + 2) % kN, d = (i + 3) % kN;
    return det3pt<I>(g.x(a), g.y(a), g.z(a), g.x(b), g.y(b), g.z(b), g.x(c), g.y(c), g.z(c), g.x(d), g.y(d), g.z(d));
}
// Horner, as m2.cpp: p = c8; p = p x + ck.
template <class X, class C>
KB_X2_INLINE X horner2(const C* c, const X& x) {
    X p = c[kDeg];
    for (int k = kDeg - 1; k >= 0; --k) p = p * x + c[k];
    return p;
}

// One unit of timed functions, which registers itself before main: what the check needs.
struct Unit {
    const char* backend;   // the BACKEND of its entries' names ("x2", "x2p", "x2d", "x2u", "x2a")
    // Fills the unit's operands from ops(), outside the timed code.
    void (*fill)();
    // Clears its results (NaN).
    void (*clear)();
    // The results of entry `name` after it ran, as (l0, l1, h0, h1) per element, each bound the exact
    // value l0 + l1 or h0 + h1 (not necessarily normalized): returns the number of elements.
    int (*read)(const char* name, double* out);
    // The same computation through operands read from volatile objects, by the same kernels (the
    // reference of a timed function, bit for bit), or nullptr; returns the number of elements.
    int (*reference)(const char* name, double* out);
    // A chain step by step (sum and prod): the state after step k from the state before it, both
    // (l0, l1, h0, h1) as read gives them, by the same kernel, or nullptr.
    void (*step)(const char* name, const double* before, int k, double* after);
    Unit* next;
};
extern Unit* units;   // constant-initialized, in x2_check.cpp

// The check of every function of these units (x2_check.cpp): before it is timed.
bool check(const Entry& e, char* why, std::size_t size);

}  // namespace kairn_bench::x2
