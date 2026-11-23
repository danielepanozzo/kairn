// A product the program computes, passed straight into a Kairn operation, must give the same result
// as the same operation on that product rounded first: the guard of the generated kernels (rule
// R3: guard(a) in add_2_1 and in the constructor kernels) keeps a compiler that contracts across
// statements from fusing the product into a kernel's error-free sums. Each form below is computed
// twice, with the product written in the call, and with an honestly rounded product (returned
// through a volatile by a function that is not inlined), on operands chosen so that the sums
// cancel, and the results are compared bit for bit.
//
//   boundary --expect none     every form agrees (the headers as they are)
//   boundary --expect some     built against a copy of the headers without the guard
//                              (tests/api/CMakeLists.txt), on a compiler and setting that fuse:
//                              some form must differ, so that the test above cannot pass for want
//                              of a compiler that fuses
//   boundary --expect report   prints the counts only
//
// The forms whose limb operand is only multiplied (x * (a * b), a ball scaled by a * b) or only
// compared (the member test of an interval) need no guard and must agree in every build.
//
// A third kind (rule R3, the factors of a fused operation: docs/developer/architecture.md): every
// public operation that takes a value of T from the program as a factor, with the other factor a
// constant the compiler sees, F = 1, -1 or 2 (E2(F) * (a*b), two_prod(a*b, F), ...), in double and
// float. A compiler that sees F = 1 rewrites fma(x, 1, s) as x + s and may fuse the program's
// product into that addition. These operations are called with the headers as they are, and every
// form must agree: --factor none in the build with the guard. The build without the guard reports
// them (--factor report), or requires a difference (--factor some) where a compiler was measured to
// fuse (tests/api/CMakeLists.txt; docs/developer/testing.md).
//
//   boundary --expect E --factor none|some|report
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
using I1 = kairn::Interval<double, 1>;
using I2 = kairn::Interval<double, 2>;

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
PAIR(plus_one, E2, (E2 x, double a, double b), return x + E1(a * b), return x + E1(a))
PAIR(minus_one, E2, (E2 x, double a, double b), return x - E1(a * b), return x - E1(a))
PAIR(finite_plus, E2, (E2 x, double a, double b), return kairn::finite::add(x, a * b), return kairn::finite::add(x, a))
PAIR(finite_rminus, E2, (E2 x, double a, double b), return kairn::finite::sub(a * b, x), return kairn::finite::sub(a, x))
PAIR(ball2_plus_point, B2, (B2 y, double a, double b), return y + a * b, return y + a)
PAIR(ball1_point_minus, B1, (B1 y, double a, double b), return a * b - y, return a - y)
// The enclosure interface (headers-pred): a point of the program in a ball, whose member test adds
// it (ball_contains_point_1 guards it; for two limbs make_2 does), against a ball centered at the
// rounded product with a radius that the guarded point is within and a fused one is not; and the
// ball from an interval of two T, whose bounds are guarded and added to the midpoint.
PAIR(ball1_contains, bool, (B1 y, double a, double b), return y.contains(a * b), return y.contains(a))
PAIR(ball2_contains, bool, (B2 y, double a, double b), return y.contains(a * b), return y.contains(a))
PAIR(ball1_from_interval, B1, (B1 y, double a, double b), return B1::from_interval(a * b, a * b) + y,
     return B1::from_interval(a, a) + y)
PAIR(ball2_from_interval, B2, (B2 y, double a, double b), return B2::from_interval(a * b, a * b) + y,
     return B2::from_interval(a, a) + y)
// from_bounds, the spelling of a set from two bounds that a ball and an interval share: the ball's
// is from_interval's kernel, the interval's that of its constructor, which guard the bounds; the
// interval is then added to an interval at the opposite of the product.
PAIR(ball1_from_bounds, B1, (B1 y, double a, double b), return B1::from_bounds(a * b, a * b) + y,
     return B1::from_bounds(a, a) + y)
PAIR(ball2_from_bounds, B2, (B2 y, double a, double b), return B2::from_bounds(a * b, a * b) + y,
     return B2::from_bounds(a, a) + y)
PAIR(interval1_from_bounds, I1, (I1 x, double a, double b), return I1::from_bounds(a * b, a * b) + x,
     return I1::from_bounds(a, a) + x)
