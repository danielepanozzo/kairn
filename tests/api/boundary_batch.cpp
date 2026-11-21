// boundary.cpp for the functions on arrays (batch.hpp): an array that the program fills with
// products in the same function and passes straight into a sum, a map or axpy must give the same
// result as the same function on the array of those products rounded first. The loops on arrays of
// the program are the _entry loops, whose steps guard each limb they add (rule R3: a + 0 in the
// scalar loops, the form's intrinsic in the packed ones), so that a compiler that inlines the loop
// and forwards the stores cannot fuse a product into the loop's first addition. Each form is
// computed twice, with the products written in place into arrays of the function, and with
// honestly rounded products (through a volatile, in a function that is not inlined), on elements
// chosen so that the additions cancel, and the results are compared bit for bit, every limb (a zero
// as a zero under MSVC, as boundary_packed.cpp says).
//
//   boundary_batch --expect none     every form agrees (the headers as they are)
//   boundary_batch --expect some     built against the copy of the headers without the guard
//                                    (tests/api/CMakeLists.txt), on a compiler and setting that
//                                    fuse: some form must differ
//   boundary_batch --expect report   prints the counts only, and says so if nothing differs
//
// The forms whose array is only multiplied or compared (dot, scale, mul_pow2, the x of axpy, conv,
// norm_upper) need no guard and must agree in every build.
#include <kairn/batch.hpp>

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

// The length of every array: two registers and a tail, whatever the form.
constexpr int N = 2 * kairn::Packed<float, 1>::lanes + 3;
// The most limbs a form writes: a map of two limbs, or a convolution of N and 2 coefficients.
constexpr int OUT = 2 * (N + 1) + 1;

template <class T>
NOINLINE T rounded(T a, T b) {
    volatile T p = a * b;
    return p;
}

// The products in place, from the factors a and b, or the rounded products, given in a.
template <class T>
struct InPlace {
    static ALWAYS_INLINE T one(const T* a, const T* b, int i) { return a[i] * b[i]; }
};
template <class T>
struct Rounded {
    static ALWAYS_INLINE T one(const T* a, const T*, int i) { return a[i]; }
};

template <int K, class T>
ALWAYS_INLINE kairn::SoAView<const T, K> view(const T* h, const T* l, int n) {
    if constexpr (K == 1) {
        (void)l;
        return kairn::SoAView<const T, 1>(h, std::size_t(n));
    } else {
        return kairn::SoAView<const T, 2>(h, l, std::size_t(n));
    }
}
template <int K, class T>
ALWAYS_INLINE kairn::SoAView<T, K> out_view(T* h, T* l, int n) {
    if constexpr (K == 1) {
        (void)l;
        return kairn::SoAView<T, 1>(h, std::size_t(n));
    } else {
        return kairn::SoAView<T, 2>(h, l, std::size_t(n));
    }
}
template <class T, int K>
ALWAYS_INLINE void put(T* out, const kairn::Reduction<kairn::Expansion<T, K>>& r) {
    for (int j = 0; j < K; ++j) out[j] = r.value.limb[j];
    out[K] = r.finite ? T(1) : T(0);
}

// A form: its body, with c the cancelling elements (c[i] within a few units of -(a[i] b[i])), the
// factors in a and b, and the result written to out. NAME_inline and NAME_rounded are the two ways,
// each a function that is not inlined, so that the products of the first are in the same function
// as the call.
#define FORM(NAME, ...)                                                                                   \
    template <class T, class M>                                                                           \
    ALWAYS_INLINE void NAME##_body([[maybe_unused]] const T* c, [[maybe_unused]] const T* a,              \
                                   [[maybe_unused]] const T* b, [[maybe_unused]] T* out) {                \
        __VA_ARGS__                                                                                       \
    }                                                                                                     \
    template <class T>                                                                                    \
    NOINLINE void NAME##_inline(const T* c, const T* a, const T* b, T* out) {                             \
        NAME##_body<T, InPlace<T>>(c, a, b, out);                                                         \
    }                                                                                                     \
    template <class T>                                                                                    \
    NOINLINE void NAME##_rounded(const T* c, const T* a, const T* b, T* out) {                            \
        NAME##_body<T, Rounded<T>>(c, a, b, out);                                                         \
    }

// Products and cancelling elements in turn, into one array (a sum), and for two limbs a zero tail.
#define MIXED(s, t)                                       \
    T s[N], t[N];                                         \
    for (int i = 0; i < N; ++i) {                         \
        s[i] = i % 2 ? c[i / 2] : M::one(a, b, i / 2);    \
        t[i] = T(0);                                      \
    }
// The products alone, into an array, with a zero tail.
#define PRODUCTS(s, t)                                    \
    T s[N], t[N];                                         \
    for (int i = 0; i < N; ++i) {                         \
        s[i] = M::one(a, b, i);                           \
        t[i] = T(0);                                      \
    }
#define CANCEL(K) view<K>(c, zero, N)

