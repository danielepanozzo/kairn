// boundary.cpp for the functions on arrays (batch.hpp) and the accumulator (accumulator.hpp): an
// array that the program fills with products in the same function and passes straight into a sum,
// a map or axpy, or a product it computes and adds to an accumulator or gives Accumulator::from_state
// as its state, must give the same result as the same function on those products rounded first. The loops on arrays of
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
// norm_upper) need no guard by the generator's rule R3, and must agree in every build: on the other
// factor of a product read at run time (from a volatile), which the compiler cannot know.
//
// A third kind, --factor none|some|report (rule R3, the factors of a fused operation:
// docs/developer/architecture.md): every function that takes an array or a value of T from the
// program as a factor, with the other factor a constant F (1, -1, 2) the compiler sees (an array of
// F the function fills, a scalar F). A compiler that sees F = 1 rewrites fma(x, 1, s) as x + s and
// may fuse the program's product into that addition: Clang 18 on x86-64 and Apple clang 21 under
// -ffp-contract=fast did so in the dot product of one limb and Apple clang 21 in the accumulator's
// add_product of one limb, whose loops and kernel now guard both factors (dot_1_entry,
// acc_mul_entry_1). With the headers as they are every form must agree (--factor none); the copy
// without the guard requires a difference where a compiler was measured to fuse (--factor some,
// tests/api/CMakeLists.txt) and reports elsewhere.
//
//   boundary_batch --expect E --factor none|some|report
//
// A fourth kind: arrays filled with the products of Packed<T, 1> (x * y, the opaque product
// fma(x, y, +0) of kernel scale_step_1), W at a time, then passed into a map or a sum that adds
// them. With the guard they must agree (--expect none); against the copy without it they are
// counted and reported only: the opaque product alone is not a product a compiler can fuse, and
// none measured did.
#include <kairn/accumulator.hpp>
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
// 1, read at run time: a factor the compiler does not know.
template <class T>
NOINLINE T run_time_one() {
    volatile T one = T(1);
    return one;
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
ALWAYS_INLINE void put_acc(T* out, const kairn::Accumulator<T, K>& acc) {
    for (int j = 0; j < K; ++j) out[j] = acc.running_sum().limb[j];
    out[K] = acc.magnitudes();
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
FORM(sum1_seq, MIXED(s, t) put<T, 1>(out, kairn::sum(kairn::sequential, view<1>(s, t, N)));)
FORM(sum2_seq, MIXED(s, t) put<T, 2>(out, kairn::sum(kairn::sequential, view<2>(s, t, N)));)
FORM(sum_fast2, MIXED(s, t) put<T, 2>(out, kairn::sum_fast(view<2>(s, t, N)));)
FORM(sum_fast2_seq, MIXED(s, t) put<T, 2>(out, kairn::sum_fast(kairn::sequential, view<2>(s, t, N)));)
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
// Only multiplied or compared: no guard needed. The other factor of a dot product is read at run
// time: a 1 the compiler does not know.
FORM(dot1, MIXED(s, t) const T zero[N] = {}; T ones[N];
     for (int i = 0; i < N; ++i) ones[i] = run_time_one<T>();
     put<T, 1>(out, kairn::dot(view<1>(s, t, N), view<1>(ones, zero, N)));)
FORM(dot1_seq, MIXED(s, t) const T zero[N] = {}; T ones[N];
     for (int i = 0; i < N; ++i) ones[i] = run_time_one<T>();
     put<T, 1>(out, kairn::dot(kairn::sequential, view<1>(s, t, N), view<1>(ones, zero, N)));)
FORM(dot2, MIXED(s, t) const T zero[N] = {}; T ones[N];
     for (int i = 0; i < N; ++i) ones[i] = run_time_one<T>();
     put<T, 2>(out, kairn::dot(view<2>(s, t, N), view<2>(ones, zero, N)));)
// The other factor a constant F the compiler sees (1, -1 or 2: an array of F the function fills,
// a scalar F): the third kind, KNOWN (rule R3, the factors of a fused operation). FORMK is FORM
// with F as a template parameter; ARRAYSK makes s (the products and the cancelling elements in
// turn, as MIXED), r (the cancelling element first, then the product), t a zero tail, fs every
// element F, and cf the cancelling elements times F, so that F p + c F cancels too.
#define FORMK(NAME, ...)                                                                                  \
    template <class T, int C, class M>                                                                    \
    ALWAYS_INLINE void NAME##_body([[maybe_unused]] const T* c, [[maybe_unused]] const T* a,              \
                                   [[maybe_unused]] const T* b, [[maybe_unused]] T* out) {                \
        constexpr T F = C == 0 ? T(1) : C == 1 ? T(-1) : T(2);                                            \
        __VA_ARGS__                                                                                       \
    }                                                                                                     \
    template <class T, int C>                                                                             \
    NOINLINE void NAME##_inline(const T* c, const T* a, const T* b, T* out) {                             \
        NAME##_body<T, C, InPlace<T>>(c, a, b, out);                                                      \
    }                                                                                                     \
    template <class T, int C>                                                                             \
    NOINLINE void NAME##_rounded(const T* c, const T* a, const T* b, T* out) {                            \
        NAME##_body<T, C, Rounded<T>>(c, a, b, out);                                                      \
    }
