// boundary.cpp for Packed (packed.hpp) and the containers (soa.hpp): a product the program computes,
// in the registers of the form with its intrinsics (in T for the form of one lane) or in T into an
// array, and passes straight into Packed, must give the same result as the same operation on that
// product rounded first. The guard of the packed kernels (rule R3: guard(a) in add_2_1_full,
// sub_2_1_full, sub_1_2_full, their cores, make_2 and make_2_limbs, written with the form's
// intrinsics) keeps a compiler that contracts across statements from fusing the product into a
// kernel's error-free sums. Each form below is computed twice, with the product written in place,
// and with an honestly rounded product (returned through a volatile by a function that is not
// inlined), on operands chosen so that the sums cancel, one pair per lane and a different pair in
// each lane, and the results are compared bit for bit, every limb of every lane (a zero limb as a
// zero under MSVC, which folds the guard's +0: packed.cpp says what was measured).
//
//   boundary_packed --expect none     every form agrees (the headers as they are)
//   boundary_packed --expect some     built against a copy of the headers without the guard, the
//                                     packed guards included (tests/api/CMakeLists.txt), on a
//                                     compiler and setting that fuse: some form must differ, so
//                                     that the test above cannot pass for want of a compiler that
//                                     fuses
//   boundary_packed --expect report   prints the counts only, and says so if nothing differs
//
// The forms whose operand is only multiplied or compared need no guard and must agree in every
// build: a product is fused only into an addition. A third kind (--factor none|some|report): the
// products of Packed<T, 2> and Packed<T, 1> with the other factor a constant F (1, -1, 2) the
// compiler sees (KNOWN below); --factor none in the build with the guard: every form agrees.
//
// The arithmetic of Packed<T, 1> is in the first kind (the register of products as an operand of
// x + y and x - y, whose kernels guard both operands) and the second (x * y). Two kinds more, of
// its product x * y of the program's factors (kernel scale_step_1, the opaque product
// fma(x, y, +0)): passed straight into an operation of Kairn that adds it (x * y + z of one limb as
// a program writes it, and x + a of two limbs), and added by the program itself with the form's
// own addition, on the registers. Both must agree in the build with the guard (--expect none);
// against the copy without it they are counted and reported only (the product there is the same).
#include <kairn/kairn.hpp>
#include <kairn/packed.hpp>
#include <kairn/soa.hpp>

#include <cstdint>
#include <cstdio>
#include <cstring>
#include <type_traits>

#if defined(_MSC_VER) && !defined(__clang__)
#define NOINLINE __declspec(noinline)
#define ALWAYS_INLINE __forceinline
#define KAIRN_TEST_ZERO_SIGN_FREE 1
#else
#define NOINLINE __attribute__((noinline))
#define ALWAYS_INLINE inline __attribute__((always_inline))
#define KAIRN_TEST_ZERO_SIGN_FREE 0
#endif

