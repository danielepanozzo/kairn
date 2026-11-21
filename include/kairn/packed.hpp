/// @file
/// Packed<T, k>: W numbers of k limbs of type T (float or double) held in registers, limb j of all
/// W numbers in one register, and their operations; PackedMask<T>, the W truth values that a
/// comparison of packed numbers returns (docs/developer/design/milestone2.md, "Packed type and
/// containers").
///
/// Packed has no arithmetic of its own. Each operation calls the packed form of the generated
/// kernel that the operation of the same name of Expansion calls (include/kairn/gen/avx2.hpp or
/// gen/neon.hpp), or, where the target has neither, that scalar kernel itself, with W = 1
/// (gen/scalar.hpp). The generator emits every packed kernel from the description of the scalar
/// one and its tests compare the two lane by lane, bit for bit; so the statement of each operation
/// is that of the operation of Expansion in each lane: lane i of x + y is the number that
/// Expansion's x + y gives for lane i of x and lane i of y, with that operation's bound, its
/// results for infinities and NaN, and its requirement of canonical operands. Nothing is stated
/// across lanes: W operations are done side by side, never combined.
///
/// Which form is compiled is decided once per translation unit by KAIRN_PACKED_FORM (below): AVX2
/// with FMA (W = 4 for double, 8 for float), Advanced SIMD of AArch64 (W = 2, 4), or the scalar
/// form (W = 1). A loop written with Packed<T, k> and Packed<T, k>::lanes compiles unchanged in
/// the three. There is no dispatch at run time: the code is that of the instruction set the
/// translation unit is compiled for.
///
/// One limb: Packed<T, 1> is the packed T, the limb operand of the mixed forms of two limbs
/// (x + a, a - x, x < a), and it has negation, abs, the comparisons and the conversions to one
/// limb, which are, as for Expansion<T, 1>, the exact IEEE 754 operations of T, computed with the
/// instructions the generated kernels use for them (a sign bit flipped or cleared, a comparison of
/// lanes). It has no arithmetic: the kernels the arithmetic of Expansion<T, 1> names, add_1_1 and
/// mul_1_1, are not entry kernels, the only ones a public header may call (rule R3, which
/// gen/tests/test_rules.py checks), and Expansion<T, 1> computes the operations of T itself, which
/// Packed does not do: none of its operations rounds but through a kernel.
///
/// Not here: the arithmetic of one limb (above), sign, isfinite and is_normalized (no kernel computes them; is_normalized of two limbs
/// rounds), the operands marked kairn::unverified (every kernel these operations call is proved
/// today; an operation whose kernel is not proved does not compile, and has no marked form), the
/// building blocks of blocks.hpp, Ball and Interval, a reduction across lanes (a program writes it
/// with lane() and the operators of Expansion, in the order it chooses), and constant evaluation.
#pragma once

#include "expansion.hpp"

/// The value of KAIRN_PACKED_FORM for the scalar form: one lane, the kernels of gen/scalar.hpp.
#define KAIRN_PACKED_FORM_SCALAR 2
/// The value of KAIRN_PACKED_FORM for AVX2 with FMA: 4 lanes of double, 8 of float.
#define KAIRN_PACKED_FORM_AVX2 4
/// The value of KAIRN_PACKED_FORM for the Advanced SIMD of AArch64: 2 lanes of double, 4 of float.
#define KAIRN_PACKED_FORM_NEON 8

/// @def KAIRN_PACKED_FORM
/// Which form of Packed this translation unit compiles: KAIRN_PACKED_FORM_AVX2 where the
/// compiler targets AVX2 and FMA (__AVX2__ and __FMA__ defined; for MSVC, which defines no macro
/// for FMA, /arch:AVX2 or later), otherwise KAIRN_PACKED_FORM_NEON on AArch64, otherwise
/// KAIRN_PACKED_FORM_SCALAR. These are the conditions of the generated headers gen/avx2.hpp and
/// gen/neon.hpp. A program may define it before including Kairn: to KAIRN_PACKED_FORM_SCALAR, to
/// get one lane anywhere; to one of the other two only where the target has it, since otherwise
/// the generated header does not compile (its #error says what is missing). Any other value does
/// not compile.
///
/// Each form is in an inline namespace of its own (kairn::packed_avx2, kairn::packed_neon,
/// kairn::packed_scalar), so that translation units compiled for different instruction sets, each
/// with its own Packed, can be linked into one program; a Packed of one form is not a Packed of
/// another. Note that kairn::fma (cmake/kairn_fma.cmake) adds -mfma, not -mavx2: on x86-64 the
/// AVX2 form needs -mavx2 -mfma, -march=x86-64-v3 or later, or /arch:AVX2.
#if !defined(KAIRN_PACKED_FORM)
#if (defined(_MSC_VER) && !defined(__clang__) && defined(__AVX2__)) || (defined(__AVX2__) && defined(__FMA__))
#define KAIRN_PACKED_FORM KAIRN_PACKED_FORM_AVX2
#elif defined(__aarch64__) || defined(_M_ARM64)
#define KAIRN_PACKED_FORM KAIRN_PACKED_FORM_NEON
#else
#define KAIRN_PACKED_FORM KAIRN_PACKED_FORM_SCALAR
#endif
#endif
// (X + 0) is 0 for a value that is empty or a name the preprocessor does not know, and no value is
// 0 or 1, so that a bare -DKAIRN_PACKED_FORM is refused too (as KAIRN_ENCLOSURE_CODE, config.hpp).
#if (KAIRN_PACKED_FORM + 0) != KAIRN_PACKED_FORM_SCALAR && (KAIRN_PACKED_FORM + 0) != KAIRN_PACKED_FORM_AVX2 && \
    (KAIRN_PACKED_FORM + 0) != KAIRN_PACKED_FORM_NEON
#error "KAIRN_PACKED_FORM must be KAIRN_PACKED_FORM_SCALAR, KAIRN_PACKED_FORM_AVX2 or KAIRN_PACKED_FORM_NEON"
#endif

#if KAIRN_PACKED_FORM == KAIRN_PACKED_FORM_AVX2
#include "gen/avx2.hpp"
#define KAIRN_DETAIL_PACKED_BEGIN inline namespace packed_avx2 {
#elif KAIRN_PACKED_FORM == KAIRN_PACKED_FORM_NEON
#include "gen/neon.hpp"
#define KAIRN_DETAIL_PACKED_BEGIN inline namespace packed_neon {
#else
#define KAIRN_DETAIL_PACKED_BEGIN inline namespace packed_scalar {
#endif
#define KAIRN_DETAIL_PACKED_END }

#include <cstdint>

