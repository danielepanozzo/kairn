// A packed kernel with a planted fault, for tests/lanes/lane_fault.py (docs/developer/testing.md,
// "Packed kernels"): mul_2_2_full of include/kairn/gen/neon.hpp and avx2.hpp, the generated code
// but for the mask of its special-value select. The generated kernel returns the core's product z
// where z0 is finite (f) and the special value r (an infinity, or NaN) elsewhere. This copy
// selects z where f holds and the four limbs of the operands are finite (g), which is the same
// (a limb that is not finite makes z0 not finite), but takes g from the neighboring lane: lane i
// reads lane i + 1, the last lane lane 0. A lane whose neighbor's operands are of its own kind
// (all finite, or not) gets the right result; a lane with finite operands and a finite product
// beside one with a non-finite operand gets r, an infinity or NaN, in place of its product. So a
// register catches the fault only if it mixes a non-finite operand with finite ones, which the
// consecutive assignment of the oracle's stream never does at W = 2 and 4 (the counts of
// docs/developer/testing.md). The planted mask is g and not f because f also fails on finite
// operands whose product overflows, and the strata edge and threshold pair those with products
// that do not in consecutive lines: a planted f is caught by both assignments.
//
// gen/tests/packed_runner.cpp is built with this header in place of the backend's
// (KAIRN_RUNNER_HEADER) and the table lane_fault.inc in place of runner_kernels.inc
// (KAIRN_RUNNER_TABLE): tests/CMakeLists.txt, kairn-gen-packed-runner-lane-fault.
#ifndef KAIRN_TESTS_LANE_FAULT_HPP
#define KAIRN_TESTS_LANE_FAULT_HPP

#include <limits>

#if defined(__AVX2__)
#include "kairn/gen/avx2.hpp"
#else
#include "kairn/gen/neon.hpp"
#endif