PAIR(interval2_from_bounds, I2, (I2 x, double a, double b), return I2::from_bounds(a * b, a * b) + x,
     return I2::from_bounds(a, a) + x)
// from_limbs of an interval and of a ball: a product of the program passed as a limb, a bound, a
// center or a radius, which the guard of make_2 or make_2_limbs takes before an operation adds it.
PAIR(interval1_from_limbs, I1, (I1 x, double a, double b), double l[2]; l[0] = a * b; l[1] = a * b;
     return I1::from_limbs(l) + x, double l[2]; l[0] = a; l[1] = a; return I1::from_limbs(l) + x)
PAIR(interval2_from_limbs, I2, (I2 x, double a, double b), double l[4]; l[0] = a * b; l[1] = 0.0; l[2] = a * b;
     l[3] = 0.0; return I2::from_limbs(l) + x, double l[4]; l[0] = a; l[1] = 0.0; l[2] = a; l[3] = 0.0;
     return I2::from_limbs(l) + x)
PAIR(ball1_from_limbs_center, B1, (B1 y, double a, double b), double l[2]; l[0] = a * b; l[1] = 0x1p-40;
     return B1::from_limbs(l) + y, double l[2]; l[0] = a; l[1] = 0x1p-40; return B1::from_limbs(l) + y)
PAIR(ball1_from_limbs_radius, B1, (B1 y, double a, double b), double l[2]; l[0] = 0.75; l[1] = a * b;
     return B1::from_limbs(l) + y, double l[2]; l[0] = 0.75; l[1] = a; return B1::from_limbs(l) + y)
PAIR(ball2_from_limbs_center, B2, (B2 y, double a, double b), double l[3]; l[0] = a * b; l[1] = 0.0;
     l[2] = 0x1p-40; return B2::from_limbs(l) + y, double l[3]; l[0] = a; l[1] = 0.0; l[2] = 0x1p-40;
     return B2::from_limbs(l) + y)
PAIR(ball2_from_limbs_radius, B2, (B2 y, double a, double b), double l[3]; l[0] = 0.75; l[1] = 0.0; l[2] = a * b;
     return B2::from_limbs(l) + y, double l[3]; l[0] = 0.75; l[1] = 0.0; l[2] = a; return B2::from_limbs(l) + y)
// A product of the program written into a limb of a number of two limbs, which is then given to the
// constructor of a ball (its center, the point, a constant, a point operand of an operation) or of
// an interval (its bounds, the point, from_bounds): the limbs of an Expansion are public, and these
// constructors guard each limb (ball_make_2_entry, interval_make_2_entry; the owner's decision of
// 2026-11-23 for the ball). Built without the guard, the limb would be the product as the program
// wrote it, which the first addition of the operation could fuse.
#define LIMB(c, v)       \
    E2 c;                \
    c.limb[0] = (v);     \
    c.limb[1] = 0.0
PAIR(ball2_center_limb, B2, (B2 y, double a, double b), LIMB(c, a * b); return B2(c, 0x1p-40) + y,
     LIMB(c, a); return B2(c, 0x1p-40) + y)
PAIR(ball2_point_limb, B2, (B2 y, double a, double b), LIMB(c, a * b); return B2(c) + y, LIMB(c, a); return B2(c) + y)
PAIR(ball2_constant_limb, B2, (B2 y, double a, double b), LIMB(c, a * b);
     return B2(kairn::Constant<E2>{c, 0x1p-40, false}) + y, LIMB(c, a);
     return B2(kairn::Constant<E2>{c, 0x1p-40, false}) + y)
PAIR(ball2_plus_limb, B2, (B2 y, double a, double b), LIMB(c, a * b); return y + c, LIMB(c, a); return y + c)
PAIR(interval2_bounds_limb, I2, (I2 x, double a, double b), LIMB(c, a * b); return I2(c, c) + x, LIMB(c, a);
     return I2(c, c) + x)
PAIR(interval2_point_limb, I2, (I2 x, double a, double b), LIMB(c, a * b); return I2(c) + x, LIMB(c, a);
     return I2(c) + x)
PAIR(interval2_from_bounds_limb, I2, (I2 x, double a, double b), LIMB(c, a * b); return I2::from_bounds(c, c) + x,
     LIMB(c, a); return I2::from_bounds(c, c) + x)