KAIRN_GEN_PUSH_WARNINGS
namespace kairn {
KAIRN_DETAIL_PACKED_BEGIN

template <class T, int K>
struct Packed;

namespace packed_detail {

// The registers of one limb type, and the operations on them that are not kernels: moves, loads,
// stores, selects, and the exact operations of one limb, each written with the instructions the
// generated kernels use for the same purpose. reg is the register of W limbs, mask a lane mask:
// every bit of a lane set, or every bit clear.
template <class T>
struct ops;

#if KAIRN_PACKED_FORM == KAIRN_PACKED_FORM_AVX2
template <>
struct ops<double> {
    using reg = __m256d;
    using mask = __m256d;
    static constexpr int lanes = 4;
    static KAIRN_FORCEINLINE reg zero() noexcept { return _mm256_setzero_pd(); }
    static KAIRN_FORCEINLINE reg broadcast(double a) noexcept { return _mm256_set1_pd(a); }
    static KAIRN_FORCEINLINE reg load(const double* p) noexcept { return _mm256_loadu_pd(p); }
    static KAIRN_FORCEINLINE void store(double* p, reg a) noexcept { _mm256_storeu_pd(p, a); }
    // Lane m set: a's lane, otherwise b's.
    static KAIRN_FORCEINLINE reg select(mask m, reg a, reg b) noexcept { return _mm256_blendv_pd(b, a, m); }
    static KAIRN_FORCEINLINE reg neg(reg a) noexcept { return _mm256_xor_pd(a, _mm256_set1_pd(-0.0)); }
    static KAIRN_FORCEINLINE reg abs(reg a) noexcept { return _mm256_andnot_pd(_mm256_set1_pd(-0.0), a); }
    static KAIRN_FORCEINLINE mask lt(reg a, reg b) noexcept { return _mm256_cmp_pd(a, b, _CMP_LT_OQ); }
    static KAIRN_FORCEINLINE mask le(reg a, reg b) noexcept { return _mm256_cmp_pd(a, b, _CMP_LE_OQ); }
    static KAIRN_FORCEINLINE mask eq(reg a, reg b) noexcept { return _mm256_cmp_pd(a, b, _CMP_EQ_OQ); }
    static KAIRN_FORCEINLINE mask none() noexcept { return _mm256_setzero_pd(); }
    static KAIRN_FORCEINLINE mask both(mask a, mask b) noexcept { return _mm256_and_pd(a, b); }
    static KAIRN_FORCEINLINE mask either(mask a, mask b) noexcept { return _mm256_or_pd(a, b); }
    static KAIRN_FORCEINLINE mask complement(mask a) noexcept { return gen::not_mask(a); }
    static KAIRN_FORCEINLINE bool all(mask a) noexcept { return _mm256_movemask_pd(a) == 0xf; }
    static KAIRN_FORCEINLINE bool any(mask a) noexcept { return _mm256_movemask_pd(a) != 0; }
    static KAIRN_FORCEINLINE bool lane(mask a, int i) noexcept { return ((_mm256_movemask_pd(a) >> i) & 1) != 0; }
};
template <>
struct ops<float> {
    using reg = __m256;
    using mask = __m256;
    static constexpr int lanes = 8;
    static KAIRN_FORCEINLINE reg zero() noexcept { return _mm256_setzero_ps(); }
    static KAIRN_FORCEINLINE reg broadcast(float a) noexcept { return _mm256_set1_ps(a); }
    static KAIRN_FORCEINLINE reg load(const float* p) noexcept { return _mm256_loadu_ps(p); }
    static KAIRN_FORCEINLINE void store(float* p, reg a) noexcept { _mm256_storeu_ps(p, a); }
    static KAIRN_FORCEINLINE reg select(mask m, reg a, reg b) noexcept { return _mm256_blendv_ps(b, a, m); }
    static KAIRN_FORCEINLINE reg neg(reg a) noexcept { return _mm256_xor_ps(a, _mm256_set1_ps(-0.0f)); }
    static KAIRN_FORCEINLINE reg abs(reg a) noexcept { return _mm256_andnot_ps(_mm256_set1_ps(-0.0f), a); }
    static KAIRN_FORCEINLINE mask lt(reg a, reg b) noexcept { return _mm256_cmp_ps(a, b, _CMP_LT_OQ); }
    static KAIRN_FORCEINLINE mask le(reg a, reg b) noexcept { return _mm256_cmp_ps(a, b, _CMP_LE_OQ); }
    static KAIRN_FORCEINLINE mask eq(reg a, reg b) noexcept { return _mm256_cmp_ps(a, b, _CMP_EQ_OQ); }
    static KAIRN_FORCEINLINE mask none() noexcept { return _mm256_setzero_ps(); }
    static KAIRN_FORCEINLINE mask both(mask a, mask b) noexcept { return _mm256_and_ps(a, b); }
    static KAIRN_FORCEINLINE mask either(mask a, mask b) noexcept { return _mm256_or_ps(a, b); }
    static KAIRN_FORCEINLINE mask complement(mask a) noexcept { return gen::not_mask(a); }
    static KAIRN_FORCEINLINE bool all(mask a) noexcept { return _mm256_movemask_ps(a) == 0xff; }
    static KAIRN_FORCEINLINE bool any(mask a) noexcept { return _mm256_movemask_ps(a) != 0; }
    static KAIRN_FORCEINLINE bool lane(mask a, int i) noexcept { return ((_mm256_movemask_ps(a) >> i) & 1) != 0; }
};
#elif KAIRN_PACKED_FORM == KAIRN_PACKED_FORM_NEON
template <>
struct ops<double> {
    using reg = float64x2_t;
    using mask = uint64x2_t;
    static constexpr int lanes = 2;
    static KAIRN_FORCEINLINE reg zero() noexcept { return vdupq_n_f64(0.0); }
    static KAIRN_FORCEINLINE reg broadcast(double a) noexcept { return vdupq_n_f64(a); }
    static KAIRN_FORCEINLINE reg load(const double* p) noexcept { return vld1q_f64(p); }
    static KAIRN_FORCEINLINE void store(double* p, reg a) noexcept { vst1q_f64(p, a); }
    static KAIRN_FORCEINLINE reg select(mask m, reg a, reg b) noexcept { return vbslq_f64(m, a, b); }
    static KAIRN_FORCEINLINE reg neg(reg a) noexcept { return vnegq_f64(a); }
    static KAIRN_FORCEINLINE reg abs(reg a) noexcept { return vabsq_f64(a); }
    static KAIRN_FORCEINLINE mask lt(reg a, reg b) noexcept { return vcltq_f64(a, b); }
    static KAIRN_FORCEINLINE mask le(reg a, reg b) noexcept { return vcleq_f64(a, b); }
    static KAIRN_FORCEINLINE mask eq(reg a, reg b) noexcept { return vceqq_f64(a, b); }
    static KAIRN_FORCEINLINE mask none() noexcept { return vdupq_n_u64(0); }
    static KAIRN_FORCEINLINE mask both(mask a, mask b) noexcept { return vandq_u64(a, b); }
    static KAIRN_FORCEINLINE mask either(mask a, mask b) noexcept { return vorrq_u64(a, b); }
    static KAIRN_FORCEINLINE mask complement(mask a) noexcept { return gen::not_mask(a); }
    // The smallest 32-bit word of the mask: all ones exactly when every lane is set; and of its
    // complement, all ones exactly when no lane is.
    static KAIRN_FORCEINLINE bool all(mask a) noexcept { return vminvq_u32(vreinterpretq_u32_u64(a)) != 0; }
    static KAIRN_FORCEINLINE bool any(mask a) noexcept {
        return vminvq_u32(vmvnq_u32(vreinterpretq_u32_u64(a))) == 0;
    }
    static KAIRN_FORCEINLINE bool lane(mask a, int i) noexcept {
        std::uint64_t t[2];
        vst1q_u64(t, a);
        return t[i] != 0;
    }
};
template <>
struct ops<float> {
    using reg = float32x4_t;
    using mask = uint32x4_t;
    static constexpr int lanes = 4;
    static KAIRN_FORCEINLINE reg zero() noexcept { return vdupq_n_f32(0.0f); }
    static KAIRN_FORCEINLINE reg broadcast(float a) noexcept { return vdupq_n_f32(a); }
    static KAIRN_FORCEINLINE reg load(const float* p) noexcept { return vld1q_f32(p); }
    static KAIRN_FORCEINLINE void store(float* p, reg a) noexcept { vst1q_f32(p, a); }
    static KAIRN_FORCEINLINE reg select(mask m, reg a, reg b) noexcept { return vbslq_f32(m, a, b); }
    static KAIRN_FORCEINLINE reg neg(reg a) noexcept { return vnegq_f32(a); }
    static KAIRN_FORCEINLINE reg abs(reg a) noexcept { return vabsq_f32(a); }
    static KAIRN_FORCEINLINE mask lt(reg a, reg b) noexcept { return vcltq_f32(a, b); }
    static KAIRN_FORCEINLINE mask le(reg a, reg b) noexcept { return vcleq_f32(a, b); }
    static KAIRN_FORCEINLINE mask eq(reg a, reg b) noexcept { return vceqq_f32(a, b); }
    static KAIRN_FORCEINLINE mask none() noexcept { return vdupq_n_u32(0); }
    static KAIRN_FORCEINLINE mask both(mask a, mask b) noexcept { return vandq_u32(a, b); }
    static KAIRN_FORCEINLINE mask either(mask a, mask b) noexcept { return vorrq_u32(a, b); }
    static KAIRN_FORCEINLINE mask complement(mask a) noexcept { return gen::not_mask(a); }
    static KAIRN_FORCEINLINE bool all(mask a) noexcept { return vminvq_u32(a) != 0; }
    static KAIRN_FORCEINLINE bool any(mask a) noexcept { return vminvq_u32(vmvnq_u32(a)) == 0; }
    static KAIRN_FORCEINLINE bool lane(mask a, int i) noexcept {
        std::uint32_t t[4];
        vst1q_u32(t, a);
        return t[i] != 0;
    }
};
#else
// One lane: the register is a limb, the mask a bool, and the exact operations those of
// Expansion<T, 1> (expansion.hpp), written the same way.
template <class T>
struct ops {
    using reg = T;
    using mask = bool;
    static constexpr int lanes = 1;
    static KAIRN_FORCEINLINE reg zero() noexcept { return T(0); }
    static KAIRN_FORCEINLINE reg broadcast(T a) noexcept { return a; }
    static KAIRN_FORCEINLINE reg load(const T* p) noexcept { return *p; }
    static KAIRN_FORCEINLINE void store(T* p, reg a) noexcept { *p = a; }
    static KAIRN_FORCEINLINE reg select(mask m, reg a, reg b) noexcept { return m ? a : b; }
    static KAIRN_FORCEINLINE reg neg(reg a) noexcept { return -a; }
    static KAIRN_FORCEINLINE reg abs(reg a) noexcept { return gen::abs_bits(a); }
    // b > a and b >= a, as Expansion<T, 1> writes them (expansion.hpp, canonical()).
    static KAIRN_FORCEINLINE mask lt(reg a, reg b) noexcept { return b > a; }
    static KAIRN_FORCEINLINE mask le(reg a, reg b) noexcept { return b >= a; }
    static KAIRN_FORCEINLINE mask eq(reg a, reg b) noexcept { return a == b; }
    static KAIRN_FORCEINLINE mask none() noexcept { return false; }
    static KAIRN_FORCEINLINE mask both(mask a, mask b) noexcept { return a && b; }
    static KAIRN_FORCEINLINE mask either(mask a, mask b) noexcept { return a || b; }
    static KAIRN_FORCEINLINE mask complement(mask a) noexcept { return !a; }
    static KAIRN_FORCEINLINE bool all(mask a) noexcept { return a; }
    static KAIRN_FORCEINLINE bool any(mask a) noexcept { return a; }
    static KAIRN_FORCEINLINE bool lane(mask a, int) noexcept { return a; }
};
#endif

// Lane i of a register, read and written through memory.
template <class T>
KAIRN_FORCEINLINE T get(const typename ops<T>::reg& a, int i) noexcept {
    T t[ops<T>::lanes];
    ops<T>::store(t, a);
    return t[i];
}
template <class T>
KAIRN_FORCEINLINE void set(typename ops<T>::reg& a, int i, T v) noexcept {
    T t[ops<T>::lanes];
    ops<T>::store(t, a);
    t[i] = v;
    a = ops<T>::load(t);
}

// The checks of KAIRN_CHECKS (config.hpp) for packed operands: those of expansion.hpp, detail::check,
// check_core and check_exact, with the environment checked once and then every lane of every
// operand, and the same messages.
template <class T, int K>
KAIRN_FORCEINLINE bool admissible(const Packed<T, K>& p) noexcept {
    for (int i = 0; i < Packed<T, K>::lanes; ++i)
        if (!kairn::detail::admissible(p.lane(i))) return false;
    return true;
}
template <class T, int K>
KAIRN_FORCEINLINE bool core_admissible(const Packed<T, K>& p) noexcept {
    if constexpr (K == 2) {
        for (int i = 0; i < Packed<T, K>::lanes; ++i)
            if (!kairn::detail::core_admissible(p.lane(i))) return false;
    }
    return true;
}
template <class... P>
KAIRN_FORCEINLINE void check([[maybe_unused]] const P&... p) noexcept {
#if KAIRN_CHECKS
    if (kairn::detail::check_environment() && !(packed_detail::admissible(p) && ...))
        kairn::detail::fail("an operand", "is not canonical (finite with x0 + x1 == x0, (+-inf, 0) or (NaN, NaN)), so "
                                          "no guarantee applies to the result");
#endif
}
template <class... P>
KAIRN_FORCEINLINE void check_core([[maybe_unused]] const P&... p) noexcept {
#if KAIRN_CHECKS
    if (kairn::detail::check_environment() && !(packed_detail::core_admissible(p) && ...))
        kairn::detail::fail("an operand", "is not normalized (x0 + x1 is not x0), so no guarantee applies to the result");
#endif
}
template <class... P>
KAIRN_FORCEINLINE void check_exact([[maybe_unused]] const P&... p) noexcept {
#if KAIRN_CHECKS
    if (kairn::detail::check_environment_except_rounding() && kairn::detail::rounding_to_nearest() &&
        !(packed_detail::admissible(p) && ...))
        kairn::detail::fail("an operand", "is not canonical (finite with x0 + x1 == x0, (+-inf, 0) or (NaN, NaN)), so "
                                          "no guarantee applies to the result");
#endif
}
// The check of Expansion<T, 2>::from_limbs on every lane of x0 and x1.
template <class T>
KAIRN_FORCEINLINE void check_limbs([[maybe_unused]] const typename ops<T>::reg& x0,
                                   [[maybe_unused]] const typename ops<T>::reg& x1) noexcept {
#if KAIRN_CHECKS
    if (kairn::detail::check_environment()) {
        for (int i = 0; i < ops<T>::lanes; ++i) {
            Expansion<T, 2> x;
            x.limb[0] = packed_detail::get<T>(x0, i);
            x.limb[1] = packed_detail::get<T>(x1, i);
            if (!kairn::detail::canonical(x))
                kairn::detail::fail("from_limbs", "the limbs are not a canonical pair (finite with x0 + x1 == x0, an "
                                                  "infinity and a zero, or two NaN)");
        }
    }
#endif
}

}  // namespace packed_detail

/// W truth values, one per lane: what a comparison of packed numbers returns, and what select()
/// chooses with. Lane i is the comparison of lane i of the operands, as Expansion's comparison
/// gives it (false with a NaN for <, <=, >, >=, ==; true for !=).
///
/// Trivially copyable; default-constructs to every lane false.
template <class T>
struct PackedMask {
    static_assert(kairn::detail::limb<T>, "PackedMask<T>: the limb type T is float or double");
    /// The register: for AVX2 __m256d or __m256, for AArch64 uint64x2_t or uint32x4_t, for one lane
    /// bool.
    using register_type = typename packed_detail::ops<T>::mask;
    /// W, as for Packed<T, k>.
    static constexpr int lanes = packed_detail::ops<T>::lanes;