namespace {

template <class T>
using P1 = kairn::Packed<T, 1>;
template <class T>
using P2 = kairn::Packed<T, 2>;
template <class T>
using E1 = kairn::Expansion<T, 1>;
template <class T>
using E2 = kairn::Expansion<T, 2>;

// What the program computes with: the intrinsics of the form, which a program of that target
// writes, and T for the form of one lane.
template <class T>
struct Program;
#if KAIRN_PACKED_FORM == KAIRN_PACKED_FORM_AVX2
const char* const form_name = "AVX2";
template <>
struct Program<double> {
    using R = __m256d;
    static ALWAYS_INLINE R load(const double* p) { return _mm256_loadu_pd(p); }
    static ALWAYS_INLINE R mul(R a, R b) { return _mm256_mul_pd(a, b); }
    static ALWAYS_INLINE R add(R a, R b) { return _mm256_add_pd(a, b); }
    static ALWAYS_INLINE void store(double* p, R a) { _mm256_storeu_pd(p, a); }
};
template <>
struct Program<float> {
    using R = __m256;
    static ALWAYS_INLINE R load(const float* p) { return _mm256_loadu_ps(p); }
    static ALWAYS_INLINE R mul(R a, R b) { return _mm256_mul_ps(a, b); }
    static ALWAYS_INLINE R add(R a, R b) { return _mm256_add_ps(a, b); }
    static ALWAYS_INLINE void store(float* p, R a) { _mm256_storeu_ps(p, a); }
};
#elif KAIRN_PACKED_FORM == KAIRN_PACKED_FORM_NEON
const char* const form_name = "NEON";
template <>
struct Program<double> {
    using R = float64x2_t;
    static ALWAYS_INLINE R load(const double* p) { return vld1q_f64(p); }
    static ALWAYS_INLINE R mul(R a, R b) { return vmulq_f64(a, b); }
    static ALWAYS_INLINE R add(R a, R b) { return vaddq_f64(a, b); }
    static ALWAYS_INLINE void store(double* p, R a) { vst1q_f64(p, a); }
};
template <>
struct Program<float> {
    using R = float32x4_t;
    static ALWAYS_INLINE R load(const float* p) { return vld1q_f32(p); }
    static ALWAYS_INLINE R mul(R a, R b) { return vmulq_f32(a, b); }
    static ALWAYS_INLINE R add(R a, R b) { return vaddq_f32(a, b); }
    static ALWAYS_INLINE void store(float* p, R a) { vst1q_f32(p, a); }
};
#else
const char* const form_name = "scalar, one lane";
template <class T>
struct Program {
    using R = T;
    static ALWAYS_INLINE R load(const T* p) { return *p; }
    static ALWAYS_INLINE R mul(R a, R b) { return a * b; }
    static ALWAYS_INLINE R add(R a, R b) { return a + b; }
    static ALWAYS_INLINE void store(T* p, R a) { *p = a; }
};
#endif
// Program<T>::R is P1<T>::register_type: from_limbs below takes it, and nothing converts to it.

template <class T>
NOINLINE T rounded(T a, T b) {
    volatile T p = a * b;
    return p;
}

// The two ways of passing a product: computed in place from the factors a and b, or the rounded
// products, given in a (b is then ignored).
template <class T>
struct InPlace {
    static ALWAYS_INLINE typename Program<T>::R reg(const T* a, const T* b) {
        return Program<T>::mul(Program<T>::load(a), Program<T>::load(b));
    }
    static ALWAYS_INLINE T one(const T* a, const T* b, int l) { return a[l] * b[l]; }
};
template <class T>
struct Rounded {
    static ALWAYS_INLINE typename Program<T>::R reg(const T* a, const T*) { return Program<T>::load(a); }
    static ALWAYS_INLINE T one(const T* a, const T*, int l) { return a[l]; }
};

// A form: its body, with x the two-limb operand, the factors in a and b (W of each, lane l's in
// a[l] and b[l]), and k a lane, for the forms that take one number. NAME_inline and NAME_rounded
// are the two ways, each a function of its own that is not inlined.
#define FORM(NAME, ...)                                                                              \
    template <class T, class M>                                                                      \
    ALWAYS_INLINE P2<T> NAME##_body([[maybe_unused]] const P2<T>& x, [[maybe_unused]] const T* a,    \
                                    [[maybe_unused]] const T* b, [[maybe_unused]] int k) {           \
        [[maybe_unused]] constexpr int W = P1<T>::lanes;                                            \
        __VA_ARGS__                                                                                  \
    }                                                                                                \
    template <class T>                                                                               \
    NOINLINE P2<T> NAME##_inline(const P2<T>& x, const T* a, const T* b, int k) {                   \
        return NAME##_body<T, InPlace<T>>(x, a, b, k);                                               \
    }                                                                                                \
    template <class T>                                                                               \
    NOINLINE P2<T> NAME##_rounded(const P2<T>& x, const T* a, const T* b, int k) {                  \
        return NAME##_body<T, Rounded<T>>(x, a, b, k);                                               \
    }

// The product as a register of the program, made a Packed<T, 1> by from_limbs.
#define PROD P1<T>::from_limbs(M::reg(a, b))
// Lane l's product as a T.
#define ONE(l) M::one(a, b, l)
// W products into arrays of the program, every element written.
#define FILL1(s)                                    \
    T s[W];                                         \
    for (int l = 0; l < W; ++l) s[l] = ONE(l);
#define FILL2(h, t)                                 \
    T h[W], t[W];                                   \
    for (int l = 0; l < W; ++l) {                   \
        h[l] = ONE(l);                              \
        t[l] = T(0);                                \
    }

// A mask as a number in each lane, 1 or 0, for the comparisons.
template <class T>
ALWAYS_INLINE P2<T> as_number(const kairn::PackedMask<T>& m) {
    return kairn::select(m, P2<T>::broadcast(E2<T>(T(1))), P2<T>());
}

