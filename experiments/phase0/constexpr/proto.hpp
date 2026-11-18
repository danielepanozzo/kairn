// Phase 0 prototype (not the library): a double-word type whose operations are constexpr, usable
// on the CUDA host and device, and whose k = 1 instance should cost what plain T costs.
//
// What it is here to answer:
//   1. Can one function body serve constant evaluation (Dekker product, no std::fma) and run time
//      (hardware FMA, or __fma_rn on the CUDA device) under is_constant_evaluated()?
//   2. Does that still compile and give the same bits with -frounding-math, on MSVC, and under
//      nvcc as `__host__ __device__ constexpr` without --expt-relaxed-constexpr?
//   3. Does Expansion<T, 1> compile to the same instructions as T?
#pragma once
#include <cmath>
#include <limits>
#include <type_traits>

#if defined(__CUDACC__)
#define PROTO_HD __host__ __device__
#else
#define PROTO_HD
#endif
// std::is_constant_evaluated() is a host-only function to nvcc (warning #20013-D when a
// __host__ __device__ function calls it without --expt-relaxed-constexpr); the builtin is not.
// GCC >= 9, Clang >= 9, MSVC >= 19.25 and nvcc all provide it.
#define PROTO_IS_CONSTANT_EVALUATED() __builtin_is_constant_evaluated()

namespace proto {

// RN(a*b + c) at run time; never called in constant evaluation.
PROTO_HD inline double fma_rt(double a, double b, double c) {
#if defined(__CUDA_ARCH__)
    return __fma_rn(a, b, c);
#else
    return std::fma(a, b, c);
#endif
}
PROTO_HD inline float fma_rt(float a, float b, float c) {
#if defined(__CUDA_ARCH__)
    return __fmaf_rn(a, b, c);
#else
    return std::fma(a, b, c);
#endif
}
// RN(a + b), RN(a - b), RN(a * b): plain operators on the host; on the CUDA device the intrinsics
// nvcc never contracts. In constant evaluation the plain operators are used everywhere.
template <class T> PROTO_HD constexpr T add_rn(T a, T b) {
#if defined(__CUDA_ARCH__)
    if (!PROTO_IS_CONSTANT_EVALUATED()) {
        if constexpr (sizeof(T) == 8) return __dadd_rn(a, b);
        else return __fadd_rn(a, b);
    }
#endif
    return a + b;
}
template <class T> PROTO_HD constexpr T sub_rn(T a, T b) { return add_rn(a, -b); }

template <class T> struct pair {
    T hi, lo;
};

// Dekker's product with Veltkamp's split: the error of RN(a*b), for constant evaluation only.
template <class T> PROTO_HD constexpr T dekker_error(T a, T b, T p) {
    const T splitter = T((1 << ((std::numeric_limits<T>::digits + 1) / 2)) + 1);
    const T ca = splitter * a, ah = ca - (ca - a), al = a - ah;
    const T cb = splitter * b, bh = cb - (cb - b), bl = b - bh;
    return ((ah * bh - p) + ah * bl + al * bh) + al * bl;
}

// TwoProd: p = RN(a*b) and e = a*b - p (exact when no underflow).
template <class T> PROTO_HD constexpr pair<T> two_prod(T a, T b) {
    if (PROTO_IS_CONSTANT_EVALUATED()) {
        const T p = a * b;
        return {p, dekker_error(a, b, p)};
    }
    const T p = fma_rt(a, b, T(0));  // the "opaque" product: nothing here can be contracted
    return {p, fma_rt(a, b, -p)};
}
// TwoSum (Knuth): s = RN(a+b) and e = a+b - s, exact.
template <class T> PROTO_HD constexpr pair<T> two_sum(T a, T b) {
    const T s = add_rn(a, b), bb = sub_rn(s, a);
    return {s, add_rn(sub_rn(a, sub_rn(s, bb)), sub_rn(b, bb))};
}
template <class T> PROTO_HD constexpr pair<T> fast_two_sum(T a, T b) {
    const T s = add_rn(a, b);
    return {s, sub_rn(b, sub_rn(s, a))};
}

template <class T, int K> struct Expansion;

template <class T> struct Expansion<T, 1> {
    T limb[1] = {};
    constexpr Expansion() = default;
    PROTO_HD constexpr Expansion(T x) : limb{x} {}
    // k = 1 is plain T. Under Clang's default (-ffp-contract=on) a * b + c on plain T is fused
    // because it is one expression, but these two operators are two functions, so nothing would
    // fuse and k = 1 would cost one instruction more per multiply-add. PROTO_K1_CONTRACT marks the
    // two operations as contractable, which lets the back end fuse them after inlining, as it does
    // for plain T. (Define PROTO_K1_NO_CONTRACT_PRAGMA to measure the difference.)
#if defined(__clang__) && !defined(PROTO_K1_NO_CONTRACT_PRAGMA) && !defined(__CUDACC__)
#define PROTO_K1_CONTRACT _Pragma("clang fp contract(fast)")
#else
#define PROTO_K1_CONTRACT
#endif
    PROTO_HD friend constexpr Expansion operator+(Expansion a, Expansion b) {
        PROTO_K1_CONTRACT
        return {a.limb[0] + b.limb[0]};
    }
    PROTO_HD friend constexpr Expansion operator*(Expansion a, Expansion b) {
        PROTO_K1_CONTRACT
        return {a.limb[0] * b.limb[0]};
    }
};

template <class T> struct Expansion<T, 2> {
    T limb[2] = {};
    constexpr Expansion() = default;
    PROTO_HD constexpr Expansion(T x) : limb{x, T(0)} {}
    PROTO_HD constexpr Expansion(T h, T l) : limb{h, l} {}
    // AccurateDWPlusDW (Joldes, Muller, Popescu 2017, Algorithm 6).
    PROTO_HD friend constexpr Expansion operator+(Expansion a, Expansion b) {
        const pair<T> s = two_sum(a.limb[0], b.limb[0]), t = two_sum(a.limb[1], b.limb[1]);
        const pair<T> v = fast_two_sum(s.hi, add_rn(s.lo, t.hi));
        const pair<T> z = fast_two_sum(v.hi, add_rn(t.lo, v.lo));
        return {z.hi, z.lo};
    }
    // DWTimesDW3 (same paper, Algorithm 12), with the plain products written as FMAs.
    PROTO_HD friend constexpr Expansion operator*(Expansion a, Expansion b) {
        const pair<T> c = two_prod(a.limb[0], b.limb[0]);
        T t = T(0);
        if (PROTO_IS_CONSTANT_EVALUATED()) {
            t = a.limb[0] * b.limb[1] + a.limb[1] * b.limb[1];
            t = a.limb[1] * b.limb[0] + t;
        } else {
            t = fma_rt(a.limb[1], b.limb[1], T(0));
            t = fma_rt(a.limb[0], b.limb[1], t);
            t = fma_rt(a.limb[1], b.limb[0], t);
        }
        const pair<T> z = fast_two_sum(c.hi, add_rn(c.lo, t));
        return {z.hi, z.lo};
    }
};

// A function generic over k, as a client would write it.
template <class X> PROTO_HD constexpr X horner3(X c0, X c1, X c2, X x) { return (c2 * x + c1) * x + c0; }

}  // namespace proto