    /// The lanes: each lane has every bit set (true) or every bit clear (false). A value written
    /// here must keep that form; any other gives any() and all() and select() no meaning.
    register_type bits;

    /// Every lane false.
    KAIRN_FORCEINLINE PackedMask() noexcept : bits(packed_detail::ops<T>::none()) {}
    /// The mask in a register (of the form above).
    KAIRN_FORCEINLINE explicit PackedMask(register_type m) noexcept : bits(m) {}

    /// Lane i, for i from 0 to lanes - 1.
    KAIRN_FORCEINLINE bool lane(int i) const noexcept { return packed_detail::ops<T>::lane(bits, i); }
};

/// W numbers of K limbs of type T (float or double), K = 1 or 2: limb j of the W numbers in the
/// register limb[j], lane i of each register being number i. Each lane is a k-number of
/// expansion.hpp, and must be canonical where Expansion requires it.
///
/// Trivially copyable and standard-layout; default-constructs to zero in every lane; holds no heap
/// memory and has no state outside its registers. Every function is noexcept and forced inline,
/// and none is usable in constant evaluation.
///
/// Checks: with KAIRN_CHECKS 1 (config.hpp), every operation checks the environment once and then
/// every lane of every operand, exactly as the operation of Expansion of the same name checks its
/// one operand, with the same messages; load and from_limbs check every lane as
/// Expansion::from_limbs does.
template <class T, int K>
struct Packed {
    static_assert(kairn::detail::limb<T>, "Packed<T, k>: the limb type T is float or double");
    static_assert(K == 1 || K == 2, "Packed<T, k>: k is 1 or 2");

