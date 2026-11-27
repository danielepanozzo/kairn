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
#include <cstring>
#include <new>

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

// The passes of a function _x16: its loop 16 times inside one scope (or one change of mode).
inline constexpr int kPasses = 16;

// The functions on arrays timed per call (backend upwa, KIND call): arrays of kLong elements, built
// from the benchmark's intervals, element i the operands X[x_index(i)] and Y[y_index(i)]; a function
// for length L makes calls_of(L) calls, on the consecutive windows [k L, (k + 1) L), covering
// covered(L) elements (the first kN elements, in L1, for the short lengths; L elements beyond), and
// repeats them passes_of(L) times, so that it makes at least 64 calls: the outer scope that some of
// them hold costs each call a 64th of it at most.
inline constexpr int kLong = 4096;
constexpr int x_index(int i) { return i % kN; }
constexpr int y_index(int i) { return (i + i / kN) % kN; }
constexpr int calls_of(int length) { return length < kN ? kN / length : 1; }
constexpr int covered(int length) { return length < kN ? kN : length; }
constexpr int passes_of(int length) { return calls_of(length) >= 64 ? 1 : 64 / calls_of(length); }

// Where the arrays of a loop are placed. A load whose address is a multiple of 4 KB away from a
// store still in flight is taken for a load of that store's data until the full addresses are
// compared (4K aliasing), which can make a loop several times slower, by chance of the placement:
// the arrays of m2.cpp's packed loops have it (Raw<T>::sxi[0] and sout[0] are 32 bytes apart
// modulo 4 KB, so each iteration's loads alias the previous iteration's stores). The arrays of these
// units are placed in pages of their own at offsets modulo 4 KB that keep every store at least 1 KB
// from every load of the same loop: Placed::at<T>(k) is array k of kSlots, each slot room bytes and
// more, the array at kOffset[k] in its slot. A loop reads the slots 0 to 3 and writes slots 8 and 9,
// or reads the slots 4 to 7 and writes slot 10.
inline constexpr int kSlots = 11;
inline constexpr std::size_t kOffset[kSlots] = {0, 256, 512, 768, 1024, 1280, 1536, 1792, 2560, 2816, 3584};
struct Placed {
    unsigned char* base = nullptr;
    std::size_t slot = 0;
    // Room for `room` bytes per array.
    explicit Placed(std::size_t room) {
        slot = (room / 4096 + 2) * 4096;
        base = static_cast<unsigned char*>(::operator new(kSlots * slot, std::align_val_t(4096)));
    }
    template <class T>
    T* at(int k) const {
        return reinterpret_cast<T*>(base + std::size_t(k) * slot + kOffset[k]);
    }
};

// The arrays of the packed loops on the default layout (up_packed.cpp, up_fenv_packed.cpp): the
// lower and the upper bounds of X and Y, read, and of the results, written, kN of each, placed.
// A timed function holds their pointers in its locals (pointers()), as a program holds the pointers
// of the arrays of its loop: reached through the structure in memory, they were loaded again in
// every iteration, after each store of the loop, by GCC and Clang.
template <class T>
struct Bounds {
    Placed place{kN * sizeof(T)};
    T* xl = place.at<T>(0);
    T* xh = place.at<T>(1);
    T* yl = place.at<T>(2);
    T* yh = place.at<T>(3);
    T* zl = place.at<T>(8);
    T* zh = place.at<T>(9);
    struct Pointers {
        T* xl;
        T* xh;
        T* yl;
        T* yh;
        T* zl;
        T* zh;
    };
    Pointers pointers() const { return {xl, xh, yl, yh, zl, zh}; }
    void fill(const Raw<T>& r) {
        for (int i = 0; i < kN; ++i) {
            xl[i] = r.xi[2 * i];
            xh[i] = r.xi[2 * i + 1];
            yl[i] = r.yi[2 * i];
            yh[i] = r.yi[2 * i + 1];
        }
    }
    void clear() {
        std::memset(zl, 0xff, kN * sizeof(T));
        std::memset(zh, 0xff, kN * sizeof(T));
    }
    int read(T* lohi) const {
        for (int i = 0; i < kN; ++i) {
            lohi[2 * i] = zl[i];
            lohi[2 * i + 1] = zh[i];
        }
        return kN;
    }
};
// The bounds of one unit (Unit: 1 for up_packed.cpp, 2 for up_fenv_packed.cpp), for both limb
// types, and the check of its functions: the bounds filled from Raw<T>, then run_and_check.
template <int Unit>
struct BoundsOf {
    static inline Bounds<double>* b64 = nullptr;
    static inline Bounds<float>* b32 = nullptr;
    static void clear(int bits) {
        if (bits == 32)
            b32->clear();
        else
            b64->clear();
    }
    static int read(const Entry& e, void* lohi) {
        return e.bits == 32 ? b32->read(static_cast<float*>(lohi)) : b64->read(static_cast<double*>(lohi));
    }
    static bool check(const Entry& e, char* why, std::size_t size) {
        if (!b64) b64 = new Bounds<double>();
        if (!b32) b32 = new Bounds<float>();
        b64->fill(*static_cast<const Raw<double>*>(m2::m2_data(64)));
        b32->fill(*static_cast<const Raw<float>*>(m2::m2_data(32)));
        return run_and_check(e, clear, read, why, size);
    }
};

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

}  // namespace kairn_bench::up
