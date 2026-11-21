// BallVector and BallVectorView (kairn/ball_vector.hpp), in the form of Packed this build compiles
// (tests/api/CMakeLists.txt builds it once per form: native, scalar, and avx2 where it applies).
// What the oracle cannot see from the lines of one loop (runner_ball_vector.hpp has the forms it
// judges):
//
// - the types: trivially copyable and standard-layout, the layout of the centers (one array per
//   limb, then the radius), the views, the conversions that exist and those that do not;
// - the constructors: every class of radius given (negative, -inf, NaN, +inf, +0, -0, positive)
//   and centers that are not finite give the whole space or the values given, through each
//   constructor (std::array, a view of centers, the view over the program's arrays), and the copy
//   of a view;
// - the two orders: every operation in the fast order and with kairn::sequential gives the same
//   bits (a zero compared as a zero under MSVC, whose packed code drops the guard's +0), for every
//   length from 0 to 37 and lengths above the lanes;
// - in place: every operation that may write an operand's arrays gives, in place, the bits it gives
//   into other arrays, and x + x in place those of x + x;
// - the value forms (operators, functions returning a BallVector) the bits of the forms with views;
// - against Ball, entry by entry: the one radius of a sum, a difference, a scaling and a scaling by
//   a power of two equals the largest of the radii of the entrywise Ball operations (what the
//   listings compute and what milestone2.md's table says, not a claim: a kernel changed so that it
//   no longer holds would be no fault of the claims, but the documentation says it, so it is
//   tested), and each center is the center of the Ball operation; the product of polynomials is
//   not compared;
// - axpy: bit for bit the two calls it is made of, scale then add in place, in both orders;
// - norm_upper: the argument of its composition, checked exactly on each case: the bound n of the
//   centers is at least the magnitude of every center (|c0| < n, or |c0| = n and the second limb
//   does not add to the magnitude) and b is at least n + r (TwoSum of n and r: b above the sum, or
//   equal with a nonpositive error); and +inf for the whole space;
// - the scaling by a power of two: exact (radius 2^n r, centers 2^n c) for every n in the range
//   where nothing underflows, the steps of ldexp beyond the powers of two of T included.
//
// KAIRN_CHECKS is off: the constructors are given negative radii, which the checks would stop
// (tests/api/checks.cpp tests that they do).
#define KAIRN_CHECKS 0
#include <kairn/ball_vector.hpp>

#include "no_crash_reports.hpp"

#include <array>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <limits>
#include <type_traits>
#include <vector>

#if defined(_MSC_VER) && !defined(__clang__)
#define KAIRN_TEST_ZERO_SIGN_FREE 1
#else
#define KAIRN_TEST_ZERO_SIGN_FREE 0
#endif