    /// T.
    using limb_type = T;
    /// The number of one lane, Expansion<T, K>.
    using value_type = Expansion<T, K>;
    /// The register of W limbs: for AVX2 __m256d or __m256, for AArch64 float64x2_t or
    /// float32x4_t, for one lane T itself.
    using register_type = typename packed_detail::ops<T>::reg;
    /// What the comparisons return.
    using mask_type = PackedMask<T>;
    /// K.
    static constexpr int limbs = K;
    /// W, the numbers in one Packed: 4 for double and 8 for float with AVX2, 2 and 4 on AArch64,
    /// 1 in the scalar form (KAIRN_PACKED_FORM).
    static constexpr int lanes = packed_detail::ops<T>::lanes;

    /// The registers, most significant limb first. Written directly, as Expansion's limbs may be,
    /// each lane must form a canonical number and no limb may be a product the compiler can see
    /// being computed (expansion.hpp says why); load() and from_limbs() guard what they are given.
    register_type limb[K];

    /// Zero in every lane.
    KAIRN_FORCEINLINE Packed() noexcept {
        for (register_type& r : limb) r = packed_detail::ops<T>::zero();
    }
    /// In each lane, the two-limb number of that lane of a, exactly (kernel make_2, as
    /// Expansion<T, 2>(a)). Implicit, as that constructor is; no check, as for it.
    template <int J>
        requires(K == 2 && J == 1 && kairn::detail::proof_checked<gen::bounds::make_2<T>>)
    KAIRN_FORCEINLINE Packed(const Packed<T, J>& a) noexcept {
        gen::make_2(a.limb[0], limb[0], limb[1]);
    }
    /// In each lane, the lane of x rounded to nearest (kernel to_nearest_2, as the explicit
    /// Expansion<T, 1>(x)). Does not round: not preceded by the debug build's check of the rounding
    /// mode (config.hpp).
    template <int J>
        requires(K == 1 && J == 2 && kairn::detail::proof_checked<gen::bounds::to_nearest_2<T>>)
    KAIRN_FORCEINLINE explicit Packed(const Packed<T, J>& x) noexcept {
        packed_detail::check_exact(x);
        gen::to_nearest_2(x.limb[0], x.limb[1], limb[0]);
    }

    /// x in every lane: its limbs, copied.
    KAIRN_FORCEINLINE static Packed broadcast(const Expansion<T, K>& x) noexcept {
        Packed p;
        for (int j = 0; j < K; ++j) p.limb[j] = packed_detail::ops<T>::broadcast(x.limb[j]);
        return p;
    }

    /// One limb: the numbers x0[0] .. x0[W - 1], copied, as Expansion<T, 1>::from_limbs does.
    /// x0 needs no alignment.
    KAIRN_FORCEINLINE static Packed load(const T* x0) noexcept
        requires(K == 1)
    {
        Packed p;
        p.limb[0] = packed_detail::ops<T>::load(x0);
        return p;
    }
    /// Two limbs: lane i is Expansion<T, 2>::from_limbs of x0[i] and x1[i], for i from 0 to W - 1
    /// (kernel make_2_limbs, each limb guarded: the limbs read, but a zero may change sign). Each
    /// pair must be canonical; checked when KAIRN_CHECKS is 1, after the environment, with the
    /// message of from_limbs, which then stops the program. x0 and x1 need no alignment.
    KAIRN_FORCEINLINE static Packed load(const T* x0, const T* x1) noexcept
        requires(K == 2 && kairn::detail::proof_checked<gen::bounds::make_2_limbs<T>>)
    {
        return from_limbs(packed_detail::ops<T>::load(x0), packed_detail::ops<T>::load(x1));
    }
    /// One limb: load(x0).
    KAIRN_FORCEINLINE static Packed load_unchecked(const T* x0) noexcept
        requires(K == 1)
    {
        return load(x0);
    }
    /// Two limbs: lane i is Expansion<T, 2>::from_limbs_unchecked of x0[i] and x1[i]: as load(),
    /// without the check.
    KAIRN_FORCEINLINE static Packed load_unchecked(const T* x0, const T* x1) noexcept
        requires(K == 2 && kairn::detail::proof_checked<gen::bounds::make_2_limbs<T>>)
    {
        return from_limbs_unchecked(packed_detail::ops<T>::load(x0), packed_detail::ops<T>::load(x1));
    }
    /// The tail of an array: lanes 0 to count - 1 as load(x0) reads them, reading only x0[0] to
    /// x0[count - 1], and fill in the other lanes. 0 <= count <= W.
    KAIRN_FORCEINLINE static Packed load_partial(const T* x0, int count, const Expansion<T, 1>& fill = {}) noexcept
        requires(K == 1)
    {
        T t[lanes];
        for (int i = 0; i < lanes; ++i) t[i] = i < count ? x0[i] : fill.limb[0];
        return load(t);
    }
    /// The tail of two arrays: lanes 0 to count - 1 as load(x0, x1) reads them, with its check,
    /// reading only the first count elements of each, and fill in the other lanes. 0 <= count <= W.
    KAIRN_FORCEINLINE static Packed load_partial(const T* x0, const T* x1, int count,
                                                 const Expansion<T, 2>& fill = {}) noexcept
        requires(K == 2 && kairn::detail::proof_checked<gen::bounds::make_2_limbs<T>>)
    {
        T t0[lanes], t1[lanes];
        for (int i = 0; i < lanes; ++i) {
            t0[i] = i < count ? x0[i] : fill.limb[0];
            t1[i] = i < count ? x1[i] : fill.limb[1];
        }
        return load(t0, t1);
    }

    /// One limb: the registers as they are (as Expansion<T, 1>::from_limbs).
    KAIRN_FORCEINLINE static Packed from_limbs(register_type x0) noexcept
        requires(K == 1)
    {
        Packed p;
        p.limb[0] = x0;
        return p;
    }
    /// Two limbs: lane i is Expansion<T, 2>::from_limbs of lane i of x0 and of x1 (kernel
    /// make_2_limbs), checked as load() checks.
    KAIRN_FORCEINLINE static Packed from_limbs(register_type x0, register_type x1) noexcept
        requires(K == 2 && kairn::detail::proof_checked<gen::bounds::make_2_limbs<T>>)
    {
        packed_detail::check_limbs<T>(x0, x1);
        return from_limbs_unchecked(x0, x1);
    }
    /// One limb: from_limbs(x0).
    KAIRN_FORCEINLINE static Packed from_limbs_unchecked(register_type x0) noexcept
        requires(K == 1)
    {
        return from_limbs(x0);
    }
    /// Two limbs: as from_limbs(x0, x1), without the check (Expansion<T, 2>::from_limbs_unchecked).
    KAIRN_FORCEINLINE static Packed from_limbs_unchecked(register_type x0, register_type x1) noexcept
        requires(K == 2 && kairn::detail::proof_checked<gen::bounds::make_2_limbs<T>>)
    {
        Packed p;
        gen::make_2_limbs(x0, x1, p.limb[0], p.limb[1]);
        return p;
    }

    /// One limb: writes lane i to x0[i], for i from 0 to W - 1: the limbs, copied. No alignment.
    KAIRN_FORCEINLINE void store(T* x0) const noexcept
        requires(K == 1)
    {
        packed_detail::ops<T>::store(x0, limb[0]);
    }
    /// Two limbs: writes the limbs of lane i to x0[i] and x1[i]: copied.
    KAIRN_FORCEINLINE void store(T* x0, T* x1) const noexcept
        requires(K == 2)
    {
        packed_detail::ops<T>::store(x0, limb[0]);
        packed_detail::ops<T>::store(x1, limb[1]);
    }
    /// The tail of an array: writes lanes 0 to count - 1 only, to x0[0] .. x0[count - 1].
    /// 0 <= count <= W.
    KAIRN_FORCEINLINE void store_partial(T* x0, int count) const noexcept
        requires(K == 1)
    {
        T t[lanes];
        packed_detail::ops<T>::store(t, limb[0]);
        for (int i = 0; i < count; ++i) x0[i] = t[i];
    }
    /// The tail of two arrays: writes lanes 0 to count - 1 only.
    KAIRN_FORCEINLINE void store_partial(T* x0, T* x1, int count) const noexcept
        requires(K == 2)
    {
        T t0[lanes], t1[lanes];
        packed_detail::ops<T>::store(t0, limb[0]);
        packed_detail::ops<T>::store(t1, limb[1]);
        for (int i = 0; i < count; ++i) {
            x0[i] = t0[i];
            x1[i] = t1[i];
        }
    }