// A register of the program, through Packed<T, 1>::from_limbs, into the mixed forms.
FORM(plus, return x + PROD;)
FORM(plus_rev, return PROD + x;)
FORM(minus, return x - PROD;)
FORM(rminus, return PROD - x;)
FORM(plus_assign, P2<T> y = x; y += PROD; return y;)
FORM(minus_assign, P2<T> y = x; y -= PROD; return y;)
FORM(widen, return P2<T>(PROD) + x;)
FORM(widen_init, const P2<T> y = PROD; return x + y;)
FORM(add_fast, return kairn::add_fast(x, P2<T>(PROD));)
FORM(negated, return x + -PROD;)
FORM(magnitude, return x + kairn::abs(PROD);)
FORM(selected, return x + kairn::select(!kairn::PackedMask<T>(), PROD, P1<T>());)
FORM(finite_plus, return kairn::finite::add(x, PROD);)
FORM(finite_plus_rev, return kairn::finite::add(PROD, x);)
FORM(finite_minus, return kairn::finite::sub(x, PROD);)
FORM(finite_rminus, return kairn::finite::sub(PROD, x);)
FORM(finite_add_fast, return kairn::finite::add_fast(x, P2<T>(PROD));)
// The register as the leading limb of a Packed<T, 2>.
FORM(from_limbs, return P2<T>::from_limbs(M::reg(a, b), P1<T>().limb[0]) + x;)
FORM(from_limbs_unchecked, return P2<T>::from_limbs_unchecked(M::reg(a, b), P1<T>().limb[0]) + x;)
// One number, a product in T, in every lane or in one.
FORM(broadcast1, return x + P1<T>::broadcast(E1<T>(ONE(k)));)
FORM(broadcast2, return P2<T>::broadcast(E2<T>(ONE(k))) + x;)
FORM(set_lane1, P1<T> q; for (int l = 0; l < W; ++l) q.set_lane(l, E1<T>(ONE(l))); return x + q;)
FORM(set_lane2, P2<T> q; for (int l = 0; l < W; ++l) q.set_lane(l, E2<T>(ONE(l))); return q + x;)
// Arrays the program fills with products, then loads.
FORM(load1, FILL1(s) return x + P1<T>::load(s);)
FORM(load2, FILL2(h, t) return P2<T>::load(h, t) + x;)
FORM(load2_unchecked, FILL2(h, t) return P2<T>::load_unchecked(h, t) + x;)
FORM(load_partial1, FILL1(s) return x + P1<T>::load_partial(s, k, E1<T>(ONE(k)));)
FORM(load_partial2, FILL2(h, t) return P2<T>::load_partial(h, t, k, E2<T>(ONE(k))) + x;)
FORM(stored1, T s[W]; Program<T>::store(s, M::reg(a, b)); return x + P1<T>::load(s);)
FORM(stored2, T h[W]; T t[W] = {}; Program<T>::store(h, M::reg(a, b)); return P2<T>::load(h, t) + x;)
// Views of those arrays, and an SoA whose limbs the program writes.
FORM(view1, FILL1(s) const kairn::SoAView<T, 1> v(s, W); return x + v.load(0);)
FORM(view2, FILL2(h, t) const kairn::SoAView<T, 2> v(h, t, W); return v.load(0) + x;)
FORM(view1_partial, FILL1(s) const kairn::SoAView<T, 1> v(s, W); return x + v.load_partial(0, k, E1<T>(ONE(k)));)
FORM(view2_partial, FILL2(h, t) const kairn::SoAView<T, 2> v(h, t, W); return v.load_partial(0, k, E2<T>(ONE(k))) + x;)
FORM(view1_element, FILL1(s) const kairn::SoAView<const T, 1> v(s, W); P1<T> q;
     for (int l = 0; l < W; ++l) q.set_lane(l, v[std::size_t(l)]); return x + q;)
FORM(view2_get, FILL2(h, t) const kairn::SoAView<const T, 2> v(h, t, W); P2<T> q;
     for (int l = 0; l < W; ++l) q.set_lane(l, v.get(std::size_t(l))); return q + x;)
FORM(view1_set, T s[W] = {}; const kairn::SoAView<T, 1> v(s, W);
     for (int l = 0; l < W; ++l) v.set(std::size_t(l), E1<T>(ONE(l))); return x + v.load(0);)
FORM(view2_assign, T h[W] = {}; T t[W] = {}; const kairn::SoAView<T, 2> v(h, t, W);
     for (int l = 0; l < W; ++l) v[std::size_t(l)] = E2<T>(ONE(l)); return v.load(0) + x;)
FORM(view1_store, T s[W] = {}; const kairn::SoAView<T, 1> v(s, W); v.store(0, PROD); return x + v.load(0);)
FORM(soa1, kairn::SoA<T, 1> s(W); for (int l = 0; l < W; ++l) s.limb(0)[l] = ONE(l); return x + s.load(0);)
FORM(soa2, kairn::SoA<T, 2> s(W); for (int l = 0; l < W; ++l) s.limb(0)[l] = ONE(l); return s.load(0) + x;)
FORM(soa1_element, kairn::SoA<T, 1> s(W); for (int l = 0; l < W; ++l) s[std::size_t(l)] = E1<T>(ONE(l));
     return x + s.load(0);)