#define ARRAYSK                                                                   \
    [[maybe_unused]] T s[N], r[N], t[N], fs[N], cf[N];                           \
    [[maybe_unused]] const T zero[N] = {};                                       \
    for (int i = 0; i < N; ++i) {                                                \
        s[i] = i % 2 ? c[i / 2] : M::one(a, b, i / 2);                           \
        r[i] = i % 2 ? M::one(a, b, i / 2) : c[i / 2];                           \
        t[i] = T(0);                                                             \
        fs[i] = F;                                                               \
        cf[i] = c[i] * F;                                                        \
    }
// A map of the products px with the cancelling elements cf, into z.
#define MAPK(K, CALL)                                                             \
    ARRAYSK [[maybe_unused]] T px[N];                                             \
    for (int i = 0; i < N; ++i) px[i] = M::one(a, b, i);                          \
    T zh[N], zl[N];                                                               \
    const auto z = out_view<K>(zh, zl, N);                                        \
    const bool f = CALL;                                                          \
    for (int i = 0; i < N; ++i) {                                                 \
        out[i] = zh[i];                                                           \
        out[N + i] = K == 2 ? zl[i] : T(0);                                       \
    }                                                                             \
    out[2 * N] = f ? T(1) : T(0);
#define CONVK(K, X, Y)                                                            \
    ARRAYSK T fl[2] = {F, F}, f0[2] = {T(0), T(0)}, zh[N + 1], zl[N + 1];         \
    (void)fl, (void)f0;                                                           \
    const bool f = kairn::conv(X, Y, out_view<K>(zh, zl, N + 1));                 \
    for (int i = 0; i <= N; ++i) {                                                \
        out[i] = zh[i];                                                           \
        out[N + 1 + i] = K == 2 ? zl[i] : T(0);                                   \
    }                                                                             \
    out[2 * N + 2] = f ? T(1) : T(0);