#undef LIMB
// Multiplicands: no guard, and none needed.
PAIR(times, E2, (E2 x, double a, double b), return x * (a * b), return x * a)
PAIR(ball2_scale, B2, (B2 y, double a, double b), return y * (a * b), return y * a)
PAIR(ball1_scale, B1, (B1 y, double a, double b), return y * (a * b), return y * a)
// A point of the program only compared, in the member test of an interval: no guard needed (for two
// limbs make_2 guards it, and nothing adds it).
PAIR(interval1_contains, bool, (I1 x, double a, double b), return x.contains(a * b), return x.contains(a))
PAIR(interval2_contains, bool, (I2 x, double a, double b), return x.contains(a * b), return x.contains(a))

template <class X>
bool same(const X& u, const X& v) {
    return std::memcmp(&u, &v, sizeof u) == 0;
}

// The third kind: the other factor F, a constant the compiler sees. Each form is computed with the
// product a*b in the call (NAME_inline) and with the rounded product (NAME_ref, which gets it as a),
// and every limb of the result is compared.
template <int C, class T>
constexpr T known() {
    return C == 0 ? T(1) : C == 1 ? T(-1) : T(2);
}
template <class T>
struct Limbs {
    T v[3];
};
template <class T>
Limbs<T> limbs(const kairn::Expansion<T, 2>& x) { return {{x.limb[0], x.limb[1], T(0)}}; }
template <class T>
Limbs<T> limbs(const kairn::Expansion<T, 1>& x) { return {{x.limb[0], T(0), T(0)}}; }
template <class T>
Limbs<T> limbs(const kairn::Ball<T, 2>& x) { return {{x.center().limb[0], x.center().limb[1], x.radius()}}; }
template <class T>
Limbs<T> limbs(const kairn::Ball<T, 1>& x) { return {{x.center().limb[0], x.radius(), T(0)}}; }
template <class T>
Limbs<T> limbs(const kairn::ProductAndError<T>& x) { return {{x.product, x.error, T(0)}}; }
template <class T>
Limbs<T> limbs(T x) { return {{x, T(0), T(0)}}; }

#define KNOWN(NAME, ...)                                                                   \
    template <class T, int C, class Q>                                                     \
    inline Limbs<T> NAME##_body(Q q) {                                                     \
        using X1 = kairn::Expansion<T, 1>;                                                 \
        using X2 = kairn::Expansion<T, 2>;                                                 \
        using Y1 = kairn::Ball<T, 1>;                                                      \
        using Y2 = kairn::Ball<T, 2>;                                                      \
        constexpr T F = known<C, T>();                                                     \
        (void)sizeof(X1), (void)sizeof(X2), (void)sizeof(Y1), (void)sizeof(Y2), (void)F;   \
        return limbs<T>(__VA_ARGS__);                                                      \
    }                                                                                      \
    template <class T, int C>                                                              \
    NOINLINE Limbs<T> NAME##_inline(T a, T b) { return NAME##_body<T, C>(a * b); }         \
    template <class T, int C>                                                              \
    NOINLINE Limbs<T> NAME##_ref(T a, T) { return NAME##_body<T, C>(a); }

// q is the product (a*b, or the rounded product); F the constant.
KNOWN(k_times, X2(F) * q)
KNOWN(k_times_rev, q * X2(F))
KNOWN(k_times_assign, [&] { X2 x(F); x *= q; return x; }())
KNOWN(k_finite_times, kairn::finite::mul(X2(F), q))
KNOWN(k_finite_times_rev, kairn::finite::mul(q, X2(F)))
KNOWN(k_times_one, X2(F) * X1(q))
KNOWN(k_one_times, X1(q) * X2(F))
KNOWN(k_finite_one, kairn::finite::mul(X2(F), X1(q)))
KNOWN(k_one_one, X1(F) * X1(q))
KNOWN(k_two_prod, kairn::two_prod(q, F))
KNOWN(k_two_prod_rev, kairn::two_prod(F, q))
KNOWN(k_two_prod_error, kairn::two_prod(q, F).error)
KNOWN(k_rmul, kairn::rmul(q, F))
KNOWN(k_mul_down, kairn::mul_down(q, F))
KNOWN(k_mul_down_rev, kairn::mul_down(F, q))
KNOWN(k_mul_up, kairn::mul_up(q, F))
KNOWN(k_mul_up_rev, kairn::mul_up(F, q))
KNOWN(k_ball2, Y2(X2(F), T(0x1p-20)) * q)
KNOWN(k_ball2_rev, q * Y2(X2(F), T(0x1p-20)))
KNOWN(k_ball2_assign, [&] { Y2 y(X2(F), T(0x1p-20)); y *= q; return y; }())
KNOWN(k_ball1, Y1(X1(F), T(0x1p-20)) * q)
KNOWN(k_ball1_rev, q * Y1(X1(F), T(0x1p-20)))
KNOWN(k_ball1_one, Y1(X1(F), T(0x1p-20)) * X1(q))

