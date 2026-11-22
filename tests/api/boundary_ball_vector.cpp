// boundary.cpp for BallVector (kairn/ball_vector.hpp): a product the program computes and passes
// straight in, as a center, a radius, or an array of centers it fills with products, must give the
// same result as the same operation on the product rounded first. The guards of the constructor
// loops (rule R3: bv_center_entry_1 guards each center of one limb, bv_make_radius the radius;
// Expansion<T, 2>(a) is make_2, which guards a) keep a compiler that contracts across statements
// from fusing the product into the error-free sums of the operation that follows. Each form is
// computed twice, with the products written in the call, and with honestly rounded products
// (returned through a volatile by a function that is not inlined), on operands chosen so that the
// sums cancel, and the results are compared bit for bit, every center and the radius (a zero as a
// zero under MSVC, whose packed code drops the guard's +0).
//
//   boundary_ball_vector --expect none     every form agrees (the headers as they are)
//   boundary_ball_vector --expect some     built against a copy of the headers without the guards
//                                          (tests/api/CMakeLists.txt), on a compiler and setting
//                                          that fuse: some form must differ, so that the test
//                                          above cannot pass for want of a compiler that fuses
//   boundary_ball_vector --expect report   prints the counts only, and says so if nothing differs
//
// The forms whose operand is only multiplied (the scaling by a product, axpy's a) need no guard and
// must agree in every build.
//
// A third kind, as in boundary.cpp (rule R3, the factors of a fused operation:
// docs/developer/architecture.md): the operations of a ball vector that take a value of T from the
// program as a factor, with the other factor a constant the compiler sees, F = 1, -1 or 2, in double
// and float: the scaling by a product of centers F and by F of centers that are products (x * a,
// a * x, x *= a, scale(x, a, z), one and two limbs), and axpy with a product as its scalar a over
// centers F, and with F as a over centers that are products. A compiler that sees F = 1 rewrites
// fma(x, 1, s) as x + s and may fuse the program's product into that addition. With the headers as
// they are every form must agree (--factor none); the build without the guards reports them
// (--factor report: no compiler was measured to fuse one).
//
//   boundary_ball_vector --expect E --factor none|some|report
#define KAIRN_CHECKS 0
#include <kairn/ball_vector.hpp>

#include <array>
#include <cstdint>
#include <cstdio>
#include <cstring>

#if defined(_MSC_VER) && !defined(__clang__)
#define NOINLINE __declspec(noinline)
#define KAIRN_TEST_ZERO_SIGN_FREE 1
#else
#define NOINLINE __attribute__((noinline))
#define KAIRN_TEST_ZERO_SIGN_FREE 0
#endif

