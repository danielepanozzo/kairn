// api.upward.differential: every operation of kairn::upward::Interval<T> and every function on
// arrays against the default kairn::Interval<T, 1> on the same operands (the design page, "Tests
// and CI"), for double and float. Requires the rounding mode upward set by kairn::upward::Scope and
// the options of docs/concepts/upward.md (GCC and Clang -frounding-math, MSVC /fp:strict): built
// with kairn::upward.
//
//   differential LINES   writes every upward result as a completed line of the line protocol to
//                        LINES, for the oracle to judge in exact arithmetic (differential.cmake);
//                        exit 0 if every comparison with the default type passed
//
// The operands: every pair of a list of special intervals (the empty set, the whole line, the
// half-lines, zero and the zero bounds, points, bounds at Omega and below the normal range, products
// of bounds below 2^(2p-1) eta), every special interval with every special number (zeros, Omega,
// eta, the infinities, a NaN), every pair of special values given to the constructor, and random
// intervals of every magnitude. Each operation of the default type is computed outside any scope,
// each upward one inside a kairn::upward::Scope (the exact ones too, which may run in any mode),
// the values crossing through memory. What is compared (the design page, "Differences from the
// default interval"):
//
// - the sums, the differences, the operations with a number but the product, the negation, the hull,
//   the intersection, the constructor, the conversions both ways and lower() and upper(): the same
//   set, the same bounds but for the sign of a zero;
// - the products, with an interval and with a number (the default x Interval(t)): inside the
//   default's, empty exactly when it is, and the same set when no product of a finite bound of X and
//   a finite bound of Y is nonzero and below P = 2^(2p-1) eta, where the default product may be one
//   number of T wider;
// - the predicates (is_empty, is_whole, is_finite, contains, certainly_*), the three-valued
//   comparisons and kairn::upward::member, and the relations of ieee1788: the same answers;
// - the functions on arrays, on the whole list of pairs (so that the registers of the array form and
//   the elements after them both compute some): bit for bit the operators of Interval<T>, the signs
//   of zero included, but for the bits of a NaN, and in place the same.
//
// Every operation is written as a program writes it: unmarked where gen/upward.hpp says its kernel
// is proved, with kairn::unverified otherwise (both compile in every state).
#include <kairn/upward.hpp>

#include <algorithm>
#include <bit>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <limits>
#include <random>
#include <string>
#include <vector>