template <class T>
using KnownFn = Limbs<T> (*)(T, T);
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
    KROW(k_times, "E2(F) * (a*b)"),
    KROW(k_times_rev, "(a*b) * E2(F)"),
    KROW(k_times_assign, "x = E2(F); x *= a*b"),
    KROW(k_finite_times, "finite::mul(E2(F), a*b)"),
    KROW(k_finite_times_rev, "finite::mul(a*b, E2(F))"),
    KROW(k_times_one, "E2(F) * E1(a*b)"),
    KROW(k_one_times, "E1(a*b) * E2(F)"),
    KROW(k_finite_one, "finite::mul(E2(F), E1(a*b))"),
    KROW(k_one_one, "E1(F) * E1(a*b)"),
    KROW(k_two_prod, "two_prod(a*b, F)"),
    KROW(k_two_prod_rev, "two_prod(F, a*b)"),
    KROW(k_two_prod_error, "two_prod(a*b, F).error"),
    KROW(k_rmul, "rmul(a*b, F)"),
    KROW(k_mul_down, "mul_down(a*b, F)"),
    KROW(k_mul_down_rev, "mul_down(F, a*b)"),
    KROW(k_mul_up, "mul_up(a*b, F)"),
    KROW(k_mul_up_rev, "mul_up(F, a*b)"),
    KROW(k_ball2, "Ball2(E2(F), r) * (a*b)"),
    KROW(k_ball2_rev, "(a*b) * Ball2(E2(F), r)"),
    KROW(k_ball2_assign, "Y = Ball2(E2(F), r); Y *= a*b"),
    KROW(k_ball1, "Ball1(E1(F), r) * (a*b)"),
    KROW(k_ball1_rev, "(a*b) * Ball1(E1(F), r)"),
    KROW(k_ball1_one, "Ball1(E1(F), r) * E1(a*b)"),
};

std::uint64_t state = 0x9E3779B97F4A7C15ull;
double uniform() {  // in [0.5, 1)
    state ^= state << 13;
    state ^= state >> 7;
    state ^= state << 17;
    return 0.5 + double(state >> 11) * 0x1p-54;
}

}  // namespace

// The known factors: every form, both types and the three constants, on `cases` pairs each.
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
long known_run(const KnownFn<T>* in, const KnownFn<T>* ref, long cases, const char* name, const char* type) {
    long total = 0;
    for (int c = 0; c < 3; ++c) {
        long differ = 0;
        for (long i = 0; i < cases; ++i) {
            const T a = uniform_of<T>(), b = uniform_of<T>();
            const T p = rounded_of(a, b);
            differ += !same(in[c](a, b), ref[c](p, T(1)));
        }
        if (differ)
            std::printf("  %-30s %-6s F = %-2g differs in %6ld of %ld: a product of the program fused through "
                        "the known factor\n", name, type, c == 0 ? 1.0 : c == 1 ? -1.0 : 2.0, differ, cases);
        total += differ;
    }
    return total;
}