// Multiplied or compared: no guard, and none needed.
FORM(times, return x * PROD;)
FORM(times_rev, return PROD * x;)
FORM(times_assign, P2<T> y = x; y *= PROD; return y;)
FORM(finite_times, return kairn::finite::mul(x, PROD);)
FORM(less, return as_number(x < PROD);)
FORM(less_rev, return as_number(PROD < x);)
FORM(less_equal, return as_number(x <= PROD);)
FORM(less_equal_rev, return as_number(PROD <= x);)
FORM(equal, return as_number(x == PROD);)
FORM(not_equal, return as_number(PROD != x);)

// One limb: the arithmetic of Packed<T, 1> (add_entry_step_1 and sub_entry_step_1 guard both
// operands), the register of products against the leading limb of x as a Packed<T, 1>; each
// result widened to two limbs exactly, for the comparison.
#define X1 P1<T>::from_limbs(x.limb[0])
FORM(p1_plus, return P2<T>(X1 + PROD);)
FORM(p1_plus_rev, return P2<T>(PROD + X1);)
FORM(p1_minus, return P2<T>(X1 - PROD);)
FORM(p1_rminus, return P2<T>(PROD - X1);)
FORM(p1_plus_assign, P1<T> y = X1; y += PROD; return P2<T>(y);)
FORM(p1_minus_assign, P1<T> y = X1; y -= PROD; return P2<T>(y);)
FORM(p1_broadcast, return P2<T>(X1 + P1<T>::broadcast(E1<T>(ONE(k))));)
FORM(p1_load, FILL1(s) return P2<T>(P1<T>::load(s) + X1);)
FORM(p1_times, return P2<T>(X1 * PROD);)
FORM(p1_times_assign, P1<T> y = X1; y *= PROD; return P2<T>(y);)
// The product of Packed<T, 1> (scale_step_1, the opaque product fma(a, b, +0)) of the program's
// factors, loaded: with the rounded products the factors are p and 1, and p 1 is p. KPROD passed
// straight into an operation of Kairn that adds it (with one limb, x * y + z as a program writes
// it; with two, x + a), which guards it: it must agree with the guard. And KPROD added by the
// program itself, on the registers of the form with its own addition: the opaque product is not a
// product a compiler fuses into that addition either (measured: these forms must agree in the build
// with the guard, whose product is the same as without it).
#define KPROD (P1<T>::load(a) * P1<T>::load(b))
FORM(kp_plus, return P2<T>(KPROD + X1);)
FORM(kp_plus_rev, return P2<T>(X1 + KPROD);)
FORM(kp_minus, return P2<T>(X1 - KPROD);)
FORM(kp_plus_assign, P1<T> y = X1; y += KPROD; return P2<T>(y);)
FORM(kp_mixed, return x + KPROD;)
FORM(kp_mixed_minus, return x - KPROD;)
FORM(kp_program_add, return P2<T>(P1<T>::from_limbs(Program<T>::add(KPROD.limb[0], x.limb[0])));)
FORM(kp_program_add_rev, return P2<T>(P1<T>::from_limbs(Program<T>::add(x.limb[0], KPROD.limb[0])));)
// A square of the program, a * a, which a compiler can prove is never -0: Apple clang 21 under
// -ffp-contract=fast then drops the guard a * a + 0, which it may since the two have the same value,
// and fuses the square into the kernel's first addition (a finding of 2026-11-23, in Packed<T, 1> +
// and in x + a of two limbs, and outside this file in kairn::two_sum and the sums of arrays: the
// guard of rule R3 does not hold such a product). Counted and printed, never required to agree, so
// that every build shows whether its compiler does it (run_squares).
#define SQUARE P1<T>::from_limbs(M::reg(a, a))
FORM(sq_p1_plus, return P2<T>(X1 + SQUARE);)
FORM(sq_plus, return x + SQUARE;)

