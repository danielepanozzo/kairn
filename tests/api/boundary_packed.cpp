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
// build: a product is fused only into an addition.
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
    static ALWAYS_INLINE void store(double* p, R a) { _mm256_storeu_pd(p, a); }
};
template <>
struct Program<float> {
    using R = __m256;
    static ALWAYS_INLINE R load(const float* p) { return _mm256_loadu_ps(p); }
    static ALWAYS_INLINE R mul(R a, R b) { return _mm256_mul_ps(a, b); }
    static ALWAYS_INLINE void store(float* p, R a) { _mm256_storeu_ps(p, a); }
};
#elif KAIRN_PACKED_FORM == KAIRN_PACKED_FORM_NEON
const char* const form_name = "NEON";
template <>
struct Program<double> {
    using R = float64x2_t;
    static ALWAYS_INLINE R load(const double* p) { return vld1q_f64(p); }
    static ALWAYS_INLINE R mul(R a, R b) { return vmulq_f64(a, b); }
    static ALWAYS_INLINE void store(double* p, R a) { vst1q_f64(p, a); }
};
template <>
struct Program<float> {
    using R = float32x4_t;
    static ALWAYS_INLINE R load(const float* p) { return vld1q_f32(p); }
    static ALWAYS_INLINE R mul(R a, R b) { return vmulq_f32(a, b); }
    static ALWAYS_INLINE void store(float* p, R a) { vst1q_f32(p, a); }
};
#else
const char* const form_name = "scalar, one lane";
template <class T>
struct Program {
    using R = T;
    static ALWAYS_INLINE R load(const T* p) { return *p; }
    static ALWAYS_INLINE R mul(R a, R b) { return a * b; }
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

template <class T>
using Fn = P2<T> (*)(const P2<T>&, const T*, const T*, int);

template <class T>
struct Form {
    const char* name;
    Fn<T> in_place, rounded;
    bool plus_x;       // x is +p, for the forms that subtract or negate the product; else -p
    bool needs_guard;  // false: multiplied or compared
};
#define ROW(NAME, TEXT, PLUS, GUARD) {TEXT, &NAME##_inline<T>, &NAME##_rounded<T>, PLUS, GUARD}

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
    long guarded = 0, unguarded = 0;
};

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
        std::printf("  %-36s differs in %6ld of %ld, in lanes %s%s\n", forms[f].name, differ[f], registers, seen,
                    forms[f].needs_guard ? "" : "   (multiplied or compared: no guard needed)");
        (forms[f].needs_guard ? totals.guarded : totals.unguarded) += differ[f];
    }
}

}  // namespace

int main(int argc, char** argv) {
    const char* expect = argc == 3 && std::strcmp(argv[1], "--expect") == 0 ? argv[2] : "";
    if (std::strcmp(expect, "none") != 0 && std::strcmp(expect, "some") != 0 && std::strcmp(expect, "report") != 0) {
        std::fprintf(stderr, "usage: boundary_packed --expect none|some|report\n");
        return 2;
    }
#ifdef KAIRN_TEST_UNGUARDED_COPY
    std::printf("against the copy of the headers without the guard\n");
#endif
    Totals totals;
    run<double>("double", 40000, totals);
    run<float>("float", 40000, totals);
    std::printf("forms that need the guard: %ld registers differ; forms that need none: %ld\n", totals.guarded,
                totals.unguarded);
    if (std::strcmp(expect, "report") == 0 && totals.guarded == 0)
        std::printf("no form differs: this compiler and setting fused no product into Packed here, so this build "
                    "does not show that the guard is needed\n");
    bool ok = totals.unguarded == 0;
    if (std::strcmp(expect, "none") == 0) ok = ok && totals.guarded == 0;
    if (std::strcmp(expect, "some") == 0) ok = ok && totals.guarded > 0;
    std::printf("%s (expected: %s)%s\n", ok ? "ok" : "FAILED", expect,
                KAIRN_TEST_ZERO_SIGN_FREE ? " (a zero limb compared as a zero: MSVC)" : "");
    return ok ? 0 : 1;
}
