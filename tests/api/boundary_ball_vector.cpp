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

}  // namespace

int main(int argc, char** argv) {
    const char* expect = argc == 3 && std::strcmp(argv[1], "--expect") == 0 ? argv[2] : "";
    if (std::strcmp(expect, "none") != 0 && std::strcmp(expect, "some") != 0 && std::strcmp(expect, "report") != 0) {
        std::fprintf(stderr, "usage: boundary_ball_vector --expect none|some|report\n");
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
    bool ok = multiplied == 0;
    if (std::strcmp(expect, "none") == 0) ok = ok && guarded == 0;
    if (std::strcmp(expect, "some") == 0) ok = ok && guarded > 0;
    std::printf("%s (expected: %s)%s\n", ok ? "ok" : "FAILED", expect,
                KAIRN_TEST_ZERO_SIGN_FREE ? " (a zero limb compared as a zero: MSVC)" : "");
    return ok ? 0 : 1;
}