// Sums of an array that holds the products.
FORM(sum1, MIXED(s, t) put<T, 1>(out, kairn::sum(view<1>(s, t, N)));)
FORM(sum2, MIXED(s, t) put<T, 2>(out, kairn::sum(view<2>(s, t, N)));)
FORM(sum1_seq, MIXED(s, t) put<T, 1>(out, kairn::sum(view<1>(s, t, N), kairn::sequential));)
FORM(sum2_seq, MIXED(s, t) put<T, 2>(out, kairn::sum(view<2>(s, t, N), kairn::sequential));)
FORM(sum_fast2, MIXED(s, t) put<T, 2>(out, kairn::sum_fast(view<2>(s, t, N)));)
FORM(sum_fast2_seq, MIXED(s, t) put<T, 2>(out, kairn::sum_fast(view<2>(s, t, N), kairn::sequential));)
// Maps whose operand that is added holds the products: x of add and sub, y of sub and axpy.
#define MAP(K, CALL)                                                       \
    PRODUCTS(s, t) [[maybe_unused]] const T zero[N] = {};                  \
    T zh[N], zl[N];                                                        \
    const auto z = out_view<K>(zh, zl, N);                                 \
    const bool f = CALL;                                                   \
    for (int i = 0; i < N; ++i) {                                          \
        out[i] = zh[i];                                                    \
        out[N + i] = K == 2 ? zl[i] : T(0);                                \
    }                                                                      \
    out[2 * N] = f ? T(1) : T(0);
FORM(add1, MAP(1, kairn::add(view<1>(s, t, N), CANCEL(1), z)))
FORM(add2, MAP(2, kairn::add(view<2>(s, t, N), CANCEL(2), z)))
FORM(add1_y, MAP(1, kairn::add(CANCEL(1), view<1>(s, t, N), z)))
FORM(add2_y, MAP(2, kairn::add(CANCEL(2), view<2>(s, t, N), z)))
FORM(sub1, MAP(1, kairn::sub(CANCEL(1), view<1>(s, t, N), z)))
FORM(sub2, MAP(2, kairn::sub(CANCEL(2), view<2>(s, t, N), z)))
FORM(axpy1, MAP(1, kairn::axpy(T(-1), CANCEL(1), view<1>(s, t, N), z)))
FORM(axpy2_1, MAP(2, kairn::axpy(T(-1), CANCEL(2), view<2>(s, t, N), z)))
FORM(axpy2, MAP(2, kairn::axpy(kairn::Expansion<T, 2>(T(-1)), CANCEL(2), view<2>(s, t, N), z)))
// Only multiplied or compared: no guard needed.
FORM(dot1, PRODUCTS(s, t) const T zero[N] = {}; T ones[N];
     for (int i = 0; i < N; ++i) ones[i] = T(1);
     put<T, 1>(out, kairn::dot(view<1>(s, t, N), view<1>(ones, zero, N)));)
FORM(dot2, PRODUCTS(s, t) const T zero[N] = {}; T ones[N];
     for (int i = 0; i < N; ++i) ones[i] = T(1);
     put<T, 2>(out, kairn::dot(view<2>(s, t, N), view<2>(ones, zero, N)));)
FORM(scale1, MAP(1, kairn::scale(view<1>(s, t, N), T(3), z)))
FORM(scale2, MAP(2, kairn::scale(view<2>(s, t, N), T(3), z)))
FORM(mul_pow2_2, MAP(2, kairn::mul_pow2(view<2>(s, t, N), T(0.5), z)))
FORM(axpy2_x, MAP(2, kairn::axpy(T(3), view<2>(s, t, N), CANCEL(2), z)))
FORM(norm2, PRODUCTS(s, t) const kairn::Reduction<T> r = kairn::norm_upper(view<2>(s, t, N));
     out[0] = r.value; out[1] = r.finite ? T(1) : T(0);)
FORM(conv2, PRODUCTS(s, t) const T zero[N] = {}; T ones[2] = {T(1), T(1)}; T z2[2] = {T(0), T(0)};
     T zh[N + 1], zl[N + 1];
     const bool f = kairn::conv(view<2>(s, t, N), view<2>(ones, z2, 2), out_view<2>(zh, zl, N + 1));
     for (int i = 0; i <= N; ++i) { out[i] = zh[i]; out[N + 1 + i] = zl[i]; }
     out[2 * N + 2] = f ? T(1) : T(0); (void)zero;)