    /// Lane i, for i from 0 to W - 1, as a number: its limbs, copied.
    KAIRN_FORCEINLINE Expansion<T, K> lane(int i) const noexcept {
        Expansion<T, K> x;
        for (int j = 0; j < K; ++j) x.limb[j] = packed_detail::get<T>(limb[j], i);
        return x;
    }
    /// Sets lane i to x: its limbs, copied; the other lanes are unchanged.
    KAIRN_FORCEINLINE void set_lane(int i, const Expansion<T, K>& x) noexcept {
        for (int j = 0; j < K; ++j) packed_detail::set<T>(limb[j], i, x.limb[j]);
    }
};

namespace packed_detail {

// x 2^n in steps, as detail::ldexp_steps of expansion.hpp does for one number: the same steps, each
// the packed form of the kernel it calls there, with the same power of two in every lane.
template <bool Full, class T>
KAIRN_FORCEINLINE Packed<T, 2> scale2(const Packed<T, 2>& x, T c) noexcept {
    Packed<T, 2> z;
    if constexpr (Full) {
        gen::mul_pow2_2_full(x.limb[0], x.limb[1], ops<T>::broadcast(c), z.limb[0], z.limb[1]);
    } else {
        gen::mul_pow2_2(x.limb[0], x.limb[1], ops<T>::broadcast(c), z.limb[0], z.limb[1]);
    }
    return z;
}
template <bool Full, class T>
KAIRN_FORCEINLINE Packed<T, 2> ldexp_steps(Packed<T, 2> x, int n) noexcept {
    constexpr int lo = kairn::detail::pow2_min<T>, hi = kairn::detail::pow2_max<T>;
    constexpr int up = hi + 1 - lo, down = lo - hi - 2;
    if (n > up) n = up;
    if (down > n) n = down;
    if (lo > n) {
        x = packed_detail::scale2<Full>(x, kairn::detail::pow2<T>(n - lo));
        n = lo;
    }
    while (n > hi) {
        x = packed_detail::scale2<Full>(x, kairn::detail::pow2<T>(hi));
        n -= hi;
    }
    return packed_detail::scale2<Full>(x, kairn::detail::pow2<T>(n));
}
}  // namespace packed_detail

KAIRN_DETAIL_PACKED_END

// The operations: function templates in kairn, found by argument-dependent lookup from the inline
// namespace of Packed. As the operators of two limbs of expansion.hpp, no operand converts: a
// one-limb operand matches only the form written for it, gated on the kernel it calls.

// --- Masks -------------------------------------------------------------------------------------

/// Whether every lane of m is true.
template <class T>
KAIRN_FORCEINLINE bool all(const PackedMask<T>& m) noexcept {
    return packed_detail::ops<T>::all(m.bits);
}
/// Whether some lane of m is true.
template <class T>
KAIRN_FORCEINLINE bool any(const PackedMask<T>& m) noexcept {
    return packed_detail::ops<T>::any(m.bits);
}
/// Lane by lane, a and b.
template <class T>
KAIRN_FORCEINLINE PackedMask<T> operator&(const PackedMask<T>& a, const PackedMask<T>& b) noexcept {
    return PackedMask<T>(packed_detail::ops<T>::both(a.bits, b.bits));
}
/// Lane by lane, a or b.
template <class T>
KAIRN_FORCEINLINE PackedMask<T> operator|(const PackedMask<T>& a, const PackedMask<T>& b) noexcept {
    return PackedMask<T>(packed_detail::ops<T>::either(a.bits, b.bits));
}
/// Lane by lane, not a.
template <class T>
KAIRN_FORCEINLINE PackedMask<T> operator!(const PackedMask<T>& a) noexcept {
    return PackedMask<T>(packed_detail::ops<T>::complement(a.bits));
}
/// In each lane, that of a where m is true and that of b where it is false: limbs moved, nothing
/// computed, so each lane is the number it was in a or b, bit for bit.
template <class T, int K>
KAIRN_FORCEINLINE Packed<T, K> select(const PackedMask<T>& m, const Packed<T, K>& a, const Packed<T, K>& b) noexcept {
    Packed<T, K> z;
    for (int j = 0; j < K; ++j) z.limb[j] = packed_detail::ops<T>::select(m.bits, a.limb[j], b.limb[j]);
    return z;
}

// --- One limb ----------------------------------------------------------------------------------

/// In each lane, -x exactly: the sign bit flipped.
/// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
template <class T>
KAIRN_FORCEINLINE Packed<T, 1> operator-(const Packed<T, 1>& x) noexcept {
    packed_detail::check_exact(x);
    Packed<T, 1> z;
    z.limb[0] = packed_detail::ops<T>::neg(x.limb[0]);
    return z;
}
/// In each lane, whether x < y: the comparison of T. False if either is NaN.
/// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
template <class T>
KAIRN_FORCEINLINE PackedMask<T> operator<(const Packed<T, 1>& x, const Packed<T, 1>& y) noexcept {
    packed_detail::check_exact(x, y);
    return PackedMask<T>(packed_detail::ops<T>::lt(x.limb[0], y.limb[0]));
}
/// In each lane, whether x > y. False if either is NaN.
/// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
template <class T>
KAIRN_FORCEINLINE PackedMask<T> operator>(const Packed<T, 1>& x, const Packed<T, 1>& y) noexcept {
    packed_detail::check_exact(x, y);
    return PackedMask<T>(packed_detail::ops<T>::lt(y.limb[0], x.limb[0]));
}
/// In each lane, whether x <= y. False if either is NaN.
/// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
template <class T>
KAIRN_FORCEINLINE PackedMask<T> operator<=(const Packed<T, 1>& x, const Packed<T, 1>& y) noexcept {
    packed_detail::check_exact(x, y);
    return PackedMask<T>(packed_detail::ops<T>::le(x.limb[0], y.limb[0]));
}
/// In each lane, whether x >= y. False if either is NaN.
/// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
template <class T>
KAIRN_FORCEINLINE PackedMask<T> operator>=(const Packed<T, 1>& x, const Packed<T, 1>& y) noexcept {
    packed_detail::check_exact(x, y);
    return PackedMask<T>(packed_detail::ops<T>::le(y.limb[0], x.limb[0]));
}
/// In each lane, whether x == y (+0 equals -0). False if either is NaN.
/// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
template <class T>
KAIRN_FORCEINLINE PackedMask<T> operator==(const Packed<T, 1>& x, const Packed<T, 1>& y) noexcept {
    packed_detail::check_exact(x, y);
    return PackedMask<T>(packed_detail::ops<T>::eq(x.limb[0], y.limb[0]));
}
/// In each lane, whether x != y. True if either is NaN.
/// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
template <class T>
KAIRN_FORCEINLINE PackedMask<T> operator!=(const Packed<T, 1>& x, const Packed<T, 1>& y) noexcept {
    packed_detail::check_exact(x, y);
    return PackedMask<T>(packed_detail::ops<T>::complement(packed_detail::ops<T>::eq(x.limb[0], y.limb[0])));
}
/// In each lane, |x| exactly: the sign bit cleared.
/// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
template <class T>
KAIRN_FORCEINLINE Packed<T, 1> abs(const Packed<T, 1>& x) noexcept {
    packed_detail::check_exact(x);
    Packed<T, 1> z;
    z.limb[0] = packed_detail::ops<T>::abs(x.limb[0]);
    return z;
}
/// x itself: in each lane, the one-limb number rounded to nearest is itself.
/// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
template <class T>
KAIRN_FORCEINLINE Packed<T, 1> to_nearest(const Packed<T, 1>& x) noexcept {
    packed_detail::check_exact(x);
    return x;
}
/// x itself.
/// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
template <class T>
KAIRN_FORCEINLINE Packed<T, 1> to_down(const Packed<T, 1>& x) noexcept {
    packed_detail::check_exact(x);
    return x;
}
/// x itself.
/// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
template <class T>
KAIRN_FORCEINLINE Packed<T, 1> to_up(const Packed<T, 1>& x) noexcept {
    packed_detail::check_exact(x);
    return x;
}
/// In each lane, |x| exactly.
/// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
template <class T>
KAIRN_FORCEINLINE Packed<T, 1> abs_upper(const Packed<T, 1>& x) noexcept {
    return kairn::abs(x);
}

// --- Two limbs: arithmetic, the full kernels -----------------------------------------------------

/// In each lane, x + y (kernel add_2_2_full): Expansion's x + y, IEEE-like.
template <class T>
    requires kairn::detail::proof_checked<gen::bounds::add_2_2_full<T>>
KAIRN_FORCEINLINE Packed<T, 2> operator+(const Packed<T, 2>& x, const Packed<T, 2>& y) noexcept {
    packed_detail::check(x, y);
    Packed<T, 2> w;
    gen::add_2_2_full(x.limb[0], x.limb[1], y.limb[0], y.limb[1], w.limb[0], w.limb[1]);
    return w;
}
/// In each lane, x + a with a of one limb (kernel add_2_1_full, which guards a).
template <class T>
    requires kairn::detail::proof_checked<gen::bounds::add_2_1_full<T>>
KAIRN_FORCEINLINE Packed<T, 2> operator+(const Packed<T, 2>& x, const Packed<T, 1>& a) noexcept {
    packed_detail::check(x, a);
    Packed<T, 2> w;
    gen::add_2_1_full(x.limb[0], x.limb[1], a.limb[0], w.limb[0], w.limb[1]);
    return w;
}
/// a + x: the same operation as x + a (kernel add_2_1_full).
template <class T>
    requires kairn::detail::proof_checked<gen::bounds::add_2_1_full<T>>
KAIRN_FORCEINLINE Packed<T, 2> operator+(const Packed<T, 1>& a, const Packed<T, 2>& x) noexcept {
    return x + a;
}
/// In each lane, x - y (kernel sub_2_2_full).
template <class T>
    requires kairn::detail::proof_checked<gen::bounds::sub_2_2_full<T>>
KAIRN_FORCEINLINE Packed<T, 2> operator-(const Packed<T, 2>& x, const Packed<T, 2>& y) noexcept {
    packed_detail::check(x, y);
    Packed<T, 2> w;
    gen::sub_2_2_full(x.limb[0], x.limb[1], y.limb[0], y.limb[1], w.limb[0], w.limb[1]);
    return w;
}
/// In each lane, x - a (kernel sub_2_1_full).
template <class T>
    requires kairn::detail::proof_checked<gen::bounds::sub_2_1_full<T>>
KAIRN_FORCEINLINE Packed<T, 2> operator-(const Packed<T, 2>& x, const Packed<T, 1>& a) noexcept {
    packed_detail::check(x, a);
    Packed<T, 2> w;
    gen::sub_2_1_full(x.limb[0], x.limb[1], a.limb[0], w.limb[0], w.limb[1]);
    return w;
}
/// In each lane, a - x (kernel sub_1_2_full).
template <class T>
    requires kairn::detail::proof_checked<gen::bounds::sub_1_2_full<T>>
KAIRN_FORCEINLINE Packed<T, 2> operator-(const Packed<T, 1>& a, const Packed<T, 2>& x) noexcept {
    packed_detail::check(a, x);
    Packed<T, 2> w;
    gen::sub_1_2_full(a.limb[0], x.limb[0], x.limb[1], w.limb[0], w.limb[1]);
    return w;
}
/// In each lane, x * y (kernel mul_2_2_full).
template <class T>
    requires kairn::detail::proof_checked<gen::bounds::mul_2_2_full<T>>
KAIRN_FORCEINLINE Packed<T, 2> operator*(const Packed<T, 2>& x, const Packed<T, 2>& y) noexcept {
    packed_detail::check(x, y);
    Packed<T, 2> w;
    gen::mul_2_2_full(x.limb[0], x.limb[1], y.limb[0], y.limb[1], w.limb[0], w.limb[1]);
    return w;
}
/// In each lane, x * a (kernel mul_2_1_full).
template <class T>
    requires kairn::detail::proof_checked<gen::bounds::mul_2_1_full<T>>
KAIRN_FORCEINLINE Packed<T, 2> operator*(const Packed<T, 2>& x, const Packed<T, 1>& a) noexcept {
    packed_detail::check(x, a);
    Packed<T, 2> w;
    gen::mul_2_1_full(x.limb[0], x.limb[1], a.limb[0], w.limb[0], w.limb[1]);
    return w;
}
/// a * x: the same operation as x * a (kernel mul_2_1_full).
template <class T>
    requires kairn::detail::proof_checked<gen::bounds::mul_2_1_full<T>>
KAIRN_FORCEINLINE Packed<T, 2> operator*(const Packed<T, 1>& a, const Packed<T, 2>& x) noexcept {
    return x * a;
}
/// x = x + y (kernel add_2_2_full).
template <class T>
    requires kairn::detail::proof_checked<gen::bounds::add_2_2_full<T>>
KAIRN_FORCEINLINE Packed<T, 2>& operator+=(Packed<T, 2>& x, const Packed<T, 2>& y) noexcept {
    return x = x + y;
}
/// x = x + a (kernel add_2_1_full).
template <class T>
    requires kairn::detail::proof_checked<gen::bounds::add_2_1_full<T>>
KAIRN_FORCEINLINE Packed<T, 2>& operator+=(Packed<T, 2>& x, const Packed<T, 1>& a) noexcept {
    return x = x + a;
}
/// x = x - y (kernel sub_2_2_full).
template <class T>
    requires kairn::detail::proof_checked<gen::bounds::sub_2_2_full<T>>
KAIRN_FORCEINLINE Packed<T, 2>& operator-=(Packed<T, 2>& x, const Packed<T, 2>& y) noexcept {
    return x = x - y;
}
/// x = x - a (kernel sub_2_1_full).
template <class T>
    requires kairn::detail::proof_checked<gen::bounds::sub_2_1_full<T>>
KAIRN_FORCEINLINE Packed<T, 2>& operator-=(Packed<T, 2>& x, const Packed<T, 1>& a) noexcept {
    return x = x - a;
}
/// x = x * y (kernel mul_2_2_full).
template <class T>
    requires kairn::detail::proof_checked<gen::bounds::mul_2_2_full<T>>
KAIRN_FORCEINLINE Packed<T, 2>& operator*=(Packed<T, 2>& x, const Packed<T, 2>& y) noexcept {
    return x = x * y;
}
/// x = x * a (kernel mul_2_1_full).
template <class T>
    requires kairn::detail::proof_checked<gen::bounds::mul_2_1_full<T>>
KAIRN_FORCEINLINE Packed<T, 2>& operator*=(Packed<T, 2>& x, const Packed<T, 1>& a) noexcept {
    return x = x * a;
}
/// In each lane, -x, limb by limb (kernel neg_2).
/// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
template <class T>
    requires kairn::detail::proof_checked<gen::bounds::neg_2<T>>
KAIRN_FORCEINLINE Packed<T, 2> operator-(const Packed<T, 2>& x) noexcept {
    packed_detail::check_exact(x);
    Packed<T, 2> z;
    gen::neg_2(x.limb[0], x.limb[1], z.limb[0], z.limb[1]);
    return z;
}
/// In each lane, |x| (kernel abs_2).
/// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
template <class T>
    requires kairn::detail::proof_checked<gen::bounds::abs_2<T>>
KAIRN_FORCEINLINE Packed<T, 2> abs(const Packed<T, 2>& x) noexcept {
    packed_detail::check_exact(x);
    Packed<T, 2> z;
    gen::abs_2(x.limb[0], x.limb[1], z.limb[0], z.limb[1]);
    return z;
}
/// In each lane, the fast addition (kernel add_fast_2_2_full), with its bound relative to the
/// operands.
template <class T>
    requires kairn::detail::proof_checked<gen::bounds::add_fast_2_2_full<T>>
KAIRN_FORCEINLINE Packed<T, 2> add_fast(const Packed<T, 2>& x, const Packed<T, 2>& y) noexcept {
    packed_detail::check(x, y);
    Packed<T, 2> w;
    gen::add_fast_2_2_full(x.limb[0], x.limb[1], y.limb[0], y.limb[1], w.limb[0], w.limb[1]);
    return w;
}
/// In each lane, x times 2^n, for every n, the same n in every lane (kernel mul_pow2_2_full, with
/// c = 2^n): kairn::ldexp of the lane, in the same steps when 2^n is not a number of T (argued and
/// tested through the oracle, not machine-checked).
template <class T>
    requires kairn::detail::proof_checked<gen::bounds::mul_pow2_2_full<T>>
KAIRN_FORCEINLINE Packed<T, 2> ldexp(const Packed<T, 2>& x, int n) noexcept {
    packed_detail::check(x);
    return packed_detail::ldexp_steps<true>(x, n);
}
/// In each lane, x / 2 (kernel mul_pow2_2_full, with c = 1/2): as ldexp(x, -1).
template <class T>
    requires kairn::detail::proof_checked<gen::bounds::mul_pow2_2_full<T>>
KAIRN_FORCEINLINE Packed<T, 2> half(const Packed<T, 2>& x) noexcept {
    packed_detail::check(x);
    return packed_detail::scale2<true>(x, T(0.5));
}

// --- Two limbs: comparisons and conversions to one limb -------------------------------------------

/// In each lane, whether x < y (kernel lt_2_2).
/// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
template <class T>
    requires kairn::detail::proof_checked<gen::bounds::lt_2_2<T>>
KAIRN_FORCEINLINE PackedMask<T> operator<(const Packed<T, 2>& x, const Packed<T, 2>& y) noexcept {
    packed_detail::check_exact(x, y);
    PackedMask<T> m;
    gen::lt_2_2(x.limb[0], x.limb[1], y.limb[0], y.limb[1], m.bits);
    return m;
}
/// In each lane, whether x > y (kernel lt_2_2 on y, x).
/// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
template <class T>
    requires kairn::detail::proof_checked<gen::bounds::lt_2_2<T>>
KAIRN_FORCEINLINE PackedMask<T> operator>(const Packed<T, 2>& x, const Packed<T, 2>& y) noexcept {
    return y < x;
}
/// In each lane, whether x <= y (kernel le_2_2).
/// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
template <class T>
    requires kairn::detail::proof_checked<gen::bounds::le_2_2<T>>
KAIRN_FORCEINLINE PackedMask<T> operator<=(const Packed<T, 2>& x, const Packed<T, 2>& y) noexcept {
    packed_detail::check_exact(x, y);
    PackedMask<T> m;
    gen::le_2_2(x.limb[0], x.limb[1], y.limb[0], y.limb[1], m.bits);
    return m;
}
/// In each lane, whether x >= y (kernel le_2_2 on y, x).
/// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
template <class T>
    requires kairn::detail::proof_checked<gen::bounds::le_2_2<T>>
KAIRN_FORCEINLINE PackedMask<T> operator>=(const Packed<T, 2>& x, const Packed<T, 2>& y) noexcept {
    return y <= x;
}
/// In each lane, whether x == y (kernel eq_2_2).
/// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
template <class T>
    requires kairn::detail::proof_checked<gen::bounds::eq_2_2<T>>
KAIRN_FORCEINLINE PackedMask<T> operator==(const Packed<T, 2>& x, const Packed<T, 2>& y) noexcept {
    packed_detail::check_exact(x, y);
    PackedMask<T> m;
    gen::eq_2_2(x.limb[0], x.limb[1], y.limb[0], y.limb[1], m.bits);
    return m;
}
/// In each lane, whether x != y: not x == y (kernel eq_2_2).
/// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
template <class T>
    requires kairn::detail::proof_checked<gen::bounds::eq_2_2<T>>
KAIRN_FORCEINLINE PackedMask<T> operator!=(const Packed<T, 2>& x, const Packed<T, 2>& y) noexcept {
    return !(x == y);
}
/// In each lane, whether x < a, a of one limb (kernel lt_2_1).
/// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
template <class T>
    requires kairn::detail::proof_checked<gen::bounds::lt_2_1<T>>
KAIRN_FORCEINLINE PackedMask<T> operator<(const Packed<T, 2>& x, const Packed<T, 1>& a) noexcept {
    packed_detail::check_exact(x, a);
    PackedMask<T> m;
    gen::lt_2_1(x.limb[0], x.limb[1], a.limb[0], m.bits);
    return m;
}
/// In each lane, whether a < x (kernel lt_1_2).
/// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
template <class T>
    requires kairn::detail::proof_checked<gen::bounds::lt_1_2<T>>
KAIRN_FORCEINLINE PackedMask<T> operator<(const Packed<T, 1>& a, const Packed<T, 2>& x) noexcept {
    packed_detail::check_exact(a, x);
    PackedMask<T> m;
    gen::lt_1_2(a.limb[0], x.limb[0], x.limb[1], m.bits);
    return m;
}
/// In each lane, whether x > a: a < x (kernel lt_1_2).
/// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
template <class T>
    requires kairn::detail::proof_checked<gen::bounds::lt_1_2<T>>
KAIRN_FORCEINLINE PackedMask<T> operator>(const Packed<T, 2>& x, const Packed<T, 1>& a) noexcept {
    return a < x;
}
/// In each lane, whether a > x: x < a (kernel lt_2_1).
/// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
template <class T>
    requires kairn::detail::proof_checked<gen::bounds::lt_2_1<T>>
KAIRN_FORCEINLINE PackedMask<T> operator>(const Packed<T, 1>& a, const Packed<T, 2>& x) noexcept {
    return x < a;
}
/// In each lane, whether x <= a (kernel le_2_1).
/// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
template <class T>
    requires kairn::detail::proof_checked<gen::bounds::le_2_1<T>>
KAIRN_FORCEINLINE PackedMask<T> operator<=(const Packed<T, 2>& x, const Packed<T, 1>& a) noexcept {
    packed_detail::check_exact(x, a);
    PackedMask<T> m;
    gen::le_2_1(x.limb[0], x.limb[1], a.limb[0], m.bits);
    return m;
}
/// In each lane, whether a <= x (kernel le_1_2).
/// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
template <class T>
    requires kairn::detail::proof_checked<gen::bounds::le_1_2<T>>
KAIRN_FORCEINLINE PackedMask<T> operator<=(const Packed<T, 1>& a, const Packed<T, 2>& x) noexcept {
    packed_detail::check_exact(a, x);
    PackedMask<T> m;
    gen::le_1_2(a.limb[0], x.limb[0], x.limb[1], m.bits);
    return m;
}
/// In each lane, whether x >= a: a <= x (kernel le_1_2).
/// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
template <class T>
    requires kairn::detail::proof_checked<gen::bounds::le_1_2<T>>
KAIRN_FORCEINLINE PackedMask<T> operator>=(const Packed<T, 2>& x, const Packed<T, 1>& a) noexcept {
    return a <= x;
}
/// In each lane, whether a >= x: x <= a (kernel le_2_1).
/// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
template <class T>
    requires kairn::detail::proof_checked<gen::bounds::le_2_1<T>>
KAIRN_FORCEINLINE PackedMask<T> operator>=(const Packed<T, 1>& a, const Packed<T, 2>& x) noexcept {
    return x <= a;
}
/// In each lane, whether x == a (kernel eq_2_1).
/// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
template <class T>
    requires kairn::detail::proof_checked<gen::bounds::eq_2_1<T>>
KAIRN_FORCEINLINE PackedMask<T> operator==(const Packed<T, 2>& x, const Packed<T, 1>& a) noexcept {
    packed_detail::check_exact(x, a);
    PackedMask<T> m;
    gen::eq_2_1(x.limb[0], x.limb[1], a.limb[0], m.bits);
    return m;
}
/// In each lane, whether a == x (kernel eq_2_1).
/// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
template <class T>
    requires kairn::detail::proof_checked<gen::bounds::eq_2_1<T>>
KAIRN_FORCEINLINE PackedMask<T> operator==(const Packed<T, 1>& a, const Packed<T, 2>& x) noexcept {
    return x == a;
}
/// In each lane, whether x != a (kernel eq_2_1).
/// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
template <class T>
    requires kairn::detail::proof_checked<gen::bounds::eq_2_1<T>>
KAIRN_FORCEINLINE PackedMask<T> operator!=(const Packed<T, 2>& x, const Packed<T, 1>& a) noexcept {
    return !(x == a);
}
/// In each lane, whether a != x (kernel eq_2_1).
/// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
template <class T>
    requires kairn::detail::proof_checked<gen::bounds::eq_2_1<T>>
KAIRN_FORCEINLINE PackedMask<T> operator!=(const Packed<T, 1>& a, const Packed<T, 2>& x) noexcept {
    return !(x == a);
}

/// In each lane, x rounded to nearest, ties to even: the leading limb (kernel to_nearest_2).
/// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
template <class T>
    requires kairn::detail::proof_checked<gen::bounds::to_nearest_2<T>>
KAIRN_FORCEINLINE Packed<T, 1> to_nearest(const Packed<T, 2>& x) noexcept {
    return Packed<T, 1>(x);
}
/// In each lane, the largest T not above x (kernel to_down_2).
/// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
template <class T>
    requires kairn::detail::proof_checked<gen::bounds::to_down_2<T>>
KAIRN_FORCEINLINE Packed<T, 1> to_down(const Packed<T, 2>& x) noexcept {
    packed_detail::check_exact(x);
    Packed<T, 1> t;
    gen::to_down_2(x.limb[0], x.limb[1], t.limb[0]);
    return t;
}
/// In each lane, the smallest T not below x (kernel to_up_2).
/// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
template <class T>
    requires kairn::detail::proof_checked<gen::bounds::to_up_2<T>>
KAIRN_FORCEINLINE Packed<T, 1> to_up(const Packed<T, 2>& x) noexcept {
    packed_detail::check_exact(x);
    Packed<T, 1> t;
    gen::to_up_2(x.limb[0], x.limb[1], t.limb[0]);
    return t;
}
/// In each lane, the smallest T not below |x| (kernel abs_upper_2).
/// Does not round: not preceded by the debug build's check of the rounding mode (config.hpp).
template <class T>
    requires kairn::detail::proof_checked<gen::bounds::abs_upper_2<T>>
KAIRN_FORCEINLINE Packed<T, 1> abs_upper(const Packed<T, 2>& x) noexcept {
    packed_detail::check_exact(x);
    Packed<T, 1> t;
    gen::abs_upper_2(x.limb[0], x.limb[1], t.limb[0]);
    return t;
}

/// The finite cores (decision D5), lane by lane: the functions of kairn::finite of expansion.hpp
/// for packed operands, each the packed form of the core that the function of the same name
/// calls, with its contract in each lane (a lane whose leading limb is not finite is not canonical:
/// select or test it before passing it to an operator). None for one limb, which has no arithmetic.
namespace finite {

/// In each lane, x + y, the core alone (kernel add_2_2).
template <class T>
    requires kairn::detail::proof_checked<gen::bounds::add_2_2<T>>
KAIRN_FORCEINLINE Packed<T, 2> add(const Packed<T, 2>& x, const Packed<T, 2>& y) noexcept {
    packed_detail::check_core(x, y);
    Packed<T, 2> z;
    gen::add_2_2(x.limb[0], x.limb[1], y.limb[0], y.limb[1], z.limb[0], z.limb[1]);
    return z;
}
/// In each lane, x + a, the core alone (kernel add_2_1), which guards a.
template <class T>
    requires kairn::detail::proof_checked<gen::bounds::add_2_1<T>>
KAIRN_FORCEINLINE Packed<T, 2> add(const Packed<T, 2>& x, const Packed<T, 1>& a) noexcept {
    packed_detail::check_core(x);
    Packed<T, 2> z;
    gen::add_2_1(x.limb[0], x.limb[1], a.limb[0], z.limb[0], z.limb[1]);
    return z;
}
/// In each lane, a + x, the core alone (kernel add_2_1).
template <class T>
    requires kairn::detail::proof_checked<gen::bounds::add_2_1<T>>
KAIRN_FORCEINLINE Packed<T, 2> add(const Packed<T, 1>& a, const Packed<T, 2>& x) noexcept {
    return finite::add(x, a);
}
/// In each lane, x - y, the core alone (kernel sub_2_2).
template <class T>
    requires kairn::detail::proof_checked<gen::bounds::sub_2_2<T>>
KAIRN_FORCEINLINE Packed<T, 2> sub(const Packed<T, 2>& x, const Packed<T, 2>& y) noexcept {
    packed_detail::check_core(x, y);
    Packed<T, 2> z;
    gen::sub_2_2(x.limb[0], x.limb[1], y.limb[0], y.limb[1], z.limb[0], z.limb[1]);
    return z;
}
/// In each lane, x - a, the core alone (kernel sub_2_1).
template <class T>
    requires kairn::detail::proof_checked<gen::bounds::sub_2_1<T>>
KAIRN_FORCEINLINE Packed<T, 2> sub(const Packed<T, 2>& x, const Packed<T, 1>& a) noexcept {
    packed_detail::check_core(x);
    Packed<T, 2> z;
    gen::sub_2_1(x.limb[0], x.limb[1], a.limb[0], z.limb[0], z.limb[1]);
    return z;
}
/// In each lane, a - x, the core alone (kernel sub_1_2).
template <class T>
    requires kairn::detail::proof_checked<gen::bounds::sub_1_2<T>>
KAIRN_FORCEINLINE Packed<T, 2> sub(const Packed<T, 1>& a, const Packed<T, 2>& x) noexcept {
    packed_detail::check_core(x);
    Packed<T, 2> z;
    gen::sub_1_2(a.limb[0], x.limb[0], x.limb[1], z.limb[0], z.limb[1]);
    return z;
}
/// In each lane, x * y, the core alone (kernel mul_2_2).
template <class T>
    requires kairn::detail::proof_checked<gen::bounds::mul_2_2<T>>
KAIRN_FORCEINLINE Packed<T, 2> mul(const Packed<T, 2>& x, const Packed<T, 2>& y) noexcept {
    packed_detail::check_core(x, y);
    Packed<T, 2> z;
    gen::mul_2_2(x.limb[0], x.limb[1], y.limb[0], y.limb[1], z.limb[0], z.limb[1]);
    return z;
}
/// In each lane, x * a, the core alone (kernel mul_2_1).
template <class T>
    requires kairn::detail::proof_checked<gen::bounds::mul_2_1<T>>
KAIRN_FORCEINLINE Packed<T, 2> mul(const Packed<T, 2>& x, const Packed<T, 1>& a) noexcept {
    packed_detail::check_core(x);
    Packed<T, 2> z;
    gen::mul_2_1(x.limb[0], x.limb[1], a.limb[0], z.limb[0], z.limb[1]);
    return z;
}
/// In each lane, a * x, the core alone (kernel mul_2_1).
template <class T>
    requires kairn::detail::proof_checked<gen::bounds::mul_2_1<T>>
KAIRN_FORCEINLINE Packed<T, 2> mul(const Packed<T, 1>& a, const Packed<T, 2>& x) noexcept {
    return finite::mul(x, a);
}
/// In each lane, the fast addition, the core alone (kernel add_fast_2_2).
template <class T>
    requires kairn::detail::proof_checked<gen::bounds::add_fast_2_2<T>>
KAIRN_FORCEINLINE Packed<T, 2> add_fast(const Packed<T, 2>& x, const Packed<T, 2>& y) noexcept {
    packed_detail::check_core(x, y);
    Packed<T, 2> z;
    gen::add_fast_2_2(x.limb[0], x.limb[1], y.limb[0], y.limb[1], z.limb[0], z.limb[1]);
    return z;
}
/// In each lane, x times 2^n, the core alone (kernel mul_pow2_2), in the steps of kairn::ldexp.
template <class T>
    requires kairn::detail::proof_checked<gen::bounds::mul_pow2_2<T>>
KAIRN_FORCEINLINE Packed<T, 2> ldexp(const Packed<T, 2>& x, int n) noexcept {
    packed_detail::check_core(x);
    return packed_detail::ldexp_steps<false>(x, n);
}

}  // namespace finite

}  // namespace kairn
KAIRN_GEN_POP_WARNINGS