namespace {

constexpr std::size_t N = 8;
using E1 = kairn::Expansion<double, 1>;
using E2 = kairn::Expansion<double, 2>;
using BV1 = kairn::BallVector<double, 1, N>;
using BV2 = kairn::BallVector<double, 2, N>;

NOINLINE double rounded(double a, double b) {
    volatile double p = a * b;
    return p;
}

// The factors: a[i] and b[i], the product of entry i; for a reference, the rounded products in a
// and 1 in b. y cancels the products (its centers within a few units of -a b), with a small radius.
struct Factors {
    double a[N], b[N];
};

// The forms, each with the product inline (a[i] * b[i]); the reference is the same function given
// the rounded products and ones, which multiply to themselves exactly.
NOINLINE BV1 center1(const Factors& f, const BV1& y) {
    std::array<E1, N> c;
    for (std::size_t i = 0; i < N; ++i) c[i] = E1(f.a[i] * f.b[i]);
    return BV1(c, 0x1p-40) + y;
}
NOINLINE BV1 view1(const Factors& f, const BV1& y) {
    double c[N];
    for (std::size_t i = 0; i < N; ++i) c[i] = f.a[i] * f.b[i];
    double r = 0x1p-40;
    const kairn::BallVectorView<double, 1> v(kairn::SoAView<double, 1>(c, N), r);
    BV1 z;
    kairn::add(v, y, z);
    return z;
}
NOINLINE BV1 soa1(const Factors& f, const BV1& y) {
    double c[N];
    for (std::size_t i = 0; i < N; ++i) c[i] = f.a[i] * f.b[i];
    return BV1(kairn::SoAView<const double, 1>(c, N), 0x1p-40) + y;
}
NOINLINE BV1 radius1(const Factors& f, const BV1& y) {
    std::array<E1, N> c;
    for (std::size_t i = 0; i < N; ++i) c[i] = E1(0.75);
    return BV1(c, f.a[0] * f.b[0]) + y;
}
NOINLINE BV2 center2(const Factors& f, const BV2& y) {
    std::array<E2, N> c;
    for (std::size_t i = 0; i < N; ++i) c[i] = E2(f.a[i] * f.b[i]);
    return BV2(c, 0x1p-40) + y;
}
NOINLINE BV2 radius2(const Factors& f, const BV2& y) {
    std::array<E2, N> c;
    for (std::size_t i = 0; i < N; ++i) c[i] = E2(0.75);
    return BV2(c, f.a[0] * f.b[0]) + y;
}
// Multiplied only: the scaling by a product, and axpy's a.
NOINLINE BV2 scale2(const Factors& f, const BV2& y) { return y * (f.a[0] * f.b[0]); }
NOINLINE BV1 axpy1(const Factors& f, const BV1& y) { return kairn::axpy(f.a[1] * f.b[1], y, y); }

template <class X>
bool same(const X& u, const X& v) {
    for (int j = 0; j < X::limbs; ++j)
        for (std::size_t i = 0; i < N; ++i) {
            const double p = u.limb(j)[i], q = v.limb(j)[i];
            if (KAIRN_TEST_ZERO_SIGN_FREE && p == 0 && q == 0) continue;
            if (std::memcmp(&p, &q, sizeof p) != 0) return false;
        }
    const double p = u.radius(), q = v.radius();
    return std::memcmp(&p, &q, sizeof p) == 0;
}

std::uint64_t state = 0x9E3779B97F4A7C15ull;
double uniform() {  // in [0.5, 1)
    state ^= state << 13;
    state ^= state >> 7;
    state ^= state << 17;
    return 0.5 + double(state >> 11) * 0x1p-54;
}

// The third kind: the other factor F, a constant the compiler sees. Each form is computed with the
// product a*b in the call (NAME_inline) and with the rounded product (NAME_ref, which gets it as a),
// and every limb of every center and the radius are compared.
template <int C, class T>
constexpr T known() {
    return C == 0 ? T(1) : C == 1 ? T(-1) : T(2);
}
// Every limb of every center, then the radius.
template <class T>
struct Flat {
    T v[2 * N + 1];
};
template <class T, int K>
Flat<T> flat(const kairn::BallVector<T, K, N>& x) {
    Flat<T> f{};
    for (int j = 0; j < K; ++j)
        for (std::size_t i = 0; i < N; ++i) f.v[std::size_t(j) * N + i] = x.limb(j)[i];
    f.v[2 * N] = x.radius();
    return f;
}
// A ball vector of N centers v and radius 2^-20.
template <class T, int K>
kairn::BallVector<T, K, N> filled(T v) {
    std::array<kairn::Expansion<T, K>, N> c;
    for (std::size_t i = 0; i < N; ++i) c[i] = kairn::Expansion<T, K>(v);
    return kairn::BallVector<T, K, N>(c, T(0x1p-20));
}
#define KNOWN(NAME, ...)                                                                   \
    template <class T, int C>                                                              \
    inline Flat<T> NAME##_body(T q) {                                                      \
        using V1 = kairn::BallVector<T, 1, N>;                                             \
        using V2 = kairn::BallVector<T, 2, N>;                                             \
        constexpr T F = known<C, T>();                                                     \
        (void)sizeof(V1), (void)sizeof(V2), (void)F;                                       \
        return flat(__VA_ARGS__);                                                          \
    }                                                                                      \
    template <class T, int C>                                                              \
    NOINLINE Flat<T> NAME##_inline(T a, T b) { return NAME##_body<T, C>(a * b); }          \
    template <class T, int C>                                                              \
    NOINLINE Flat<T> NAME##_ref(T a, T) { return NAME##_body<T, C>(a); }

