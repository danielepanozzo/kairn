// Every operation of Packed<T, k> (include/kairn/packed.hpp) against the public operation of
// Expansion<T, k> of the same name, lane by lane and bit for bit, for T = double and float and
// k = 1 and 2, on a corpus of operands that has every kind of value: zeros of both signs,
// subnormal numbers, the smallest normal number, ordinary and random numbers, the largest finite
// number and pairs near it whose results overflow, the infinities and NaN. Each operation is run
// on every pair (or every operand) of the corpus, one per lane position in turn, with the other
// lanes filled from the corpus by a fixed pseudo-random sequence, so that every lane position is
// exercised and a register holds a NaN beside a finite number or an overflow in one lane only;
// the program counts such registers and fails if an operation of the extended domain met none.
//
// "Bit for bit": every limb of every lane equals the limb the scalar operation gives, and a mask
// lane its bool; a NaN is compared as a NaN, since which NaN comes out is not specified (by Kairn
// or by the generator's own lane-by-lane tests, whose runners print every NaN as nan).
//
// Also: masks (any, all, lane, &, |, !, select), the moves (broadcast, lane, set_lane, load and
// store from unaligned arrays, load_partial and store_partial for every count, from_limbs), and
// the type's properties (trivially copyable, standard layout, the number of lanes of the form).
//
// Built with the build's flags (the form of the target: AVX2, NEON, or one lane), with
// KAIRN_PACKED_FORM_SCALAR, and on x86-64 where the build lacks AVX2 with it (tests/api/CMakeLists.txt).
// Prints one line per group and exits 1 on the first failures (at most 20 printed).
#include <kairn/kairn.hpp>
#include <kairn/packed.hpp>

#include <bit>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <limits>
#include <type_traits>
#include <vector>