FORMK(dot1_k, ARRAYSK put<T, 1>(out, kairn::dot(view<1>(s, t, N), view<1>(fs, zero, N)));)
FORMK(dot1_seq_k, ARRAYSK put<T, 1>(out, kairn::dot(kairn::sequential, view<1>(s, t, N), view<1>(fs, zero, N)));)
FORMK(dot1_rev_k, ARRAYSK put<T, 1>(out, kairn::dot(view<1>(fs, zero, N), view<1>(s, t, N)));)
FORMK(dot1_rev_seq_k, ARRAYSK put<T, 1>(out, kairn::dot(kairn::sequential, view<1>(fs, zero, N), view<1>(s, t, N)));)
FORMK(dot2_k, ARRAYSK put<T, 2>(out, kairn::dot(view<2>(s, t, N), view<2>(fs, zero, N)));)
FORMK(dot2_seq_k, ARRAYSK put<T, 2>(out, kairn::dot(kairn::sequential, view<2>(s, t, N), view<2>(fs, zero, N)));)
FORMK(dot2_rev_k, ARRAYSK put<T, 2>(out, kairn::dot(view<2>(fs, zero, N), view<2>(s, t, N)));)
FORMK(conv1_k, CONVK(1, view<1>(r, t, N), view<1>(fl, f0, 2)))
FORMK(conv1_rev_k, CONVK(1, view<1>(fl, f0, 2), view<1>(r, t, N)))
FORMK(conv2_k, CONVK(2, view<2>(r, t, N), view<2>(fl, f0, 2)))
FORMK(axpy1_k, MAPK(1, kairn::axpy(F, view<1>(px, t, N), view<1>(cf, zero, N), z)))
FORMK(axpy21_k, MAPK(2, kairn::axpy(F, view<2>(px, t, N), view<2>(cf, zero, N), z)))
FORMK(axpy2_k, MAPK(2, kairn::axpy(kairn::Expansion<T, 2>(F), view<2>(px, t, N), view<2>(cf, zero, N), z)))
FORMK(axpy1_a_k, MAPK(1, kairn::axpy(M::one(a, b, 0), view<1>(fs, zero, N), view<1>(cf, zero, N), z)))
FORMK(scale1_k, MAPK(1, kairn::scale(view<1>(px, t, N), F, z)))
FORMK(scale2_k, MAPK(2, kairn::scale(view<2>(px, t, N), F, z)))
FORMK(scale1_a_k, MAPK(1, kairn::scale(view<1>(fs, zero, N), M::one(a, b, 0), z)))
FORMK(mul_pow2_1_k, MAPK(1, kairn::mul_pow2(view<1>(px, t, N), C == 1 ? T(0.5) : F, z)))
FORMK(mul_pow2_2_k, MAPK(2, kairn::mul_pow2(view<2>(px, t, N), C == 1 ? T(0.5) : F, z)))
FORMK(acc_product1_k, kairn::Accumulator<T, 1> acc;
      for (int i = 0; i < N / 2; ++i) { acc.add_product(M::one(a, b, i), F); acc.add(c[i] * F); } put_acc(out, acc);)
FORMK(acc_product1_rev_k, kairn::Accumulator<T, 1> acc;
      for (int i = 0; i < N / 2; ++i) { acc.add_product(F, M::one(a, b, i)); acc.add(c[i] * F); } put_acc(out, acc);)
FORMK(acc_product1_once_k, kairn::Accumulator<T, 1> acc; acc.add(c[0] * F); acc.add_product(M::one(a, b, 0), F);
      put_acc(out, acc);)
FORMK(acc_product2_k, kairn::Accumulator<T, 2> acc;
      for (int i = 0; i < N / 2; ++i) { acc.add_product(M::one(a, b, i), F); acc.add(c[i] * F); } put_acc(out, acc);)
FORMK(acc_product2_rev_k, kairn::Accumulator<T, 2> acc;
      for (int i = 0; i < N / 2; ++i) { acc.add_product(F, M::one(a, b, i)); acc.add(c[i] * F); } put_acc(out, acc);)
// The accumulator: products added (guarded by acc_add_k), and products times a factor read at run
// time added with add_product (only multiplied), with the cancelling elements between them.
FORM(acc_add1, kairn::Accumulator<T, 1> acc; for (int i = 0; i < N / 2; ++i) { acc.add(M::one(a, b, i)); acc.add(c[i]); }
     put_acc(out, acc);)
FORM(acc_add2, kairn::Accumulator<T, 2> acc; for (int i = 0; i < N / 2; ++i) { acc.add(M::one(a, b, i)); acc.add(c[i]); }
     put_acc(out, acc);)
// from_state: a product as the running sum (one limb) and as the sum of magnitudes, which the
// accumulator's kernels then add to (rule R3: from_state guards them, the leading limb of make_2).
FORM(acc_from_state1, kairn::Accumulator<T, 1> acc =
         kairn::Accumulator<T, 1>::from_state(kairn::Expansion<T, 1>(M::one(a, b, 0)), M::one(a, b, 1), 1);
     acc.add(c[0]); acc.add(c[1]); put_acc(out, acc);)
FORM(acc_from_state2, kairn::Accumulator<T, 2> acc =
         kairn::Accumulator<T, 2>::from_state(kairn::Expansion<T, 2>(T(0.75)), M::one(a, b, 0), 1);
     acc.add(c[0]); acc.add(c[1]); put_acc(out, acc);)
