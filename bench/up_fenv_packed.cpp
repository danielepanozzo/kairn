// Measurement props for the functions on arrays of the round-up interval (bench/up_data.hpp,
// up_arrays.cpp): the classical packed interval, the rounding mode set upward once around a whole
// loop of packed operations, as m2_fenv_packed.cpp: interval_add_1, interval_sub_1 and
// interval_mul_1 for double (backend upwa) and float (upwaf), variant fenv_loop, on one array per
// bound placed as the arrays of the round-up interval are (up_data.hpp, Bounds; m2_fenv_packed.cpp
// times the sum and the product of double on the arrays of m2.cpp). Two plain numbers per interval,
// the lower bound as RD(t) = -RU(-t), no special case. Not part of the library; compiled as
// m2_fenv_packed.cpp (m2_fenv.cpp says how the compilers are made to honor the mode; AVX2 and FMA
// on x86-64); it does not include Kairn: the register operations are spelled here. Checked against
// Kairn's default kernels before it is timed.
#include <cfenv>

#include "up_data.hpp"

#if defined(__clang__)
#pragma STDC FENV_ACCESS ON
#elif defined(_MSC_VER)
#pragma fenv_access(on)
#endif

#if (defined(__AVX2__) && defined(__FMA__)) || defined(__aarch64__)

#if defined(__AVX2__)
#include <immintrin.h>
#else
#include <arm_neon.h>
#endif

namespace {
using kairn_bench::m2::Entry;
using kairn_bench::m2::kN;
using kairn_bench::m2::Raw;

#if defined(__AVX2__)
struct D {
    using V = __m256d;
    static constexpr int W = 4;
    static V load(const double* p) { return _mm256_loadu_pd(p); }
    static void store(double* p, V v) { _mm256_storeu_pd(p, v); }
    static V add(V a, V b) { return _mm256_add_pd(a, b); }
    static V sub(V a, V b) { return _mm256_sub_pd(a, b); }
    static V mul(V a, V b) { return _mm256_mul_pd(a, b); }
    static V neg(V a) { return _mm256_xor_pd(a, _mm256_set1_pd(-0.0)); }
    static V max(V a, V b) { return _mm256_max_pd(a, b); }
};
struct F {
    using V = __m256;
    static constexpr int W = 8;
    static V load(const float* p) { return _mm256_loadu_ps(p); }
    static void store(float* p, V v) { _mm256_storeu_ps(p, v); }
    static V add(V a, V b) { return _mm256_add_ps(a, b); }
    static V sub(V a, V b) { return _mm256_sub_ps(a, b); }
    static V mul(V a, V b) { return _mm256_mul_ps(a, b); }
    static V neg(V a) { return _mm256_xor_ps(a, _mm256_set1_ps(-0.0f)); }
    static V max(V a, V b) { return _mm256_max_ps(a, b); }
};
#else
struct D {
    using V = float64x2_t;
    static constexpr int W = 2;
    static V load(const double* p) { return vld1q_f64(p); }
    static void store(double* p, V v) { vst1q_f64(p, v); }
    static V add(V a, V b) { return vaddq_f64(a, b); }
    static V sub(V a, V b) { return vsubq_f64(a, b); }
    static V mul(V a, V b) { return vmulq_f64(a, b); }
    static V neg(V a) { return vnegq_f64(a); }
    static V max(V a, V b) { return vmaxq_f64(a, b); }
};
struct F {
    using V = float32x4_t;
    static constexpr int W = 4;
    static V load(const float* p) { return vld1q_f32(p); }
    static void store(float* p, V v) { vst1q_f32(p, v); }
    static V add(V a, V b) { return vaddq_f32(a, b); }
    static V sub(V a, V b) { return vsubq_f32(a, b); }
    static V mul(V a, V b) { return vmulq_f32(a, b); }
    static V neg(V a) { return vnegq_f32(a); }
    static V max(V a, V b) { return vmaxq_f32(a, b); }
};
#endif

// The bounds of this unit, and the check of its functions.
struct Mine : kairn_bench::up::BoundsOf<2> {
    template <class T>
    static kairn_bench::up::Bounds<T>* bounds() {
        if constexpr (sizeof(T) == 8)
            return b64;
        else
            return b32;
    }
};

// The interval operations under the mode upward, as m2_fenv_packed.cpp writes them.
template <class R>
KB_UP_INLINE void iadd(typename R::V xl, typename R::V xu, typename R::V yl, typename R::V yu, typename R::V& zl,
                       typename R::V& zu) {
    zl = R::neg(R::add(R::neg(xl), R::neg(yl)));
    zu = R::add(xu, yu);
}
template <class R>
KB_UP_INLINE void isub(typename R::V xl, typename R::V xu, typename R::V yl, typename R::V yu, typename R::V& zl,
                       typename R::V& zu) {
    zl = R::neg(R::sub(yu, xl));
    zu = R::sub(xu, yl);
}
template <class R>
KB_UP_INLINE void imul(typename R::V xl, typename R::V xu, typename R::V yl, typename R::V yu, typename R::V& zl,
                       typename R::V& zu) {
    const typename R::V nl = R::neg(xl), nu = R::neg(xu);
    zl = R::neg(R::max(R::max(R::mul(nl, yl), R::mul(nl, yu)), R::max(R::mul(nu, yl), R::mul(nu, yu))));
    zu = R::max(R::max(R::mul(xl, yl), R::mul(xl, yu)), R::max(R::mul(xu, yl), R::mul(xu, yu)));
}

}  // namespace