namespace {

template <class T>
using U = kairn::upward::Interval<T>;
template <class T>
using D = kairn::Interval<T, 1>;
namespace up = kairn::upward;

#define PROVED(KERNEL) kairn::gen::upward::bounds::KERNEL<T>::proved
#define AS(KERNEL, x)                             \
    [&] {                                         \
        if constexpr (PROVED(KERNEL)) return (x); \
        else return kairn::unverified(x);         \
    }()
#define AS_BOTH(K1, K2, x)                                  \
    [&] {                                                   \
        if constexpr (PROVED(K1) && PROVED(K2)) return (x); \
        else return kairn::unverified(x);                   \
    }()

long compared = 0, failed = 0;

void report(const char* what, const std::string& detail) {
    ++failed;
    if (failed <= 40) std::printf("FAILED: %s: %s\n", what, detail.c_str());
}

std::string hex(double v) {
    if (v != v) return "nan";
    if (v == std::numeric_limits<double>::infinity()) return "inf";
    if (v == -std::numeric_limits<double>::infinity()) return "-inf";
    char buf[64];
    std::snprintf(buf, sizeof buf, "%a", v);
    return buf;
}
template <class T>
const char* format_name() {
    return sizeof(T) == 8 ? "binary64" : "binary32";
}
// The same bits, or two NaN: the bits of a NaN are not specified (the design page, "The printers":
// the register form makes the NaN of an empty product with every bit set, the NEON array form the
// constant quiet NaN), and no claim compares NaNs.
template <class T>
bool same_bits(T a, T b) {
    if (a != a && b != b) return true;
    if constexpr (sizeof(T) == 8) {
        return std::bit_cast<std::uint64_t>(a) == std::bit_cast<std::uint64_t>(b);
    } else {
        return std::bit_cast<std::uint32_t>(a) == std::bit_cast<std::uint32_t>(b);
    }
}

// The completed lines for the oracle.
std::ofstream* lines = nullptr;
long written = 0;
template <class T>
void line(const char* kernel, std::initializer_list<T> in, std::initializer_list<T> out,
          std::initializer_list<bool> masks = {}) {
    std::string s = kernel;
    s += ' ';
    s += format_name<T>();
    for (T v : in) s += ' ' + hex(static_cast<double>(v));
    s += " ->";
    for (T v : out) s += ' ' + hex(static_cast<double>(v));
    for (bool m : masks) s += m ? " 1" : " 0";
    s += '\n';
    *lines << s;
    ++written;
}

// The stored pair of an upward interval, and the default interval of the same set.
template <class T>
struct Pair {
    T u, n;
};
template <class T>
Pair<T> limbs(const U<T>& x) {
    T p[2] = {};
    x.to_limbs(p);
    return {p[0], p[1]};
}
// The interval of a stored pair, as a program loads one: from_limbs.
template <class T>
U<T> state(Pair<T> z) {
    const T p[2] = {z.u, z.n};
    return U<T>::from_limbs(p);
}
template <class T>
D<T> as_default(Pair<T> z) {
    if (z.u != z.u) return D<T>::empty();
    return D<T>::from_bounds(-z.n, z.u);
}
template <class T>
std::string text(const D<T>& x) {
    return "[" + hex(static_cast<double>(x.lower().limb[0])) + ", " + hex(static_cast<double>(x.upper().limb[0])) + "]";
}
template <class T>
std::string text(Pair<T> z) {
    return "(" + hex(static_cast<double>(z.u)) + ", " + hex(static_cast<double>(z.n)) + ")";
}
// The same set: both empty, or the same bounds, a zero of either sign.
template <class T>
bool same_set(const D<T>& a, const D<T>& b) {
    return a.lower().limb[0] == b.lower().limb[0] && a.upper().limb[0] == b.upper().limb[0];
}
template <class T>
bool canonical(Pair<T> z) {
    if (z.u != z.u || z.n != z.n) return z.u != z.u && z.n != z.n;
    const T inf = std::numeric_limits<T>::infinity();
    return z.u > -inf && z.n > -inf && -z.n <= z.u;
}
void check(bool ok, const char* what, const std::string& detail) {
    ++compared;
    if (!ok) report(what, detail);
}
template <class T>
void check_set(Pair<T> got, const D<T>& want, const char* what, const std::string& operands) {
    check(canonical(got) && same_set(as_default(got), want), what,
          operands + ": " + text(got) + ", the default " + text(want));
}

// Whether a and c are finite, nonzero, and |a c| < P = 2^(2p-1) eta, exactly.
template <class T>
bool tiny_product(T a, T c) {
    if (!std::isfinite(a) || !std::isfinite(c) || a == 0 || c == 0) return false;
    constexpr int log2_p = std::numeric_limits<T>::digits - 1 + std::numeric_limits<T>::min_exponent;
    const int ea = std::ilogb(a), ec = std::ilogb(c), e = ea + ec;  // |a c| in [2^e, 2^(e+2))
    if (e >= log2_p) return false;
    if (e + 2 <= log2_p) return true;
    const T ma = std::scalbn(std::fabs(a), -ea), mc = std::scalbn(std::fabs(c), -ec);  // in [1, 2)
    return std::fma(ma, mc, T(-2)) < 0;  // the sign of ma mc - 2, exactly
}
// Whether the default product of x and y may be wider than the exactly rounded one.
template <class T>
bool may_be_wider(const D<T>& x, const D<T>& y) {
    if (x.is_empty() || y.is_empty()) return false;
    const T xb[2] = {x.lower().limb[0], x.upper().limb[0]}, yb[2] = {y.lower().limb[0], y.upper().limb[0]};
    for (T a : xb)
        for (T c : yb)
            if (tiny_product(a, c)) return true;
    return false;
}
// The products compared where the default one may be wider, and those of them where it was.
long below_p = 0, tighter = 0;
template <class T>
void check_product(Pair<T> got, const D<T>& x, const D<T>& y, const D<T>& want, const char* what,
                   const std::string& operands) {
    const D<T> g = as_default(got);
    const bool wider = may_be_wider(x, y);
    const bool ok = canonical(got) && g.is_empty() == want.is_empty() && (wider ? want.contains(g) : same_set(g, want));
    check(ok, what, operands + ": " + text(got) + ", the default " + text(want));
    below_p += wider;
    tighter += wider && ok && !same_set(g, want);
}

// --- The operands --------------------------------------------------------------------------------

// small: a magnitude whose square is below P; below_p: below P, so its product with 1 is.
template <class T>
struct Scales;
template <>
struct Scales<double> {
    static constexpr double small = 0x1p-500, below_p = 0x1.8p-970;
};
template <>
struct Scales<float> {
    static constexpr float small = 0x1p-60f, below_p = 0x1.8p-103f;
};
template <class T>
struct Values : Scales<T> {
    static constexpr T inf = std::numeric_limits<T>::infinity();
    static constexpr T nan = std::numeric_limits<T>::quiet_NaN();
    static constexpr T omega = std::numeric_limits<T>::max();
    static constexpr T lambda = std::numeric_limits<T>::min();
    static constexpr T eta = std::numeric_limits<T>::denorm_min();
    static constexpr T p = T(1) + std::numeric_limits<T>::epsilon();
};

template <class T>
std::vector<D<T>> special_intervals() {
    using V = Values<T>;
    const T b[][2] = {
        {V::inf, -V::inf}, {-V::inf, V::inf}, {T(0), T(0)}, {T(-0.0), T(0)}, {T(1), V::inf}, {-V::inf, T(-1)},
        {T(0), V::inf}, {-V::inf, T(0)}, {T(-3), V::inf}, {-V::inf, T(2)}, {T(1), T(1)}, {T(-1), T(-1)},
        {V::p, V::p}, {-V::p, V::p}, {T(0), T(1)}, {T(-1), T(0)}, {T(-1), T(2)}, {T(-2), T(-1)}, {T(1), T(3)},
        {V::omega, V::omega}, {-V::omega, -V::omega}, {V::omega / 2, V::omega}, {-V::omega, V::omega},
        {V::omega, V::inf}, {-V::inf, -V::omega}, {V::eta, V::eta}, {-V::eta, V::eta}, {V::eta, 2 * V::eta},
        {V::lambda / 2, V::lambda}, {V::lambda, T(1)}, {V::small, V::small}, {-V::small, 2 * V::small},
        {V::below_p, T(1)}, {T(-1), V::below_p}, {T(0x1.5p-3), T(0x1.9p+2)},
    };
    std::vector<D<T>> v;
    for (const auto& x : b) v.push_back(D<T>::from_bounds(x[0], x[1]));
    return v;
}
template <class T>
std::vector<T> special_numbers() {
    using V = Values<T>;
    return {T(0), T(-0.0), T(1), T(-1), V::p, T(0.5), V::omega, -V::omega, V::eta, -V::eta, V::lambda,
            V::small, V::below_p, V::inf, -V::inf, V::nan, T(-0x1.7p+5)};
}
// Random intervals: bounds of every magnitude and both signs, some of them a zero or an infinity.
template <class T>
std::vector<D<T>> random_intervals(std::mt19937_64& rng, int count) {
    using V = Values<T>;
    constexpr int lo_e = std::numeric_limits<T>::min_exponent - std::numeric_limits<T>::digits;
    constexpr int hi_e = std::numeric_limits<T>::max_exponent;
    std::uniform_int_distribution<int> kind(0, 15), e(lo_e, hi_e - 1), near(-8, 8), sign(0, 1);
    std::uniform_real_distribution<T> m(T(0.5), T(1));
    const auto value = [&]() -> T {
        const int k = kind(rng);
        if (k == 0) return T(0);
        if (k == 1) return sign(rng) ? V::inf : -V::inf;
        const T mag = k < 9 ? std::ldexp(m(rng), near(rng)) : std::ldexp(m(rng), e(rng));
        return sign(rng) ? -mag : mag;
    };
    std::vector<D<T>> v;
    while (int(v.size()) < count) {
        T a = value(), b = value();
        if (b < a) std::swap(a, b);
        if (a == V::inf || b == -V::inf) continue;
        v.push_back(D<T>::from_bounds(a, b));
    }
    return v;
}

// --- The differential ----------------------------------------------------------------------------

template <class T>
void run(std::mt19937_64& rng) {
    std::vector<D<T>> xs = special_intervals<T>();
    const std::size_t n_special = xs.size();
    const std::vector<D<T>> random = random_intervals<T>(rng, 40);
    xs.insert(xs.end(), random.begin(), random.end());
    const std::vector<T> ts = special_numbers<T>();
    const std::size_t n = xs.size();
    // The pairs: every pair of special intervals, and the random intervals with every interval.
    std::vector<std::size_t> pi, pj;
    for (std::size_t i = 0; i < n; ++i)
        for (std::size_t j = 0; j < n; ++j)
            if (i < n_special || j < n_special || i == j || (i + j) % 7 == 0) {
                pi.push_back(i);
                pj.push_back(j);
            }
    const std::size_t np = pi.size(), nt = ts.size();
    const char* f = sizeof(T) == 8 ? "double" : "float";
    std::printf("%s: %zu intervals (%zu special), %zu pairs, %zu numbers\n", f, n, n_special, np, nt);

    // The operands as upward states (the conversion from the default type), outside any scope.
    std::vector<Pair<T>> s(n);
    for (std::size_t i = 0; i < n; ++i) s[i] = limbs(U<T>(AS(upward_from_interval_1, xs[i])));

    // The upward results, each inside a Scope.
    enum { add, sub, mul, hull, meet, nbin };
    std::vector<Pair<T>> bin(np * nbin);
    std::vector<unsigned char> rel(np * 6);
    std::vector<kairn::Trit> cmp(np * 6);
    enum { plus, minus, rminus, times, rplus, rtimes, nnum };
    std::vector<Pair<T>> num(n * nt * nnum);
    std::vector<unsigned char> member(n * (nt + 2) * 2);
    std::vector<Pair<T>> neg(n), round(n);
    std::vector<T> lower(n), upper(n);
    std::vector<D<T>> back(n);
    std::vector<unsigned char> pred(n * 6);
    {
        up::Scope scope;
        for (std::size_t k = 0; k < np; ++k) {
            const U<T> x = state(s[pi[k]]), y = state(s[pj[k]]);
            bin[k * nbin + add] = limbs(AS(upward_add_1, x) + y);
            bin[k * nbin + sub] = limbs(AS(upward_sub_1, x) - y);
            bin[k * nbin + mul] = limbs(AS(upward_mul_1, x) * y);
            bin[k * nbin + hull] = limbs(x.hull(AS(upward_hull_1, y)));
            bin[k * nbin + meet] = limbs(x.intersection(AS(upward_intersection_1, y)));
            rel[k * 6 + 0] = y.contains(AS(upward_subset_1, x));
            rel[k * 6 + 1] = up::ieee1788::subset(AS(upward_subset_1, x), y);
            rel[k * 6 + 2] = up::ieee1788::equal(AS(upward_rel_equal_1, x), y);
            rel[k * 6 + 3] = up::ieee1788::interior(AS(upward_rel_interior_1, x), y);
            rel[k * 6 + 4] = up::ieee1788::disjoint(AS(upward_rel_disjoint_1, x), y);
            cmp[k * 6 + 0] = up::less(AS(upward_less_1, x), y);
            cmp[k * 6 + 1] = up::less_equal(AS(upward_less_equal_1, x), y);
            cmp[k * 6 + 2] = up::equal(AS(upward_equal_1, x), y);
            cmp[k * 6 + 3] = up::greater(AS(upward_less_1, x), y);
            cmp[k * 6 + 4] = up::greater_equal(AS(upward_less_equal_1, x), y);
            cmp[k * 6 + 5] = up::not_equal(AS(upward_equal_1, x), y);
        }
        for (std::size_t i = 0; i < n; ++i) {
            const U<T> x = state(s[i]);
            for (std::size_t k = 0; k < nt; ++k) {
                const T t = ts[k];
                Pair<T>* r = &num[(i * nt + k) * nnum];
                r[plus] = limbs(AS(upward_add_num_1, x) + t);
                r[minus] = limbs(AS(upward_add_num_1, x) - t);
                r[rminus] = limbs(t - AS_BOTH(upward_add_num_1, upward_neg_1, x));
                r[times] = limbs(AS(upward_mul_num_1, x) * t);
                r[rplus] = limbs(t + AS(upward_add_num_1, x));
                r[rtimes] = limbs(t * AS(upward_mul_num_1, x));
            }
            // Members: the special numbers and the two bounds.
            for (std::size_t k = 0; k < nt + 2; ++k) {
                const T t = k < nt ? ts[k] : k == nt ? xs[i].lower().limb[0] : xs[i].upper().limb[0];
                member[(i * (nt + 2) + k) * 2] = x.contains(AS(upward_contains_1, t));
                member[(i * (nt + 2) + k) * 2 + 1] = up::member(AS(upward_contains_1, t), x) == kairn::Trit::yes;
            }
            neg[i] = limbs(-AS(upward_neg_1, x));
            lower[i] = AS(upward_to_interval_1, x).lower();
            upper[i] = AS(upward_to_interval_1, x).upper();
            back[i] = AS(upward_to_interval_1, x).to_interval();
            round[i] = limbs(U<T>(AS(upward_from_interval_1, back[i])));
            pred[i * 6 + 0] = AS(upward_empty_1, x).is_empty();
            pred[i * 6 + 1] = AS(upward_entire_1, x).is_whole();
            pred[i * 6 + 2] = x.is_finite();
            pred[i * 6 + 3] = AS(upward_positive_1, x).certainly_positive();
            pred[i * 6 + 4] = AS(upward_negative_1, x).certainly_negative();
            pred[i * 6 + 5] = AS(upward_zero_1, x).certainly_zero();
        }
    }

    // Against the default type, outside any scope; and the lines for the oracle.
    static const char* const bin_names[] = {"x + y", "x - y", "x * y", "x.hull(y)", "x.intersection(y)"};
    static const char* const bin_kernels[] = {"upward_add_1", "upward_sub_1", "upward_mul_1", "upward_hull_1",
                                              "upward_intersection_1"};
    for (std::size_t k = 0; k < np; ++k) {
        const D<T>&x = xs[pi[k]], &y = xs[pj[k]];
        const Pair<T> a = s[pi[k]], b = s[pj[k]];
        const std::string ops = std::string(f) + " " + text(x) + ", " + text(y);
        const D<T> want[] = {x + y, x - y, x * y, x.hull(y), x.intersection(y)};
        for (int o = 0; o < nbin; ++o) {
            const Pair<T> z = bin[k * nbin + o];
            if (o == mul) check_product(z, x, y, want[o], bin_names[o], ops);
            else check_set(z, want[o], bin_names[o], ops);
            line<T>(bin_kernels[o], {a.u, a.n, b.u, b.n}, {z.u, z.n});
        }
        const bool rel_want[] = {y.contains(x), kairn::ieee1788::subset(x, y), kairn::ieee1788::equal(x, y),
                                 kairn::ieee1788::interior(x, y), kairn::ieee1788::disjoint(x, y)};
        static const char* const rel_names[] = {"y.contains(x)", "ieee1788::subset", "ieee1788::equal",
                                                "ieee1788::interior", "ieee1788::disjoint"};
        static const char* const rel_kernels[] = {"upward_subset_1", "upward_subset_1", "upward_rel_equal_1",
                                                  "upward_rel_interior_1", "upward_rel_disjoint_1"};
        for (int o = 0; o < 5; ++o) {
            const bool m = rel[k * 6 + o] != 0;
            check(m == rel_want[o], rel_names[o], ops);
            if (o != 1) line<T>(rel_kernels[o], {a.u, a.n, b.u, b.n}, {}, {m});
        }
        const kairn::Trit cmp_want[] = {kairn::less(x, y), kairn::less_equal(x, y), kairn::equal(x, y),
                                        kairn::greater(x, y), kairn::greater_equal(x, y), kairn::not_equal(x, y)};
        static const char* const cmp_names[] = {"less", "less_equal", "equal", "greater", "greater_equal", "not_equal"};
        static const char* const cmp_kernels[] = {"upward_less_1", "upward_less_equal_1", "upward_equal_1"};
        for (int o = 0; o < 6; ++o) {
            const kairn::Trit t = cmp[k * 6 + o];
            check(t == cmp_want[o], cmp_names[o], ops);
            if (o < 3) line<T>(cmp_kernels[o], {a.u, a.n, b.u, b.n}, {}, {t == kairn::Trit::yes, t == kairn::Trit::no});
        }
    }
    static const char* const num_names[] = {"x + t", "x - t", "t - x", "x * t", "t + x", "t * x"};
    for (std::size_t i = 0; i < n; ++i) {
        const D<T>& x = xs[i];
        const Pair<T> a = s[i];
        for (std::size_t k = 0; k < nt; ++k) {
            const T t = ts[k];
            const D<T> dt(kairn::unverified(t));
            const std::string ops = std::string(f) + " " + text(x) + ", t = " + hex(static_cast<double>(t));
            const D<T> want[] = {x + dt, x - dt, dt - x, x * dt, dt + x, dt * x};
            const Pair<T>* r = &num[(i * nt + k) * nnum];
            for (int o = 0; o < nnum; ++o) {
                if (o == times || o == rtimes) check_product(r[o], x, dt, want[o], num_names[o], ops);
                else check_set(r[o], want[o], num_names[o], ops);
            }
            // The kernels' lines: x + t; x - t is x + (-t); t - x is (-x) + t, (-x) stored (n, u).
            line<T>("upward_add_num_1", {a.u, a.n, t}, {r[plus].u, r[plus].n});
            line<T>("upward_add_num_1", {a.u, a.n, T(-t)}, {r[minus].u, r[minus].n});
            line<T>("upward_add_num_1", {a.n, a.u, t}, {r[rminus].u, r[rminus].n});
            line<T>("upward_mul_num_1", {a.u, a.n, t}, {r[times].u, r[times].n});
            check(same_bits(r[rplus].u, r[plus].u) && same_bits(r[rplus].n, r[plus].n), "t + x, bit for bit x + t", ops);
            check(same_bits(r[rtimes].u, r[times].u) && same_bits(r[rtimes].n, r[times].n), "t * x, bit for bit x * t", ops);
        }
        for (std::size_t k = 0; k < nt + 2; ++k) {
            const T t = k < nt ? ts[k] : k == nt ? x.lower().limb[0] : x.upper().limb[0];
            const std::string ops = std::string(f) + " " + text(x) + ", t = " + hex(static_cast<double>(t));
            const bool want = x.contains(t);
            check((member[(i * (nt + 2) + k) * 2] != 0) == want, "x.contains(t)", ops);
            check((member[(i * (nt + 2) + k) * 2 + 1] != 0) == want, "member(t, x)", ops);
            line<T>("upward_contains_1", {a.u, a.n, t}, {}, {member[(i * (nt + 2) + k) * 2] != 0});
        }
        const std::string ops = std::string(f) + " " + text(x);
        check_set(neg[i], -x, "-x", ops);
        line<T>("upward_neg_1", {a.u, a.n}, {neg[i].u, neg[i].n});
        check(lower[i] == x.lower().limb[0] && upper[i] == x.upper().limb[0], "lower(), upper()", ops);
        check(same_set(back[i], x), "to_interval()", ops + ": " + text(back[i]));
        line<T>("upward_to_interval_1", {a.u, a.n}, {back[i].lower().limb[0], back[i].upper().limb[0]});
        check_set(a, x, "Interval(kairn::Interval<T, 1>)", ops);
        line<T>("upward_from_interval_1", {x.lower().limb[0], x.upper().limb[0]}, {a.u, a.n});
        check(same_bits(round[i].u, a.u) && same_bits(round[i].n, a.n), "the round trip through the default type", ops);
        const bool pred_want[] = {x.is_empty(), x.is_whole(), x.is_finite(), x.certainly_positive(),
                                  x.certainly_negative(), x.certainly_zero()};
        static const char* const pred_names[] = {"is_empty", "is_whole", "is_finite", "certainly_positive",
                                                 "certainly_negative", "certainly_zero"};
        static const char* const pred_kernels[] = {"upward_empty_1", "upward_entire_1", nullptr, "upward_positive_1",
                                                   "upward_negative_1", "upward_zero_1"};
        for (int o = 0; o < 6; ++o) {
            check((pred[i * 6 + o] != 0) == pred_want[o], pred_names[o], ops);
            if (pred_kernels[o]) line<T>(pred_kernels[o], {a.u, a.n}, {}, {pred[i * 6 + o] != 0});
        }
    }

    // The constructor, on every pair of special values (each special number and each bound).
    std::vector<T> vals = ts;
    for (const D<T>& x : special_intervals<T>()) {
        vals.push_back(x.lower().limb[0]);
        vals.push_back(x.upper().limb[0]);
    }
    const std::size_t nv = vals.size();
    std::vector<Pair<T>> made(nv * nv * 2);
    {
        up::Scope scope;
        for (std::size_t i = 0; i < nv; ++i)
            for (std::size_t j = 0; j < nv; ++j) {
                made[(i * nv + j) * 2] = limbs(U<T>(AS(upward_make_1, vals[i]), vals[j]));
                made[(i * nv + j) * 2 + 1] = limbs(U<T>::from_bounds(AS(upward_make_1, vals[i]), vals[j]));
            }
    }
    for (std::size_t i = 0; i < nv; ++i)
        for (std::size_t j = 0; j < nv; ++j) {
            const D<T> want(kairn::unverified(vals[i]), vals[j]);
            const std::string ops = std::string(f) + " lo " + hex(static_cast<double>(vals[i])) + ", hi " +
                                    hex(static_cast<double>(vals[j]));
            const Pair<T> z = made[(i * nv + j) * 2];
            check_set(z, want, "Interval(lo, hi)", ops);
            check(same_bits(made[(i * nv + j) * 2 + 1].u, z.u) && same_bits(made[(i * nv + j) * 2 + 1].n, z.n),
                  "from_bounds(lo, hi), bit for bit Interval(lo, hi)", ops);
            if (i <= j || (i + j) % 3 == 0) line<T>("upward_make_1", {vals[i], vals[j]}, {z.u, z.n});
        }

    // The functions on arrays, on the whole list of pairs, from code that rounds to nearest (their own
    // scope sets the mode), and in place inside a Scope: bit for bit the operators.
    {
        std::vector<T> xu(np), xn(np), yu(np), yn(np), zu(np), zn(np);
        for (std::size_t k = 0; k < np; ++k) {
            xu[k] = s[pi[k]].u;
            xn[k] = s[pi[k]].n;
            yu[k] = s[pj[k]].u;
            yn[k] = s[pj[k]].n;
        }
        const up::View<const T> x(xu.data(), xn.data(), np), y(yu.data(), yn.data(), np);
        const up::View<T> z(zu.data(), zn.data(), np);
        const auto compare = [&](const char* what, auto want) {
            bool same = true;
            std::size_t at = 0;
            for (std::size_t k = 0; k < np && same; ++k) {
                const Pair<T> w = want(k);
                same = same_bits(zu[k], w.u) && same_bits(zn[k], w.n);
                at = k;
            }
            check(same, what, std::string(f) + ", element " + std::to_string(at) + " of " + std::to_string(np));
        };
        const auto inplace = [&](auto call) {
            std::copy(xu.begin(), xu.end(), zu.begin());
            std::copy(xn.begin(), xn.end(), zn.begin());
            up::Scope scope;
            call();
        };
        up::add(z, AS(upward_add_1, x), y);
        compare("kairn::upward::add(z, x, y)", [&](std::size_t k) { return bin[k * nbin + add]; });
        up::sub(z, AS(upward_sub_1, x), y);
        compare("kairn::upward::sub(z, x, y)", [&](std::size_t k) { return bin[k * nbin + sub]; });
        up::mul(z, AS(upward_mul_1, x), y);
        compare("kairn::upward::mul(z, x, y)", [&](std::size_t k) { return bin[k * nbin + mul]; });
        up::neg(z, AS(upward_neg_1, x));
        compare("kairn::upward::neg(z, x)", [&](std::size_t k) { return neg[pi[k]]; });
        inplace([&] { up::add(z, AS(upward_add_1, up::View<const T>(z)), y); });
        compare("kairn::upward::add(z, z, y), in place in a Scope", [&](std::size_t k) { return bin[k * nbin + add]; });
        inplace([&] { up::mul(z, AS(upward_mul_1, up::View<const T>(z)), y); });
        compare("kairn::upward::mul(z, z, y), in place in a Scope", [&](std::size_t k) { return bin[k * nbin + mul]; });
        inplace([&] { up::neg(z, AS(upward_neg_1, up::View<const T>(z))); });
        compare("kairn::upward::neg(z, z), in place in a Scope", [&](std::size_t k) { return neg[pi[k]]; });
        for (std::size_t t = 0; t < nt; ++t) {
            up::add(z, AS(upward_add_num_1, x), ts[t]);
            compare("kairn::upward::add(z, x, t)", [&](std::size_t k) { return num[(pi[k] * nt + t) * nnum + plus]; });
            up::mul(z, AS(upward_mul_num_1, x), ts[t]);
            compare("kairn::upward::mul(z, x, t)", [&](std::size_t k) { return num[(pi[k] * nt + t) * nnum + times]; });
            inplace([&] { up::add(z, AS(upward_add_num_1, up::View<const T>(z)), ts[t]); });
            compare("kairn::upward::add(z, z, t), in place in a Scope",
                    [&](std::size_t k) { return num[(pi[k] * nt + t) * nnum + plus]; });
            inplace([&] { up::mul(z, AS(upward_mul_num_1, up::View<const T>(z)), ts[t]); });
            compare("kairn::upward::mul(z, z, t), in place in a Scope",
                    [&](std::size_t k) { return num[(pi[k] * nt + t) * nnum + times]; });
        }
    }
}

}  // namespace

