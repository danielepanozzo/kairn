// A square of the program, a * a, passed straight into each public operation of Kairn through which
// a value of T enters: is its guard kept, or does the compiler drop it (a square is never -0, so
// a * a + 0 has the value of a * a) and fuse the square into the kernel's first addition?
//
// Each form is computed twice, in functions that are not inlined: with the squares written in
// place, and with them rounded first (stored and loaded through a volatile in a function that is
// not inlined). The operands c come in three families: "cancel", c within a few units of -RN(a*a)
// for a sum (of +RN(a*a) for a difference), where a fused result is furthest from the rounded one
// relatively; "same", c within a few units of +RN(a*a) for a sum, where the rounding errors of the
// operation itself are largest; "mixed", c of either sign and of a magnitude within a factor 4 of
// the square's. The program prints, per form, family and type, in how many cases the two results
// differ, and for the first L of those (default 25) a line CASE that check.py reads: the rounded
// squares p and the operands c, which are what the program passed in and define the exact value v
// the operation is about, the results with the squares in place and with them rounded, and what
// the operation claims of v (exactness, rounding, an error bound, an enclosure), so that check.py
// can say whether a fused result violates the claim or only changes bits.
//
//   square_kairn [N [L]]                (default N = 4000 cases per row, L = 25)
//   square_kairn [N [L]] | python3 check.py
//
// Build: c++ -std=c++20 -O2 -ffp-contract=fast -I<kairn>/include square_kairn.cpp (README.md).
#include <kairn/accumulator.hpp>
#include <kairn/ball_vector.hpp>
#include <kairn/batch.hpp>
#include <kairn/kairn.hpp>
#include <kairn/packed.hpp>

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

#if defined(_MSC_VER) && !defined(__clang__)
#define NOINLINE __declspec(noinline)
#define INLINE __forceinline
#else
#define NOINLINE __attribute__((noinline))
#define INLINE inline __attribute__((always_inline))
#endif

namespace {

constexpr int N = 4;  // the squares of one case (the arrays have 2N elements)

template <class T>
NOINLINE T rounded_square(T a) {
    volatile T v = a * a;
    return v;
}
template <class T>
NOINLINE T run_time(T x) {
    volatile T v = x;
    return v;
}

// The square of a[i], in place or rounded (then a holds the rounded squares).
template <class T>
struct InPlace {
    static INLINE T sq(const T* a, int i) { return a[i] * a[i]; }
};
template <class T>
struct Rounded {
    static INLINE T sq(const T* a, int i) { return a[i]; }
};

template <class T>
struct Out {
    T v[8] = {};
};

template <class T>
using E1 = kairn::Expansion<T, 1>;
template <class T>
using E2 = kairn::Expansion<T, 2>;
template <class T>
using P1 = kairn::Packed<T, 1>;
template <class T>
using P2 = kairn::Packed<T, 2>;

// A form: its body computes o from the squares M::sq(a, i) and the operands c[i].
#define FORM(NAME, ...)                                                                          \
    template <class T, class M>                                                                  \
    INLINE void NAME##_body([[maybe_unused]] const T* a, [[maybe_unused]] const T* c, Out<T>& o) { \
        __VA_ARGS__                                                                              \
    }                                                                                            \
    template <class T>                                                                           \
    NOINLINE Out<T> NAME##_in(const T* a, const T* c) {                                          \
        Out<T> o;                                                                                \
        NAME##_body<T, InPlace<T>>(a, c, o);                                                     \
        return o;                                                                                \
    }                                                                                            \
    template <class T>                                                                           \
    NOINLINE Out<T> NAME##_ro(const T* a, const T* c) {                                          \
        Out<T> o;                                                                                \
        NAME##_body<T, Rounded<T>>(a, c, o);                                                     \
        return o;                                                                                \
    }
#define SQ(i) M::sq(a, i)