// q is the product (a*b, or the rounded product); F the constant.
KNOWN(k_scale1_by_f, filled<T, 1>(q) * F)
KNOWN(k_scale2_by_f, filled<T, 2>(q) * F)
KNOWN(k_scale1_of_f, filled<T, 1>(F) * q)
KNOWN(k_scale2_of_f, filled<T, 2>(F) * q)
KNOWN(k_scale2_of_f_rev, q * filled<T, 2>(F))
KNOWN(k_scale2_of_f_assign, [&] { V2 x = filled<T, 2>(F); x *= q; return x; }())
KNOWN(k_scale2_of_f_fn, [&] { V2 z; kairn::scale(filled<T, 2>(F), q, z); return z; }())
KNOWN(k_axpy1_a, kairn::axpy(q, filled<T, 1>(F), filled<T, 1>(T(0.375))))
KNOWN(k_axpy2_a, kairn::axpy(q, filled<T, 2>(F), filled<T, 2>(T(0.375))))
KNOWN(k_axpy2_f, kairn::axpy(F, filled<T, 2>(q), filled<T, 2>(T(-0.375))))

template <class T>
using KnownFn = Flat<T> (*)(T, T);
struct KnownForm {
    const char* name;
    KnownFn<double> d[3];
    KnownFn<double> dr[3];
    KnownFn<float> f[3];
    KnownFn<float> fr[3];
};
#define KROW(NAME, TEXT)                                                                                       \
    {TEXT,                                                                                                     \
     {&NAME##_inline<double, 0>, &NAME##_inline<double, 1>, &NAME##_inline<double, 2>},                        \
     {&NAME##_ref<double, 0>, &NAME##_ref<double, 1>, &NAME##_ref<double, 2>},                                 \
     {&NAME##_inline<float, 0>, &NAME##_inline<float, 1>, &NAME##_inline<float, 2>},                           \
     {&NAME##_ref<float, 0>, &NAME##_ref<float, 1>, &NAME##_ref<float, 2>}}
const KnownForm known_forms[] = {
    KROW(k_scale1_by_f, "BV1({a*b}, r) * F"),
    KROW(k_scale2_by_f, "BV2({a*b}, r) * F"),
    KROW(k_scale1_of_f, "BV1({F}, r) * (a*b)"),
    KROW(k_scale2_of_f, "BV2({F}, r) * (a*b)"),
    KROW(k_scale2_of_f_rev, "(a*b) * BV2({F}, r)"),
    KROW(k_scale2_of_f_assign, "x = BV2({F}, r); x *= a*b"),
    KROW(k_scale2_of_f_fn, "scale(BV2({F}, r), a*b, z)"),
    KROW(k_axpy1_a, "axpy(a*b, BV1({F}, r), Y)"),
    KROW(k_axpy2_a, "axpy(a*b, BV2({F}, r), Y)"),
    KROW(k_axpy2_f, "axpy(F, BV2({a*b}, r), Y)"),
};

template <class T>
T uniform_of() {
    if constexpr (sizeof(T) == 8) {
        return uniform();
    } else {
        state ^= state << 13;
        state ^= state >> 7;
        state ^= state << 17;
        return 0.5f + float(state >> 40) * 0x1p-25f;
    }
}
template <class T>
NOINLINE T rounded_of(T a, T b) {
    volatile T p = a * b;
    return p;
}
template <class T>
bool same_flat(const Flat<T>& u, const Flat<T>& v) {
    for (std::size_t i = 0; i < 2 * N + 1; ++i) {
        if (KAIRN_TEST_ZERO_SIGN_FREE && u.v[i] == 0 && v.v[i] == 0) continue;
        if (std::memcmp(&u.v[i], &v.v[i], sizeof(T)) != 0) return false;
    }
    return true;
}
template <class T>
long known_run(const KnownFn<T>* in, const KnownFn<T>* ref, long cases, const char* name, const char* type) {
    long total = 0;
    for (int c = 0; c < 3; ++c) {
        long differ = 0;
        for (long i = 0; i < cases; ++i) {
            const T a = uniform_of<T>(), b = uniform_of<T>();
            const T p = rounded_of(a, b);
            differ += !same_flat(in[c](a, b), ref[c](p, T(1)));
        }
        if (differ)
            std::printf("  %-30s %-6s F = %-2g differs in %6ld of %ld: a product of the program fused through "
                        "the known factor\n", name, type, c == 0 ? 1.0 : c == 1 ? -1.0 : 2.0, differ, cases);
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
        std::fprintf(stderr, "usage: boundary_ball_vector --expect none|some|report --factor none|some|report\n");
        return 2;
    }
#ifdef KAIRN_TEST_UNGUARDED_COPY
    std::printf("against the copy of the headers without the guard\n");
#endif
    enum { n_forms = 8 };
    const char* names[n_forms] = {"BV1({a*b}, r) + Y",   "BallVectorView({a*b}, r) + Y", "BV1(SoAView({a*b}), r) + Y",
                                  "BV1(c, a*b) + Y",     "BV2({E2(a*b)}, r) + Y",        "BV2(c, a*b) + Y",
                                  "Y * (a*b) (BV2)",     "axpy(a*b, Y, Y) (BV1)"};
    const bool multiplicand[n_forms] = {false, false, false, false, false, false, true, true};
    long differ[n_forms] = {};
    const long cases = 20000;
    for (long k = 0; k < cases; ++k) {
        Factors f, p;
        std::array<E1, N> y1c;
        std::array<E2, N> y2c, r2c;
        std::array<E1, N> r1c;
        for (std::size_t i = 0; i < N; ++i) {
            f.a[i] = uniform();
            f.b[i] = uniform();
            p.a[i] = rounded(f.a[i], f.b[i]);
            p.b[i] = 1.0;
            const double near = 1.0 + double((k + long(i)) % 7) * 0x1p-30;
            y1c[i] = E1(-p.a[i] * near);
            y2c[i] = E2(-p.a[i] * near);
            r1c[i] = E1(-0.5);
            r2c[i] = E2(-0.5);
        }
        // Radii that cancel the product in the sum of the radii: a radius near the product's
        // for the forms that pass the product as a radius.
        const BV1 y1(y1c, 0x1p-40), r1(r1c, p.a[0] * uniform());
        const BV2 y2(y2c, 0x1p-40), r2(r2c, p.a[0] * uniform());
        int i = 0;
        differ[i++] += !same(center1(f, y1), center1(p, y1));
        differ[i++] += !same(view1(f, y1), view1(p, y1));
        differ[i++] += !same(soa1(f, y1), soa1(p, y1));
        differ[i++] += !same(radius1(f, r1), radius1(p, r1));
        differ[i++] += !same(center2(f, y2), center2(p, y2));
        differ[i++] += !same(radius2(f, r2), radius2(p, r2));
        differ[i++] += !same(scale2(f, y2), scale2(p, y2));
        differ[i++] += !same(axpy1(f, y1), axpy1(p, y1));
    }
    long guarded = 0, multiplied = 0;
    for (int i = 0; i < n_forms; ++i) {
        std::printf("  %-32s differs in %6ld of %ld%s\n", names[i], differ[i], cases,
                    multiplicand[i] ? "   (multiplicand: no guard needed)" : "");
        (multiplicand[i] ? multiplied : guarded) += differ[i];
    }
    if (std::strcmp(expect, "report") == 0 && guarded == 0)
        std::printf("no form differs: this compiler and setting fused no product into a ball vector here, so this "
                    "build does not show that the guard is needed\n");
    // The known factors.
    const long known_cases = 20000;
    long known_total = 0;
    std::printf("the other factor a constant F the compiler sees (1, -1, 2), %ld pairs per form, type and F:\n",
                known_cases);
    for (const KnownForm& k : known_forms) {
        known_total += known_run<double>(k.d, k.dr, known_cases, k.name, "double");
        known_total += known_run<float>(k.f, k.fr, known_cases, k.name, "float");
    }
    std::printf("  %d forms: %ld cases differ%s\n", int(sizeof known_forms / sizeof known_forms[0]), known_total,
                known_total ? "" : " (no form differs)");
    bool ok = multiplied == 0;
    if (std::strcmp(expect, "none") == 0) ok = ok && guarded == 0;
    if (std::strcmp(expect, "some") == 0) ok = ok && guarded > 0;
    bool ok_known = true;
    if (std::strcmp(factor, "none") == 0) ok_known = known_total == 0;
    if (std::strcmp(factor, "some") == 0) ok_known = known_total > 0;
    std::printf("%s (expected: %s; with a known factor: %s)%s\n", ok && ok_known ? "ok" : "FAILED", expect, factor,
                KAIRN_TEST_ZERO_SIGN_FREE ? " (a zero limb compared as a zero: MSVC)" : "");
    return ok && ok_known ? 0 : 1;
}
