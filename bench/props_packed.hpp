// Measurement props for packed code, as props.hpp for scalar code: the plain-product variants and
// form (a) of the full kernels, with blends, written once over a few register operations spelled
// as kairn/gen/avx2.hpp and kairn/gen/neon.hpp spell them. Not part of the library.
#pragma once

#if (defined(__AVX2__) && defined(__FMA__)) || (defined(_MSC_VER) && !defined(__clang__) && defined(__AVX2__))
#include <kairn/gen/avx2.hpp>
#define KB_PACKED_AVX2 1
#elif defined(__aarch64__) || defined(_M_ARM64)
#include <kairn/gen/neon.hpp>
#define KB_PACKED_NEON 1
#endif

#include <limits>

#if defined(KB_PACKED_AVX2) || defined(KB_PACKED_NEON)
#define KB_PACKED 1

namespace kairn_bench::packed {

#if defined(KB_PACKED_AVX2)
inline constexpr const char* backend = "avx2";
using V = __m256d;
using M = __m256d;
inline constexpr int W = 4;
KAIRN_GEN_FORCEINLINE V load(const double* p) noexcept { return _mm256_loadu_pd(p); }
KAIRN_GEN_FORCEINLINE void store(double* p, V v) noexcept { _mm256_storeu_pd(p, v); }
KAIRN_GEN_FORCEINLINE V set1(double a) noexcept { return _mm256_set1_pd(a); }
KAIRN_GEN_FORCEINLINE V add(V a, V b) noexcept { return _mm256_add_pd(a, b); }
KAIRN_GEN_FORCEINLINE V sub(V a, V b) noexcept { return _mm256_sub_pd(a, b); }
KAIRN_GEN_FORCEINLINE V mul(V a, V b) noexcept { return _mm256_mul_pd(a, b); }
KAIRN_GEN_FORCEINLINE V prod(V a, V b) noexcept { return _mm256_fmadd_pd(a, b, _mm256_setzero_pd()); }
KAIRN_GEN_FORCEINLINE V fma(V a, V b, V c) noexcept { return _mm256_fmadd_pd(a, b, c); }
KAIRN_GEN_FORCEINLINE V fms(V a, V b, V c) noexcept { return _mm256_fmsub_pd(a, b, c); }
KAIRN_GEN_FORCEINLINE V abs(V a) noexcept { return _mm256_andnot_pd(_mm256_set1_pd(-0.0), a); }
KAIRN_GEN_FORCEINLINE M lt(V a, V b) noexcept { return _mm256_cmp_pd(a, b, _CMP_LT_OQ); }
KAIRN_GEN_FORCEINLINE M eq(V a, V b) noexcept { return _mm256_cmp_pd(a, b, _CMP_EQ_OQ); }
KAIRN_GEN_FORCEINLINE M and_(M a, M b) noexcept { return _mm256_and_pd(a, b); }
KAIRN_GEN_FORCEINLINE V select(M m, V a, V b) noexcept { return _mm256_blendv_pd(b, a, m); }
#else
inline constexpr const char* backend = "neon";
using V = float64x2_t;
using M = uint64x2_t;
inline constexpr int W = 2;
KAIRN_GEN_FORCEINLINE V load(const double* p) noexcept { return vld1q_f64(p); }
KAIRN_GEN_FORCEINLINE void store(double* p, V v) noexcept { vst1q_f64(p, v); }
KAIRN_GEN_FORCEINLINE V set1(double a) noexcept { return vdupq_n_f64(a); }
KAIRN_GEN_FORCEINLINE V add(V a, V b) noexcept { return vaddq_f64(a, b); }
KAIRN_GEN_FORCEINLINE V sub(V a, V b) noexcept { return vsubq_f64(a, b); }
KAIRN_GEN_FORCEINLINE V mul(V a, V b) noexcept { return vmulq_f64(a, b); }
KAIRN_GEN_FORCEINLINE V prod(V a, V b) noexcept { return vfmaq_f64(vdupq_n_f64(0.0), a, b); }
KAIRN_GEN_FORCEINLINE V fma(V a, V b, V c) noexcept { return vfmaq_f64(c, a, b); }
KAIRN_GEN_FORCEINLINE V fms(V a, V b, V c) noexcept { return vfmaq_f64(vnegq_f64(c), a, b); }
KAIRN_GEN_FORCEINLINE V abs(V a) noexcept { return vabsq_f64(a); }
KAIRN_GEN_FORCEINLINE M lt(V a, V b) noexcept { return vcltq_f64(a, b); }
KAIRN_GEN_FORCEINLINE M eq(V a, V b) noexcept { return vceqq_f64(a, b); }
KAIRN_GEN_FORCEINLINE M and_(M a, M b) noexcept { return vandq_u64(a, b); }
KAIRN_GEN_FORCEINLINE V select(M m, V a, V b) noexcept { return vbslq_f64(m, a, b); }
#endif

KAIRN_GEN_FORCEINLINE V inf() noexcept { return set1(std::numeric_limits<double>::infinity()); }

KAIRN_GEN_FORCEINLINE void fast_two_sum(V a, V b, V& s_out, V& e_out) noexcept {
    const V s = add(a, b);
    const V z = sub(s, a);
    s_out = s;
    e_out = sub(b, z);
}

// --- The opaque product written as a plain product ----------------------------------------------

KAIRN_GEN_FORCEINLINE void two_prod_plain(V a, V b, V& p_out, V& e_out) noexcept {
    const V p = mul(a, b);
    p_out = p;
    e_out = fms(a, b, p);
}

KAIRN_GEN_FORCEINLINE void mul_2_1_plain(V x0, V x1, V a, V& z0, V& z1) noexcept {
    const V ch = mul(x0, a);
    const V cl1 = fms(x0, a, ch);
    const V cl3 = fma(x1, a, cl1);
    fast_two_sum(ch, cl3, z0, z1);
}

KAIRN_GEN_FORCEINLINE void mul_2_2_plain(V x0, V x1, V y0, V y1, V& z0, V& z1) noexcept {
    const V ch = mul(x0, y0);
    const V cl1 = fms(x0, y0, ch);
    const V tl0 = mul(x1, y1);
    const V tl1 = fma(x0, y1, tl0);
    const V cl2 = fma(x1, y0, tl1);
    const V cl3 = add(cl1, cl2);
    fast_two_sum(ch, cl3, z0, z1);
}

KAIRN_GEN_FORCEINLINE void ball_mul_2_plain(V cx0, V cx1, V rx, V cy0, V cy1, V ry, V& cz0_out, V& cz1_out, V& rz_out) noexcept {
    V cz0, cz1, ax, ay, mz, s1, s2, d, rz;
    mul_2_2_plain(cx0, cx1, cy0, cy1, cz0, cz1);
    kairn::gen::abs_upper_2(cx0, cx1, ax);
    kairn::gen::abs_upper_2(cy0, cy1, ay);
    const V t1 = kairn::gen::next_up(mul(ax, ry));
    const V t2 = kairn::gen::next_up(mul(ay, rx));
    const V t3 = kairn::gen::next_up(mul(rx, ry));
    kairn::gen::radd(t1, t2, s1);
    kairn::gen::radd(s1, t3, s2);
    kairn::gen::abs_upper_2(cz0, cz1, mz);
    const V d0 = kairn::gen::next_up(mul(set1(0x1.0000000000001p-104), mz));
    kairn::gen::radd(d0, set1(0x1p-1073), d);
    kairn::gen::radd(s2, d, rz);
    cz0_out = cz0;
    cz1_out = cz1;
    rz_out = rz;
}

// --- The full kernels, form (a), with blends ----------------------------------------------------

KAIRN_GEN_FORCEINLINE void fixup_sel(V z0, V z1, V t, V& w0, V& w1) noexcept {
    const V a = abs(z0);
    const M f = lt(a, inf());
    const V r0 = prod(t, inf());
    const M n = eq(r0, r0);
    const V r1 = select(n, set1(0.0), r0);
    w0 = select(f, z0, r0);
    w1 = select(f, z1, r1);
}

KAIRN_GEN_FORCEINLINE void add_2_2_full_sel(V x0, V x1, V y0, V y1, V& w0, V& w1) noexcept {
    V z0, z1;
    kairn::gen::add_2_2(x0, x1, y0, y1, z0, z1);
    fixup_sel(z0, z1, add(x0, y0), w0, w1);
}

KAIRN_GEN_FORCEINLINE void mul_2_2_full_sel(V x0, V x1, V y0, V y1, V& w0, V& w1) noexcept {
    V z0, z1;
    kairn::gen::mul_2_2(x0, x1, y0, y1, z0, z1);
    fixup_sel(z0, z1, prod(x0, y0), w0, w1);
}

KAIRN_GEN_FORCEINLINE void ball_fixup_sel(V cz0, V cz1, V rz, V rx, V ry, V& cw0, V& cw1, V& rw) noexcept {
    const V q = add(rx, ry);
    const M e = eq(q, q);
    const M f1 = lt(abs(cz0), inf());
    const M f2 = lt(rz, inf());
    const M f = and_(f1, f2);
    const V zero = set1(0.0);
    const V c0 = select(f, cz0, zero);
    const V c1 = select(f, cz1, zero);
    const V r = select(f, rz, inf());
    cw0 = select(e, c0, q);
    cw1 = select(e, c1, q);
    rw = select(e, r, q);
}

KAIRN_GEN_FORCEINLINE void ball_add_2_full_sel(V cx0, V cx1, V rx, V cy0, V cy1, V ry, V& cw0, V& cw1, V& rw) noexcept {
    V cz0, cz1, rz;
    kairn::gen::ball_add_2(cx0, cx1, rx, cy0, cy1, ry, cz0, cz1, rz);
    ball_fixup_sel(cz0, cz1, rz, rx, ry, cw0, cw1, rw);
}

KAIRN_GEN_FORCEINLINE void ball_mul_2_full_sel(V cx0, V cx1, V rx, V cy0, V cy1, V ry, V& cw0, V& cw1, V& rw) noexcept {
    V cz0, cz1, rz;
    kairn::gen::ball_mul_2(cx0, cx1, rx, cy0, cy1, ry, cz0, cz1, rz);
    ball_fixup_sel(cz0, cz1, rz, rx, ry, cw0, cw1, rw);
}

}  // namespace kairn_bench::packed

#endif
