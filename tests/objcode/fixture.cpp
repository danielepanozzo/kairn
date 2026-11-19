// The negative control of the object-code check (objcode.py --controls; docs/developer/testing.md,
// "Object code"): the textbook a * b + c that rule R1 keeps out of every kernel, which GCC fuses
// into one FMA by default and Clang under -ffp-contract=fast (the Phase 0 contraction experiment).
// Each function computes it once, from in[0], in[1] and in[2] into out[0]: as two statements, which
// only a compiler that contracts across statements fuses, and as one expression, which Clang also
// fuses under its default -ffp-contract=on; for double and float, and with the packed backend's
// intrinsics when KAIRN_OBJCODE_PACKED is defined. Its source is one product and one sum, and
// objcode.py judges the object code of each function against that.
//
// The program calls each function on operands whose product is not a number of the format, so
// that RN(a b + c) and RN(RN(a b) + c) differ, and prints for each "NAME fused" or "NAME unfused":
// what the compiler did, seen without looking at its code. objcode.py requires the check to fail
// exactly on the functions that print "fused".
#include <cstdio>

#if defined(KAIRN_OBJCODE_PACKED)
#if defined(__AVX2__)
#include <immintrin.h>
#elif defined(__aarch64__) || defined(_M_ARM64)
#include <arm_neon.h>
#endif
#endif

#if defined(_MSC_VER) && !defined(__clang__)
#define KAIRN_OBJCODE_NOINLINE __declspec(noinline)
#else
#define KAIRN_OBJCODE_NOINLINE __attribute__((noinline))
#endif

#define KAIRN_OBJCODE_SCALAR(T)                                                                         \
    extern "C" KAIRN_OBJCODE_NOINLINE void kairn_objcode_fixture_scalar_##T##_statements(const T* in, \
                                                                                        T* out) {   \
        const T p = in[0] * in[1];                                                                 \
        out[0] = p + in[2];                                                                        \
    }                                                                                              \
    extern "C" KAIRN_OBJCODE_NOINLINE void kairn_objcode_fixture_scalar_##T##_expression(const T* in, \
                                                                                        T* out) {   \
        out[0] = in[0] * in[1] + in[2];                                                            \
    }
KAIRN_OBJCODE_SCALAR(double)
KAIRN_OBJCODE_SCALAR(float)

#if defined(KAIRN_OBJCODE_PACKED) && defined(__AVX2__)
#define KAIRN_OBJCODE_PACKED_FIXTURE(T, V, MUL, ADD)                                                    \
    extern "C" KAIRN_OBJCODE_NOINLINE void kairn_objcode_fixture_packed_##T##_statements(const V* in, \
                                                                                        V* out) {   \
        const V p = MUL(in[0], in[1]);                                                             \
        out[0] = ADD(p, in[2]);                                                                    \
    }
KAIRN_OBJCODE_PACKED_FIXTURE(double, __m256d, _mm256_mul_pd, _mm256_add_pd)
KAIRN_OBJCODE_PACKED_FIXTURE(float, __m256, _mm256_mul_ps, _mm256_add_ps)
#define KAIRN_OBJCODE_PACKED_D __m256d
#define KAIRN_OBJCODE_PACKED_F __m256
#define KAIRN_OBJCODE_SET_D(x) _mm256_set1_pd(x)
#define KAIRN_OBJCODE_SET_F(x) _mm256_set1_ps(x)
#define KAIRN_OBJCODE_LANE_D(v) _mm256_cvtsd_f64(v)
#define KAIRN_OBJCODE_LANE_F(v) _mm256_cvtss_f32(v)
#elif defined(KAIRN_OBJCODE_PACKED) && (defined(__aarch64__) || defined(_M_ARM64))
#define KAIRN_OBJCODE_PACKED_FIXTURE(T, V, MUL, ADD)                                                    \
    extern "C" KAIRN_OBJCODE_NOINLINE void kairn_objcode_fixture_packed_##T##_statements(const V* in, \
                                                                                        V* out) {   \
        const V p = MUL(in[0], in[1]);                                                             \
        out[0] = ADD(p, in[2]);                                                                    \
    }
