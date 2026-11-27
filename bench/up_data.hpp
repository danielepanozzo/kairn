// The benchmark of the round-up interval (bench/README.md, "The round-up interval"): what the units
// up_*.cpp share. Requires the rounding mode upward set by kairn::upward::Scope and the options of
// docs/concepts/upward.md (GCC and Clang -frounding-math, MSVC /fp:strict): bench/CMakeLists.txt
// gives the units that include kairn/upward.hpp (up_type.cpp, up_arrays.cpp) the option of the
// target kairn::upward, and each of their functions that rounds holds a Scope or runs inside one.
// This header includes no Kairn header, so that the props that change the rounding mode
// (up_fenv.cpp, up_fenv_packed.cpp) can use it.
//
// The program kairn-bench-up-LEVEL is the driver of Milestone 2 (m2_main.cpp) with the units of the
// first part of that benchmark (m2.cpp, m2_fenv.cpp, m2_packed.cpp, m2_fenv_packed.cpp), whose
// functions on the default Interval<T, 1> are the comparisons, and these units, each of which adds
// its table to kairn_bench::m2::m2_extra_tables before main. Every function of these tables has its
// own check (up_check.cpp): run under rounding to nearest on cleared outputs, its results are read
// as (lower, upper) pairs and compared with Kairn's default kernels on the same operands; equal
// bounds, but for the sign of a zero; for a computation with products, a bound one number tighter
// than the default's is accepted where the default's product may be one number wider (a product of
// bounds below 2^(2p-1) eta; none occurs on these operands); and a computation that rounds must
// differ from the same computation rounded to nearest in some values, or the mode was not honored.
#pragma once

#include <cstddef>

#include "m2_data.hpp"

#if defined(_MSC_VER) && !defined(__clang__)
#define KB_UP_INLINE __forceinline
#else
#define KB_UP_INLINE inline __attribute__((always_inline))
#endif

// A function that the compiler neither inlines nor analyzes from its callers (GCC's noipa: no
// parameter removed or specialized), for the calls of the scopes' measurements.
#if defined(__GNUC__) && !defined(__clang__)
#define KB_UP_NOIPA __attribute__((noipa))
#else
#define KB_UP_NOIPA KB_NOINLINE
#endif

// A barrier of the compiler between the passes of a function that repeats its loop (variants _x16):
// no load or store moves across it, so that each pass computes again.
#if defined(_MSC_VER) && !defined(__clang__)
#include <intrin.h>
#define KB_UP_FENCE() _ReadWriteBarrier()
#else
#define KB_UP_FENCE() __asm__ __volatile__("" ::: "memory")
#endif

namespace kairn_bench::up {

using m2::Entry;
using m2::kDeg;
using m2::kN;
using m2::Raw;

// The passes of a function _x16: its loop 16 times inside one scope (or one change of mode).
inline constexpr int kPasses = 16;

// The functions on arrays timed per call (backend upwa, KIND call): arrays of kLong elements, built
// from the benchmark's intervals, element i the operands X[x_index(i)] and Y[y_index(i)]; a function
// for length L makes calls_of(L) calls, on the consecutive windows [k L, (k + 1) L), covering
// covered(L) elements: the first kN elements (in L1) for the short lengths, L elements beyond.
inline constexpr int kLong = 4096;
constexpr int x_index(int i) { return i % kN; }
constexpr int y_index(int i) { return (i + i / kN) % kN; }
constexpr int calls_of(int length) { return length < kN ? kN / length : 1; }
constexpr int covered(int length) { return length < kN ? kN : length; }

// The determinant of coordinate differences, the sign filter of an orientation test in three
// dimensions: the points a, b, c, d of element i are the elements det_index(i, 0..3) of the arrays
// X, Y and F (their three coordinates), and the value is det(a - d, b - d, c - d), the 3 by 3
// determinant of the differences, expanded along its first row. Written here for every type that
// has -, * and +; every type evaluates the same expression in the same order.
constexpr int det_index(int i, int k) { return (i + 64 * k) % kN; }

template <class I>
KB_UP_INLINE I det3(const I& ax, const I& ay, const I& az, const I& bx, const I& by, const I& bz, const I& cx,
                    const I& cy, const I& cz, const I& dx, const I& dy, const I& dz) {
    const I ux = ax - dx, uy = ay - dy, uz = az - dz;
    const I vx = bx - dx, vy = by - dy, vz = bz - dz;
    const I wx = cx - dx, wy = cy - dy, wz = cz - dz;
    return ux * (vy * wz - vz * wy) - uy * (vx * wz - vz * wx) + uz * (vx * wy - vy * wx);
}

// det3 at element i, the coordinates given by g: g.x(j), g.y(j), g.f(j) of point j.
template <class I, class G>
KB_UP_INLINE I det3_at(const G& g, int i) {
    const int a = det_index(i, 0), b = det_index(i, 1), c = det_index(i, 2), d = det_index(i, 3);
    return det3<I>(g.x(a), g.y(a), g.f(a), g.x(b), g.y(b), g.f(b), g.x(c), g.y(c), g.f(c), g.x(d), g.y(d), g.f(d));
}

// The Horner evaluation of the benchmark of Milestone 2 (m2.cpp): p = c8; p = p x + ck, every
// coefficient a point of the type, the Chebyshev polynomial T8.
template <class X, class C>
KB_UP_INLINE X horner(const C* c, const X& x) {
    X p = c[kDeg];
    for (int k = kDeg - 1; k >= 0; --k) p = p * x + c[k];
    return p;
}

// The checks (up_check.cpp). A unit's check fills its operands, then calls run_and_check with
// what clears its outputs and what reads them: read writes the results of entry e as (lower,
// upper) pairs of T into lohi (room for 2 kLong values) and returns their number.
using ClearFn = void (*)(int bits);
using ReadFn = int (*)(const Entry& e, void* lohi);
bool run_and_check(const Entry& e, ClearFn clear, ReadFn read, char* why, std::size_t size);
// The checks of functions that write Raw<T> (the props, which include no Kairn, and the default
// kernels): r.out as kN (lower, upper) pairs, or r.sout[0] and r.sout[1] as kN lower and upper
// bounds; a chain writes r.cout[0], r.cout[1].
bool check_raw_out(const Entry& e, char* why, std::size_t size);
bool check_raw_sout(const Entry& e, char* why, std::size_t size);

}  // namespace kairn_bench::up