namespace {

long checks = 0, failures = 0;
void expect(bool ok, const char* what, long i = -1) {
    ++checks;
    if (ok) return;
    ++failures;
    if (failures <= 20) std::printf("FAILED: %s (case %ld)\n", what, i);
}

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
// Two ball vectors with the same bits: every limb of every center, and the radius.
template <class X, class Y>
bool same(const X& x, const Y& y) {
    if (x.size() != y.size() || !same_limb(x.radius(), y.radius())) return false;
    for (int j = 0; j < X::limbs; ++j)
        for (std::size_t i = 0; i < x.size(); ++i)
            if (!same_limb(x.limb(j)[i], y.limb(j)[i])) return false;
    return true;
}

std::uint64_t state = 0x9E3779B97F4A7C15ull;
std::uint64_t next() {
    state ^= state << 13;
    state ^= state >> 7;
    state ^= state << 17;
    return state;
}
template <class T>
T uniform() {  // in [-1, 1)
    if constexpr (sizeof(T) == 8) {
        return -1.0 + double(next() >> 11) * 0x1p-52;
    } else {
        return -1.0f + float(next() >> 40) * 0x1p-23f;
    }
}
// A random number of K limbs around 2^e, canonical.
template <class T, int K>
kairn::Expansion<T, K> number(int e) {
    const T h = std::ldexp(uniform<T>(), e);
    if constexpr (K == 1) {
        return kairn::Expansion<T, 1>(h);
    } else {
        const T limbs[2] = {h, std::ldexp(uniform<T>(), e - std::numeric_limits<T>::digits - 2)};
        const T l = h + limbs[1] == h ? limbs[1] : T(0);
        const T pair[2] = {h, l};
        return kairn::Expansion<T, 2>::from_limbs(pair);
    }
}

// The arrays of a ball vector as a program holds them, made a ball vector by the view's
// constructor.
template <class T, int K>
struct Arrays {
    std::vector<T> limb[K];
    T r = T(0);
    Arrays(std::size_t n, int e, T radius) : r(radius) {
        for (int j = 0; j < K; ++j) limb[j].resize(n);
        for (std::size_t i = 0; i < n; ++i) {
            const kairn::Expansion<T, K> c = number<T, K>(e + int(next() % 5) - 2);
            for (int j = 0; j < K; ++j) limb[j][i] = c.limb[j];
        }
    }
    explicit Arrays(std::size_t n) {
        for (int j = 0; j < K; ++j) limb[j].assign(n, T(0));
    }
    Arrays(const Arrays&) = delete;
    kairn::SoAView<T, K> soa() {
        if constexpr (K == 1) {
            return kairn::SoAView<T, 1>(limb[0].data(), limb[0].size());
        } else {
            return kairn::SoAView<T, 2>(limb[0].data(), limb[1].data(), limb[0].size());
        }
    }
    kairn::BallVectorView<T, K> view() { return kairn::BallVectorView<T, K>(soa(), r); }
};

// --- The types --------------------------------------------------------------------------------

using BV13 = kairn::BallVector<double, 1, 3>;
using BV24 = kairn::BallVector<double, 2, 4>;
using V1 = kairn::BallVectorView<double, 1>;
using CV1 = kairn::BallVectorView<const double, 1>;
using V2 = kairn::BallVectorView<double, 2>;
using CV2 = kairn::BallVectorView<const double, 2>;
static_assert(std::is_trivially_copyable_v<BV13> && std::is_trivially_copyable_v<BV24>);
static_assert(std::is_standard_layout_v<BV13> && std::is_standard_layout_v<BV24>);
static_assert(sizeof(BV13) == 4 * sizeof(double) && sizeof(BV24) == 9 * sizeof(double));
static_assert(sizeof(kairn::BallVector<float, 2, 5>) == 11 * sizeof(float));
static_assert(std::is_trivially_copyable_v<V1> && std::is_trivially_copyable_v<CV2>);
static_assert(std::is_nothrow_default_constructible_v<BV13> && std::is_nothrow_copy_constructible_v<BV24>);
static_assert(std::is_nothrow_constructible_v<BV13, const std::array<kairn::Expansion<double, 1>, 3>&, double>);
static_assert(std::is_convertible_v<V1, CV1> && !std::is_convertible_v<CV1, V1>);
static_assert(std::is_convertible_v<BV13&, V1> && std::is_convertible_v<const BV13&, CV1>);
static_assert(!std::is_convertible_v<const BV13&, V1>);
static_assert(!std::is_convertible_v<CV1, BV13> && std::is_constructible_v<BV13, CV1>);
static_assert(!std::is_default_constructible_v<V1>);
static_assert(BV13::size() == 3 && BV24::limbs == 2);
static_assert(std::is_same_v<BV24::value_type, kairn::Ball<double, 2>>);
// The accessors are constexpr; the whole space and the point 0 too.
constexpr BV24 whole_space = BV24::whole();
static_assert(whole_space.is_whole() && !whole_space.is_finite() && whole_space.center(3).limb[0] == 0);
static_assert(BV13().is_finite() && BV13().radius() == 0 && BV13().entry(2).radius() == 0);
static_assert(BV24::whole().entry(1).is_whole());

// What the functions accept, and what they refuse (the compile-fail cases are api.reject.ball_vector.*).
template <class X, class Y, class Z>
concept addable = requires(const X& x, const Y& y, Z&& z) { kairn::add(x, y, static_cast<Z&&>(z)); };
static_assert(addable<BV13, BV13, BV13&> && addable<BV13, CV1, V1> && addable<CV1, V1, V1>);
static_assert(addable<CV1, CV1, BV13&> && addable<V1, BV13, const V1&>);
static_assert(!addable<BV13, BV13, const BV13&>);                  // a const BallVector is not written
static_assert(!addable<BV13, BV13, BV13>);                         // nor a temporary one
static_assert(!addable<BV13, BV13, CV1>);                          // nor a view of const limbs
static_assert(!addable<BV13, kairn::BallVector<double, 1, 4>, BV13&>);   // lengths fixed and different
static_assert(!addable<BV13, kairn::BallVector<float, 1, 3>, BV13&>);    // limb types
static_assert(!addable<BV13, kairn::BallVector<double, 2, 3>, BV13&>);   // limbs
static_assert(!addable<BV13, kairn::Ball<double, 1>, BV13&>);           // a Ball is not a ball vector
template <class X, class Y, class Z>
concept multipliable = requires(const X& x, const Y& y, Z&& z) { kairn::convolution(x, y, static_cast<Z&&>(z)); };
static_assert(multipliable<BV13, BV24, kairn::BallVector<double, 2, 6>&> == false);
static_assert(multipliable<BV13, kairn::BallVector<double, 1, 4>, kairn::BallVector<double, 1, 6>&>);
static_assert(!multipliable<BV13, kairn::BallVector<double, 1, 4>, kairn::BallVector<double, 1, 7>&>);
static_assert(multipliable<CV1, CV1, V1>);
static_assert(std::is_same_v<decltype(kairn::convolution(BV13(), kairn::BallVector<double, 1, 5>())),
                             kairn::BallVector<double, 1, 7>>);

// --- The constructors ---------------------------------------------------------------------------

template <class T, int K>
void constructors() {
    using L = std::numeric_limits<T>;
    using E = kairn::Expansion<T, K>;
    const T inf = L::infinity(), nan = L::quiet_NaN();
    const std::array<E, 3> c = {number<T, K>(0), number<T, K>(3), number<T, K>(-40)};
    // Each class of radius: the whole space, or the radius given.
    const T radii[] = {-T(1), -inf, nan, inf, T(0), -T(0), T(0.25), L::denorm_min(), (L::max)()};
    for (T r : radii) {
        const bool whole = !(r >= 0) || r == inf;
        const kairn::BallVector<T, K, 3> x(c, r);
        expect(x.is_whole() == whole && x.is_finite() == !whole, "the constructor: the state");
        Arrays<T, K> a(3, 0, r);
        for (int j = 0; j < K; ++j)
            for (std::size_t i = 0; i < 3; ++i) a.limb[j][i] = c[i].limb[j];
        const kairn::BallVectorView<T, K> v = a.view();
        expect(same(x, v), "the view's constructor: the bits of BallVector's");
        const kairn::BallVector<T, K, 3> w(kairn::SoAView<const T, K>(Arrays<T, K>(3).soa()), r);
        expect(w.is_whole() == whole, "the constructor from a view of centers: the state");
        if (whole) {
            for (std::size_t i = 0; i < 3; ++i)
                for (int j = 0; j < K; ++j) expect(x.center(i).limb[j] == 0, "the whole space: every center zero");
            expect(x.radius() == inf, "the whole space: the radius +inf");
            expect(a.r == inf && a.limb[0][1] == 0, "the view's constructor writes the whole space into the arrays");
        } else {
            expect(x.radius() == r, "the radius given");
            for (std::size_t i = 0; i < 3; ++i)
                for (int j = 0; j < K; ++j) expect(x.center(i).limb[j] == c[i].limb[j], "the centers given");
        }
        // The copy of a view: the same bits. A part of a read-only view: its entries, the same radius.
        expect(same(kairn::BallVector<T, K, 3>(v), v), "BallVector(view): a copy");
        const kairn::BallVectorView<const T, K> part = kairn::BallVectorView<const T, K>(v).subview(1, 2);
        expect(part.size() == 2 && same_limb(part.radius(), v.radius()) && part.limb(0) == v.limb(0) + 1 &&
                   part.limb(K - 1) == v.limb(K - 1) + 1,
               "subview");
    }
    // A center that is not finite: the whole space, whatever the radius.
    for (T bad : {inf, -inf, nan}) {
        std::array<E, 3> d = c;
        d[1] = E(bad);
        const kairn::BallVector<T, K, 3> x(d, T(1));
        expect(x.is_whole() && x.center(1).limb[0] == 0, "a center that is not finite: the whole space");
    }
    // entry(i): center i and the shared radius, a copy.
    const kairn::BallVector<T, K, 3> x(c, T(0.5));
    for (std::size_t i = 0; i < 3; ++i) {
        const kairn::Ball<T, K> b = x.entry(i);
        expect(b.radius() == T(0.5) && b.center().limb[0] == c[i].limb[0], "entry(i)");
    }
    expect(x.centers().size() == 3 && x.centers().get(2).limb[0] == c[2].limb[0], "centers()");
    // A view sees what its BallVector holds, and what an operation writes there.
    kairn::BallVector<T, K, 3> y = x;
    kairn::BallVectorView<T, K> yv = y;
    kairn::neg(yv, yv);
    expect(y.center(0).limb[0] == -c[0].limb[0] && y.radius() == T(0.5), "an operation through a view of a BallVector");
}

// --- Every operation: the two orders, in place, the value forms, Ball entry by entry ------------

template <class T, int K>
kairn::Ball<T, K> ball_of(const kairn::BallVectorView<const T, K>& x, std::size_t i) {
    return x.entry(i);
}

template <class T, int K>
void operations(std::size_t n, int e, long id) {
    using L = std::numeric_limits<T>;
    // Radii from zero to about the centers, now and then the whole space.
    const int re = e - int(next() % 40);
    const T rx = next() % 9 == 0 ? T(0) : std::ldexp(T(0.5) + T(0.5) * std::fabs(uniform<T>()), re);
    const T ry = next() % 11 == 0 ? L::infinity() : std::ldexp(T(0.5) + T(0.5) * std::fabs(uniform<T>()), re - 3);
    Arrays<T, K> ax(n, e, rx), ay(n, e + int(next() % 3) - 1, ry);
    const kairn::BallVectorView<T, K> xv = ax.view(), yv = ay.view();
    const kairn::BallVectorView<const T, K> x = xv, y = yv;
    const T a = std::ldexp(uniform<T>(), int(next() % 9) - 4);
    const int p = int(next() % 64) - 32;
    {
        Arrays<T, K> z(n);
        auto zv = z.view();
        kairn::neg(x, zv);
        Arrays<T, K> s(n);
        auto sv = s.view();
        kairn::neg(kairn::sequential, x, sv);
        expect(same(zv, sv), "neg: the orders", id);
        Arrays<T, K> c(n);
        for (int j = 0; j < K; ++j) c.limb[j] = ax.limb[j];
        c.r = ax.r;
        auto cv = kairn::BallVectorView<T, K>(c.soa(), c.r);
        kairn::neg(cv, cv);
        expect(same(cv, zv), "neg: in place", id);
        for (std::size_t i = 0; i < n; ++i) {
            const kairn::Ball<T, K> b = -ball_of(x, i);
            expect(same_limb(b.radius(), zv.radius()) && b.center().limb[0] == zv.center(i).limb[0],
                   "neg: the Ball of each entry", id);
        }
    }
    // The sum, the difference, the scalings, with the largest entrywise Ball radius.
    struct Op {
        const char* name;
        int kind;  // 0 add, 1 sub, 2 scale, 3 ldexp, 4 half, 5 axpy
    };
    for (const Op op : {Op{"add", 0}, Op{"sub", 1}, Op{"scale", 2}, Op{"ldexp", 3}, Op{"half", 4}, Op{"axpy", 5}}) {
        Arrays<T, K> z1(n), z2(n), z3(n);
        auto v1 = z1.view(), v2 = z2.view(), v3 = z3.view();
        Arrays<T, K> c(n);
        for (int j = 0; j < K; ++j) c.limb[j] = ax.limb[j];
        c.r = ax.r;
        auto cv = kairn::BallVectorView<T, K>(c.soa(), c.r);
        switch (op.kind) {
            case 0:
                kairn::add(x, y, v1), kairn::add(kairn::sequential, x, y, v2), kairn::add(cv, y, cv);
                break;
            case 1:
                kairn::sub(x, y, v1), kairn::sub(kairn::sequential, x, y, v2), kairn::sub(cv, y, cv);
                break;
            case 2:
                kairn::scale(x, a, v1), kairn::scale(kairn::sequential, x, a, v2), kairn::scale(cv, a, cv);
                break;
            case 3:
                kairn::ldexp(x, p, v1), kairn::ldexp(kairn::sequential, x, p, v2), kairn::ldexp(cv, p, cv);
                break;
            case 4:
                kairn::half(x, v1), kairn::half(kairn::sequential, x, v2), kairn::half(cv, cv);
                break;
            default:
                kairn::axpy(a, x, y, v1), kairn::axpy(kairn::sequential, a, x, y, v2), kairn::axpy(a, cv, y, cv);
                // The composition: scale into z, then add in place.
                kairn::scale(x, a, v3);
                kairn::add(v3, y, v3);
                expect(same(v1, v3), "axpy: the two calls it is made of", id);
                kairn::scale(kairn::sequential, x, a, v3);
                kairn::add(kairn::sequential, v3, y, v3);
                expect(same(v2, v3), "axpy: the two calls it is made of, sequential", id);
                break;
        }
        expect(same(v1, v2), op.name, id);
        expect(same(cv, v1), op.name, id);
        if (op.kind == 5 || !v1.is_finite() || n == 0) continue;
        // Entry by entry: the center of the Ball operation, and the largest of the radii.
        T largest = T(0);
        bool centers = true;
        for (std::size_t i = 0; i < n; ++i) {
            const kairn::Ball<T, K> bx = ball_of(x, i), by = ball_of(y, i);
            const kairn::Ball<T, K> b = op.kind == 0   ? bx + by
                                        : op.kind == 1 ? bx - by
                                        : op.kind == 2 ? bx * a
                                        : op.kind == 3 ? kairn::ldexp(bx, p)
                                                       : kairn::half(bx);
            if (b.radius() > largest) largest = b.radius();
            // As values: the sign of a zero is not specified (a guard or a negation may give either).
            for (int j = 0; j < K; ++j) centers = centers && b.center().limb[j] == v1.center(i).limb[j];
        }
        expect(centers, "the centers are those of the Ball operation, entry by entry", id);
        expect(largest == v1.radius(), "the one radius is the largest of the entrywise Ball radii", id);
    }
    // The bound of the members, and the argument of its composition, exactly.
    {
        const T b = kairn::norm_upper(x), bs = kairn::norm_upper(kairn::sequential, x);
        expect(same_limb(b, bs), "norm_upper: the orders", id);
        if (x.is_whole()) {
            expect(b == L::infinity(), "norm_upper of the whole space", id);
        } else {
            T m = T(0);
            for (std::size_t i = 0; i < n; ++i) m = std::fabs(x.limb(0)[i]) > m ? std::fabs(x.limb(0)[i]) : m;
            // n, the bound of the centers: m for one limb, its successor for two.
            const T nb = K == 1 ? m : std::nextafter(m, L::infinity());
            for (std::size_t i = 0; i < n; ++i) {
                const T c0 = std::fabs(x.limb(0)[i]);
                const T c1 = K == 2 ? (x.limb(0)[i] >= 0 ? x.limb(K - 1)[i] : -x.limb(K - 1)[i]) : T(0);
                expect(nb > c0 || (nb == c0 && !(c1 > 0)), "norm_upper: n bounds each center", id);
            }
            // TwoSum of n and r, exact: b is at least the exact sum.
            const T s = nb + x.radius(), bb = s - nb, err = (nb - (s - bb)) + (x.radius() - bb);
            expect(b > s || (b == s && !(err > 0)), "norm_upper: b is at least n + r", id);
        }
    }
}

template <class T, int K, std::size_t N>
void value_forms(int e, long id) {
    Arrays<T, K> ax(N, e, std::ldexp(T(1), e - 20)), ay(N, e, std::ldexp(T(1), e - 25));
    std::array<kairn::Expansion<T, K>, N> cx, cy;
    for (std::size_t i = 0; i < N; ++i) {
        for (int j = 0; j < K; ++j) {
            cx[i].limb[j] = ax.limb[j][i];
            cy[i].limb[j] = ay.limb[j][i];
        }
    }
    const kairn::BallVector<T, K, N> x(cx, ax.r), y(cy, ay.r);
    const auto xv = ax.view(), yv = ay.view();
    const T a = T(3) * uniform<T>();
    Arrays<T, K> z(N);
    auto zv = z.view();
    kairn::add(xv, yv, zv);
    expect(same(x + y, zv), "x + y: the bits of add", id);
    kairn::BallVector<T, K, N> w = x;
    w += y;
    expect(same(w, zv), "x += y", id);
    kairn::sub(xv, yv, zv);
    expect(same(x - y, zv), "x - y", id);
    w = x;
    w -= y;
    expect(same(w, zv), "x -= y", id);
    kairn::scale(xv, a, zv);
    expect(same(x * a, zv) && same(a * x, zv), "x a, a x", id);
    w = x;
    w *= a;
    expect(same(w, zv), "x *= a", id);
    kairn::neg(xv, zv);
    expect(same(-x, zv), "-x", id);
    kairn::ldexp(xv, -7, zv);
    expect(same(kairn::ldexp(x, -7), zv) && same(kairn::ldexp(kairn::sequential, x, -7), zv), "ldexp(x, n)", id);
    kairn::half(xv, zv);
    expect(same(kairn::half(x), zv) && same(kairn::half(kairn::sequential, x), zv), "half(x)", id);
    kairn::axpy(a, xv, yv, zv);
    expect(same(kairn::axpy(a, x, y), zv) && same(kairn::axpy(kairn::sequential, a, x, y), zv), "axpy(a, x, y)", id);
    expect(same_limb(kairn::norm_upper(x), kairn::norm_upper(xv)), "norm_upper(x)", id);
    // x + x in place: the bits of x + x.
    w = x;
    w += w;
    expect(same(w, x + x), "x += x", id);
    // The product: the value form, the views, against Ball on each coefficient.
    Arrays<T, K> p(2 * N - 1);
    auto pv = p.view();
    kairn::convolution(xv, yv, pv);
    const auto q = kairn::convolution(x, y);
    expect(same(q, pv) && same(kairn::convolution(kairn::sequential, x, y), pv), "convolution(x, y)", id);
}

// The scaling by a power of two is exact where nothing underflows, the steps of ldexp included:
// centers around 2^e (second limbs about 2^-p below them) and a radius 2^(e - 3), with e chosen so
// that every limb of 2^n X is a normal number, and below the largest finite number over 2^4.
template <class T, int K>
void exact_scaling() {
    using L = std::numeric_limits<T>;
    for (int n : {1, -1, 5, -5, L::max_exponent - 4, -(L::max_exponent - 4), 2 * L::max_exponent - 100,
                  -(2 * L::max_exponent - 100)}) {
        const int e = n > 0 ? L::min_exponent + L::digits + 8 : L::max_exponent - 8;
        Arrays<T, K> a(17, e, std::ldexp(T(1), e - 3));
        if constexpr (K == 2)
            for (std::size_t i = 0; i < 17; ++i)
                if (std::fabs(std::ldexp(a.limb[1][i], n)) < (L::min)() * 2 || std::fabs(a.limb[1][i]) < (L::min)() * 2)
                    a.limb[1][i] = 0;
        const auto x = a.view();
        Arrays<T, K> z(17);
        auto zv = z.view();
        kairn::ldexp(x, n, zv);
        bool exact = x.is_finite() && zv.radius() == std::ldexp(x.radius(), n);
        for (std::size_t i = 0; i < 17; ++i)
            for (int j = 0; j < K; ++j) exact = exact && zv.limb(j)[i] == std::ldexp(x.limb(j)[i], n);
        expect(exact, "ldexp: exact where nothing underflows", n);
    }
}

template <class T, int K>
void run(long cases) {
    constructors<T, K>();
    exact_scaling<T, K>();
    const int top = std::numeric_limits<T>::max_exponent;
    for (long i = 0; i < cases; ++i) {
        const std::size_t n = i < 38 ? std::size_t(i) : std::size_t(next() % 200);
        const int e = int(next() % 80) - 40 + (i % 50 == 0 ? top - 6 : 0) - (i % 70 == 0 ? top - 30 : 0);
        operations<T, K>(n, e, i);
    }
    for (long i = 0; i < 20; ++i) {
        value_forms<T, K, 1>(int(i), i);
        value_forms<T, K, 3>(int(i), i);
        value_forms<T, K, 4>(-int(i), i);
        value_forms<T, K, 9>(int(i), i);
    }
}

}  // namespace

int main() {
    kairn_test::no_crash_reports();
    run<double, 1>(600);
    run<double, 2>(600);
    run<float, 1>(600);
    run<float, 2>(600);
    std::printf("ball_vector (Packed with %d lanes of double): %ld checks, %ld failures%s\n",
                kairn::Packed<double, 1>::lanes, checks, failures,
                KAIRN_TEST_ZERO_SIGN_FREE ? " (a zero limb compared as a zero: MSVC)" : "");
    return failures == 0 ? 0 : 1;
}