KAIRN_OBJCODE_PACKED_FIXTURE(double, float64x2_t, vmulq_f64, vaddq_f64)
KAIRN_OBJCODE_PACKED_FIXTURE(float, float32x4_t, vmulq_f32, vaddq_f32)
#define KAIRN_OBJCODE_PACKED_D float64x2_t
#define KAIRN_OBJCODE_PACKED_F float32x4_t
#define KAIRN_OBJCODE_SET_D(x) vdupq_n_f64(x)
#define KAIRN_OBJCODE_SET_F(x) vdupq_n_f32(x)
#define KAIRN_OBJCODE_LANE_D(v) vgetq_lane_f64(v, 0)
#define KAIRN_OBJCODE_LANE_F(v) vgetq_lane_f32(v, 0)
#endif

namespace {

// (1 + 2^-27)(1 - 2^-27) - 1 is -2^-54 with one rounding and 0 with two: the product 1 - 2^-54
// rounds to 1. In float, (1 + 2^-13)(1 - 2^-13) - 1 is -2^-26, or 0.
// The operands are read through volatile objects, so that nothing is computed at compile time.
volatile double dops[3] = {1 + 0x1p-27, 1 - 0x1p-27, -1.0};
volatile float fops[3] = {1 + 0x1p-13f, 1 - 0x1p-13f, -1.0f};

const char* verdict(double r, double fused) {
    return r == fused ? "fused" : r == 0 ? "unfused" : "neither";
}

}  // namespace

int main() {
    const double d[3] = {dops[0], dops[1], dops[2]};
    const float f[3] = {fops[0], fops[1], fops[2]};
    double rd = 1;
    float rf = 1;
    kairn_objcode_fixture_scalar_double_statements(d, &rd);
    std::printf("kairn_objcode_fixture_scalar_double_statements %s\n", verdict(rd, -0x1p-54));
    kairn_objcode_fixture_scalar_double_expression(d, &rd);
    std::printf("kairn_objcode_fixture_scalar_double_expression %s\n", verdict(rd, -0x1p-54));
    kairn_objcode_fixture_scalar_float_statements(f, &rf);
    std::printf("kairn_objcode_fixture_scalar_float_statements %s\n", verdict(rf, -0x1p-26));
    kairn_objcode_fixture_scalar_float_expression(f, &rf);
    std::printf("kairn_objcode_fixture_scalar_float_expression %s\n", verdict(rf, -0x1p-26));
#if defined(KAIRN_OBJCODE_PACKED_D)
    const KAIRN_OBJCODE_PACKED_D vd[3] = {KAIRN_OBJCODE_SET_D(d[0]), KAIRN_OBJCODE_SET_D(d[1]),
                                          KAIRN_OBJCODE_SET_D(d[2])};
    const KAIRN_OBJCODE_PACKED_F vf[3] = {KAIRN_OBJCODE_SET_F(f[0]), KAIRN_OBJCODE_SET_F(f[1]),
                                          KAIRN_OBJCODE_SET_F(f[2])};
    KAIRN_OBJCODE_PACKED_D od = KAIRN_OBJCODE_SET_D(1);
    KAIRN_OBJCODE_PACKED_F of = KAIRN_OBJCODE_SET_F(1);
    kairn_objcode_fixture_packed_double_statements(vd, &od);
    std::printf("kairn_objcode_fixture_packed_double_statements %s\n", verdict(KAIRN_OBJCODE_LANE_D(od), -0x1p-54));
    kairn_objcode_fixture_packed_float_statements(vf, &of);
    std::printf("kairn_objcode_fixture_packed_float_statements %s\n", verdict(KAIRN_OBJCODE_LANE_F(of), -0x1p-26));
#endif
    return 0;
}