int main(int argc, char** argv) {
    if (argc != 2) {
        std::fprintf(stderr, "usage: differential LINES\n");
        return 2;
    }
    std::ofstream file(argv[1], std::ios::binary);
    if (!file) {
        std::fprintf(stderr, "differential: cannot write %s\n", argv[1]);
        return 2;
    }
    lines = &file;
    std::mt19937_64 rng(20261126);
    run<double>(rng);
    run<float>(rng);
    file.close();
    if (!file) {
        std::fprintf(stderr, "differential: writing %s failed\n", argv[1]);
        return 2;
    }
    std::printf("api.upward.differential: %ld comparisons with the default type, %ld failed; %ld products with a product "
                "of bounds below P, %ld of them tighter than the default's; %ld lines for the oracle "
                "(KAIRN_UPWARD_FORM %d, KAIRN_UPWARD_ARRAYS %d)\n",
                compared, failed, below_p, tighter, written, KAIRN_UPWARD_FORM, KAIRN_UPWARD_ARRAYS);
    // The cases below P must be there, and some of them tighter: otherwise the test did not compare
    // what it is for.
    if (below_p == 0 || tighter == 0) std::printf("FAILED: no product below P, or none tighter than the default's\n");
    return failed == 0 && below_p > 0 && tighter > 0 ? 0 : 1;
}