// The other factor a constant the compiler sees (rule R3, the factors of a fused operation:
// docs/developer/architecture.md): Packed<T, 2> of F in every lane, F = 1, -1 or 2, times the
// program's register of products. A compiler that sees F = 1 rewrites fma(x, 1, s) as x + s and may
// fuse the product into that addition. With the headers as they are every form must agree
// (--factor none); the copy without the guard reports, or requires a difference where measured.
template <int C, class T>
constexpr T known() {
    return C == 0 ? T(1) : C == 1 ? T(-1) : T(2);
}
#define KNOWN(NAME, ...)                                                                             \
    template <class T, int C, class M>                                                               \
    ALWAYS_INLINE P2<T> NAME##_body([[maybe_unused]] const T* a, [[maybe_unused]] const T* b) {      \
        [[maybe_unused]] const P2<T> X = P2<T>::broadcast(E2<T>(known<C, T>()));                     \
        __VA_ARGS__                                                                                  \
    }                                                                                                \
    template <class T, int C>                                                                        \
    NOINLINE P2<T> NAME##_inline(const T* a, const T* b) { return NAME##_body<T, C, InPlace<T>>(a, b); } \
    template <class T, int C>                                                                        \
    NOINLINE P2<T> NAME##_rounded(const T* a, const T* b) { return NAME##_body<T, C, Rounded<T>>(a, b); }
KNOWN(k_times, return X * PROD;)
KNOWN(k_times_rev, return PROD * X;)
KNOWN(k_times_assign, P2<T> y = X; y *= PROD; return y;)
KNOWN(k_finite_times, return kairn::finite::mul(X, PROD);)
KNOWN(k_finite_times_rev, return kairn::finite::mul(PROD, X);)

