// Kairn's packed interval kernels of one limb (kairn/gen/avx2.hpp, neon.hpp), the comparisons of the
// functions on arrays of the round-up interval (bench/up_data.hpp, up_arrays.cpp) that m2_packed.cpp
// does not have: interval_sub_1 for double (backend upwa) and interval_add_1, interval_sub_1,
// interval_mul_1 for float (upwaf), variant packed, one interval per lane, on one array per bound
// (Raw<T>::sxi, syi), the results to sout[0] and sout[1]. Ordinary code under rounding to nearest,
// compiled as m2_packed.cpp (AVX2 and FMA on x86-64); without a packed backend its table is empty.
#include "m2_data.hpp"
#include "props_packed.hpp"
#include "up_data.hpp"

#if defined(KB_PACKED)

namespace {
namespace kg = kairn::gen;
using kairn_bench::m2::Entry;
using kairn_bench::m2::kN;
using kairn_bench::m2::Raw;

#if defined(KB_PACKED_AVX2)
using VD = __m256d;
using VF = __m256;
constexpr int WD = 4, WF = 8;
KAIRN_GEN_FORCEINLINE VD load(const double* p) noexcept { return _mm256_loadu_pd(p); }
KAIRN_GEN_FORCEINLINE void store(double* p, VD v) noexcept { _mm256_storeu_pd(p, v); }
KAIRN_GEN_FORCEINLINE VF load(const float* p) noexcept { return _mm256_loadu_ps(p); }
KAIRN_GEN_FORCEINLINE void store(float* p, VF v) noexcept { _mm256_storeu_ps(p, v); }
#else
using VD = float64x2_t;
using VF = float32x4_t;
constexpr int WD = 2, WF = 4;
KAIRN_GEN_FORCEINLINE VD load(const double* p) noexcept { return vld1q_f64(p); }
KAIRN_GEN_FORCEINLINE void store(double* p, VD v) noexcept { vst1q_f64(p, v); }
KAIRN_GEN_FORCEINLINE VF load(const float* p) noexcept { return vld1q_f32(p); }
KAIRN_GEN_FORCEINLINE void store(float* p, VF v) noexcept { vst1q_f32(p, v); }
#endif

template <class T>
struct Lanes;
template <>
struct Lanes<double> {
    using V = VD;
    static constexpr int W = WD;
};
template <>
struct Lanes<float> {
    using V = VF;
    static constexpr int W = WF;
};

}  // namespace

// X(B, SUF, T, KERNEL)
#define KB_UPP_LIST(X)                                                                             \
    X("upwa", upwa, double, interval_sub_1)                                                        \
    X("upwaf", upwaf, float, interval_add_1)                                                       \
    X("upwaf", upwaf, float, interval_sub_1)                                                       \
    X("upwaf", upwaf, float, interval_mul_1)

#define KB_UPP_DEF(B, SUF, T, KERNEL)                                                              \
    extern "C" KB_NOINLINE void kb_##SUF##_tp_##KERNEL##__packed(void* kb_data) {                  \
        Raw<T>& r = *static_cast<Raw<T>*>(kb_data);                                                \
        using V = Lanes<T>::V;                                                                     \
        for (int i = 0; i < kN; i += Lanes<T>::W) {                                                \
            V zl, zu;                                                                              \
            kg::KERNEL(load(&r.sxi[0][i]), load(&r.sxi[1][i]), load(&r.syi[0][i]), load(&r.syi[1][i]), zl, zu); \
            store(&r.sout[0][i], zl);                                                              \
            store(&r.sout[1][i], zu);                                                              \
        }                                                                                          \
    }
#define KB_UPP_ROW(B, SUF, T, KERNEL)                                                              \
    {B "/tp/" #KERNEL "/packed", kb_##SUF##_tp_##KERNEL##__packed, int(8 * sizeof(T)), Lanes<T>::W, kN, 0, 0, \
     kairn_bench::up::check_raw_sout},

KB_UPP_LIST(KB_UPP_DEF)

namespace {
const Entry table[] = {
    KB_UPP_LIST(KB_UPP_ROW)
    {nullptr, nullptr, 0, 0, 0, 0, 0, nullptr},
};
kairn_bench::m2::TableLink link{table, nullptr};
[[maybe_unused]] const bool registered =
    (link.next = kairn_bench::m2::m2_extra_tables, kairn_bench::m2::m2_extra_tables = &link, true);
}  // namespace

#endif