namespace {

template <class T>
using E1 = kairn::Expansion<T, 1>;
template <class T>
using E2 = kairn::Expansion<T, 2>;
template <class T>
using P1 = kairn::Packed<T, 1>;
template <class T>
using P2 = kairn::Packed<T, 2>;

#if KAIRN_PACKED_FORM == KAIRN_PACKED_FORM_AVX2
constexpr int lanes_double = 4, lanes_float = 8;
const char* const form_name = "AVX2";
#elif KAIRN_PACKED_FORM == KAIRN_PACKED_FORM_NEON
constexpr int lanes_double = 2, lanes_float = 4;
const char* const form_name = "NEON";
#else
constexpr int lanes_double = 1, lanes_float = 1;
const char* const form_name = "scalar";
#endif
static_assert(P2<double>::lanes == lanes_double && P1<double>::lanes == lanes_double);
static_assert(P2<float>::lanes == lanes_float && P1<float>::lanes == lanes_float);
static_assert(kairn::PackedMask<double>::lanes == lanes_double && kairn::PackedMask<float>::lanes == lanes_float);

template <class T>
constexpr bool regular() {
    return std::is_trivially_copyable_v<P1<T>> && std::is_trivially_copyable_v<P2<T>> &&
           std::is_standard_layout_v<P1<T>> && std::is_standard_layout_v<P2<T>> &&
           std::is_trivially_copyable_v<kairn::PackedMask<T>> && std::is_nothrow_default_constructible_v<P2<T>> &&
           sizeof(P2<T>) == 2 * sizeof(typename P2<T>::register_type) &&
           sizeof(P1<T>) == sizeof(typename P1<T>::register_type) &&
           sizeof(typename P1<T>::register_type) == sizeof(T) * P1<T>::lanes;
}
static_assert(regular<double>() && regular<float>());

long failures = 0, checked = 0;

template <class T>
using Bits = std::conditional_t<sizeof(T) == 8, std::uint64_t, std::uint32_t>;
template <class T>
bool same_limb(T a, T b) {
    if (a != a) return b != b;
    return std::bit_cast<Bits<T>>(a) == std::bit_cast<Bits<T>>(b);
}
template <class T, int K>
bool same(const kairn::Expansion<T, K>& a, const kairn::Expansion<T, K>& b) {
    for (int j = 0; j < K; ++j)
        if (!same_limb(a.limb[j], b.limb[j])) return false;
    return true;
}
bool same(bool a, bool b) { return a == b; }
// The products of one limb (x * y, half, ldexp, finite::mul of Packed<T, 1>) are the kernel
// mul_1_1, the opaque product fma(a, b, +0), which gives +0 where T's product a * b, the scalar
// operation of Expansion<T, 1>, gives -0. Their zero results are compared by value, and counted.
long zero_signs = 0;
template <class T, int K>
bool same_value(const kairn::Expansion<T, K>& a, const kairn::Expansion<T, K>& b) {
    if (same(a, b)) return true;
    if constexpr (K == 1) {
        if (a.limb[0] == 0 && b.limb[0] == 0) {
            ++zero_signs;
            return true;
        }
    }
    return false;
}

template <class T, int K>
void print(const kairn::Expansion<T, K>& x) {
    for (int j = 0; j < K; ++j) std::printf(" %a", double(x.limb[j]));
}
void print(bool b) { std::printf(" %d", int(b)); }

template <class T>
const char* type_name() {
    return sizeof(T) == 8 ? "double" : "float";
}

// A lane of a packed result, as a number or a bool.
template <class T, int K>
kairn::Expansion<T, K> lane_of(const kairn::Packed<T, K>& p, int i) {
    return p.lane(i);
}
template <class T>
bool lane_of(const kairn::PackedMask<T>& m, int i) {
    return m.lane(i);
}

template <class R, class S>
void report(const char* op, const char* type, int lane, const R& got, const S& want) {
    ++failures;
    if (failures > 20) return;
    std::printf("FAILED %s (%s): lane %d: packed", op, type, lane);
    print(got);
    std::printf(", scalar");
    print(want);
    std::printf("\n");
}

// The corpus of one limb type: values of one limb, and canonical two-limb numbers.
template <class T>
struct Corpus {
    std::vector<E1<T>> one;
    std::vector<E2<T>> two;
};
template <class T>
T opaque(T x) {
    volatile T v = x;
    return v;
}
template <class T>
E2<T> raw(T h, T l) {
    E2<T> x;
    x.limb[0] = h;
    x.limb[1] = l;
    return x;
}
// A fixed pseudo-random sequence (64-bit LCG), the same on every platform.
struct Random {
    std::uint64_t s;
    std::uint64_t next() {
        s = s * 6364136223846793005u + 1442695040888963407u;
        return s >> 11;
    }
    int below(int n) { return int(next() % std::uint64_t(n)); }
};
template <class T>
Corpus<T> make_corpus() {
    using L = std::numeric_limits<T>;
    const T eta = opaque(L::denorm_min()), lambda = opaque((L::min)()), big = opaque((L::max)());
    const T inf = opaque(L::infinity()), nan = opaque(L::quiet_NaN()), u = opaque(L::epsilon() / 2);
    const T sub = lambda * T(0.75);
    const T top = std::ldexp(T(1), L::max_exponent - L::digits - 2);
    Corpus<T> c;
    const T ones[] = {T(0), -T(0), eta, -eta, sub, -sub, lambda, -lambda, T(1), T(-1), T(1.5), T(-2.25), T(3),
                      big, -big, big / 2, -big / 2, inf, -inf, nan};
    for (T a : ones) c.one.push_back(E1<T>(a));
    Random r{7};
    for (int i = 0; i < 16; ++i) {
        const int e = r.below(2 * L::max_exponent) - L::max_exponent;   // across the whole range
        const T m = T(1) + T(r.next() % (std::uint64_t(1) << 20)) / T(1 << 20);
        c.one.push_back(E1<T>(std::ldexp(r.below(2) ? m : -m, e)));
    }
    const E2<T> twos[] = {raw<T>(0, 0), raw<T>(-T(0), -T(0)), raw<T>(0, -T(0)), raw<T>(-T(0), 0), raw<T>(eta, 0),
                          raw<T>(-eta, -T(0)), raw<T>(lambda, 0), raw<T>(T(1), eta), raw<T>(T(1), -eta),
                          raw<T>(T(-1), eta), raw<T>(T(1), u), raw<T>(T(1), -u / 2), raw<T>(T(-1), u / 2),
                          raw<T>(T(1.5), u / 128), raw<T>(T(2.25), -u / 32), raw<T>(T(-1.5), -u / 128),
                          raw<T>(big, top), raw<T>(big, -top), raw<T>(-big, top), raw<T>(big / 2, top / 4),
                          raw<T>(inf, 0), raw<T>(-inf, 0), raw<T>(inf, -T(0)), raw<T>(nan, nan)};
    for (const E2<T>& x : twos) c.two.push_back(x);
    // Random canonical pairs, made by the scalar sum of a limb and a smaller one, across the range.
    for (int i = 0; i < 16; ++i) {
        const int e = r.below(2 * L::max_exponent - 4) - L::max_exponent + 2;
        const T m = T(1) + T(r.next() % (std::uint64_t(1) << 20)) / T(1 << 20);
        const T a = std::ldexp(r.below(2) ? m : -m, e);
        const T b = std::ldexp(T(r.below(1000) + 1) / T(1000), e - L::digits - 2 - r.below(8));
        c.two.push_back(E2<T>(a) + (r.below(2) ? b : -b));
    }
    return c;
}

template <class T>
const std::vector<kairn::Expansion<T, 1>>& values(const Corpus<T>& c, std::integral_constant<int, 1>) {
    return c.one;
}
template <class T>
const std::vector<kairn::Expansion<T, 2>>& values(const Corpus<T>& c, std::integral_constant<int, 2>) {
    return c.two;
}

// Counts of the registers of one operation whose lanes mixed kinds of values.
struct Mixed {
    long operands = 0;  // a lane with a finite leading limb and a lane with a non-finite one
    long results = 0;   // the same among the results: an overflow, or a NaN, in some lanes only
};
template <class T, int K>
bool finite_lane(const kairn::Expansion<T, K>& x) {
    return std::isfinite(x.limb[0]);
}
bool finite_lane(bool) { return true; }
template <class V>
void count_mixed(const V* lanes, int w, long& counter) {
    bool f = false, nf = false;
    for (int i = 0; i < w; ++i) (finite_lane(lanes[i]) ? f : nf) = true;
    if (f && nf) ++counter;
}

// A unary operation: on every operand of the corpus at every lane position in turn.
template <class T, int KX, class PF, class SF>
Mixed unary(const char* op, const Corpus<T>& c, PF pf, SF sf, bool zero_by_value = false) {
    using X = kairn::Packed<T, KX>;
    constexpr int W = X::lanes;
    const auto& xs = values(c, std::integral_constant<int, KX>());
    const long before = failures;
    Random r{11};
    Mixed mixed;
    for (std::size_t k = 0; k < xs.size() * W; ++k) {
        X x;
        kairn::Expansion<T, KX> xl[W];
        for (int i = 0; i < W; ++i) {
            xl[i] = i == int(k % W) ? xs[k / W] : xs[std::size_t(r.below(int(xs.size())))];
            x.set_lane(i, xl[i]);
        }
        count_mixed(xl, W, mixed.operands);
        const auto z = pf(x);
        std::remove_cvref_t<decltype(sf(xl[0]))> want[W];
        for (int i = 0; i < W; ++i) {
            want[i] = sf(xl[i]);
            ++checked;
            bool ok = false;
            if constexpr (std::is_same_v<decltype(want[i]), bool&>) ok = same(lane_of(z, i), want[i]);
            else ok = zero_by_value ? same_value(lane_of(z, i), want[i]) : same(lane_of(z, i), want[i]);
            if (!ok) report(op, type_name<T>(), i, lane_of(z, i), want[i]);
        }
        count_mixed(want, W, mixed.results);
        if (failures > before + 4) break;
    }
    return mixed;
}

// A binary operation: on every pair of the corpus, at lane k mod W for the k-th pair.
template <class T, int KX, int KY, class PF, class SF>
Mixed binary(const char* op, const Corpus<T>& c, PF pf, SF sf, bool zero_by_value = false) {
    using X = kairn::Packed<T, KX>;
    using Y = kairn::Packed<T, KY>;
    constexpr int W = X::lanes;
    const auto& xs = values(c, std::integral_constant<int, KX>());
    const auto& ys = values(c, std::integral_constant<int, KY>());
    const long before = failures;
    Random r{13};
    Mixed mixed;
    std::size_t k = 0;
    for (std::size_t a = 0; a < xs.size(); ++a) {
        for (std::size_t b = 0; b < ys.size(); ++b, ++k) {
            X x;
            Y y;
            kairn::Expansion<T, KX> xl[W];
            kairn::Expansion<T, KY> yl[W];
            for (int i = 0; i < W; ++i) {
                const bool mine = i == int(k % W);
                xl[i] = mine ? xs[a] : xs[std::size_t(r.below(int(xs.size())))];
                yl[i] = mine ? ys[b] : ys[std::size_t(r.below(int(ys.size())))];
                x.set_lane(i, xl[i]);
                y.set_lane(i, yl[i]);
            }
            count_mixed(xl, W, mixed.operands);
            const auto z = pf(x, y);
            std::remove_cvref_t<decltype(sf(xl[0], yl[0]))> want[W];
            for (int i = 0; i < W; ++i) {
                want[i] = sf(xl[i], yl[i]);
                ++checked;
                bool ok = false;
                if constexpr (std::is_same_v<decltype(want[i]), bool&>) ok = same(lane_of(z, i), want[i]);
                else ok = zero_by_value ? same_value(lane_of(z, i), want[i]) : same(lane_of(z, i), want[i]);
                if (!ok) report(op, type_name<T>(), i, lane_of(z, i), want[i]);
            }
            count_mixed(want, W, mixed.results);
            if (failures > before + 4) return mixed;
        }
    }
    return mixed;
}

// The operations of the extended domain must have met registers of mixed kinds.
// With one lane there is nothing to mix. (if constexpr: MSVC reports a constant condition, C4127.)
void expect_mixed([[maybe_unused]] const char* op, [[maybe_unused]] const Mixed& m, [[maybe_unused]] bool results) {
    if constexpr (lanes_double > 1) {
        if (m.operands == 0 || (results && m.results == 0)) {
            ++failures;
            std::printf("FAILED %s: no register mixed finite and non-finite %s (%ld operand registers, %ld result "
                        "registers)\n",
                        op, m.operands == 0 ? "operands" : "results", m.operands, m.results);
        }
    }
}

template <class T>
void arithmetic(const Corpus<T>& c) {
    using A1 = E1<T>;
    using A2 = E2<T>;
    // One limb.
    expect_mixed("p1 + p1", binary<T, 1, 1>("p1 + p1", c, [](P1<T> x, P1<T> y) { return x + y; },
                                            [](A1 x, A1 y) { return x + y; }), true);
    binary<T, 1, 1>("p1 - p1", c, [](P1<T> x, P1<T> y) { return x - y; }, [](A1 x, A1 y) { return x - y; });
    expect_mixed("p1 * p1", binary<T, 1, 1>("p1 * p1", c, [](P1<T> x, P1<T> y) { return x * y; },
                                            [](A1 x, A1 y) { return x * y; }, true), true);
    binary<T, 1, 1>("p1 += p1", c, [](P1<T> x, P1<T> y) { return x += y; }, [](A1 x, A1 y) { return x += y; });
    binary<T, 1, 1>("p1 -= p1", c, [](P1<T> x, P1<T> y) { return x -= y; }, [](A1 x, A1 y) { return x -= y; });
    binary<T, 1, 1>("p1 *= p1", c, [](P1<T> x, P1<T> y) { return x *= y; }, [](A1 x, A1 y) { return x *= y; }, true);
    binary<T, 1, 1>("add_fast p1", c, [](P1<T> x, P1<T> y) { return kairn::add_fast(x, y); },
                    [](A1 x, A1 y) { return kairn::add_fast(x, y); });
    binary<T, 1, 1>("finite::add p1", c, [](P1<T> x, P1<T> y) { return kairn::finite::add(x, y); },
                    [](A1 x, A1 y) { return kairn::finite::add(x, y); });
    binary<T, 1, 1>("finite::sub p1", c, [](P1<T> x, P1<T> y) { return kairn::finite::sub(x, y); },
                    [](A1 x, A1 y) { return kairn::finite::sub(x, y); });
    binary<T, 1, 1>("finite::mul p1", c, [](P1<T> x, P1<T> y) { return kairn::finite::mul(x, y); },
                    [](A1 x, A1 y) { return kairn::finite::mul(x, y); }, true);
    binary<T, 1, 1>("finite::add_fast p1", c, [](P1<T> x, P1<T> y) { return kairn::finite::add_fast(x, y); },
                    [](A1 x, A1 y) { return kairn::finite::add_fast(x, y); });
    unary<T, 1>("-p1", c, [](P1<T> x) { return -x; }, [](A1 x) { return -x; });
    unary<T, 1>("abs p1", c, [](P1<T> x) { return kairn::abs(x); }, [](A1 x) { return kairn::abs(x); });
    unary<T, 1>("half p1", c, [](P1<T> x) { return kairn::half(x); }, [](A1 x) { return kairn::half(x); }, true);
    unary<T, 1>("to_nearest p1", c, [](P1<T> x) { return kairn::to_nearest(x); },
                [](A1 x) { return A1(kairn::to_nearest(x)); });
    unary<T, 1>("to_down p1", c, [](P1<T> x) { return kairn::to_down(x); }, [](A1 x) { return A1(kairn::to_down(x)); });
    unary<T, 1>("to_up p1", c, [](P1<T> x) { return kairn::to_up(x); }, [](A1 x) { return A1(kairn::to_up(x)); });
    unary<T, 1>("abs_upper p1", c, [](P1<T> x) { return kairn::abs_upper(x); },
                [](A1 x) { return A1(kairn::abs_upper(x)); });
    for (int n : {-2200, -1100, -1075, -1074, -1060, -1022, -150, -149, -126, -60, -1, 0, 1, 3, 60, 127, 128,
                  1023, 1024, 2000, 2200}) {
        unary<T, 1>("ldexp p1", c, [n](P1<T> x) { return kairn::ldexp(x, n); }, [n](A1 x) { return kairn::ldexp(x, n); }, true);
        unary<T, 1>("finite::ldexp p1", c, [n](P1<T> x) { return kairn::finite::ldexp(x, n); },
                    [n](A1 x) { return kairn::finite::ldexp(x, n); }, true);
    }

    // Two limbs: the full kernels and their mixed forms (a T operand is a lane of a Packed<T, 1>).
    expect_mixed("p2 + p2", binary<T, 2, 2>("p2 + p2", c, [](P2<T> x, P2<T> y) { return x + y; },
                                            [](A2 x, A2 y) { return x + y; }), true);
    binary<T, 2, 1>("p2 + p1", c, [](P2<T> x, P1<T> a) { return x + a; }, [](A2 x, A1 a) { return x + a.limb[0]; });
    binary<T, 1, 2>("p1 + p2", c, [](P1<T> a, P2<T> x) { return a + x; }, [](A1 a, A2 x) { return a.limb[0] + x; });
    binary<T, 2, 2>("p2 - p2", c, [](P2<T> x, P2<T> y) { return x - y; }, [](A2 x, A2 y) { return x - y; });
    binary<T, 2, 1>("p2 - p1", c, [](P2<T> x, P1<T> a) { return x - a; }, [](A2 x, A1 a) { return x - a.limb[0]; });
    binary<T, 1, 2>("p1 - p2", c, [](P1<T> a, P2<T> x) { return a - x; }, [](A1 a, A2 x) { return a.limb[0] - x; });
    expect_mixed("p2 * p2", binary<T, 2, 2>("p2 * p2", c, [](P2<T> x, P2<T> y) { return x * y; },
                                            [](A2 x, A2 y) { return x * y; }), true);
    binary<T, 2, 1>("p2 * p1", c, [](P2<T> x, P1<T> a) { return x * a; }, [](A2 x, A1 a) { return x * a.limb[0]; });
    binary<T, 1, 2>("p1 * p2", c, [](P1<T> a, P2<T> x) { return a * x; }, [](A1 a, A2 x) { return a.limb[0] * x; });
    binary<T, 2, 2>("p2 += p2", c, [](P2<T> x, P2<T> y) { return x += y; }, [](A2 x, A2 y) { return x += y; });
    binary<T, 2, 1>("p2 += p1", c, [](P2<T> x, P1<T> a) { return x += a; }, [](A2 x, A1 a) { return x += a.limb[0]; });
    binary<T, 2, 2>("p2 -= p2", c, [](P2<T> x, P2<T> y) { return x -= y; }, [](A2 x, A2 y) { return x -= y; });
    binary<T, 2, 1>("p2 -= p1", c, [](P2<T> x, P1<T> a) { return x -= a; }, [](A2 x, A1 a) { return x -= a.limb[0]; });
    binary<T, 2, 2>("p2 *= p2", c, [](P2<T> x, P2<T> y) { return x *= y; }, [](A2 x, A2 y) { return x *= y; });
    binary<T, 2, 1>("p2 *= p1", c, [](P2<T> x, P1<T> a) { return x *= a; }, [](A2 x, A1 a) { return x *= a.limb[0]; });
    binary<T, 2, 2>("add_fast p2", c, [](P2<T> x, P2<T> y) { return kairn::add_fast(x, y); },
                    [](A2 x, A2 y) { return kairn::add_fast(x, y); });
    unary<T, 2>("-p2", c, [](P2<T> x) { return -x; }, [](A2 x) { return -x; });
    unary<T, 2>("abs p2", c, [](P2<T> x) { return kairn::abs(x); }, [](A2 x) { return kairn::abs(x); });
    unary<T, 2>("half p2", c, [](P2<T> x) { return kairn::half(x); }, [](A2 x) { return kairn::half(x); });
    for (int n : {-2200, -2099, -1100, -1074, -1060, -1022, -149, -126, -60, -1, 0, 1, 3, 60, 127, 128, 1023, 1024,
                  2000, 2098, 2200}) {
        unary<T, 2>("ldexp p2", c, [n](P2<T> x) { return kairn::ldexp(x, n); }, [n](A2 x) { return kairn::ldexp(x, n); });
    }

    // Two limbs: the finite cores.
    binary<T, 2, 2>("finite::add p2", c, [](P2<T> x, P2<T> y) { return kairn::finite::add(x, y); },
                    [](A2 x, A2 y) { return kairn::finite::add(x, y); });
    binary<T, 2, 1>("finite::add p2 p1", c, [](P2<T> x, P1<T> a) { return kairn::finite::add(x, a); },
                    [](A2 x, A1 a) { return kairn::finite::add(x, a.limb[0]); });
    binary<T, 1, 2>("finite::add p1 p2", c, [](P1<T> a, P2<T> x) { return kairn::finite::add(a, x); },
                    [](A1 a, A2 x) { return kairn::finite::add(a.limb[0], x); });
    binary<T, 2, 2>("finite::sub p2", c, [](P2<T> x, P2<T> y) { return kairn::finite::sub(x, y); },
                    [](A2 x, A2 y) { return kairn::finite::sub(x, y); });
    binary<T, 2, 1>("finite::sub p2 p1", c, [](P2<T> x, P1<T> a) { return kairn::finite::sub(x, a); },
                    [](A2 x, A1 a) { return kairn::finite::sub(x, a.limb[0]); });
    binary<T, 1, 2>("finite::sub p1 p2", c, [](P1<T> a, P2<T> x) { return kairn::finite::sub(a, x); },
                    [](A1 a, A2 x) { return kairn::finite::sub(a.limb[0], x); });
    binary<T, 2, 2>("finite::mul p2", c, [](P2<T> x, P2<T> y) { return kairn::finite::mul(x, y); },
                    [](A2 x, A2 y) { return kairn::finite::mul(x, y); });
    binary<T, 2, 1>("finite::mul p2 p1", c, [](P2<T> x, P1<T> a) { return kairn::finite::mul(x, a); },
                    [](A2 x, A1 a) { return kairn::finite::mul(x, a.limb[0]); });
    binary<T, 1, 2>("finite::mul p1 p2", c, [](P1<T> a, P2<T> x) { return kairn::finite::mul(a, x); },
                    [](A1 a, A2 x) { return kairn::finite::mul(a.limb[0], x); });
    binary<T, 2, 2>("finite::add_fast p2", c, [](P2<T> x, P2<T> y) { return kairn::finite::add_fast(x, y); },
                    [](A2 x, A2 y) { return kairn::finite::add_fast(x, y); });
    for (int n : {-2200, -1100, -1074, -60, -1, 0, 1, 60, 1023, 1024, 2200}) {
        unary<T, 2>("finite::ldexp p2", c, [n](P2<T> x) { return kairn::finite::ldexp(x, n); },
                    [n](A2 x) { return kairn::finite::ldexp(x, n); });
    }

    // Conversions between the numbers of limbs, and to one limb.
    unary<T, 1>("P2(p1)", c, [](P1<T> a) { return P2<T>(a); }, [](A1 a) { return A2(a); });
    unary<T, 2>("P1(p2)", c, [](P2<T> x) { return P1<T>(x); }, [](A2 x) { return A1(x); });
    unary<T, 2>("to_nearest p2", c, [](P2<T> x) { return kairn::to_nearest(x); },
                [](A2 x) { return A1(kairn::to_nearest(x)); });
    unary<T, 2>("to_down p2", c, [](P2<T> x) { return kairn::to_down(x); }, [](A2 x) { return A1(kairn::to_down(x)); });
    unary<T, 2>("to_up p2", c, [](P2<T> x) { return kairn::to_up(x); }, [](A2 x) { return A1(kairn::to_up(x)); });
    unary<T, 2>("abs_upper p2", c, [](P2<T> x) { return kairn::abs_upper(x); },
                [](A2 x) { return A1(kairn::abs_upper(x)); });
}

// The six comparisons of operands of KX and KY limbs, each through the mask's lane, its complement,
// and its combination with the reversed comparison.
template <class T, int KX, int KY>
void comparisons(const Corpus<T>& c, const char* kind) {
    using X = kairn::Packed<T, KX>;
    using Y = kairn::Packed<T, KY>;
    using A = kairn::Expansion<T, KX>;
    using B = kairn::Expansion<T, KY>;
    char name[64];
    const auto label = [&](const char* op) {
        std::snprintf(name, sizeof name, "%s %s", op, kind);
        return name;
    };
    // A one-limb operand beside a two-limb one as a T, the form the scalar operator takes (x < a);
    // two operands of one K as they are.
    const auto scalar = [](const auto& v) {
        if constexpr (KX != KY && sizeof(v) == sizeof(T)) return v.limb[0];
        else return v;
    };
    expect_mixed(label("<"), binary<T, KX, KY>(label("<"), c, [](X x, Y y) { return x < y; },
                                                [&](A x, B y) { return scalar(x) < scalar(y); }), false);
    binary<T, KX, KY>(label(">"), c, [](X x, Y y) { return x > y; }, [&](A x, B y) { return scalar(x) > scalar(y); });
    binary<T, KX, KY>(label("<="), c, [](X x, Y y) { return x <= y; }, [&](A x, B y) { return scalar(x) <= scalar(y); });
    binary<T, KX, KY>(label(">="), c, [](X x, Y y) { return x >= y; }, [&](A x, B y) { return scalar(x) >= scalar(y); });
    binary<T, KX, KY>(label("=="), c, [](X x, Y y) { return x == y; }, [&](A x, B y) { return scalar(x) == scalar(y); });
    binary<T, KX, KY>(label("!="), c, [](X x, Y y) { return x != y; }, [&](A x, B y) { return scalar(x) != scalar(y); });
    binary<T, KX, KY>(label("!(<)"), c, [](X x, Y y) { return !(x < y); }, [&](A x, B y) { return !(scalar(x) < scalar(y)); });
    binary<T, KX, KY>(label("< & >="), c, [](X x, Y y) { return (x < y) & (x >= y); },
                      [&](A x, B y) { return (scalar(x) < scalar(y)) && (scalar(x) >= scalar(y)); });
    binary<T, KX, KY>(label("< | =="), c, [](X x, Y y) { return (x < y) | (x == y); },
                      [&](A x, B y) { return (scalar(x) < scalar(y)) || (scalar(x) == scalar(y)); });
}

// any, all and select, on the masks of x < y over the pairs of the corpus.
template <class T, int K>
void masks(const Corpus<T>& c) {
    using X = kairn::Packed<T, K>;
    constexpr int W = X::lanes;
    const auto& xs = values(c, std::integral_constant<int, K>());
    Random r{17};
    for (std::size_t k = 0; k < xs.size() * xs.size(); ++k) {
        X x, y;
        kairn::Expansion<T, K> xl[W], yl[W];
        for (int i = 0; i < W; ++i) {
            xl[i] = i == 0 ? xs[k / xs.size()] : xs[std::size_t(r.below(int(xs.size())))];
            yl[i] = i == 0 ? xs[k % xs.size()] : xs[std::size_t(r.below(int(xs.size())))];
            x.set_lane((i + int(k)) % W, xl[i]);
            y.set_lane((i + int(k)) % W, yl[i]);
        }
        const kairn::PackedMask<T> m = x < y;
        bool any = false, all = true;
        for (int i = 0; i < W; ++i) {
            const bool b = m.lane(i);
            any = any || b;
            all = all && b;
            ++checked;
            if (!same(kairn::select(m, x, y).lane(i), b ? x.lane(i) : y.lane(i)))
                report("select", type_name<T>(), i, kairn::select(m, x, y).lane(i), b ? x.lane(i) : y.lane(i));
        }
        if (kairn::any(m) != any || kairn::all(m) != all) {
            ++failures;
            std::printf("FAILED any/all (%s): got %d %d, lanes give %d %d\n", type_name<T>(), int(kairn::any(m)),
                        int(kairn::all(m)), int(any), int(all));
        }
    }
    // The constant masks.
    const kairn::PackedMask<T> none;
    const kairn::PackedMask<T> every = !none;
    if (kairn::any(none) || !kairn::all(every) || kairn::all(none) || !kairn::any(every)) {
        ++failures;
        std::printf("FAILED the masks of no lane and of every lane (%s)\n", type_name<T>());
    }
    // One lane set, at each position.
    for (int p = 0; p < W; ++p) {
        X x, y;
        for (int i = 0; i < W; ++i) {
            x.set_lane(i, kairn::Expansion<T, K>(T(i == p ? 1 : 2)));
            y.set_lane(i, kairn::Expansion<T, K>(T(i == p ? 2 : 1)));
        }
        const kairn::PackedMask<T> m = x < y;
        bool ok = kairn::any(m) && (kairn::all(m) == (W == 1));
        for (int i = 0; i < W; ++i) ok = ok && m.lane(i) == (i == p);
        ++checked;
        if (!ok) {
            ++failures;
            std::printf("FAILED a mask with lane %d alone set (%s)\n", p, type_name<T>());
        }
    }
}

// broadcast, lane and set_lane, load and store (unaligned), load_partial and store_partial for
// every count, and from_limbs, against the scalar constructors.
template <class T>
void moves(const Corpus<T>& c) {
    constexpr int W = P2<T>::lanes;
    Random r{19};
    for (std::size_t k = 0; k < c.two.size(); ++k) {
        // Arrays one element off any alignment of a register, with a sentinel on both sides.
        T buf0[W + 3], buf1[W + 3], one[W + 3];
        T* x0 = buf0 + 1;
        T* x1 = buf1 + 1;
        T* a = one + 1;
        E2<T> want[W];
        for (int i = 0; i < W; ++i) {
            const E2<T>& v = i == int(k % W) ? c.two[k] : c.two[std::size_t(r.below(int(c.two.size())))];
            x0[i] = v.limb[0];
            x1[i] = v.limb[1];
            a[i] = c.one[std::size_t(r.below(int(c.one.size())))].limb[0];
            const T limbs[2] = {x0[i], x1[i]};
            want[i] = E2<T>::from_limbs(limbs);
        }
        const P2<T> p = P2<T>::load(x0, x1), pu = P2<T>::load_unchecked(x0, x1);
        const P2<T> pr = P2<T>::from_limbs(p.limb[0], p.limb[1]);
        const P1<T> q = P1<T>::load(a);
        for (int i = 0; i < W; ++i) {
            const T limbs[2] = {x0[i], x1[i]};
            checked += 4;
            if (!same(p.lane(i), want[i])) report("load", type_name<T>(), i, p.lane(i), want[i]);
            if (!same(pu.lane(i), E2<T>::from_limbs_unchecked(limbs)))
                report("load_unchecked", type_name<T>(), i, pu.lane(i), E2<T>::from_limbs_unchecked(limbs));
            if (!same(pr.lane(i), want[i])) report("from_limbs", type_name<T>(), i, pr.lane(i), want[i]);
            if (!same(q.lane(i), E1<T>::from_limbs(a + i))) report("load p1", type_name<T>(), i, q.lane(i), E1<T>(a[i]));
        }
        // store: the limbs of each lane, and nothing outside the W elements.
        T s0[W + 2], s1[W + 2], s2[W + 2];
        const T mark = T(-7.5);
        for (int i = 0; i < W + 2; ++i) s0[i] = s1[i] = s2[i] = mark;
        p.store(s0 + 1, s1 + 1);
        q.store(s2 + 1);
        bool ok = same_limb(s0[0], mark) && same_limb(s0[W + 1], mark) && same_limb(s1[0], mark) &&
                  same_limb(s1[W + 1], mark) && same_limb(s2[0], mark) && same_limb(s2[W + 1], mark);
        for (int i = 0; i < W; ++i)
            ok = ok && same_limb(s0[i + 1], p.lane(i).limb[0]) && same_limb(s1[i + 1], p.lane(i).limb[1]) &&
                 same_limb(s2[i + 1], a[i]);
        ++checked;
        if (!ok) {
            ++failures;
            std::printf("FAILED store (%s): pair %zu\n", type_name<T>(), k);
        }
        // The tail: every count, with a fill of its own.
        const E2<T> fill = E2<T>(T(-3.25));
        for (int n = 0; n <= W; ++n) {
            const P2<T> t = P2<T>::load_partial(x0, x1, n, fill);
            const P1<T> t1 = P1<T>::load_partial(a, n, E1<T>(T(0.5)));
            for (int i = 0; i < W; ++i) {
                checked += 2;
                if (!same(t.lane(i), i < n ? want[i] : fill)) report("load_partial", type_name<T>(), i, t.lane(i), fill);
                if (!same(t1.lane(i), E1<T>(i < n ? a[i] : T(0.5))))
                    report("load_partial p1", type_name<T>(), i, t1.lane(i), E1<T>(a[i]));
            }
            for (int i = 0; i < W + 2; ++i) s0[i] = s1[i] = s2[i] = mark;
            p.store_partial(s0 + 1, s1 + 1, n);
            q.store_partial(s2 + 1, n);
            ok = true;
            for (int i = 0; i < W + 2; ++i) {
                const bool written = i >= 1 && i <= n;
                ok = ok && same_limb(s0[i], written ? p.lane(i - 1).limb[0] : mark) &&
                     same_limb(s1[i], written ? p.lane(i - 1).limb[1] : mark) &&
                     same_limb(s2[i], written ? a[i - 1] : mark);
            }
            ++checked;
            if (!ok) {
                ++failures;
                std::printf("FAILED store_partial (%s): count %d\n", type_name<T>(), n);
            }
        }
        // broadcast, and set_lane against lane: every limb as given, -0 and NaN included.
        const P2<T> b = P2<T>::broadcast(c.two[k]);
        P2<T> s = b;
        s.set_lane(int(k % W), c.two[(k + 1) % c.two.size()]);
        for (int i = 0; i < W; ++i) {
            checked += 2;
            if (!same(b.lane(i), c.two[k])) report("broadcast", type_name<T>(), i, b.lane(i), c.two[k]);
            const E2<T>& w = i == int(k % W) ? c.two[(k + 1) % c.two.size()] : c.two[k];
            if (!same(s.lane(i), w)) report("set_lane", type_name<T>(), i, s.lane(i), w);
        }
    }
    // Zero by default.
    const P2<T> z;
    const P1<T> z1;
    for (int i = 0; i < W; ++i) {
        checked += 2;
        if (!same(z.lane(i), E2<T>()) || !same(z1.lane(i), E1<T>())) report("Packed()", type_name<T>(), i, z.lane(i), E2<T>());
    }
}

template <class T>
void all_of_one_type() {
    const Corpus<T> c = make_corpus<T>();
    const long before = failures, before_checked = checked;
    arithmetic(c);
    comparisons<T, 1, 1>(c, "p1 p1");
    comparisons<T, 2, 2>(c, "p2 p2");
    comparisons<T, 2, 1>(c, "p2 p1");
    comparisons<T, 1, 2>(c, "p1 p2");
    masks<T, 1>(c);
    masks<T, 2>(c);
    moves(c);
    std::printf("%s: %s, %d lanes: %ld lanes compared with the scalar operations, %ld differ\n", type_name<T>(),
                form_name, P2<T>::lanes, checked - before_checked, failures - before);
}

}  // namespace

int main() {
    all_of_one_type<double>();
    all_of_one_type<float>();
    if (failures) {
        std::printf("FAILED: %ld differences\n", failures);
        return 1;
    }
    std::printf("ok: every operation of Packed gives, in every lane, the bits of the scalar operation; the products "
                "of one limb gave +0 where T's product gives -0 in %ld lanes (the kernel mul_1_1 is fma(a, b, +0))\n",
                zero_signs);
    return 0;
}