// --- The building blocks ---------------------------------------------------------------------
FORM(two_sum_c_p, const auto r = kairn::two_sum(c[0], SQ(0)); o.v[0] = r.sum; o.v[1] = r.error;)
FORM(two_sum_p_c, const auto r = kairn::two_sum(SQ(0), c[0]); o.v[0] = r.sum; o.v[1] = r.error;)
FORM(fast_two_sum, const auto r = kairn::fast_two_sum(c[0], SQ(0)); o.v[0] = r.sum; o.v[1] = r.error;)
FORM(add_down, o.v[0] = kairn::add_down(c[0], SQ(0));)
FORM(add_up, o.v[0] = kairn::add_up(c[0], SQ(0));)
FORM(two_prod_1, const auto r = kairn::two_prod(SQ(0), T(1)); o.v[0] = r.product; o.v[1] = r.error;)
FORM(mul_down_1, o.v[0] = kairn::mul_down(SQ(0), T(1));)
FORM(mul_up_1, o.v[0] = kairn::mul_up(SQ(0), T(1));)
// --- Expansion<T, 2> with a T --------------------------------------------------------------------
FORM(e2_plus_t, const E2<T> z = E2<T>(c[0]) + SQ(0); o.v[0] = z.limb[0]; o.v[1] = z.limb[1];)
FORM(t_plus_e2, const E2<T> z = SQ(0) + E2<T>(c[0]); o.v[0] = z.limb[0]; o.v[1] = z.limb[1];)
FORM(e2_minus_t, const E2<T> z = E2<T>(c[0]) - SQ(0); o.v[0] = z.limb[0]; o.v[1] = z.limb[1];)
FORM(e2_plus_assign, E2<T> z = E2<T>(c[0]); z += SQ(0); o.v[0] = z.limb[0]; o.v[1] = z.limb[1];)
FORM(finite_add, const E2<T> z = kairn::finite::add(E2<T>(c[0]), SQ(0)); o.v[0] = z.limb[0]; o.v[1] = z.limb[1];)
FORM(make_2, const E2<T> z = E2<T>(SQ(0)) + E2<T>(c[0]); o.v[0] = z.limb[0]; o.v[1] = z.limb[1];)
FORM(from_limbs, const T l[2] = {SQ(0), T(0)}; const E2<T> z = E2<T>::from_limbs(l) + E2<T>(c[0]);
     o.v[0] = z.limb[0]; o.v[1] = z.limb[1];)
FORM(e2_one_times_t, const E2<T> z = E2<T>(T(1)) * SQ(0) + E2<T>(c[0]); o.v[0] = z.limb[0]; o.v[1] = z.limb[1];)
// --- Interval and Ball ---------------------------------------------------------------------------
FORM(interval1, const kairn::Interval<T, 1> z = kairn::Interval<T, 1>(SQ(0), SQ(0)) + kairn::Interval<T, 1>(c[0], c[0]);
     o.v[0] = z.lower().limb[0]; o.v[2] = z.upper().limb[0];)
FORM(interval2, const kairn::Interval<T, 2> z = kairn::Interval<T, 2>(SQ(0), SQ(0)) + kairn::Interval<T, 2>(c[0], c[0]);
     o.v[0] = z.lower().limb[0]; o.v[1] = z.lower().limb[1]; o.v[2] = z.upper().limb[0]; o.v[3] = z.upper().limb[1];)
FORM(ball1, const kairn::Ball<T, 1> z = kairn::Ball<T, 1>(SQ(0), T(0)) + kairn::Ball<T, 1>(c[0], T(0));
     o.v[0] = z.center().limb[0]; o.v[2] = z.radius();)
FORM(ball1_radius, const kairn::Ball<T, 1> z = kairn::Ball<T, 1>(T(0), SQ(0)) + kairn::Ball<T, 1>(T(0), -c[0]);
     o.v[0] = z.center().limb[0]; o.v[2] = z.radius();)
FORM(ball2, const kairn::Ball<T, 2> z = kairn::Ball<T, 2>(E2<T>(SQ(0)), T(0)) + kairn::Ball<T, 2>(E2<T>(c[0]), T(0));
     o.v[0] = z.center().limb[0]; o.v[1] = z.center().limb[1]; o.v[2] = z.radius();)
FORM(ball1_plus_t, const kairn::Ball<T, 1> z = kairn::Ball<T, 1>(c[0], T(0)) + SQ(0);
     o.v[0] = z.center().limb[0]; o.v[2] = z.radius();)
FORM(ball2_plus_t, const kairn::Ball<T, 2> z = kairn::Ball<T, 2>(E2<T>(c[0]), T(0)) + SQ(0);
     o.v[0] = z.center().limb[0]; o.v[1] = z.center().limb[1]; o.v[2] = z.radius();)
FORM(ball2_one_times_t,const kairn::Ball<T, 2> z = kairn::Ball<T, 2>(E2<T>(T(1)), T(0)) * SQ(0) +
                                                    kairn::Ball<T, 2>(E2<T>(c[0]), T(0));
     o.v[0] = z.center().limb[0]; o.v[1] = z.center().limb[1]; o.v[2] = z.radius();)