template <class T>
using Fn = void (*)(const T*, const T*, const T*, T*);
template <class T>
struct Form {
    const char* name;
    Fn<T> in_place, rounded;
    bool needs_guard;  // false: multiplied or compared
};
#define ROW(NAME, TEXT, GUARD) {TEXT, &NAME##_inline<T>, &NAME##_rounded<T>, GUARD}

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
void run(const char* type, long rounds, Totals& totals) {
    const Form<T> forms[] = {
        ROW(sum1, "sum(SoAView<T, 1>{a*b, c, ...})", true),
        ROW(sum2, "sum(SoAView<T, 2>{a*b, c, ...}, {0})", true),
        ROW(sum1_seq, "sum(.. 1 limb .., sequential)", true),
        ROW(sum2_seq, "sum(.. 2 limbs .., sequential)", true),
        ROW(sum_fast2, "sum_fast(.. 2 limbs ..)", true),
        ROW(sum_fast2_seq, "sum_fast(.. 2 limbs .., sequential)", true),
        ROW(add1, "add({a*b}, c, z)", true),
        ROW(add2, "add({a*b}, c, z), 2 limbs", true),
        ROW(add1_y, "add(c, {a*b}, z)", true),
        ROW(add2_y, "add(c, {a*b}, z), 2 limbs", true),
        ROW(sub1, "sub(c, {a*b}, z)", true),
        ROW(sub2, "sub(c, {a*b}, z), 2 limbs", true),
        ROW(axpy1, "axpy(-1, c, {a*b}, z)", true),
        ROW(axpy2_1, "axpy(-1, c, {a*b}, z), 2 limbs", true),
        ROW(axpy2, "axpy(E2(-1), c, {a*b}, z)", true),
        ROW(dot1, "dot({a*b}, {1})", false),
        ROW(dot2, "dot({a*b}, {1}), 2 limbs", false),
        ROW(scale1, "scale({a*b}, 3, z)", false),
        ROW(scale2, "scale({a*b}, 3, z), 2 limbs", false),
        ROW(mul_pow2_2, "mul_pow2({a*b}, 1/2, z)", false),
        ROW(axpy2_x, "axpy(3, {a*b}, c, z)", false),
        ROW(norm2, "norm_upper({a*b})", false),
        ROW(conv2, "conv({a*b}, {1, 1}, z)", false),
    };
    constexpr int n_forms = int(sizeof forms / sizeof forms[0]);
    long differ[n_forms] = {};
    bool shown = false;
    const T step = sizeof(T) == 8 ? T(0x1p-30) : T(0x1p-20);
    for (long r = 0; r < rounds; ++r) {
        T a[N], b[N], p[N], one[N], c[N];
        for (int i = 0; i < N; ++i) {
            a[i] = uniform<T>();
            b[i] = uniform<T>();
            p[i] = rounded(a[i], b[i]);
            one[i] = T(1);
        }
        // c[i] cancels the product of the element before it in a sum, and the product of the same
        // index in a map.
        for (int i = 0; i < N; ++i) c[i] = -p[i] * (T(1) + T((r + i) % 7) * step);
        for (int f = 0; f < n_forms; ++f) {
            T u[OUT] = {}, v[OUT] = {};
            forms[f].in_place(c, a, b, u);
            forms[f].rounded(c, p, one, v);
            bool differs = false;
            for (int i = 0; i < OUT; ++i) {
                if (same_limb(u[i], v[i])) continue;
                differs = true;
                if (!shown) {
                    shown = true;
                    std::printf("  first difference: %s, %s, limb %d of the result: %a with the products in place, "
                                "%a with them rounded\n",
                                forms[f].name, type, i, double(u[i]), double(v[i]));
                }
            }
            differ[f] += differs;
        }
    }
    std::printf("the functions on arrays of %s (%d elements, Packed of %d lanes), %ld rounds per form:\n", type, N,
                kairn::Packed<T, 1>::lanes, rounds);
    for (int f = 0; f < n_forms; ++f) {
        std::printf("  %-40s differs in %6ld of %ld%s\n", forms[f].name, differ[f], rounds,
                    forms[f].needs_guard ? "" : "   (multiplied or compared: no guard needed)");
        (forms[f].needs_guard ? totals.guarded : totals.unguarded) += differ[f];
    }
}

}  // namespace

int main(int argc, char** argv) {
    const char* expect = argc == 3 && std::strcmp(argv[1], "--expect") == 0 ? argv[2] : "";
    if (std::strcmp(expect, "none") != 0 && std::strcmp(expect, "some") != 0 && std::strcmp(expect, "report") != 0) {
        std::fprintf(stderr, "usage: boundary_batch --expect none|some|report\n");
        return 2;
    }
#ifdef KAIRN_TEST_UNGUARDED_COPY
    std::printf("against the copy of the headers without the guard\n");
#endif
    Totals totals;
    run<double>("double", 20000, totals);
    run<float>("float", 20000, totals);
    std::printf("forms that need the guard: %ld rounds differ; forms that need none: %ld\n", totals.guarded,
                totals.unguarded);
    if (std::strcmp(expect, "report") == 0 && totals.guarded == 0)
        std::printf("no form differs: this compiler and setting fused no product into the loops here, so this build "
                    "does not show that the guard is needed\n");
    bool ok = totals.unguarded == 0;
    if (std::strcmp(expect, "none") == 0) ok = ok && totals.guarded == 0;
    if (std::strcmp(expect, "some") == 0) ok = ok && totals.guarded > 0;
    std::printf("%s (expected: %s)%s\n", ok ? "ok" : "FAILED", expect,
                KAIRN_TEST_ZERO_SIGN_FREE ? " (a zero limb compared as a zero: MSVC)" : "");
    return ok ? 0 : 1;
}