int main(int argc, char** argv) {
    const char* expect = argc == 5 && std::strcmp(argv[1], "--expect") == 0 ? argv[2] : "";
    const char* factor = argc == 5 && std::strcmp(argv[3], "--factor") == 0 ? argv[4] : "";
    const auto valid = [](const char* e) {
        return std::strcmp(e, "none") == 0 || std::strcmp(e, "some") == 0 || std::strcmp(e, "report") == 0;
    };
    if (!valid(expect) || !valid(factor)) {
        std::fprintf(stderr, "usage: boundary --expect none|some|report --factor none|some|report\n");
        return 2;
    }
    enum { n_forms = 47 };
    const char* names[n_forms] = {"x + a*b", "a*b + x", "x - a*b", "a*b - x", "x += a*b", "x -= a*b", "E2(a*b) + x",
                                  "from_limbs({a*b, 0}) + x", "E2(E1(a) * E1(b)) + x", "Ball2(a*b) + Y",
                                  "Ball2(E2(a*b), r) + Y", "Ball2(c, a*b) + Y", "Ball1(a*b) + Y",
                                  "Ball1(E1(a) * E1(b), r) + Y", "Ball1(c, a*b) + Y", "x + E1(a*b)", "x - E1(a*b)",
                                  "finite::add(x, a*b)", "finite::sub(a*b, x)", "Y + a*b (Ball2)", "a*b - Y (Ball1)",
                                  "Ball1.contains(a*b)", "Ball2.contains(a*b)", "Ball1::from_interval(a*b, a*b)",
                                  "Ball2::from_interval(a*b, a*b)", "Ball1::from_bounds(a*b, a*b)",
                                  "Ball2::from_bounds(a*b, a*b)", "Interval1::from_bounds(a*b, a*b) + X",
                                  "Interval2::from_bounds(a*b, a*b) + X", "Interval1::from_limbs({a*b, a*b}) + X",
                                  "Interval2::from_limbs({a*b, 0, a*b, 0}) + X", "Ball1::from_limbs({a*b, r}) + Y",
                                  "Ball1::from_limbs({c, a*b}) + Y", "Ball2::from_limbs({a*b, 0, r}) + Y",
                                  "Ball2::from_limbs({c, 0, a*b}) + Y", "Ball2({a*b, 0}, r) + Y",
                                  "Ball2({a*b, 0}) + Y", "Ball2(Constant{{a*b, 0}, r}) + Y", "Y + {a*b, 0} (Ball2)",
                                  "Interval2({a*b, 0}, {a*b, 0}) + X", "Interval2({a*b, 0}) + X",
                                  "Interval2::from_bounds({a*b, 0}, {a*b, 0}) + X", "x * (a*b)", "Ball2 * (a*b)",
                                  "Ball1 * (a*b)", "Interval1.contains(a*b)", "Interval2.contains(a*b)"};
    bool multiplicand[n_forms] = {};
    for (int f = n_forms - 5; f < n_forms; ++f) multiplicand[f] = true;
    long differ[n_forms] = {};
    const long cases = 200000;
    for (long i = 0; i < cases; ++i) {
        const double a = uniform(), b = uniform();
        const double p = rounded(a, b);
        const double near = 1.0 + double(i % 7) * 0x1p-30;
        // Leading limbs that cancel the product, or nearly double it for the differences.
        const E2 xm = E2(-p * near), xp = E2(p * near);
        const B2 y2(E2(-p * near), 0x1p-40), r2(E2(-0.5), p * uniform());
        const B1 y1(E1(-p * near), 0x1p-40), r1(E1(-0.5), p * uniform()), m1(E1(p * near), 0x1p-40);
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
        differ[f++] += !same(plus_one_inline(xm, a, b), plus_one_ref(xm, p, 1.0));
        differ[f++] += !same(minus_one_inline(xp, a, b), minus_one_ref(xp, p, 1.0));
        differ[f++] += !same(finite_plus_inline(xm, a, b), finite_plus_ref(xm, p, 1.0));
        differ[f++] += !same(finite_rminus_inline(xp, a, b), finite_rminus_ref(xp, p, 1.0));
        differ[f++] += !same(ball2_plus_point_inline(y2, a, b), ball2_plus_point_ref(y2, p, 1.0));
        differ[f++] += !same(ball1_point_minus_inline(m1, a, b), ball1_point_minus_ref(m1, p, 1.0));
        // A ball centered at the rounded product: radius 0 for one limb, which the guarded point
        // meets exactly; for two limbs 2^-990, above the bound of the error of an exact difference
        // and far below the error of a product fused into it.
        const B1 at1(E1(p), 0.0);
        const B2 at2(E2(p), 0x1p-990);
        differ[f++] += !same(ball1_contains_inline(at1, a, b), ball1_contains_ref(at1, p, 1.0));
        differ[f++] += !same(ball2_contains_inline(at2, a, b), ball2_contains_ref(at2, p, 1.0));
        differ[f++] += !same(ball1_from_interval_inline(y1, a, b), ball1_from_interval_ref(y1, p, 1.0));
        differ[f++] += !same(ball2_from_interval_inline(y2, a, b), ball2_from_interval_ref(y2, p, 1.0));
        differ[f++] += !same(ball1_from_bounds_inline(y1, a, b), ball1_from_bounds_ref(y1, p, 1.0));
        differ[f++] += !same(ball2_from_bounds_inline(y2, a, b), ball2_from_bounds_ref(y2, p, 1.0));
        const I1 xi1(-p * near);
        const I2 xi2(E2(-p * near));
        differ[f++] += !same(interval1_from_bounds_inline(xi1, a, b), interval1_from_bounds_ref(xi1, p, 1.0));
        differ[f++] += !same(interval2_from_bounds_inline(xi2, a, b), interval2_from_bounds_ref(xi2, p, 1.0));
        differ[f++] += !same(interval1_from_limbs_inline(xi1, a, b), interval1_from_limbs_ref(xi1, p, 1.0));
        differ[f++] += !same(interval2_from_limbs_inline(xi2, a, b), interval2_from_limbs_ref(xi2, p, 1.0));
        differ[f++] += !same(ball1_from_limbs_center_inline(y1, a, b), ball1_from_limbs_center_ref(y1, p, 1.0));
        differ[f++] += !same(ball1_from_limbs_radius_inline(r1, a, b), ball1_from_limbs_radius_ref(r1, p, 1.0));
        differ[f++] += !same(ball2_from_limbs_center_inline(y2, a, b), ball2_from_limbs_center_ref(y2, p, 1.0));
        differ[f++] += !same(ball2_from_limbs_radius_inline(r2, a, b), ball2_from_limbs_radius_ref(r2, p, 1.0));
        differ[f++] += !same(ball2_center_limb_inline(y2, a, b), ball2_center_limb_ref(y2, p, 1.0));
        differ[f++] += !same(ball2_point_limb_inline(y2, a, b), ball2_point_limb_ref(y2, p, 1.0));
        differ[f++] += !same(ball2_constant_limb_inline(y2, a, b), ball2_constant_limb_ref(y2, p, 1.0));
        differ[f++] += !same(ball2_plus_limb_inline(y2, a, b), ball2_plus_limb_ref(y2, p, 1.0));
        differ[f++] += !same(interval2_bounds_limb_inline(xi2, a, b), interval2_bounds_limb_ref(xi2, p, 1.0));
        differ[f++] += !same(interval2_point_limb_inline(xi2, a, b), interval2_point_limb_ref(xi2, p, 1.0));
        differ[f++] += !same(interval2_from_bounds_limb_inline(xi2, a, b), interval2_from_bounds_limb_ref(xi2, p, 1.0));
        differ[f++] += !same(times_inline(xm, a, b), times_ref(xm, p, 1.0));
        differ[f++] += !same(ball2_scale_inline(y2, a, b), ball2_scale_ref(y2, p, 1.0));
        differ[f++] += !same(ball1_scale_inline(y1, a, b), ball1_scale_ref(y1, p, 1.0));
        const I1 pt1(p);
        const I2 pt2(p);
        differ[f++] += !same(interval1_contains_inline(pt1, a, b), interval1_contains_ref(pt1, p, 1.0));
        differ[f++] += !same(interval2_contains_inline(pt2, a, b), interval2_contains_ref(pt2, p, 1.0));
    }
    long guarded = 0, multiplied = 0;
    for (int f = 0; f < n_forms; ++f) {
        std::printf("  %-28s differs in %6ld of %ld%s\n", names[f], differ[f], cases,
                    multiplicand[f] ? "   (multiplied or compared: no guard needed)" : "");
        (multiplicand[f] ? multiplied : guarded) += differ[f];
    }
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
    std::printf("%s (expected: %s; with a known factor: %s)\n", ok && ok_known ? "ok" : "FAILED", expect, factor);
    return ok && ok_known ? 0 : 1;
}