// --- Packed -------------------------------------------------------------------------------------
FORM(p1_plus, constexpr int W = P1<T>::lanes; T s[W], t[W]; for (int l = 0; l < W; ++l) { s[l] = SQ(0); t[l] = c[0]; }
     const P1<T> z = P1<T>::load(t) + P1<T>::load(s); o.v[0] = z.lane(0).limb[0];)
FORM(p1_broadcast, const P1<T> z = P1<T>::broadcast(E1<T>(c[0])) + P1<T>::broadcast(E1<T>(SQ(0)));
     o.v[0] = z.lane(0).limb[0];)
FORM(p2_plus_p1,constexpr int W = P1<T>::lanes; T s[W], t[W], u[W] = {};
     for (int l = 0; l < W; ++l) { s[l] = SQ(0); t[l] = c[0]; }
     const P2<T> z = P2<T>::load(t, u) + P1<T>::load(s); o.v[0] = z.lane(0).limb[0]; o.v[1] = z.lane(0).limb[1];)
// --- The accumulator ------------------------------------------------------------------------------
FORM(acc1_add, kairn::Accumulator<T, 1> acc; acc.add(SQ(0)); acc.add(c[0]); const auto b = acc.ball();
     o.v[0] = b.center().limb[0]; o.v[2] = b.radius();)
FORM(acc2_add, kairn::Accumulator<T, 2> acc; acc.add(SQ(0)); acc.add(c[0]); const auto b = acc.ball();
     o.v[0] = b.center().limb[0]; o.v[1] = b.center().limb[1]; o.v[2] = b.radius();)
FORM(acc1_product_1, kairn::Accumulator<T, 1> acc; acc.add_product(SQ(0), T(1)); acc.add(c[0]); const auto b = acc.ball();
     o.v[0] = b.center().limb[0]; o.v[2] = b.radius();)
// --- The functions on arrays ----------------------------------------------------------------------
#define ARRAY(s, z) T s[2 * N]; [[maybe_unused]] T z[2 * N] = {};for (int i = 0; i < N; ++i) { s[2 * i] = SQ(i); s[2 * i + 1] = c[i]; }
FORM(sum1, ARRAY(s, z) const auto r = kairn::sum(kairn::SoAView<const T, 1>(s, 2 * N)); o.v[0] = r.value.limb[0];)
FORM(sum1_seq, ARRAY(s, z) const auto r = kairn::sum(kairn::sequential, kairn::SoAView<const T, 1>(s, 2 * N));
     o.v[0] = r.value.limb[0];)
FORM(sum2, ARRAY(s, z) const auto r = kairn::sum(kairn::SoAView<const T, 2>(s, z, 2 * N));
     o.v[0] = r.value.limb[0]; o.v[1] = r.value.limb[1];)
FORM(map_add1, T s[N], z[N]; for (int i = 0; i < N; ++i) s[i] = SQ(i);
     kairn::add(kairn::SoAView<const T, 1>(s, N), kairn::SoAView<const T, 1>(c, N), kairn::SoAView<T, 1>(z, N));
     o.v[0] = z[0];)
FORM(dot1_ones, ARRAY(s, z) T ones[2 * N]; for (int i = 0; i < 2 * N; ++i) ones[i] = T(1);
     const auto r = kairn::dot(kairn::SoAView<const T, 1>(s, 2 * N), kairn::SoAView<const T, 1>(ones, 2 * N));
     o.v[0] = r.value.limb[0];)
FORM(axpy1, T s[N], z[N]; for (int i = 0; i < N; ++i) s[i] = SQ(i);
     kairn::axpy(T(1), kairn::SoAView<const T, 1>(c, N), kairn::SoAView<const T, 1>(s, N), kairn::SoAView<T, 1>(z, N));
     o.v[0] = z[0];)
// --- Ball vectors ---------------------------------------------------------------------------------
FORM(bv1, std::array<E1<T>, N> x{}, y{}; for (int i = 0; i < N; ++i) { x[i] = E1<T>(SQ(i)); y[i] = E1<T>(c[i]); }
     const kairn::BallVector<T, 1, N> z = kairn::BallVector<T, 1, N>(x, T(0)) + kairn::BallVector<T, 1, N>(y, T(0));
     o.v[0] = z.center(0).limb[0]; o.v[2] = z.radius();)