// X(B, SUF, T, R, KERNEL, OP)
#define KB_UPFP_LIST(X)                                                                            \
    X("upwa", upwa, double, D, interval_add_1, iadd)                                               \
    X("upwa", upwa, double, D, interval_sub_1, isub)                                               \
    X("upwa", upwa, double, D, interval_mul_1, imul)                                               \
    X("upwaf", upwaf, float, F, interval_add_1, iadd)                                              \
    X("upwaf", upwaf, float, F, interval_sub_1, isub)                                              \
    X("upwaf", upwaf, float, F, interval_mul_1, imul)

#define KB_UPFP_DEF(B, SUF, T, R, KERNEL, OP)                                                      \
    extern "C" KB_NOINLINE void kb_##SUF##_tp_##KERNEL##__fenv_loop(void*) {                       \
        const kairn_bench::up::Bounds<T>& b = *Mine::bounds<T>();                                  \
        std::fesetround(FE_UPWARD);                                                                \
        for (int i = 0; i < kN; i += R::W) {                                                       \
            R::V zl, zu;                                                                           \
            OP<R>(R::load(b.xl + i), R::load(b.xh + i), R::load(b.yl + i), R::load(b.yh + i), zl, zu); \
            R::store(b.zl + i, zl);                                                                \
            R::store(b.zh + i, zu);                                                                \
        }                                                                                          \
        std::fesetround(FE_TONEAREST);                                                             \
    }
#define KB_UPFP_ROW(B, SUF, T, R, KERNEL, OP)                                                      \
    {B "/tp/" #KERNEL "/fenv_loop", kb_##SUF##_tp_##KERNEL##__fenv_loop, int(8 * sizeof(T)), R::W, kN, 0, 0, \
     Mine::check},

KB_UPFP_LIST(KB_UPFP_DEF)

namespace {
const Entry table[] = {
    KB_UPFP_LIST(KB_UPFP_ROW)
    {nullptr, nullptr, 0, 0, 0, 0, 0, nullptr},
};
kairn_bench::m2::TableLink link{table, nullptr};
[[maybe_unused]] const bool registered =
    (link.next = kairn_bench::m2::m2_extra_tables, kairn_bench::m2::m2_extra_tables = &link, true);
}  // namespace

#endif