template <class T>
using KnownFn = P2<T> (*)(const T*, const T*);
template <class T>
struct KnownForm {
    const char* name;
    KnownFn<T> in_place[3], rounded[3];
};
#define KROW(NAME, TEXT)                                                                 \
    {TEXT,                                                                               \
     {&NAME##_inline<T, 0>, &NAME##_inline<T, 1>, &NAME##_inline<T, 2>},                 \
     {&NAME##_rounded<T, 0>, &NAME##_rounded<T, 1>, &NAME##_rounded<T, 2>}}

template <class T>
using Fn = P2<T> (*)(const P2<T>&, const T*, const T*, int);

template <class T>
struct Form {
    const char* name;
    Fn<T> in_place, rounded;
    bool plus_x;  // x is +p, for the forms that subtract or negate the product; else -p
    // 0: needs the guard; 1: multiplied or compared, no guard needed; 2: the product of
    // Packed<T, 1> into an operation of Kairn; 3: the product of Packed<T, 1> added by the program.
    int kind;
};
#define ROW(NAME, TEXT, PLUS, GUARD) {TEXT, &NAME##_inline<T>, &NAME##_rounded<T>, PLUS, (GUARD) ? 0 : 1}
#define ROWK(NAME, TEXT, PLUS, KIND) {TEXT, &NAME##_inline<T>, &NAME##_rounded<T>, PLUS, KIND}

template <class T>
using Bits = std::conditional_t<sizeof(T) == 8, std::uint64_t, std::uint32_t>;
template <class T>
bool same_limb(T u, T v) {
    if (KAIRN_TEST_ZERO_SIGN_FREE && u == T(0) && v == T(0)) return true;
    Bits<T> x, y;
    std::memcpy(&x, &u, sizeof u);
    std::memcpy(&y, &v, sizeof v);
    return x == y;
}

std::uint64_t state = 0x9E3779B97F4A7C15ull;
std::uint64_t next() {
    state ^= state << 13;
    state ^= state >> 7;
    state ^= state << 17;
    return state;
}
template <class T>
T uniform() {  // in [0.5, 1)
    if constexpr (sizeof(T) == 8) {
        return 0.5 + double(next() >> 11) * 0x1p-54;
    } else {
        return 0.5f + float(next() >> 40) * 0x1p-25f;
    }
}

struct Totals {
    long guarded = 0, unguarded = 0, known = 0, kairn_product = 0, program_add = 0;
};

template <class T>
void run_known(const char* type, long registers, Totals& totals) {
    constexpr int W = P1<T>::lanes;
    const KnownForm<T> forms[] = {
        KROW(k_times, "P2(F) * P1(a*b)"),
        KROW(k_times_rev, "P1(a*b) * P2(F)"),
        KROW(k_times_assign, "y = P2(F); y *= P1(a*b)"),
        KROW(k_finite_times, "finite::mul(P2(F), P1(a*b))"),
        KROW(k_finite_times_rev, "finite::mul(P1(a*b), P2(F))"),
    };
    for (const KnownForm<T>& f : forms) {
        for (int c = 0; c < 3; ++c) {
            long differ = 0;
            for (long i = 0; i < registers; ++i) {
                T a[W], b[W], p[W];
                for (int l = 0; l < W; ++l) {
                    a[l] = uniform<T>();
                    b[l] = uniform<T>();
                    p[l] = rounded(a[l], b[l]);
                }
                const P2<T> u = f.in_place[c](a, b), v = f.rounded[c](p, b);
                bool differs = false;
                for (int l = 0; l < W; ++l) {
                    const E2<T> ul = u.lane(l), vl = v.lane(l);
                    differs = differs || !same_limb(ul.limb[0], vl.limb[0]) || !same_limb(ul.limb[1], vl.limb[1]);
                }
                differ += differs;
            }
            if (differ)
                std::printf("  %-32s %-6s F = %-2g differs in %6ld of %ld registers: a product of the program fused "
                            "through the known factor\n", f.name, type, c == 0 ? 1.0 : c == 1 ? -1.0 : 2.0, differ,
                            registers);
            totals.known += differ;
        }
    }
}

template <class T>
void run(const char* type, long registers, Totals& totals) {
    constexpr int W = P1<T>::lanes;
    const Form<T> forms[] = {
        ROW(plus, "x + a*b", false, true),
        ROW(plus_rev, "a*b + x", false, true),
        ROW(minus, "x - a*b", true, true),
        ROW(rminus, "a*b - x", true, true),
        ROW(plus_assign, "x += a*b", false, true),
        ROW(minus_assign, "x -= a*b", true, true),
        ROW(widen, "P2(a*b) + x", false, true),
        ROW(widen_init, "P2 y = a*b; x + y", false, true),
        ROW(add_fast, "add_fast(x, P2(a*b))", false, true),
        ROW(negated, "x + -(a*b)", true, true),
        ROW(magnitude, "x + abs(a*b)", false, true),
        ROW(selected, "x + select(m, a*b, 0)", false, true),
        ROW(finite_plus, "finite::add(x, a*b)", false, true),
        ROW(finite_plus_rev, "finite::add(a*b, x)", false, true),
        ROW(finite_minus, "finite::sub(x, a*b)", true, true),
        ROW(finite_rminus, "finite::sub(a*b, x)", true, true),
        ROW(finite_add_fast, "finite::add_fast(x, P2(a*b))", false, true),
        ROW(from_limbs, "P2::from_limbs(a*b, 0) + x", false, true),
        ROW(from_limbs_unchecked, "P2::from_limbs_unchecked(a*b, 0)", false, true),
        ROW(broadcast1, "x + P1::broadcast(E1(a*b))", false, true),
        ROW(broadcast2, "P2::broadcast(E2(a*b)) + x", false, true),
        ROW(set_lane1, "P1.set_lane(l, E1(a*b)); x + P1", false, true),
        ROW(set_lane2, "P2.set_lane(l, E2(a*b)); P2 + x", false, true),
        ROW(load1, "x + P1::load({a*b})", false, true),
        ROW(load2, "P2::load({a*b}, {0}) + x", false, true),
        ROW(load2_unchecked, "P2::load_unchecked({a*b}, {0})", false, true),
        ROW(load_partial1, "x + P1::load_partial({a*b}, k, a*b)", false, true),
        ROW(load_partial2, "P2::load_partial(.., k, a*b) + x", false, true),
        ROW(stored1, "store(s, A*B); x + P1::load(s)", false, true),
        ROW(stored2, "store(h, A*B); P2::load(h, 0) + x", false, true),
        ROW(view1, "x + SoAView<T, 1>({a*b}).load(0)", false, true),
        ROW(view2, "SoAView<T, 2>({a*b}, {0}).load(0)", false, true),
        ROW(view1_partial, "x + view1.load_partial(0, k, a*b)", false, true),
        ROW(view2_partial, "view2.load_partial(0, k, a*b) + x", false, true),
        ROW(view1_element, "set_lane(l, view1[l]); x + P1", false, true),
        ROW(view2_get, "set_lane(l, view2.get(l)); P2 + x", false, true),
        ROW(view1_set, "view1.set(l, E1(a*b)); x + load", false, true),
        ROW(view2_assign, "view2[l] = E2(a*b); load + x", false, true),
        ROW(view1_store, "view1.store(0, a*b); x + load", false, true),
        ROW(soa1, "SoA<T, 1>.limb(0)[l] = a*b; x + load", false, true),
        ROW(soa2, "SoA<T, 2>.limb(0)[l] = a*b; load + x", false, true),
        ROW(soa1_element, "SoA<T, 1>[l] = E1(a*b); x + load", false, true),
        ROW(times, "x * (a*b)", false, false),
        ROW(times_rev, "(a*b) * x", false, false),
        ROW(times_assign, "x *= a*b", false, false),
        ROW(finite_times, "finite::mul(x, a*b)", false, false),
        ROW(less, "x < a*b", true, false),
        ROW(less_rev, "a*b < x", true, false),
        ROW(less_equal, "x <= a*b", true, false),
        ROW(less_equal_rev, "a*b <= x", true, false),
        ROW(equal, "x == a*b", true, false),
        ROW(not_equal, "a*b != x", true, false),
        ROW(p1_plus, "P1 x + a*b", false, true),
        ROW(p1_plus_rev, "a*b + P1 x", false, true),
        ROW(p1_minus, "P1 x - a*b", true, true),
        ROW(p1_rminus, "a*b - P1 x", true, true),
        ROW(p1_plus_assign, "P1 x += a*b", false, true),
        ROW(p1_minus_assign, "P1 x -= a*b", true, true),
        ROW(p1_broadcast, "P1 x + P1::broadcast(E1(a*b))", false, true),
        ROW(p1_load, "P1::load({a*b}) + P1 x", false, true),
        ROW(p1_times, "P1 x * (a*b)", false, false),
        ROW(p1_times_assign, "P1 x *= a*b", false, false),
        ROWK(kp_plus, "P1(a) * P1(b) + P1 x", false, 2),
        ROWK(kp_plus_rev, "P1 x + P1(a) * P1(b)", false, 2),
        ROWK(kp_minus, "P1 x - P1(a) * P1(b)", true, 2),
        ROWK(kp_plus_assign, "P1 x += P1(a) * P1(b)", false, 2),
        ROWK(kp_mixed, "x + P1(a) * P1(b)", false, 2),
        ROWK(kp_mixed_minus, "x - P1(a) * P1(b)", true, 2),
        ROWK(kp_program_add, "add(P1(a) * P1(b), x) by the program", false, 3),
        ROWK(kp_program_add_rev, "add(x, P1(a) * P1(b)) by the program", false, 3),
    };
    constexpr int n_forms = int(sizeof forms / sizeof forms[0]);
    long differ[n_forms] = {};
    unsigned lanes_seen[n_forms] = {};
    bool shown = false;
    // Leading limbs within a few units of the product, so that the sums cancel; 2^-30 and 2^-20 are
    // far below the precision of the product and above that of the limb.
    const T step = sizeof(T) == 8 ? T(0x1p-30) : T(0x1p-20);
    for (long i = 0; i < registers; ++i) {
        T a[W], b[W], p[W], one[W];
        P2<T> xm, xp;
        for (int l = 0; l < W; ++l) {
            a[l] = uniform<T>();
            b[l] = uniform<T>();
            p[l] = rounded(a[l], b[l]);
            one[l] = T(1);
            const T near = T(1) + T((i + l) % 7) * step;
            xm.set_lane(l, E2<T>(-p[l] * near));
            xp.set_lane(l, E2<T>(p[l] * near));
        }
        const int k = int(i % W);
        for (int f = 0; f < n_forms; ++f) {
            const P2<T>& x = forms[f].plus_x ? xp : xm;
            const P2<T> u = forms[f].in_place(x, a, b, k);
            const P2<T> v = forms[f].rounded(x, p, one, k);
            bool differs = false;
            for (int l = 0; l < W; ++l) {
                const E2<T> ul = u.lane(l), vl = v.lane(l);
                if (same_limb(ul.limb[0], vl.limb[0]) && same_limb(ul.limb[1], vl.limb[1])) continue;
                differs = true;
                lanes_seen[f] |= 1u << l;
                if (!shown) {
                    shown = true;
                    std::printf("  first difference: %s, %s, lane %d of %d: a = %a, b = %a, x = (%a, %a)\n"
                                "    product in place (%a, %a), rounded product %a: (%a, %a)\n",
                                forms[f].name, type, l, W, double(a[l]), double(b[l]), double(x.lane(l).limb[0]),
                                double(x.lane(l).limb[1]), double(ul.limb[0]), double(ul.limb[1]), double(p[l]),
                                double(vl.limb[0]), double(vl.limb[1]));
                }
            }
            differ[f] += differs;
        }
    }
    std::printf("Packed<%s, k> (%s, %d lanes), %ld registers per form:\n", type, form_name, W, registers);
    for (int f = 0; f < n_forms; ++f) {
        char seen[33] = {};
        for (int l = 0; l < W; ++l) seen[l] = (lanes_seen[f] >> l) & 1 ? char('0' + l % 10) : '.';
        static const char* const notes[] = {"", "   (multiplied or compared: no guard needed)",
                                            "   (the product of Packed<T, 1> into Kairn)",
                                            "   (the product of Packed<T, 1> added by the program)"};
        std::printf("  %-38s differs in %6ld of %ld, in lanes %s%s\n", forms[f].name, differ[f], registers, seen,
                    notes[forms[f].kind]);
        long* const count[] = {&totals.guarded, &totals.unguarded, &totals.kairn_product, &totals.program_add};
        *count[forms[f].kind] += differ[f];
    }
}

// The squares (SQUARE above): a in [1/2, 1), x within a few units of -RN(a a), the square in place
// against the rounded square. The registers that differ, printed and returned; no verdict.
template <class T>
long run_squares(const char* type, long registers) {
    constexpr int W = P1<T>::lanes;
    const Form<T> forms[] = {ROWK(sq_p1_plus, "P1 x + a*a", false, 0), ROWK(sq_plus, "x + a*a", false, 0)};
    const T step = sizeof(T) == 8 ? T(0x1p-30) : T(0x1p-20);
    long total = 0;
    for (const Form<T>& f : forms) {
        long differ = 0;
        for (long i = 0; i < registers; ++i) {
            T a[W], p[W], one[W];
            P2<T> x;
            for (int l = 0; l < W; ++l) {
                a[l] = uniform<T>();
                p[l] = rounded(a[l], a[l]);
                one[l] = T(1);
                x.set_lane(l, E2<T>(-p[l] * (T(1) + T((i + l) % 7) * step)));
            }
            const P2<T> u = f.in_place(x, a, a, 0), v = f.rounded(x, p, one, 0);
            bool differs = false;
            for (int l = 0; l < W; ++l) {
                const E2<T> ul = u.lane(l), vl = v.lane(l);
                differs = differs || !same_limb(ul.limb[0], vl.limb[0]) || !same_limb(ul.limb[1], vl.limb[1]);
            }
            differ += differs;
        }
        std::printf("  %-38s %-6s differs in %6ld of %ld   (a square of the program: reported only)\n", f.name, type,
                    differ, registers);
        total += differ;
    }
    return total;
}

}  // namespace

int main(int argc, char** argv) {
    const char* expect = argc == 5 && std::strcmp(argv[1], "--expect") == 0 ? argv[2] : "";
    const char* factor = argc == 5 && std::strcmp(argv[3], "--factor") == 0 ? argv[4] : "";
    const auto valid = [](const char* e) {
        return std::strcmp(e, "none") == 0 || std::strcmp(e, "some") == 0 || std::strcmp(e, "report") == 0;
    };
    if (!valid(expect) || !valid(factor)) {
        std::fprintf(stderr, "usage: boundary_packed --expect none|some|report --factor none|some|report\n");
        return 2;
    }
#ifdef KAIRN_TEST_UNGUARDED_COPY
    std::printf("against the copy of the headers without the guard\n");
#endif
    Totals totals;
    run<double>("double", 40000, totals);
    run<float>("float", 40000, totals);
    std::printf("the other factor a constant F the compiler sees (1, -1, 2), 20000 registers per form, type and F:\n");
    run_known<double>("double", 20000, totals);
    run_known<float>("float", 20000, totals);
    std::printf("a square of the program, a * a, whose guard a compiler may drop (no verdict), 20000 registers per form "
                "and type:\n");
    const long squares = run_squares<double>("double", 20000) + run_squares<float>("float", 20000);
    std::printf("forms that need the guard: %ld registers differ; forms that need none: %ld; with a known factor: %ld\n",
                totals.guarded, totals.unguarded, totals.known);
    std::printf("a square of the program: %ld registers differ%s\n", squares,
                squares ? ": this compiler dropped the guard of a square and fused it (reported, no verdict)" : "");
    std::printf("the product of Packed<T, 1> passed into Kairn: %ld registers differ; added by the program: %ld\n",
                totals.kairn_product, totals.program_add);
    if (std::strcmp(expect, "report") == 0 && totals.guarded == 0)
        std::printf("no form differs: this compiler and setting fused no product into Packed here, so this build "
                    "does not show that the guard is needed\n");
    bool ok = totals.unguarded == 0;
    if (std::strcmp(expect, "none") == 0) ok = ok && totals.guarded == 0 && totals.kairn_product == 0 &&
                                                 totals.program_add == 0;
    if (std::strcmp(expect, "some") == 0) ok = ok && totals.guarded > 0;
    if (std::strcmp(factor, "none") == 0) ok = ok && totals.known == 0;
    if (std::strcmp(factor, "some") == 0) ok = ok && totals.known > 0;
    std::printf("%s (expected: %s; with a known factor: %s)%s\n", ok ? "ok" : "FAILED", expect, factor,
                KAIRN_TEST_ZERO_SIGN_FREE ? " (a zero limb compared as a zero: MSVC)" : "");
    return ok ? 0 : 1;
}