FORM(bv2, std::array<E2<T>, N> x{}, y{}; for (int i = 0; i < N; ++i) { x[i] = E2<T>(SQ(i)); y[i] = E2<T>(c[i]); }
     const kairn::BallVector<T, 2, N> z = kairn::BallVector<T, 2, N>(x, T(0)) + kairn::BallVector<T, 2, N>(y, T(0));
     o.v[0] = z.center(0).limb[0]; o.v[1] = z.center(0).limb[1]; o.v[2] = z.radius();)

// What each form claims of the value v (check.py says how each is judged):
//   pair: (v0, v1) is exactly v;  rn: v0 is v rounded to nearest;  down, up: v0 <= v, v0 >= v;
//   rel K: |v0 + v1 - v| <= K u^2 |v| / (1 - 4u);  mulrel: the product by Expansion<T, 2>(1) within
//   2u^2 |p|, then the sum within 3u^2/(1 - 4u) of its operands;
//   set: v0 + v1 <= v <= v2 + v3;  ball: |v - v0 - v1| <= v2;
//   sumb B: |v0 + v1 - v| <= unit sum |x| + tiny, with the bound B of 2N terms that main prints
//   (traits<T>::sum, traits<Expansion<T, 2>>::sum, traits<T>::dot);
//   rad: the radius v2 >= v (the sum of two radii).
// And what v is: "+" p + c, "-" c - p, "1" p (a product by 1), "sum" the sum of every p and c,
// "+0" p[0] + c[0] (the first entry of an operation entry by entry), "r" p - c (two radii, c < 0).
template <class T>
struct Row {
    const char* name;
    const char* kind;
    const char* v;
    Out<T> (*in)(const T*, const T*);
    Out<T> (*ro)(const T*, const T*);
};
#define ROW(NAME, KIND, V) {#NAME, KIND, V, &NAME##_in<T>, &NAME##_ro<T>}

std::uint64_t state = 0x9E3779B97F4A7C15ull;
std::uint64_t next() {
    state ^= state << 13;
    state ^= state >> 7;
    state ^= state << 17;
    return state;
}
template <class T>
T unit() {  // in [1/2, 1)
    if (sizeof(T) == 8) return T(0.5 + double(next() >> 11) * 0x1p-54);
    return T(0.5f + float(next() >> 40) * 0x1p-25f);
}
template <class T>
bool same(T x, T y) {
    return std::memcmp(&x, &y, sizeof x) == 0;
}

template <class T>
T operand(const char* family, const char* v, T p, long i, int j) {
    const T near = T(1) + T((i + j) % 7 + 1) * (sizeof(T) == 8 ? T(0x1p-30) : T(0x1p-12));
    const bool minus = std::strcmp(v, "-") == 0, radius = std::strcmp(v, "r") == 0;
    if (std::strcmp(family, "mixed") == 0) {
        // fast_two_sum(c, p) requires |c| >= |p| (v "+f"): there c is from |p| to 4|p|.
        const T m = std::strcmp(v, "+f") == 0 ? p * (T(1) + unit<T>()) * T(1 << (next() % 2))
                                               : p * unit<T>() * T(1 << (next() % 4)) * T(0.5);
        return radius || next() % 2 ? -m : m;
    }
    const bool cancel = std::strcmp(family, "cancel") == 0;
    if (radius) return -p * near;
    return (cancel != minus) ? -p * near : p * near;
}

