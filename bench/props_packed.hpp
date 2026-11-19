// Measurement props for packed code, as props.hpp for scalar code: the generated packed cores
// with every opaque product written as a plain multiplication, the baseline of "what does the
// opaque product cost", over a few register operations spelled as kairn/gen/avx2.hpp and
// kairn/gen/neon.hpp spell them. Not part of the library. The packed full kernels are not props:
// the generator emits them (with blends), and packed.cpp times those.
#pragma once

#if (defined(__AVX2__) && defined(__FMA__)) || (defined(_MSC_VER) && !defined(__clang__) && defined(__AVX2__))
#include <kairn/gen/avx2.hpp>
#define KB_PACKED_AVX2 1
#elif defined(__aarch64__) || defined(_M_ARM64)
#include <kairn/gen/neon.hpp>
#define KB_PACKED_NEON 1
#endif

#if defined(KB_PACKED_AVX2) || defined(KB_PACKED_NEON)
#define KB_PACKED 1

namespace kairn_bench::packed {

#if defined(KB_PACKED_AVX2)
inline constexpr const char* backend = "avx2";
using V = __m256d;
inline constexpr int W = 4;
KAIRN_GEN_FORCEINLINE V load(const double* p) noexcept { return _mm256_loadu_pd(p); }
KAIRN_GEN_FORCEINLINE void store(double* p, V v) noexcept { _mm256_storeu_pd(p, v); }
KAIRN_GEN_FORCEINLINE V set1(double a) noexcept { return _mm256_set1_pd(a); }
KAIRN_GEN_FORCEINLINE V add(V a, V b) noexcept { return _mm256_add_pd(a, b); }
KAIRN_GEN_FORCEINLINE V sub(V a, V b) noexcept { return _mm256_sub_pd(a, b); }
KAIRN_GEN_FORCEINLINE V mul(V a, V b) noexcept { return _mm256_mul_pd(a, b); }
KAIRN_GEN_FORCEINLINE V neg(V a) noexcept { return _mm256_xor_pd(a, _mm256_set1_pd(-0.0)); }
KAIRN_GEN_FORCEINLINE V fma(V a, V b, V c) noexcept { return _mm256_fmadd_pd(a, b, c); }
KAIRN_GEN_FORCEINLINE V fms(V a, V b, V c) noexcept { return _mm256_fmsub_pd(a, b, c); }
KAIRN_GEN_FORCEINLINE V abs(V a) noexcept { return _mm256_andnot_pd(_mm256_set1_pd(-0.0), a); }
#else
inline constexpr const char* backend = "neon";
using V = float64x2_t;
inline constexpr int W = 2;
KAIRN_GEN_FORCEINLINE V load(const double* p) noexcept { return vld1q_f64(p); }
KAIRN_GEN_FORCEINLINE void store(double* p, V v) noexcept { vst1q_f64(p, v); }
KAIRN_GEN_FORCEINLINE V set1(double a) noexcept { return vdupq_n_f64(a); }
KAIRN_GEN_FORCEINLINE V add(V a, V b) noexcept { return vaddq_f64(a, b); }
KAIRN_GEN_FORCEINLINE V sub(V a, V b) noexcept { return vsubq_f64(a, b); }
KAIRN_GEN_FORCEINLINE V mul(V a, V b) noexcept { return vmulq_f64(a, b); }
KAIRN_GEN_FORCEINLINE V neg(V a) noexcept { return vnegq_f64(a); }
KAIRN_GEN_FORCEINLINE V fma(V a, V b, V c) noexcept { return vfmaq_f64(c, a, b); }
KAIRN_GEN_FORCEINLINE V fms(V a, V b, V c) noexcept { return vfmaq_f64(vnegq_f64(c), a, b); }
KAIRN_GEN_FORCEINLINE V abs(V a) noexcept { return vabsq_f64(a); }
#endif

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

// ball_mul_2 (second radius design) with p = rx * ry plain; U, E and H of binary64, as in
// props.hpp.
KAIRN_GEN_FORCEINLINE void ball_mul_2_plain(V cx0, V cx1, V rx, V cy0, V cy1, V ry, V& cz0_out, V& cz1_out, V& rz_out) noexcept {
    V cz0, cz1;
    mul_2_2_plain(cx0, cx1, cy0, cy1, cz0, cz1);
    const V ax = abs(cx0);
    const V ay = abs(cy0);
    const V az = abs(cz0);
    const V p = mul(rx, ry);
    const V q = fma(ay, rx, p);
    const V w = fma(ax, ry, q);
    const V t = fma(az, set1(0x1.0000000000001p-104), w);
    const V rz = fma(t, set1(0x1.0000000000004p+0), set1(0x1.0000000000005p-1022));
    cz0_out = cz0;
    cz1_out = cz1;
    rz_out = rz;
}

}  // namespace kairn_bench::packed

#endif
