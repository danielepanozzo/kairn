/// @file
/// EXPERIMENTAL, NOT VERIFIED, not part of the library: no bound stated here is proved. The forms of
/// the product and of the sum of the four-limb interval rounded upward that were measured against the
/// ones the type uses (experiments/upward4/README.md), kept for the measurements and the checks only:
/// the type itself (upward4.hpp) does not use them. Requires the rounding mode upward set by
/// kairn::upward::Scope and the options of docs/concepts/upward.md (GCC and Clang -frounding-math).
#pragma once

#include <kairn/experimental/upward2_forms.hpp>
#include <kairn/experimental/upward4.hpp>

namespace kairn::experimental::upward4::detail {
namespace {

// --- The two sums, each with the type's test and cold path ----------------------------------------------

KAIRN_FORCEINLINE R4 add_accurate_r(const R4& x, const R4& y) noexcept {
    R4 z;
    M ok = mall();
    qadd_accurate(x.r0, x.r1, x.r2, x.r3, y.r0, y.r1, y.r2, y.r3, z.r0, z.r1, z.r2, z.r3, ok);
    ok = mand(ok, not_small(z.r0, mul(vmax(vabs(x.r0), vabs(y.r0)), vset(0x1p-48))));
    if (!(all_set(ok) && normal(z))) [[unlikely]]
        return add_special(x, y);
    return z;
}
KAIRN_FORCEINLINE R4 add_sloppy_r(const R4& x, const R4& y) noexcept {
    R4 z;
    M ok = mall();
    qadd_sloppy(x.r0, x.r1, x.r2, x.r3, y.r0, y.r1, y.r2, y.r3, z.r0, z.r1, z.r2, z.r3, ok);
    ok = mand(ok, not_small(z.r0, mul(vmax(vabs(x.r0), vabs(y.r0)), vset(0x1p-48))));
    if (!(all_set(ok) && normal(z))) [[unlikely]]
        return add_special(x, y);
    return z;
}

// --- The products ------------------------------------------------------------------------------------------
//
// Each computes, on a fast path, candidate quadruples by qmul and tests that every leading product p
// computed is finite with |p| < MAX and that the result passes normal(); otherwise it returns
// mul_special.

// Form "table": the operands of the case by a table of lane permutations (the two-limb experiment's
// controls, upward2_forms.hpp, on each of the four registers), no branch but the one to the case x ∋ 0,
// y ∋ 0 (two candidates, mul_zero_zero) and the cold path.
#if KAIRN_UPWARD2_FORM == KAIRN_UPWARD2_FORM_NEON
KAIRN_FORCEINLINE int case4(const R4& x, const R4& y) noexcept {
    const uint64x2_t wx = vandq_u64(le0(x.r0), vcombine_u64(vcreate_u64(1), vcreate_u64(2)));
    const uint64x2_t wy = vandq_u64(le0(y.r0), vcombine_u64(vcreate_u64(4), vcreate_u64(8)));
    return int(vaddvq_u64(vorrq_u64(wx, wy)));
}
#else
KAIRN_FORCEINLINE int case4(const R4& x, const R4& y) noexcept { return bits(le0(x.r0)) | (bits(le0(y.r0)) << 2); }
#endif

#if KAIRN_UPWARD2_FORM == KAIRN_UPWARD2_FORM_SSE
KAIRN_FORCEINLINE void pick_case4(const R4& x, const R4& y, int k, R4& p, R4& q) noexcept {
    const __m128i cp = _mm_load_si128(reinterpret_cast<const __m128i*>(&u2d::kCtl[k][0]));
    const __m128i cq = _mm_load_si128(reinterpret_cast<const __m128i*>(&u2d::kCtl[k][2]));
    const __m128d s = _mm_castsi128_pd(_mm_load_si128(reinterpret_cast<const __m128i*>(&u2d::kCtl[k][4])));
    p = R4{_mm_permutevar_pd(x.r0, cp), _mm_permutevar_pd(x.r1, cp), _mm_permutevar_pd(x.r2, cp), _mm_permutevar_pd(x.r3, cp)};
    q = R4{_mm_xor_pd(_mm_permutevar_pd(y.r0, cq), s), _mm_xor_pd(_mm_permutevar_pd(y.r1, cq), s),
           _mm_xor_pd(_mm_permutevar_pd(y.r2, cq), s), _mm_xor_pd(_mm_permutevar_pd(y.r3, cq), s)};
}
#elif KAIRN_UPWARD2_FORM == KAIRN_UPWARD2_FORM_NEON
KAIRN_FORCEINLINE V pick4(V a, uint8x16_t c) noexcept { return vreinterpretq_f64_u8(vqtbl1q_u8(vreinterpretq_u8_f64(a), c)); }
KAIRN_FORCEINLINE V pickq4(V a, uint8x16_t c, uint64x2_t s) noexcept {
    return vreinterpretq_f64_u64(veorq_u64(vreinterpretq_u64_f64(pick4(a, c)), s));
}
KAIRN_FORCEINLINE void pick_case4(const R4& x, const R4& y, int k, R4& p, R4& q) noexcept {
    const uint8x16_t cp = vld1q_u8(reinterpret_cast<const std::uint8_t*>(&u2d::kCtl[k][0]));
    const uint8x16_t cq = vld1q_u8(reinterpret_cast<const std::uint8_t*>(&u2d::kCtl[k][2]));
    const uint64x2_t s = vld1q_u64(&u2d::kCtl[k][4]);
    p = R4{pick4(x.r0, cp), pick4(x.r1, cp), pick4(x.r2, cp), pick4(x.r3, cp)};
    q = R4{pickq4(y.r0, cq, s), pickq4(y.r1, cq, s), pickq4(y.r2, cq, s), pickq4(y.r3, cq, s)};
}
#else
KAIRN_FORCEINLINE double at4(V a, int i) noexcept { return i ? a.v1 : a.v0; }
KAIRN_FORCEINLINE void pick_case4(const R4& x, const R4& y, int k, R4& p, R4& q) noexcept {
    const Case& c = kCases[k];
    auto pp = [&](V a) noexcept { return V{at4(a, c.p0), at4(a, c.p1)}; };
    const M s{c.s0 != 0, c.s1 != 0};
    auto qq = [&](V a) noexcept { return flip(s, V{at4(a, c.q0), at4(a, c.q1)}); };
    p = R4{pp(x.r0), pp(x.r1), pp(x.r2), pp(x.r3)};
    q = R4{qq(y.r0), qq(y.r1), qq(y.r2), qq(y.r3)};
}
#endif

KAIRN_FORCEINLINE R4 mul_table(const R4& x, const R4& y) noexcept {
    const int k = case4(x, y);
    if (k == 0) return mul_zero_zero(x, y);
    R4 p, q;
    pick_case4(x, y, k, p, q);
    bar(q);
    return mul_one(p, q, x, y);
}

// Form "sel2": operands selected by the signs of the bounds with blends, two candidates per lane, the
// greater kept (the two-limb form sel2's selection, upward2_forms.hpp, with its argument, on each of
// the four registers): branch-free, two product networks.
KAIRN_FORCEINLINE void select2_4(const R4& x, const R4& y, R4& pa, R4& qa, R4& pb, R4& qb) noexcept {
    const M xle = le0(x.r0);   // lanes: b <= 0, a >= 0
    const M ylt = lt0(y.r0);   // lanes: d < 0, c > 0
    const M ma = mand(mdup0(xle), mswap(ylt));
    const M mb = mand(mdup1(xle), ylt);
    auto sa = [&](V a) noexcept { return blend(ma, dup0(a), dup1(a)); };
    auto sb = [&](V a) noexcept { return blend(mb, dup1(a), dup0(a)); };
    pa = R4{sa(x.r0), sa(x.r1), sa(x.r2), sa(x.r3)};
    pb = R4{sb(x.r0), sb(x.r1), sb(x.r2), sb(x.r3)};
    qa = R4{flip(ma, swap(y.r0)), flip(ma, swap(y.r1)), flip(ma, swap(y.r2)), flip(ma, swap(y.r3))};
    qb = R4{flip(mb, y.r0), flip(mb, y.r1), flip(mb, y.r2), flip(mb, y.r3)};
    bar(qa);
    bar(qb);
}
KAIRN_FORCEINLINE R4 mul_sel2(const R4& x, const R4& y) noexcept {
    R4 pa, qa, pb, qb, a, b, z;
    select2_4(x, y, pa, qa, pb, qb);
    V p1, p2;
    M oka = mall(), okb = mall();
    qmul<V, true>(pa.r0, pa.r1, pa.r2, pa.r3, qa.r0, qa.r1, qa.r2, qa.r3, p1, a.r0, a.r1, a.r2, a.r3, oka);
    qmul<V, true>(pb.r0, pb.r1, pb.r2, pb.r3, qb.r0, qb.r1, qb.r2, qb.r3, p2, b.r0, b.r1, b.r2, b.r3, okb);
    // Only the chosen candidate's exactness matters: the other is an upper bound of a smaller corner
    // (an inexact one that came out above the exact one would have been chosen, and is then tested).
    const M ok = mblend(qmax(a.r0, a.r1, a.r2, a.r3, b.r0, b.r1, b.r2, b.r3, z.r0, z.r1, z.r2, z.r3), oka, okb);
    if (!(all_set(ok) && normal(z)) || any(mor(big(p1), big(p2)))) [[unlikely]]
        return mul_special(x, y);
    return z;
}

#if KAIRN_UPWARD2_AVX2
// Form "sel4" (AVX2): sel2's two candidates in the four lanes of 256-bit registers, (A | B) for each
// of the four limbs, one product network on four lanes, then the greater of the halves.
KAIRN_FORCEINLINE V4 wide(V lo, V hi) noexcept { return _mm256_set_m128d(hi, lo); }
KAIRN_FORCEINLINE R4 mul_sel4(const R4& x, const R4& y) noexcept {
    R4 pa, qa, pb, qb, z;
    select2_4(x, y, pa, qa, pb, qb);
    V4 p, c0, c1, c2, c3;
    V4 ok = all_mask<V4>();
    qmul<V4, true>(wide(pa.r0, pb.r0), wide(pa.r1, pb.r1), wide(pa.r2, pb.r2), wide(pa.r3, pb.r3), wide(qa.r0, qb.r0), wide(qa.r1, qb.r1),
         wide(qa.r2, qb.r2), wide(qa.r3, qb.r3), p, c0, c1, c2, c3, ok);
    auto lo = [](V4 a) noexcept { return _mm256_castpd256_pd128(a); };
    auto hi = [](V4 a) noexcept { return _mm256_extractf128_pd(a, 1); };
    const M c = qmax(lo(c0), lo(c1), lo(c2), lo(c3), hi(c0), hi(c1), hi(c2), hi(c3), z.r0, z.r1, z.r2, z.r3);
    const M okc = mblend(c, lo(ok), hi(ok));   // the chosen candidate's exactness (as in sel2)
    if (!(all_set(okc) && normal(z)) || any(big(p))) [[unlikely]]
        return mul_special(x, y);
    return z;
}
#endif

}  // namespace
}  // namespace kairn::experimental::upward4::detail