template <class T>
void run(const char* type, long n, long cases) {
    const Row<T> rows[] = {
        ROW(two_sum_c_p, "pair", "+"),     ROW(two_sum_p_c, "pair", "+"),       ROW(fast_two_sum, "pair", "+f"),
        ROW(add_down, "down", "+"),        ROW(add_up, "up", "+"),              ROW(two_prod_1, "pair", "1"),
        ROW(mul_down_1, "down", "1"),      ROW(mul_up_1, "up", "1"),            ROW(e2_plus_t, "rel 2", "+"),
        ROW(t_plus_e2, "rel 2", "+"),      ROW(e2_minus_t, "rel 2", "-"),       ROW(e2_plus_assign, "rel 2", "+"),
        ROW(finite_add, "rel 2", "+"),     ROW(make_2, "rel 3", "+"),           ROW(from_limbs, "rel 3", "+"),
        ROW(e2_one_times_t, "mulrel", "+"), ROW(interval1, "set", "+"),         ROW(interval2, "set", "+"),
        ROW(ball1, "ball", "+"),           ROW(ball1_radius, "rad", "r"),       ROW(ball2, "ball", "+"),
        ROW(ball1_plus_t, "ball", "+"),    ROW(ball2_plus_t, "ball", "+"),      ROW(ball2_one_times_t, "ball", "+"),
        ROW(p1_plus, "rn", "+"),           ROW(p1_broadcast, "rn", "+"),        ROW(p2_plus_p1, "rel 2", "+"),
        ROW(acc1_add, "ball", "+"),        ROW(acc2_add, "ball", "+"),          ROW(acc1_product_1, "ball", "+"),
        ROW(sum1, "sumb sum1", "sum"),     ROW(sum1_seq, "sumb sum1", "sum"),   ROW(sum2, "sumb sum2", "sum"),
        ROW(map_add1, "rn", "+0"),         ROW(dot1_ones, "sumb dot1", "sum"),  ROW(axpy1, "rn", "+0"),
        ROW(bv1, "ball", "+0"),            ROW(bv2, "ball", "+0"),
    };
    for (const Row<T>& r : rows) {
        for (const char* family : {"cancel", "same", "mixed"}) {
            long differ = 0;
            std::string lines;
            for (long i = 0; i < n; ++i) {
                T a[N], p[N], c[N];
                for (int j = 0; j < N; ++j) {
                    a[j] = unit<T>();
                    p[j] = rounded_square(a[j]);
                    c[j] = operand<T>(family, r.v, p[j], i, j);
                }
                const Out<T> u = r.in(a, c), w = r.ro(p, c);
                bool d = false;
                for (int k = 0; k < 8; ++k) d = d || !same(u.v[k], w.v[k]);
                if (!d || differ++ >= cases) continue;
                char line[1024];
                int m = std::snprintf(line, sizeof line, "CASE %s.%s %s %s %s p", r.name, family, type, r.kind, r.v);
                for (int j = 0; j < N; ++j) m += std::snprintf(line + m, sizeof line - m, " %a", double(p[j]));
                m += std::snprintf(line + m, sizeof line - m, " c");
                for (int j = 0; j < N; ++j) m += std::snprintf(line + m, sizeof line - m, " %a", double(c[j]));
                m += std::snprintf(line + m, sizeof line - m, " in");
                for (int k = 0; k < 4; ++k) m += std::snprintf(line + m, sizeof line - m, " %a", double(u.v[k]));
                m += std::snprintf(line + m, sizeof line - m, " rounded");
                for (int k = 0; k < 4; ++k) m += std::snprintf(line + m, sizeof line - m, " %a", double(w.v[k]));
                std::snprintf(line + m, sizeof line - m, "\n");
                lines += line;
            }
            char name[64];
            std::snprintf(name, sizeof name, "%s.%s", r.name, family);
            std::printf("  %-27s %-6s differs in %5ld of %ld\n%s", name, type, differ, n, lines.c_str());
        }
    }
}

}  // namespace

int main(int argc, char** argv) {
    const long n = argc > 1 ? std::atol(argv[1]) : 4000;
    const long cases = argc > 2 ? std::atol(argv[2]) : 25;
    std::printf("Packed: %d lanes of double\n", kairn::Packed<double, 1>::lanes);
    // The bounds that check.py judges the sums and the dot product against, as the library has them.
    std::printf("BOUND double sum1 %a %a\n", kairn::traits<double>::sum(2 * N).unit, kairn::traits<double>::sum(2 * N).tiny);
    std::printf("BOUND double sum2 %a %a\n", kairn::traits<E2<double>>::sum(2 * N).unit,
                kairn::traits<E2<double>>::sum(2 * N).tiny);
    std::printf("BOUND double dot1 %a %a\n", kairn::traits<double>::dot(2 * N).unit, kairn::traits<double>::dot(2 * N).tiny);
    std::printf("BOUND float sum1 %a %a\n", double(kairn::traits<float>::sum(2 * N).unit),
                double(kairn::traits<float>::sum(2 * N).tiny));
    std::printf("BOUND float sum2 %a %a\n", double(kairn::traits<E2<float>>::sum(2 * N).unit),
                double(kairn::traits<E2<float>>::sum(2 * N).tiny));
    std::printf("BOUND float dot1 %a %a\n", double(kairn::traits<float>::dot(2 * N).unit),
                double(kairn::traits<float>::dot(2 * N).tiny));
    run<double>("double", n, cases);
    run<float>("float", n, cases);
    return 0;
}