namespace kairn_lane_fault {

#if defined(__AVX2__)
// The mask of lane i + 1 in lane i.
inline __m256d neighbor(__m256d m) noexcept { return _mm256_permute4x64_pd(m, _MM_SHUFFLE(0, 3, 2, 1)); }
inline __m256 neighbor(__m256 m) noexcept {
    return _mm256_permutevar8x32_ps(m, _mm256_setr_epi32(1, 2, 3, 4, 5, 6, 7, 0));
}
// g: the four limbs of the operands finite.
inline __m256d finite(__m256d a, __m256d b, __m256d c, __m256d d) noexcept {
    const __m256d sign = _mm256_set1_pd(-0.0), inf = _mm256_set1_pd(std::numeric_limits<double>::infinity());
    const __m256d ab = _mm256_and_pd(_mm256_cmp_pd(_mm256_andnot_pd(sign, a), inf, _CMP_LT_OQ),
                                     _mm256_cmp_pd(_mm256_andnot_pd(sign, b), inf, _CMP_LT_OQ));
    const __m256d cd = _mm256_and_pd(_mm256_cmp_pd(_mm256_andnot_pd(sign, c), inf, _CMP_LT_OQ),
                                     _mm256_cmp_pd(_mm256_andnot_pd(sign, d), inf, _CMP_LT_OQ));
    return _mm256_and_pd(ab, cd);
}
inline __m256 finite(__m256 a, __m256 b, __m256 c, __m256 d) noexcept {
    const __m256 sign = _mm256_set1_ps(-0.0f), inf = _mm256_set1_ps(std::numeric_limits<float>::infinity());
    const __m256 ab = _mm256_and_ps(_mm256_cmp_ps(_mm256_andnot_ps(sign, a), inf, _CMP_LT_OQ),
                                    _mm256_cmp_ps(_mm256_andnot_ps(sign, b), inf, _CMP_LT_OQ));
    const __m256 cd = _mm256_and_ps(_mm256_cmp_ps(_mm256_andnot_ps(sign, c), inf, _CMP_LT_OQ),
                                    _mm256_cmp_ps(_mm256_andnot_ps(sign, d), inf, _CMP_LT_OQ));
    return _mm256_and_ps(ab, cd);
}

inline void mul_2_2_full(__m256d x0, __m256d x1, __m256d y0, __m256d y1, __m256d& w0_out, __m256d& w1_out) noexcept {
    const __m256d z0_ch = _mm256_fmadd_pd(x0, y0, _mm256_setzero_pd());
    const __m256d z0_cl1 = _mm256_fmsub_pd(x0, y0, z0_ch);
    const __m256d z0_tl0 = _mm256_fmadd_pd(x1, y1, _mm256_setzero_pd());
    const __m256d z0_tl1 = _mm256_fmadd_pd(x0, y1, z0_tl0);
    const __m256d z0_cl2 = _mm256_fmadd_pd(x1, y0, z0_tl1);
    const __m256d z0_cl3 = _mm256_add_pd(z0_cl1, z0_cl2);
    const __m256d z0 = _mm256_add_pd(z0_ch, z0_cl3);
    const __m256d z0_z = _mm256_sub_pd(z0, z0_ch);
    const __m256d z1 = _mm256_sub_pd(z0_cl3, z0_z);
    const __m256d t = _mm256_fmadd_pd(x0, y0, _mm256_setzero_pd());
    const __m256d a = _mm256_andnot_pd(_mm256_set1_pd(-0.0), z0);
    const __m256d f0 = _mm256_cmp_pd(a, _mm256_set1_pd(std::numeric_limits<double>::infinity()), _CMP_LT_OQ);
    // The planted fault: g of the neighboring lane.
    const __m256d f = _mm256_and_pd(f0, neighbor(finite(x0, x1, y0, y1)));
    const __m256d r0 = _mm256_mul_pd(t, _mm256_set1_pd(std::numeric_limits<double>::infinity()));
    const __m256d n = _mm256_cmp_pd(r0, r0, _CMP_EQ_OQ);
    const __m256d r1 = _mm256_blendv_pd(r0, _mm256_setzero_pd(), n);
    w0_out = _mm256_blendv_pd(r0, z0, f);
    w1_out = _mm256_blendv_pd(r1, z1, f);
}
inline void mul_2_2_full(__m256 x0, __m256 x1, __m256 y0, __m256 y1, __m256& w0_out, __m256& w1_out) noexcept {
    const __m256 z0_ch = _mm256_fmadd_ps(x0, y0, _mm256_setzero_ps());
    const __m256 z0_cl1 = _mm256_fmsub_ps(x0, y0, z0_ch);
    const __m256 z0_tl0 = _mm256_fmadd_ps(x1, y1, _mm256_setzero_ps());
    const __m256 z0_tl1 = _mm256_fmadd_ps(x0, y1, z0_tl0);
    const __m256 z0_cl2 = _mm256_fmadd_ps(x1, y0, z0_tl1);
    const __m256 z0_cl3 = _mm256_add_ps(z0_cl1, z0_cl2);
    const __m256 z0 = _mm256_add_ps(z0_ch, z0_cl3);
    const __m256 z0_z = _mm256_sub_ps(z0, z0_ch);
    const __m256 z1 = _mm256_sub_ps(z0_cl3, z0_z);
    const __m256 t = _mm256_fmadd_ps(x0, y0, _mm256_setzero_ps());
    const __m256 a = _mm256_andnot_ps(_mm256_set1_ps(-0.0f), z0);
    const __m256 f0 = _mm256_cmp_ps(a, _mm256_set1_ps(std::numeric_limits<float>::infinity()), _CMP_LT_OQ);
    // The planted fault, as above.
    const __m256 f = _mm256_and_ps(f0, neighbor(finite(x0, x1, y0, y1)));
    const __m256 r0 = _mm256_mul_ps(t, _mm256_set1_ps(std::numeric_limits<float>::infinity()));
    const __m256 n = _mm256_cmp_ps(r0, r0, _CMP_EQ_OQ);
    const __m256 r1 = _mm256_blendv_ps(r0, _mm256_setzero_ps(), n);
    w0_out = _mm256_blendv_ps(r0, z0, f);
    w1_out = _mm256_blendv_ps(r1, z1, f);
}
#else
// The mask of lane i + 1 in lane i.
inline uint64x2_t neighbor(uint64x2_t m) noexcept { return vextq_u64(m, m, 1); }
inline uint32x4_t neighbor(uint32x4_t m) noexcept { return vextq_u32(m, m, 1); }
// g: the four limbs of the operands finite.
inline uint64x2_t finite(float64x2_t a, float64x2_t b, float64x2_t c, float64x2_t d) noexcept {
    const float64x2_t inf = vdupq_n_f64(std::numeric_limits<double>::infinity());
    return vandq_u64(vandq_u64(vcltq_f64(vabsq_f64(a), inf), vcltq_f64(vabsq_f64(b), inf)),
                     vandq_u64(vcltq_f64(vabsq_f64(c), inf), vcltq_f64(vabsq_f64(d), inf)));
}
inline uint32x4_t finite(float32x4_t a, float32x4_t b, float32x4_t c, float32x4_t d) noexcept {
    const float32x4_t inf = vdupq_n_f32(std::numeric_limits<float>::infinity());
    return vandq_u32(vandq_u32(vcltq_f32(vabsq_f32(a), inf), vcltq_f32(vabsq_f32(b), inf)),
                     vandq_u32(vcltq_f32(vabsq_f32(c), inf), vcltq_f32(vabsq_f32(d), inf)));
}

inline void mul_2_2_full(float64x2_t x0, float64x2_t x1, float64x2_t y0, float64x2_t y1, float64x2_t& w0_out,
                         float64x2_t& w1_out) noexcept {
    const float64x2_t z0_ch = vfmaq_f64(vdupq_n_f64(0.0), x0, y0);
    const float64x2_t z0_cl1 = vfmaq_f64(vnegq_f64(z0_ch), x0, y0);
    const float64x2_t z0_tl0 = vfmaq_f64(vdupq_n_f64(0.0), x1, y1);
    const float64x2_t z0_tl1 = vfmaq_f64(z0_tl0, x0, y1);
    const float64x2_t z0_cl2 = vfmaq_f64(z0_tl1, x1, y0);
    const float64x2_t z0_cl3 = vaddq_f64(z0_cl1, z0_cl2);
    const float64x2_t z0 = vaddq_f64(z0_ch, z0_cl3);
    const float64x2_t z0_z = vsubq_f64(z0, z0_ch);
    const float64x2_t z1 = vsubq_f64(z0_cl3, z0_z);
    const float64x2_t t = vfmaq_f64(vdupq_n_f64(0.0), x0, y0);
    const float64x2_t a = vabsq_f64(z0);
    const uint64x2_t f0 = vcltq_f64(a, vdupq_n_f64(std::numeric_limits<double>::infinity()));
    // The planted fault: g of the neighboring lane.
    const uint64x2_t f = vandq_u64(f0, neighbor(finite(x0, x1, y0, y1)));
    const float64x2_t r0 = vmulq_f64(t, vdupq_n_f64(std::numeric_limits<double>::infinity()));
    const uint64x2_t n = vceqq_f64(r0, r0);
    const float64x2_t r1 = vbslq_f64(n, vdupq_n_f64(0.0), r0);
    w0_out = vbslq_f64(f, z0, r0);
    w1_out = vbslq_f64(f, z1, r1);
}
inline void mul_2_2_full(float32x4_t x0, float32x4_t x1, float32x4_t y0, float32x4_t y1, float32x4_t& w0_out,
                         float32x4_t& w1_out) noexcept {
    const float32x4_t z0_ch = vfmaq_f32(vdupq_n_f32(0.0f), x0, y0);
    const float32x4_t z0_cl1 = vfmaq_f32(vnegq_f32(z0_ch), x0, y0);
    const float32x4_t z0_tl0 = vfmaq_f32(vdupq_n_f32(0.0f), x1, y1);
    const float32x4_t z0_tl1 = vfmaq_f32(z0_tl0, x0, y1);
    const float32x4_t z0_cl2 = vfmaq_f32(z0_tl1, x1, y0);
    const float32x4_t z0_cl3 = vaddq_f32(z0_cl1, z0_cl2);
    const float32x4_t z0 = vaddq_f32(z0_ch, z0_cl3);
    const float32x4_t z0_z = vsubq_f32(z0, z0_ch);
    const float32x4_t z1 = vsubq_f32(z0_cl3, z0_z);
    const float32x4_t t = vfmaq_f32(vdupq_n_f32(0.0f), x0, y0);
    const float32x4_t a = vabsq_f32(z0);
    const uint32x4_t f0 = vcltq_f32(a, vdupq_n_f32(std::numeric_limits<float>::infinity()));
    // The planted fault, as above.
    const uint32x4_t f = vandq_u32(f0, neighbor(finite(x0, x1, y0, y1)));
    const float32x4_t r0 = vmulq_f32(t, vdupq_n_f32(std::numeric_limits<float>::infinity()));
    const uint32x4_t n = vceqq_f32(r0, r0);
    const float32x4_t r1 = vbslq_f32(n, vdupq_n_f32(0.0f), r0);
    w0_out = vbslq_f32(f, z0, r0);
    w1_out = vbslq_f32(f, z1, r1);
}
#endif

}  // namespace kairn_lane_fault

#endif
