// EXPERIMENTAL, NOT VERIFIED: no bound stated in this file is proved. Kairn's rule is that every
// bound it ships is machine-checked; by the owner's decision recorded on 2026-11-28 (the decisions
// log, docs/developer/design/phase0/decisions.md) this header is an exception, shipped without
// proofs so that clients can experiment while the proofs are worked on. What protects a user
// meanwhile: this banner, the opt-in below, and the exact checks of its tests (label experimental),
// which are tests, not proofs. Its interface may change or disappear in any version. GCC and Clang
// only: MSVC is refused, and no Windows build was ever tested. A file that includes it defines
// KAIRN_EXPERIMENTAL_UNVERIFIED first, so that the choice is written in the client's code
// (docs/concepts/experimental.md).
#if !defined(KAIRN_EXPERIMENTAL_UNVERIFIED)
#error "kairn/experimental/upward4_arrays.hpp is EXPERIMENTAL and NOT VERIFIED (no bound in it is proved): define KAIRN_EXPERIMENTAL_UNVERIFIED before including it to accept that (docs/concepts/experimental.md)"
#endif

/// @file
/// EXPERIMENTAL, NOT VERIFIED, opt-in: no bound stated here is proved (the banner above). The functions on
/// arrays of the four-limb interval rounded upward (experiments/upward4/README.md): element by element
/// sum, difference and product of intervals held as eight plain arrays, the limbs u0..u3 of the upper
/// quadruples and n0..n3 of the negated lower ones. Requires the options of docs/concepts/upward.md
/// (GCC and Clang -frounding-math); each function holds its own scope of the mode upward (the register
/// only, as the functions on arrays of kairn/upward.hpp and of the two-limb experiment), so it may be
/// called where the mode is to nearest.
///
/// Vectorized across elements: on AVX2 four elements per register, elsewhere two (NEON, SSE2, or the two
/// numbers of the fallback); the upper quadruples and the negated lower ones in registers of their own,
/// each lane one element, the type's kernels (upward4.hpp: the sum qadd_accurate or qadd_sloppy as the
/// type's, the product network qmul, qmax) on such registers, with the type's tests lane by lane. A pack
/// of elements in which any element fails a test (a special value, an overflow, an inexact error, a deep
/// cancellation, an underflow, a carry the fixed sequence did not propagate), and the remainder, go
/// through the type's operators one element at a time (their own fast path, or the exact cold path). So
/// each element is the type's result for it, bit for bit (the checks compare them).
#pragma once

#include <cstddef>

#include "upward4.hpp"

