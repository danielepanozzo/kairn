// A product the program computes, passed straight into a Kairn operation, must give the same result
// as the same operation on that product rounded first: the guard (detail::guard in expansion.hpp)
// keeps a compiler that contracts across statements from fusing the product into a kernel's
// error-free sums. Each form below is computed twice, with the product written in the call, and
// with an honestly rounded product (returned through a volatile by a function that is not
// inlined), on operands chosen so that the sums cancel, and the results are compared bit for bit.
//
//   boundary --expect none     every form agrees (the headers as they are)
//   boundary --expect some     built with KAIRN_DETAIL_TEST_UNGUARDED, on a compiler and setting
//                              that fuse: x + a * b must differ somewhere, so that the test above
//                              cannot pass for want of a compiler that fuses
//   boundary --expect report   prints the counts only
//
// The forms whose limb operand is only multiplied (x * (a * b), a ball scaled by a * b) need no
// guard and must agree in every build.
#include <kairn/kairn.hpp>

#include <cstdint>
#include <cstdio>
#include <cstring>

#if defined(_MSC_VER) && !defined(__clang__)
#define NOINLINE __declspec(noinline)
#else
#define NOINLINE __attribute__((noinline))
#endif

namespace {

using E1 = kairn::Expansion<double, 1>;
using E2 = kairn::Expansion<double, 2>;
using B1 = kairn::Ball<double, 1>;
using B2 = kairn::Ball<double, 2>;

NOINLINE double rounded(double a, double b) {
    volatile double p = a * b;
    return p;
}

// The forms, as (with the product inline, with the rounded product p). Each pair has the same
// signature: the reference gets p as a and 1 as b, and multiplies nothing.
#define PAIR(NAME, R, ARGS, INLINE_BODY, REF_BODY)          \
    NOINLINE R NAME##_inline ARGS { INLINE_BODY; }          \
    NOINLINE R NAME##_ref ARGS { [[maybe_unused]] const double one = b; REF_BODY; }

PAIR(plus, E2, (E2 x, double a, double b), return x + a * b, return x + a)
PAIR(plus_rev, E2, (E2 x, double a, double b), return a * b + x, return a + x)
PAIR(minus, E2, (E2 x, double a, double b), return x - a * b, return x - a)
PAIR(rminus, E2, (E2 x, double a, double b), return a * b - x, return a - x)
PAIR(plus_assign, E2, (E2 x, double a, double b), x += a * b; return x, x += a; return x)
PAIR(minus_assign, E2, (E2 x, double a, double b), x -= a * b; return x, x -= a; return x)
PAIR(construct, E2, (E2 x, double a, double b), return E2(a * b) + x, return E2(a) + x)
PAIR(from_limbs, E2, (E2 x, double a, double b), double l[2]; l[0] = a * b; l[1] = 0.0; return E2::from_limbs(l) + x,
     double l[2]; l[0] = a; l[1] = 0.0; return E2::from_limbs(l) + x)
PAIR(widen, E2, (E2 x, double a, double b), return E2(E1(a) * E1(b)) + x, return E2(E1(a)) + x)
PAIR(ball2_point, B2, (B2 y, double a, double b), return B2(a * b) + y, return B2(a) + y)
PAIR(ball2_center, B2, (B2 y, double a, double b), return B2(E2(a * b), 0x1p-40) + y, return B2(E2(a), 0x1p-40) + y)
PAIR(ball2_radius, B2, (B2 y, double a, double b), return B2(E2(0.75), a * b) + y, return B2(E2(0.75), a) + y)
PAIR(ball1_point, B1, (B1 y, double a, double b), return B1(a * b) + y, return B1(a) + y)
PAIR(ball1_center, B1, (B1 y, double a, double b), return B1(E1(a) * E1(b), 0x1p-40) + y,
     return B1(E1(a), 0x1p-40) + y)
PAIR(ball1_radius, B1, (B1 y, double a, double b), return B1(E1(0.75), a * b) + y, return B1(E1(0.75), a) + y)
// Multiplicands: no guard, and none needed.
PAIR(times, E2, (E2 x, double a, double b), return x * (a * b), return x * a)
PAIR(ball2_scale, B2, (B2 y, double a, double b), return y * (a * b), return y * a)
PAIR(ball1_scale, B1, (B1 y, double a, double b), return y * (a * b), return y * a)

template <class X>
bool same(const X& u, const X& v) {
    return std::memcmp(&u, &v, sizeof u) == 0;
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
        std::fprintf(stderr, "usage: boundary --expect none|some|report\n");
        return 2;
    }
    enum { n_forms = 18 };
    const char* names[n_forms] = {"x + a*b", "a*b + x", "x - a*b", "a*b - x", "x += a*b", "x -= a*b", "E2(a*b) + x",
                                  "from_limbs({a*b, 0}) + x", "E2(E1(a) * E1(b)) + x", "Ball2(a*b) + Y",
                                  "Ball2(E2(a*b), r) + Y", "Ball2(c, a*b) + Y", "Ball1(a*b) + Y",
                                  "Ball1(E1(a) * E1(b), r) + Y", "Ball1(c, a*b) + Y", "x * (a*b)", "Ball2 * (a*b)",
                                  "Ball1 * (a*b)"};
    const bool multiplicand[n_forms] = {false, false, false, false, false, false, false, false, false,
                                        false, false, false, false, false, false, true,  true,  true};
    long differ[n_forms] = {};
    const long cases = 200000;
    for (long i = 0; i < cases; ++i) {
        const double a = uniform(), b = uniform();
        const double p = rounded(a, b);
        const double near = 1.0 + double(i % 7) * 0x1p-30;
        // Leading limbs that cancel the product, or nearly double it for the differences.
        const E2 xm = E2(-p * near), xp = E2(p * near);
        const B2 y2(E2(-p * near), 0x1p-40), r2(E2(-0.5), p * uniform());
        const B1 y1(E1(-p * near), 0x1p-40), r1(E1(-0.5), p * uniform());
        int f = 0;
        differ[f++] += !same(plus_inline(xm, a, b), plus_ref(xm, p, 1.0));
        differ[f++] += !same(plus_rev_inline(xm, a, b), plus_rev_ref(xm, p, 1.0));
        differ[f++] += !same(minus_inline(xp, a, b), minus_ref(xp, p, 1.0));
        differ[f++] += !same(rminus_inline(xp, a, b), rminus_ref(xp, p, 1.0));
        differ[f++] += !same(plus_assign_inline(xm, a, b), plus_assign_ref(xm, p, 1.0));
        differ[f++] += !same(minus_assign_inline(xp, a, b), minus_assign_ref(xp, p, 1.0));
        differ[f++] += !same(construct_inline(xm, a, b), construct_ref(xm, p, 1.0));
        differ[f++] += !same(from_limbs_inline(xm, a, b), from_limbs_ref(xm, p, 1.0));
        differ[f++] += !same(widen_inline(xm, a, b), widen_ref(xm, p, 1.0));
        differ[f++] += !same(ball2_point_inline(y2, a, b), ball2_point_ref(y2, p, 1.0));
        differ[f++] += !same(ball2_center_inline(y2, a, b), ball2_center_ref(y2, p, 1.0));
        differ[f++] += !same(ball2_radius_inline(r2, a, b), ball2_radius_ref(r2, p, 1.0));
        differ[f++] += !same(ball1_point_inline(y1, a, b), ball1_point_ref(y1, p, 1.0));
        differ[f++] += !same(ball1_center_inline(y1, a, b), ball1_center_ref(y1, p, 1.0));
        differ[f++] += !same(ball1_radius_inline(r1, a, b), ball1_radius_ref(r1, p, 1.0));
        differ[f++] += !same(times_inline(xm, a, b), times_ref(xm, p, 1.0));
        differ[f++] += !same(ball2_scale_inline(y2, a, b), ball2_scale_ref(y2, p, 1.0));
        differ[f++] += !same(ball1_scale_inline(y1, a, b), ball1_scale_ref(y1, p, 1.0));
    }
    long guarded = 0, multiplied = 0;
    for (int f = 0; f < n_forms; ++f) {
        std::printf("  %-28s differs in %6ld of %ld%s\n", names[f], differ[f], cases,
                    multiplicand[f] ? "   (multiplicand: no guard needed)" : "");
        (multiplicand[f] ? multiplied : guarded) += differ[f];
    }
    bool ok = multiplied == 0;
    if (std::strcmp(expect, "none") == 0) ok = ok && guarded == 0;
    if (std::strcmp(expect, "some") == 0) ok = ok && differ[0] > 0;
    std::printf("%s (expected: %s)\n", ok ? "ok" : "FAILED", expect);
    return ok ? 0 : 1;
}
