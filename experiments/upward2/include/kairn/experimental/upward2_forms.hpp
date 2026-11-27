/// @file
/// EXPERIMENTAL, NOT VERIFIED, not part of the library: no bound stated here is proved. The forms of
/// the product and of the sum of the two-limb interval rounded upward that were measured against
/// the ones the type uses (experiments/upward2/README.md), kept for the measurements and the checks
/// only: the type itself (upward2.hpp) does not use them. Requires the rounding mode upward set by
/// kairn::upward::Scope and the options of docs/concepts/upward.md (GCC and Clang -frounding-math).
#pragma once

#include "upward2.hpp"

namespace kairn::experimental::upward2::detail {
namespace {

// The products: each computes, on a fast path, candidate pairs by pair_mul and checks that every
// leading product p computed is finite with |p| < MAX; otherwise it returns mul_special.

// Form "sel2": operands selected by the signs of the bounds, without branches, two candidates per
// lane, the greater kept. With x = [a, b], y = [c, d]:
//   upper = max(xa * c, xb * d),   xa = (b <= 0 and c > 0) ? b : a,   xb = (a >= 0 and d < 0) ? a : b
//   -lower = max(xa' * (-d), xb' * (-c)),  xa' = (b <= 0 and d < 0) ? b : a,  xb' = (a >= 0 and c > 0) ? a : b
// (the second line is the first for -y). Case by case: a >= 0 makes xb * d the upper bound and xa * c
// = a c no greater; b <= 0 makes xa * c the upper bound and xb * d = b d no greater; a < 0 < b gives
// max(a c, b d), which is the upper bound in each of the three cases of y. In lanes: candidate A =
// (xa * c, xa' * (-d)), candidate B = (xb * d, xb' * (-c)); a = -xn, c = -yn, so
//   A = (ma ? xu : xn) * (ma ? -(yn, yu) : (yn, yu)),  ma = (b <= 0 and (c > 0, d < 0))
//   B = (mb ? xn : xu) * (mb ? -(yu, yn) : (yu, yn)),  mb = (a >= 0 and (d < 0, c > 0)),
// each "?" per lane. The signs are those of the heads (an upper-normalized head has the sign of its
// value). At a zero bound either choice of a mask gives the same value (both candidates are 0).
KAIRN_FORCEINLINE void select2(const R& x, const R& y, R& pa, R& qa, R& pb, R& qb) noexcept {
    const M xle = le0(x.h);   // lanes: b <= 0, a >= 0
    const M ylt = lt0(y.h);   // lanes: d < 0, c > 0
    const M ma = mand(mdup0(xle), mswap(ylt));
    const M mb = mand(mdup1(xle), ylt);
    const V x0h = dup0(x.h), x1h = dup1(x.h), x0l = dup0(x.l), x1l = dup1(x.l);
    pa = R{blend(ma, x0h, x1h), blend(ma, x0l, x1l)};
    pb = R{blend(mb, x1h, x0h), blend(mb, x1l, x0l)};
    qa = R{flip(ma, swap(y.h)), flip(ma, swap(y.l))};
    qb = R{flip(mb, y.h), flip(mb, y.l)};
    bar(qa);
    bar(qb);
}

KAIRN_FORCEINLINE R mul_sel2(R x, R y) noexcept {
    R pa, qa, pb, qb;
    select2(x, y, pa, qa, pb, qb);
    V p1, p2, ah, al, bh, bl;
    pair_mul(pa.h, pa.l, qa.h, qa.l, p1, ah, al);
    pair_mul(pb.h, pb.l, qb.h, qb.l, p2, bh, bl);
    if (any(mor(big(p1), big(p2)))) [[unlikely]]
        return mul_special(x, y);
    R z;
    lexmax(ah, al, bh, bl, z.h, z.l);
    return z;
}

// Form "eight": the eight candidates of mul_special on the fast path, the greatest per lane.
KAIRN_FORCEINLINE R mul_eight(R x, R y) noexcept {
    V nyh = neg(y.h), nyl = neg(y.l);
    bar(nyh);
    bar(nyl);
    const V sxh = swap(x.h), sxl = swap(x.l);
    V p1, p2, p3, p4, h1, l1, h2, l2, h3, l3, h4, l4;
    pair_mul(x.h, x.l, dup0(y.h), dup0(y.l), p1, h1, l1);
    pair_mul(sxh, sxl, dup1(y.h), dup1(y.l), p2, h2, l2);
    pair_mul(sxh, sxl, dup0(nyh), dup0(nyl), p3, h3, l3);
    pair_mul(x.h, x.l, dup1(nyh), dup1(nyl), p4, h4, l4);
    if (any(mor(mor(big(p1), big(p2)), mor(big(p3), big(p4))))) [[unlikely]]
        return mul_special(x, y);
    V ah, al, bh, bl;
    R z;
    lexmax(h1, l1, h2, l2, ah, al);
    lexmax(h3, l3, h4, l4, bh, bl);
    lexmax(ah, al, bh, bl, z.h, z.l);
    return z;
}


#if KAIRN_UPWARD2_FORM == KAIRN_UPWARD2_FORM_NEON
// On AArch64 the four bits weighted in the lanes and added across them: one move to a general
// register instead of two.
KAIRN_FORCEINLINE int case_of(const R& x, const R& y) noexcept {
    const uint64x2_t wx = vandq_u64(le0(x.h), vcombine_u64(vcreate_u64(1), vcreate_u64(2)));
    const uint64x2_t wy = vandq_u64(le0(y.h), vcombine_u64(vcreate_u64(4), vcreate_u64(8)));
    return int(vaddvq_u64(vorrq_u64(wx, wy)));
}
#else
KAIRN_FORCEINLINE int case_of(const R& x, const R& y) noexcept { return bits(le0(x.h)) | (bits(le0(y.h)) << 2); }
#endif


// The lanes of a register picked by a case: lane 0 from lane i0 of a, lane 1 from lane i1.
#if KAIRN_UPWARD2_FORM == KAIRN_UPWARD2_FORM_SSE || KAIRN_UPWARD2_FORM == KAIRN_UPWARD2_FORM_NEON
// The controls of the cases, six 64-bit words each: the lane picks of P (two words), of Q (two),
// and the sign mask of Q (two). On x86-64 vpermilpd selects by bit 1 of each 64-bit control; on
// AArch64 TBL takes byte indices, lane k of the source being bytes 8 k to 8 k + 7.
#if KAIRN_UPWARD2_FORM == KAIRN_UPWARD2_FORM_SSE
inline constexpr std::uint64_t kPick0 = 0, kPick1 = 2;
#else
inline constexpr std::uint64_t kPick0 = 0x0706050403020100u, kPick1 = 0x0f0e0d0c0b0a0908u;
#endif
inline constexpr std::uint64_t kSign = 0x8000000000000000u;
#define KAIRN_UPWARD2_CTL(k)                                                                                     \
    {kCases[k].p0 == 1 ? kPick1 : kPick0, kCases[k].p1 == 1 ? kPick1 : kPick0, kCases[k].q0 == 1 ? kPick1 : kPick0, \
     kCases[k].q1 == 1 ? kPick1 : kPick0, kCases[k].s0 ? kSign : 0, kCases[k].s1 ? kSign : 0}
alignas(16) inline constexpr std::uint64_t kCtl[16][6] = {
    KAIRN_UPWARD2_CTL(0),  KAIRN_UPWARD2_CTL(1),  KAIRN_UPWARD2_CTL(2),  KAIRN_UPWARD2_CTL(3),
    KAIRN_UPWARD2_CTL(4),  KAIRN_UPWARD2_CTL(5),  KAIRN_UPWARD2_CTL(6),  KAIRN_UPWARD2_CTL(7),
    KAIRN_UPWARD2_CTL(8),  KAIRN_UPWARD2_CTL(9),  KAIRN_UPWARD2_CTL(10), KAIRN_UPWARD2_CTL(11),
    KAIRN_UPWARD2_CTL(12), KAIRN_UPWARD2_CTL(13), KAIRN_UPWARD2_CTL(14), KAIRN_UPWARD2_CTL(15)};
#undef KAIRN_UPWARD2_CTL
#endif
#if KAIRN_UPWARD2_FORM == KAIRN_UPWARD2_FORM_SSE
KAIRN_FORCEINLINE void pick_case(const R& x, const R& y, int k, R& p, R& q) noexcept {
    const __m128i cp = _mm_load_si128(reinterpret_cast<const __m128i*>(&kCtl[k][0]));
    const __m128i cq = _mm_load_si128(reinterpret_cast<const __m128i*>(&kCtl[k][2]));
    const __m128d s = _mm_castsi128_pd(_mm_load_si128(reinterpret_cast<const __m128i*>(&kCtl[k][4])));
    p = R{_mm_permutevar_pd(x.h, cp), _mm_permutevar_pd(x.l, cp)};
    q = R{_mm_xor_pd(_mm_permutevar_pd(y.h, cq), s), _mm_xor_pd(_mm_permutevar_pd(y.l, cq), s)};
}
#elif KAIRN_UPWARD2_FORM == KAIRN_UPWARD2_FORM_NEON
KAIRN_FORCEINLINE V pick(V a, uint8x16_t c) noexcept {
    return vreinterpretq_f64_u8(vqtbl1q_u8(vreinterpretq_u8_f64(a), c));
}
KAIRN_FORCEINLINE void pick_case(const R& x, const R& y, int k, R& p, R& q) noexcept {
    const uint8x16_t cp = vld1q_u8(reinterpret_cast<const std::uint8_t*>(&kCtl[k][0]));
    const uint8x16_t cq = vld1q_u8(reinterpret_cast<const std::uint8_t*>(&kCtl[k][2]));
    const uint64x2_t s = vld1q_u64(&kCtl[k][4]);
    p = R{pick(x.h, cp), pick(x.l, cp)};
    q = R{vreinterpretq_f64_u64(veorq_u64(vreinterpretq_u64_f64(pick(y.h, cq)), s)),
          vreinterpretq_f64_u64(veorq_u64(vreinterpretq_u64_f64(pick(y.l, cq)), s))};
}
#else
KAIRN_FORCEINLINE double at(V a, int i) noexcept { return i ? a.v1 : a.v0; }
KAIRN_FORCEINLINE void pick_case(const R& x, const R& y, int k, R& p, R& q) noexcept {
    const Case& c = kCases[k];
    p = R{V{at(x.h, c.p0), at(x.h, c.p1)}, V{at(x.l, c.p0), at(x.l, c.p1)}};
    const M s{c.s0 != 0, c.s1 != 0};
    q = R{flip(s, V{at(y.h, c.q0), at(y.h, c.q1)}), flip(s, V{at(y.l, c.q0), at(y.l, c.q1)})};
}
#endif

// Form "table": the case's operands by a table of lane permutations, no branch but the one to the
// case x ∋ 0, y ∋ 0.
KAIRN_FORCEINLINE R mul_table(R x, R y) noexcept {
    const int k = case_of(x, y);
    if (k == 0) return mul_zero_zero(x, y);
    R p, q;
    pick_case(x, y, k, p, q);
    bar(q);
    return mul_one(p, q, x, y);
}


#if KAIRN_UPWARD2_AVX2
// Form "sel4": sel2's two candidates in the four lanes of one 256-bit register, (A | B), one
// four-lane pair product, then the greater of its halves.
KAIRN_FORCEINLINE __m256d wide(__m128d lo, __m128d hi) noexcept { return _mm256_set_m128d(hi, lo); }
KAIRN_FORCEINLINE R mul_sel4(R x, R y) noexcept {
    const M xle = le0(x.h), ylt = lt0(y.h);
    const M ma = mand(mdup0(xle), mswap(ylt));
    const M mb = mand(mdup1(xle), ylt);
    const __m256d m = wide(ma, mb);
    const __m256d xh = wide(x.h, x.h), xl = wide(x.l, x.l), yh = wide(y.h, y.h), yl = wide(y.l, y.l);
    // P: default (xn, xn | xu, xu), alternative (xu, xu | xn, xn), where m is set.
    const __m256d ph = _mm256_blendv_pd(_mm256_permute_pd(xh, 0x3), _mm256_permute_pd(xh, 0xC), m);
    const __m256d pl = _mm256_blendv_pd(_mm256_permute_pd(xl, 0x3), _mm256_permute_pd(xl, 0xC), m);
    // Q: (yn, yu | yu, yn), negated where m is set.
    const __m256d sg = _mm256_and_pd(m, _mm256_set1_pd(-0.0));
    __m256d qh = _mm256_xor_pd(_mm256_permute_pd(yh, 0x9), sg);
    __m256d ql = _mm256_xor_pd(_mm256_permute_pd(yl, 0x9), sg);
    KAIRN_DETAIL_UPWARD_BARRIER(qh);
    KAIRN_DETAIL_UPWARD_BARRIER(ql);
    // pair_mul on four lanes (the same steps and reasons).
    const __m256d p = _mm256_mul_pd(ph, qh);
    const __m256d e = _mm256_fmadd_pd(ph, qh, _mm256_xor_pd(p, _mm256_set1_pd(-0.0)));
    const __m256d c = _mm256_fmadd_pd(ph, ql, _mm256_fmadd_pd(pl, qh, _mm256_mul_pd(pl, ql)));
    const __m256d w = _mm256_add_pd(e, c);
    const __m256d zh = _mm256_add_pd(p, w);
    const __m256d zl = _mm256_add_pd(_mm256_sub_pd(p, zh), w);
    const __m256d ap = _mm256_andnot_pd(_mm256_set1_pd(-0.0), p);
    if (_mm256_movemask_pd(_mm256_cmp_pd(ap, _mm256_set1_pd(kMax), _CMP_NLT_UQ)) != 0) [[unlikely]]
        return mul_special(x, y);
    R z;
    lexmax(_mm256_castpd256_pd128(zh), _mm256_castpd256_pd128(zl), _mm256_extractf128_pd(zh, 1),
           _mm256_extractf128_pd(zl, 1), z.h, z.l);
    return z;
}
#endif


// The sums measured against add_r. "lean": add_r with fast_two_sum (one orientation, three
// operations) for its two later two-sums: an upper pair of x + y always (see fast_two_sum), but not
// argued upper-normalized when the heads cancel (the checks found none that was not, on their
// samples). "sloppy": the error of the second limbs' sum dropped (t = RU(xl + yl) >= xl + yl), the
// accurate sum's third and fourth lines merged: an upper pair, upper-normalized, but its excess
// relative to the bound is unbounded when the heads cancel.
KAIRN_FORCEINLINE R add_lean(R x, R y) noexcept {
    V s, e, t, f, v, g, zh, zl;
    two_sum(x.h, y.h, s, e);
    two_sum_nonpos(x.l, y.l, t, f);
    fast_two_sum(s, add(e, t), v, g);
    fast_two_sum(v, add(f, g), zh, zl);
    sum_specials(s, zh, zl);
    return R{zh, zl};
}
KAIRN_FORCEINLINE R add_sloppy(R x, R y) noexcept {
    V s, e, zh, zl;
    two_sum(x.h, y.h, s, e);
    two_sum(s, add(e, add(x.l, y.l)), zh, zl);
    sum_specials(s, zh, zl);
    return R{zh, zl};
}

}  // namespace
}  // namespace kairn::experimental::upward2::detail