FORM(acc_product1, kairn::Accumulator<T, 1> acc; const T one = run_time_one<T>();
     for (int i = 0; i < N / 2; ++i) { acc.add_product(M::one(a, b, i), one); acc.add(c[i]); } put_acc(out, acc);)
FORM(acc_product2, kairn::Accumulator<T, 2> acc; const T one = run_time_one<T>();
     for (int i = 0; i < N / 2; ++i) { acc.add_product(M::one(a, b, i), one); acc.add(c[i]); } put_acc(out, acc);)
FORM(scale1, MAP(1, kairn::scale(view<1>(s, t, N), T(3), z)))
FORM(scale2, MAP(2, kairn::scale(view<2>(s, t, N), T(3), z)))
FORM(mul_pow2_2, MAP(2, kairn::mul_pow2(view<2>(s, t, N), T(0.5), z)))
FORM(axpy2_x, MAP(2, kairn::axpy(T(3), view<2>(s, t, N), CANCEL(2), z)))
// The products of Packed<T, 1>, x * y (scale_step_1, the opaque product) of the factors loaded W at a
// time, stored into the array that a function on arrays then adds (with the rounded products the
// factors are p and 1, and p 1 is p): the fourth kind, which must agree with the guard and is
// reported without it.
#define KPRODUCTS(s, t)                                                                           \
    T s[N], t[N];                                                                                 \
    for (int i = 0; i < N; i += kairn::Packed<T, 1>::lanes) {                                     \
        const int n = N - i < kairn::Packed<T, 1>::lanes ? N - i : kairn::Packed<T, 1>::lanes;    \
        (kairn::Packed<T, 1>::load_partial(a + i, n) * kairn::Packed<T, 1>::load_partial(b + i, n)) \
            .store_partial(s + i, n);                                                             \
    }                                                                                             \
    for (int i = 0; i < N; ++i) t[i] = T(0);
#define MAPKP(K, CALL)                                                     \
    KPRODUCTS(s, t) [[maybe_unused]] const T zero[N] = {};                 \
    T zh[N], zl[N];                                                        \
    const auto z = out_view<K>(zh, zl, N);                                 \
    const bool f = CALL;                                                   \
    for (int i = 0; i < N; ++i) {                                          \
        out[i] = zh[i];                                                    \
        out[N + i] = K == 2 ? zl[i] : T(0);                                \
    }                                                                      \
    out[2 * N] = f ? T(1) : T(0);
FORM(add1_kp, MAPKP(1, kairn::add(view<1>(s, t, N), CANCEL(1), z)))
FORM(add1_y_kp, MAPKP(1, kairn::add(CANCEL(1), view<1>(s, t, N), z)))
FORM(sub1_kp, MAPKP(1, kairn::sub(CANCEL(1), view<1>(s, t, N), z)))
FORM(add2_kp, MAPKP(2, kairn::add(view<2>(s, t, N), CANCEL(2), z)))
FORM(sum1_kp, KPRODUCTS(kp, t) T s[N]; for (int i = 0; i < N; ++i) s[i] = i % 2 ? c[i / 2] : kp[i / 2];
     put<T, 1>(out, kairn::sum(view<1>(s, t, N)));)