namespace kairn::experimental::upward4 {

/// Eight plain arrays of n intervals: element k has the upper quadruple (u[0][k], ..., u[3][k]) and the
/// negated lower one (n[0][k], ..., n[3][k]), each a canonical state as an operation returns it (as
/// Interval::to_limbs gives them: u_i = to_limbs[2 i], n_i = to_limbs[2 i + 1]). Owns nothing.
template <class T>
struct View {
    T* u[4];
    T* n[4];
    std::size_t size;
};

namespace detail {
namespace {

// AP: a register of kAW elements; AM: its mask (Mask<AP>::type, named directly).
#if KAIRN_UPWARD2_AVX2
using AP = V4;
using AM = V4;
inline constexpr std::size_t kAW = 4;
KAIRN_FORCEINLINE AP ald(const double* p) noexcept { return _mm256_loadu_pd(p); }
KAIRN_FORCEINLINE void ast(double* p, AP v) noexcept { _mm256_storeu_pd(p, v); }
KAIRN_FORCEINLINE AP mandnot(AP a, AP b) noexcept { return _mm256_andnot_pd(b, a); }   // a and not b
#else
using AP = V;
using AM = M;
inline constexpr std::size_t kAW = 2;
KAIRN_FORCEINLINE AP ald(const double* p) noexcept { return vload(p); }
KAIRN_FORCEINLINE void ast(double* p, AP v) noexcept { vstore(p, v); }
#endif

// normal_lanes: the test of normal(), lane by lane: each lane (one element) satisfies the invariant with
// a first limb of magnitude below MAX. The same tests as normal() (its comment says why each means what
// it tests), on four registers of one bound each.
#if KAIRN_UPWARD2_FORM == KAIRN_UPWARD2_FORM_SSE
KAIRN_FORCEINLINE M mandnot(M a, M b) noexcept { return _mm_andnot_pd(b, a); }
KAIRN_FORCEINLINE M normal_lanes(V z0, V z1, V z2, V z3) noexcept {
    return mand(mand(eq(add(z0, z1), z0), eq(add(z1, z2), z1)), mand(eq(add(z2, z3), z2), _mm_cmplt_pd(vabs(z0), _mm_set1_pd(kMax))));
}
#elif KAIRN_UPWARD2_FORM == KAIRN_UPWARD2_FORM_NEON
KAIRN_FORCEINLINE M mandnot(M a, M b) noexcept { return vbicq_u64(a, b); }
KAIRN_FORCEINLINE M normal_lanes(V z0, V z1, V z2, V z3) noexcept {
    const uint64x2_t d = vorrq_u64(vorrq_u64(ub(sub(add(z0, z1), z0)), ub(sub(add(z1, z2), z1))), ub(sub(add(z2, z3), z2)));
    const uint64x2_t zero = vceqzq_u64(vshlq_n_u64(d, 1));
    const uint64x2_t small = vcltq_u64(vandq_u64(ub(z0), vdupq_n_u64(0x7fffffffffffffffu)), vdupq_n_u64(0x7fefffffffffffffu));
    return vandq_u64(zero, small);
}
#else
KAIRN_FORCEINLINE M mandnot(M a, M b) noexcept { return {a.m0 && !b.m0, a.m1 && !b.m1}; }
KAIRN_FORCEINLINE M normal_lanes(V z0, V z1, V z2, V z3) noexcept {
    return {normal1(z0.v0, z1.v0, z2.v0, z3.v0), normal1(z0.v1, z1.v1, z2.v1, z3.v1)};
}
#endif
#if KAIRN_UPWARD2_AVX2
KAIRN_FORCEINLINE V4 normal_lanes(V4 z0, V4 z1, V4 z2, V4 z3) noexcept {
    return mand(mand(eq(add(z0, z1), z0), eq(add(z1, z2), z1)),
                mand(eq(add(z2, z3), z2), _mm256_cmp_pd(vabs(z0), _mm256_set1_pd(kMax), _CMP_LT_OQ)));
}
#endif

// Every loop over the four limbs below is unrolled completely, so that the arrays of registers are
// registers: GCC 16 at -O2 kept such loops (complete peeling is an -O3 heuristic there), and the product
// on arrays took 1.3 times the loop of the type's operators.
#define KAIRN_UPWARD4_UNROLL4 _Pragma("GCC unroll 4")

// A pack of kAW elements: u[i] limb i of the upper quadruples, n[i] of the negated lower ones.
struct Pack {
    AP u[4], n[4];
};
KAIRN_FORCEINLINE Pack load(const View<const double>& x, std::size_t k) noexcept {
    return Pack{{ald(x.u[0] + k), ald(x.u[1] + k), ald(x.u[2] + k), ald(x.u[3] + k)},
                {ald(x.n[0] + k), ald(x.n[1] + k), ald(x.n[2] + k), ald(x.n[3] + k)}};
}
KAIRN_FORCEINLINE void store(const View<double>& z, std::size_t k, Pack p) noexcept {
    KAIRN_UPWARD4_UNROLL4
    for (int i = 0; i < 4; ++i) {
        bar(p.u[i]);
        bar(p.n[i]);
    }
    KAIRN_UPWARD4_UNROLL4
    for (int i = 0; i < 4; ++i) {
        ast(z.u[i] + k, p.u[i]);
        ast(z.n[i] + k, p.n[i]);
    }
}
// The barriers of a kernel (docs/developer/design/upward.md, "Barriers"): the first operand pinned, the
// second behind a barrier, as the type's operators do.
KAIRN_FORCEINLINE void barriers(Pack& x, Pack& y) noexcept {
    KAIRN_UPWARD4_UNROLL4
    for (int i = 0; i < 4; ++i) {
        pin(x.u[i]);
        pin(x.n[i]);
        bar(y.u[i]);
        bar(y.n[i]);
    }
}

// One element through the type (the remainder, and the packs where an element failed a test).
KAIRN_FORCEINLINE Interval element(const View<const double>& x, std::size_t k) noexcept {
    const double p[8] = {x.u[0][k], x.n[0][k], x.u[1][k], x.n[1][k], x.u[2][k], x.n[2][k], x.u[3][k], x.n[3][k]};
    return Interval::from_limbs(p);
}
KAIRN_FORCEINLINE void put(const View<double>& z, std::size_t k, const Interval& v) noexcept {
    double q[8];
    v.to_limbs(q);
    KAIRN_UPWARD4_UNROLL4
    for (int i = 0; i < 4; ++i) {
        z.u[i][k] = q[2 * i];
        z.n[i][k] = q[2 * i + 1];
    }
}

// One bound of kAW sums, x + y: add_r's network and tests (the same steps, the same reasons) on
// registers of elements; ok cleared in the lanes that fail.
KAIRN_FORCEINLINE void sum_bound(const AP* x, const AP* y, AP* z, AM& ok) noexcept {
#if KAIRN_UPWARD4_SUM == KAIRN_UPWARD4_SUM_SLOPPY
    qadd_sloppy(x[0], x[1], x[2], x[3], y[0], y[1], y[2], y[3], z[0], z[1], z[2], z[3], ok);
#else
    qadd_accurate(x[0], x[1], x[2], x[3], y[0], y[1], y[2], y[3], z[0], z[1], z[2], z[3], ok);
#endif
    ok = mand(ok, not_small(z[0], mul(vmax(vabs(x[0]), vabs(y[0])), bcast<AP>(0x1p-48))));
    ok = mand(ok, normal_lanes(z[0], z[1], z[2], z[3]));
}

// The product of kAW elements, lane by lane the case of mul_branch (upward4.hpp) chosen by masks: the
// signs of the first limbs (normalized: the sign of a first limb is the sign of the bound) give, as
// kCases of the two-limb experiment does (the same pairs, so that every lane's network is the one the
// type's operator runs, bit for bit), for each bound one pair (P, Q), P a quadruple of x, Q one of y,
// negated where the table says:
//            y >= 0                  y <= 0                  y ∋ 0
//   x >= 0   U xu yu,  N xn (-yn)    U xn (-yu), N xu yn     U xu yu, N xu yn
//   x <= 0   U xu (-yn), N xn yu     U xn yn,  N xu (-yu)    U xn yn, N xn yu
//   x ∋ 0    U xu yu,  N xn yu       U xn yn,  N xu yn       U max(xn yn, xu yu), N max(xn yu, xu yn)
// (x >= 0 taken first where x = [0, 0], as mul_branch does). Where some lane has x ∋ 0 and y ∋ 0, the
// second candidates (xu yu, xu yn) are computed for every lane and the lexicographic greater kept in
// those lanes, with the chosen candidate's exactness (as mul_zero_zero). ok cleared in the lanes that
// fail a test: an exactness test, the invariant, a leading product not finite or reaching MAX.
KAIRN_FORCEINLINE Pack mul_pack(const Pack& x, const Pack& y, AM& ok) noexcept {
    const AM all = all_mask<AP>();
    const AM xA = le0(x.n[0]), yA = le0(y.n[0]);              // a >= 0, c >= 0
    const AM xB = mandnot(le0(x.u[0]), xA), yB = mandnot(le0(y.u[0]), yA);   // b <= 0 (and not a >= 0)
    const AM nxA = mandnot(all, xA), nyA = mandnot(all, yA);
    const AM yZ = mandnot(nyA, yB), zz = mandnot(mand(yZ, nxA), xB);
    // Upper bound: P = xn where y <= 0, or y ∋ 0 and not x >= 0; Q = yn where (y >= 0 and x <= 0) or
    // (not y >= 0 and not x >= 0); Q negated where (y >= 0 and x <= 0) or (y <= 0 and x >= 0).
    const AM pu = mor(yB, mand(yZ, nxA)), qu = mor(mand(yA, xB), mand(nyA, nxA)), su = mor(mand(yA, xB), mand(yB, xA));
    // Negated lower bound: P = xn where y >= 0, or y ∋ 0 and not x >= 0; Q = yu where (y >= 0 and not
    // x >= 0) or (y <= 0 and x <= 0) or (y ∋ 0 and not x >= 0); Q negated where (y >= 0 and x >= 0) or
    // (y <= 0 and x <= 0).
    const AM pl = mor(yA, mand(yZ, nxA)), ql = mor(mor(mand(yA, nxA), mand(yB, xB)), mand(yZ, nxA)), sl = mor(mand(yA, xA), mand(yB, xB));
    AP PU[4], QU[4], PL[4], QL[4];
    KAIRN_UPWARD4_UNROLL4
    for (int i = 0; i < 4; ++i) {
        PU[i] = blend(pu, x.n[i], x.u[i]);
        QU[i] = flip(su, blend(qu, y.n[i], y.u[i]));
        PL[i] = blend(pl, x.n[i], x.u[i]);
        QL[i] = flip(sl, blend(ql, y.u[i], y.n[i]));
        bar(QU[i]);
        bar(QL[i]);
    }
    AP p1, p2;
    Pack z;
    AM oku = all, okl = all;
    qmul(PU[0], PU[1], PU[2], PU[3], QU[0], QU[1], QU[2], QU[3], p1, z.u[0], z.u[1], z.u[2], z.u[3], oku);
    qmul(PL[0], PL[1], PL[2], PL[3], QL[0], QL[1], QL[2], QL[3], p2, z.n[0], z.n[1], z.n[2], z.n[3], okl);
    AM bad = mor(big(p1), big(p2));
    if (any(zz)) {
        // The second candidates: U xu yu, N xu yn, for every lane; kept where zz and greater.
        AP q1, q2;
        Pack w, m;
        AM oku2 = all, okl2 = all;
        qmul(x.u[0], x.u[1], x.u[2], x.u[3], y.u[0], y.u[1], y.u[2], y.u[3], q1, w.u[0], w.u[1], w.u[2], w.u[3], oku2);
        qmul(x.u[0], x.u[1], x.u[2], x.u[3], y.n[0], y.n[1], y.n[2], y.n[3], q2, w.n[0], w.n[1], w.n[2], w.n[3], okl2);
        // Only the chosen candidate's exactness matters (mul_zero_zero says why).
        const AM cu = qmax(z.u[0], z.u[1], z.u[2], z.u[3], w.u[0], w.u[1], w.u[2], w.u[3], m.u[0], m.u[1], m.u[2], m.u[3]);
        const AM cl = qmax(z.n[0], z.n[1], z.n[2], z.n[3], w.n[0], w.n[1], w.n[2], w.n[3], m.n[0], m.n[1], m.n[2], m.n[3]);
        KAIRN_UPWARD4_UNROLL4
        for (int i = 0; i < 4; ++i) {
            z.u[i] = blend(zz, m.u[i], z.u[i]);
            z.n[i] = blend(zz, m.n[i], z.n[i]);
        }
        oku = mblend(zz, mblend(cu, oku, oku2), oku);
        okl = mblend(zz, mblend(cl, okl, okl2), okl);
        bad = mor(bad, mand(zz, mor(big(q1), big(q2))));
    }
    ok = mandnot(mand(mand(oku, okl), mand(normal_lanes(z.u[0], z.u[1], z.u[2], z.u[3]), normal_lanes(z.n[0], z.n[1], z.n[2], z.n[3]))), bad);
    return z;
}

enum class ArrayOp { add, sub, mul };
template <ArrayOp Op>
KAIRN_FORCEINLINE void apply(const View<double>& z, const View<const double>& x, const View<const double>& y) noexcept {
    ::kairn::upward::detail::RegisterScope scope;
    const std::size_t n = z.size;
    std::size_t k = 0;
    for (; k + kAW <= n; k += kAW) {
        Pack a = load(x, k), b = load(y, k);
        barriers(a, b);
        Pack c;
        AM ok = all_mask<AP>();
        if constexpr (Op == ArrayOp::mul) {
            c = mul_pack(a, b, ok);
        } else if constexpr (Op == ArrayOp::add) {
            sum_bound(a.u, b.u, c.u, ok);
            sum_bound(a.n, b.n, c.n, ok);
        } else {   // x - y: the quadruples of y exchanged
            sum_bound(a.u, b.n, c.u, ok);
            sum_bound(a.n, b.u, c.n, ok);
        }
        if (!all_set(ok)) [[unlikely]] {
            for (std::size_t j = k; j < k + kAW; ++j) {
                const Interval p = element(x, j), q = element(y, j);
                put(z, j, Op == ArrayOp::add ? p + q : Op == ArrayOp::sub ? p - q : p * q);
            }
            continue;
        }
        store(z, k, c);
    }
    for (; k < n; ++k) {
        const Interval p = element(x, k), q = element(y, k);
        put(z, k, Op == ArrayOp::add ? p + q : Op == ArrayOp::sub ? p - q : p * q);
    }
}

}  // namespace
}  // namespace detail

namespace {
/// z = x + y, x - y, x * y element by element (views of the same length; z may be x or y, or arrays
/// that overlap neither). Each holds its own scope of the mode upward. Each element of z is what the
/// type's operator gives for it.
[[maybe_unused]] void add(View<double> z, View<const double> x, View<const double> y) noexcept {
    detail::apply<detail::ArrayOp::add>(z, x, y);
}
[[maybe_unused]] void sub(View<double> z, View<const double> x, View<const double> y) noexcept {
    detail::apply<detail::ArrayOp::sub>(z, x, y);
}
[[maybe_unused]] void mul(View<double> z, View<const double> x, View<const double> y) noexcept {
    detail::apply<detail::ArrayOp::mul>(z, x, y);
}
}  // namespace

}  // namespace kairn::experimental::upward4