FORM(sum2_kp, KPRODUCTS(kp, t) T s[N]; for (int i = 0; i < N; ++i) s[i] = i % 2 ? c[i / 2] : kp[i / 2];
     put<T, 2>(out, kairn::sum(view<2>(s, t, N)));)
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
    // 0: needs the guard; 1: multiplied or compared; 2: multiplied by a constant the compiler sees;
    // 3: the products of Packed<T, 1>.
    int kind;
};
#define ROW(NAME, TEXT, GUARD) {TEXT, &NAME##_inline<T>, &NAME##_rounded<T>, (GUARD) ? 0 : 1}
#define ROWKP(NAME, TEXT) {TEXT, &NAME##_inline<T>, &NAME##_rounded<T>, 3}
#define KNOWN(NAME, TEXT)                                              \
    {TEXT ", F = 1", &NAME##_inline<T, 0>, &NAME##_rounded<T, 0>, 2},  \
    {TEXT ", F = -1", &NAME##_inline<T, 1>, &NAME##_rounded<T, 1>, 2}, \
    {TEXT ", F = 2", &NAME##_inline<T, 2>, &NAME##_rounded<T, 2>, 2}

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
    long guarded = 0, unguarded = 0, known = 0, kairn_product = 0;
};

template <class T>
void run(const char* type, long rounds, Totals& totals) {
    const Form<T> forms[] = {
        ROW(sum1, "sum(SoAView<T, 1>{a*b, c, ...})", true),
        ROW(sum2, "sum(SoAView<T, 2>{a*b, c, ...}, {0})", true),
        ROW(sum1_seq, "sum(sequential, .. 1 limb ..)", true),
        ROW(sum2_seq, "sum(sequential, .. 2 limbs ..)", true),
        ROW(sum_fast2, "sum_fast(.. 2 limbs ..)", true),
        ROW(sum_fast2_seq, "sum_fast(sequential, .. 2 limbs ..)", true),
        ROW(add1, "add({a*b}, c, z)", true),
        ROW(add2, "add({a*b}, c, z), 2 limbs", true),
        ROW(add1_y, "add(c, {a*b}, z)", true),
        ROW(add2_y, "add(c, {a*b}, z), 2 limbs", true),
        ROW(sub1, "sub(c, {a*b}, z)", true),
        ROW(sub2, "sub(c, {a*b}, z), 2 limbs", true),
        ROW(axpy1, "axpy(-1, c, {a*b}, z)", true),
        ROW(axpy2_1, "axpy(-1, c, {a*b}, z), 2 limbs", true),
        ROW(axpy2, "axpy(E2(-1), c, {a*b}, z)", true),
        ROW(acc_add1, "acc.add(a*b), 1 limb", true),
        ROW(acc_add2, "acc.add(a*b), 2 limbs", true),
        ROW(acc_from_state1, "Accumulator<T, 1>::from_state(a*b, c*d, 1), then add", true),
        ROW(acc_from_state2, "Accumulator<T, 2>::from_state(s, a*b, 1), then add", true),
        ROW(dot1, "dot({a*b, c, ...}, {1})", false),
        ROW(dot1_seq, "dot(sequential, {a*b, c, ...}, {1})", false),
        ROW(dot2, "dot({a*b, c, ...}, {1}), 2 limbs", false),
        ROW(scale1, "scale({a*b}, 3, z)", false),
        ROW(scale2, "scale({a*b}, 3, z), 2 limbs", false),
        ROW(mul_pow2_2, "mul_pow2({a*b}, 1/2, z)", false),
        ROW(axpy2_x, "axpy(3, {a*b}, c, z)", false),
        ROW(norm2, "norm_upper({a*b})", false),
        ROW(conv2, "conv({a*b}, {1, 1}, z)", false),
        ROW(acc_product1, "acc.add_product(a*b, 1), 1 limb", false),
        ROW(acc_product2, "acc.add_product(a*b, 1), 2 limbs", false),
        ROWKP(add1_kp, "add({P1(a) * P1(b)}, c, z)"),
        ROWKP(add1_y_kp, "add(c, {P1(a) * P1(b)}, z)"),
        ROWKP(sub1_kp, "sub(c, {P1(a) * P1(b)}, z)"),
        ROWKP(add2_kp, "add({P1(a) * P1(b)}, c, z), 2 limbs"),
        ROWKP(sum1_kp, "sum({P1(a) * P1(b), c, ...})"),
        ROWKP(sum2_kp, "sum({P1(a) * P1(b), c, ...}, {0})"),
        KNOWN(dot1_k, "dot({a*b, c, ...}, {F})"),
        KNOWN(dot1_seq_k, "dot(sequential, {a*b, c, ...}, {F})"),
        KNOWN(dot1_rev_k, "dot({F}, {a*b, c, ...})"),
        KNOWN(dot1_rev_seq_k, "dot(sequential, {F}, {a*b, c, ...})"),
        KNOWN(dot2_k, "dot({a*b, c, ...}, {F}), 2 limbs"),
        KNOWN(dot2_seq_k, "dot(sequential, .., {F}), 2 limbs"),
        KNOWN(dot2_rev_k, "dot({F}, {a*b, c, ...}), 2 limbs"),
        KNOWN(conv1_k, "conv({c, a*b, ...}, {F, F}, z)"),
        KNOWN(conv1_rev_k, "conv({F, F}, {c, a*b, ...}, z)"),
        KNOWN(conv2_k, "conv({c, a*b, ...}, {F, F}, z), 2 limbs"),
        KNOWN(axpy1_k, "axpy(F, {a*b}, c F, z)"),
        KNOWN(axpy21_k, "axpy(F, {a*b}, c F, z), 2 limbs"),
        KNOWN(axpy2_k, "axpy(E2(F), {a*b}, c F, z)"),
        KNOWN(axpy1_a_k, "axpy(a*b, {F}, c F, z)"),
        KNOWN(scale1_k, "scale({a*b}, F, z)"),
        KNOWN(scale2_k, "scale({a*b}, F, z), 2 limbs"),
        KNOWN(scale1_a_k, "scale({F}, a*b, z)"),
        KNOWN(mul_pow2_1_k, "mul_pow2({a*b}, F or 1/2, z)"),
        KNOWN(mul_pow2_2_k, "mul_pow2({a*b}, F or 1/2, z), 2 limbs"),
        KNOWN(acc_product1_k, "acc.add_product(a*b, F), 1 limb"),
        KNOWN(acc_product1_rev_k, "acc.add_product(F, a*b), 1 limb"),
        KNOWN(acc_product1_once_k, "acc.add(c F); acc.add_product(a*b, F)"),
        KNOWN(acc_product2_k, "acc.add_product(a*b, F), 2 limbs"),
        KNOWN(acc_product2_rev_k, "acc.add_product(F, a*b), 2 limbs"),
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
        static const char* const notes[] = {"", "   (multiplied or compared: no guard needed)",
                                            "   (multiplied by a constant the compiler sees)",
                                            "   (the products of Packed<T, 1>)"};
        std::printf("  %-48s differs in %6ld of %ld%s\n", forms[f].name, differ[f], rounds, notes[forms[f].kind]);
        long* const count[] = {&totals.guarded, &totals.unguarded, &totals.known, &totals.kairn_product};
        *count[forms[f].kind] += differ[f];
    }
}

}  // namespace

int main(int argc, char** argv) {
    const char* expect = argc == 5 && std::strcmp(argv[1], "--expect") == 0 ? argv[2] : "";
    const char* factor = argc == 5 && std::strcmp(argv[3], "--factor") == 0 ? argv[4] : "";
    const auto valid = [](const char* e) {
        return std::strcmp(e, "none") == 0 || std::strcmp(e, "some") == 0 || std::strcmp(e, "report") == 0;
    };
    if (!valid(expect) || !valid(factor)) {
        std::fprintf(stderr, "usage: boundary_batch --expect none|some|report --factor none|some|report\n");
        return 2;
    }
#ifdef KAIRN_TEST_UNGUARDED_COPY
    std::printf("against the copy of the headers without the guard\n");
#endif
    Totals totals;
    run<double>("double", 20000, totals);
    run<float>("float", 20000, totals);
    std::printf("forms that need the guard: %ld rounds differ; forms that need none: %ld; with a known factor: %ld\n",
                totals.guarded, totals.unguarded, totals.known);
    std::printf("the products of Packed<T, 1>: %ld rounds differ\n", totals.kairn_product);
    if (std::strcmp(expect, "report") == 0 && totals.guarded == 0)
        std::printf("no form differs: this compiler and setting fused no product into the loops here, so this build "
                    "does not show that the guard is needed\n");
    bool ok = totals.unguarded == 0;
    if (std::strcmp(expect, "none") == 0) ok = ok && totals.guarded == 0 && totals.kairn_product == 0;
    if (std::strcmp(expect, "some") == 0) ok = ok && totals.guarded > 0;
    if (std::strcmp(factor, "none") == 0) ok = ok && totals.known == 0;
    if (std::strcmp(factor, "some") == 0) ok = ok && totals.known > 0;
    std::printf("%s (expected: %s; with a known factor: %s)%s\n", ok ? "ok" : "FAILED", expect, factor,
                KAIRN_TEST_ZERO_SIGN_FREE ? " (a zero limb compared as a zero: MSVC)" : "");
    return ok ? 0 : 1;
}
