// The functions on arrays of include/kairn/batch.hpp, beside what the oracle judges of their claims
// (api.oracle.FOLD.FORMAT, through runner_arrays.hpp): that each calls the loop its comment names,
// in the order it says, on every length around the lanes of Packed; that what a flag says of the
// result holds in every position; and the cases of the edges. For T double and float, k 1 and 2.
//
// - The orders: sum, sum_fast and dot with no order argument give, bit for bit (a zero compared as
//   a zero: under MSVC the packed guard can change its sign), what the generated loop of the lane
//   order gives with W = Packed<T, k>::lanes (gen::F_lanes, the reference of the packed loop); with
//   kairn::sequential, what the sequential loop gives (gen::F_seq); with W = 1, the two agree. On
//   arrays of lengths 0, 1, W - 1, W, W + 1, 2W - 1, 2W, 2W + 1, 3W + 2 and 97, of numbers with
//   cancellation, zeros of both signs and subnormal numbers.
// - The maps, the convolution and norm_upper give what the sequential loop gives (a map's elements
//   do not depend on the order), and a map in place (z the same arrays as x, or as y) what it gives
//   out of place.
// - The flag: an infinity or a NaN in each position of arrays of every length up to 2W + 1, and
//   sums and products that overflow, give finite = false and the canonical NaN (every limb a NaN);
//   a map's flag false makes exactly the elements that are not finite the canonical NaN.
// - The edges: empty arrays (the sum and the dot product +0, norm_upper 0 for one limb and the
//   smallest positive number for two, no coefficient for a convolution with an empty operand), a
//   view of one limb over a plain const T* array, and the types (Reduction an aggregate, trivially
//   copyable, bound by a structured binding).
//
// Built in every form of Packed the compiler can build here (tests/api/CMakeLists.txt: api.batch.FORM).
#include <kairn/batch.hpp>

#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <limits>
#include <type_traits>
#include <utility>
#include <vector>

namespace {

int failures = 0;

void check(bool ok, const char* what, const char* type, int k, std::size_t n, long where = -1) {
    if (ok) return;
    ++failures;
    if (failures <= 40)
        std::printf("FAILED %s (%s, %d limbs, n = %zu%s%ld)\n", what, type, k, n, where >= 0 ? ", at " : "",
                    where >= 0 ? where : 0L);
}

template <class T>
const char* name_of() {
    return sizeof(T) == 8 ? "double" : "float";
}

// The same value: equal bits, or both zeros, or both NaN.
template <class T>
bool same(T a, T b) {
    if (a != a) return b != b;
    if (a == 0) return b == 0;
    return std::memcmp(&a, &b, sizeof(T)) == 0;
}

// SplitMix64.
struct Random {
    std::uint64_t state;
    std::uint64_t next() {
        std::uint64_t z = (state += 0x9e3779b97f4a7c15u);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9u;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebu;
        return z ^ (z >> 31);
    }
    int below(int n) { return int(next() % std::uint64_t(n)); }
};

// K arrays of n elements: canonical numbers with cancellation (pairs of near opposites), zeros of
// both signs and subnormal numbers among them; for two limbs, a second limb below half a unit of
// the first, so that the pair is normalized.
template <class T, int K>
struct Arrays {
    std::vector<T> limb[K];
    explicit Arrays(std::size_t n, Random& r) {
        for (int j = 0; j < K; ++j) limb[j].assign(n, T(0));
        for (std::size_t i = 0; i < n; ++i) {
            T h;
            switch (r.below(8)) {
            case 0: h = T(0); break;
            case 1: h = -T(0); break;
            case 2: h = std::numeric_limits<T>::denorm_min() * T(1 + r.below(100)); break;
            case 3: h = i > 0 ? -limb[0][i - 1] * T(1 + 0x1p-20 * r.below(3)) : T(1); break;
            default: h = std::ldexp(T(1 + r.below(1 << 20)) / T(1 << 20), r.below(40) - 20) * (r.below(2) ? 1 : -1);
            }
            limb[0][i] = h;
            if constexpr (K == 2) {
                const int e = h == 0 ? 0 : std::ilogb(h);
                const T l = h == 0 || !std::isnormal(h) ? T(0) : std::ldexp(T(r.below(1 << 10)) / T(1 << 12), e - std::numeric_limits<T>::digits);
                limb[1][i] = h + l == h ? l : T(0);
            }
        }
    }
    kairn::SoAView<const T, K> view() const {
        if constexpr (K == 1) {
            return kairn::SoAView<const T, 1>(limb[0].data(), limb[0].size());
        } else {
            return kairn::SoAView<const T, 2>(limb[0].data(), limb[1].data(), limb[0].size());
        }
    }
    kairn::SoAView<T, K> view() {
        if constexpr (K == 1) {
            return kairn::SoAView<T, 1>(limb[0].data(), limb[0].size());
        } else {
            return kairn::SoAView<T, 2>(limb[0].data(), limb[1].data(), limb[0].size());
        }
    }
};

template <class T, int K>
bool same_number(const kairn::Expansion<T, K>& a, const T* b) {
    for (int j = 0; j < K; ++j)
        if (!same(a.limb[j], b[j])) return false;
    return true;
}
template <class T, int K>
bool canonical_nan(const kairn::Expansion<T, K>& a) {
    for (int j = 0; j < K; ++j)
        if (a.limb[j] == a.limb[j]) return false;
    return true;
}

// The loops, called directly: what the public function must give.
template <class T, int K>
void sum_loop(const kairn::SoAView<const T, K>& x, std::size_t lanes, bool fast, T* r, bool& f) {
    if constexpr (K == 1) {
        (void)fast;
        if (lanes) kairn::gen::sum_1_entry_lanes(x.limb(0), x.size(), lanes, r[0], f);
        else kairn::gen::sum_1_entry_seq(x.limb(0), x.size(), r[0], f);
    } else if (fast) {
        if (lanes) kairn::gen::sum_fast_2_entry_lanes(x.limb(0), x.limb(1), x.size(), lanes, r[0], r[1], f);
        else kairn::gen::sum_fast_2_entry_seq(x.limb(0), x.limb(1), x.size(), r[0], r[1], f);
    } else {
        if (lanes) kairn::gen::sum_2_entry_lanes(x.limb(0), x.limb(1), x.size(), lanes, r[0], r[1], f);
        else kairn::gen::sum_2_entry_seq(x.limb(0), x.limb(1), x.size(), r[0], r[1], f);
    }
}
template <class T, int K>
void dot_loop(const kairn::SoAView<const T, K>& x, const kairn::SoAView<const T, K>& y, std::size_t lanes, T* r,
              bool& f) {
    if constexpr (K == 1) {
        if (lanes) kairn::gen::dot_1_lanes(x.limb(0), y.limb(0), x.size(), lanes, r[0], f);
        else kairn::gen::dot_1_seq(x.limb(0), y.limb(0), x.size(), r[0], f);
    } else {
        if (lanes) kairn::gen::dot_2_lanes(x.limb(0), x.limb(1), y.limb(0), y.limb(1), x.size(), lanes, r[0], r[1], f);
        else kairn::gen::dot_2_seq(x.limb(0), x.limb(1), y.limb(0), y.limb(1), x.size(), r[0], r[1], f);
    }
}

template <class T, int K>
void orders(Random& rnd) {
    using P = kairn::Packed<T, K>;
    const std::size_t w = std::size_t(P::lanes);
    const std::size_t lengths[] = {0, 1, w - 1, w, w + 1, 2 * w - 1, 2 * w, 2 * w + 1, 3 * w + 2, 97};
    for (std::size_t n : lengths) {
        for (int trial = 0; trial < 20; ++trial) {
            const Arrays<T, K> a(n, rnd), b(n, rnd);
            const auto x = a.view(), y = b.view();
            T r[K];
            bool f = false;
            for (int fast = 0; fast < 2; ++fast) {
                const auto lane = fast ? kairn::sum_fast(x) : kairn::sum(x);
                const auto seq = fast ? kairn::sum_fast(x, kairn::sequential) : kairn::sum(x, kairn::sequential);
                sum_loop<T, K>(x, w, fast, r, f);
                check(same_number(lane.value, r) && lane.finite == f, fast ? "sum_fast is the lane order" : "sum is the lane order", name_of<T>(), K, n);
                sum_loop<T, K>(x, 0, fast, r, f);
                check(same_number(seq.value, r) && seq.finite == f, fast ? "sum_fast(x, sequential) is the sequential order" : "sum(x, sequential) is the sequential order", name_of<T>(), K, n);
                if (w == 1) check(same_number(lane.value, r), "with one lane the two orders agree", name_of<T>(), K, n);
            }
            const auto lane = kairn::dot(x, y);
            const auto seq = kairn::dot(x, y, kairn::sequential);
            dot_loop<T, K>(x, y, w, r, f);
            check(same_number(lane.value, r) && lane.finite == f, "dot is the lane order", name_of<T>(), K, n);
            dot_loop<T, K>(x, y, 0, r, f);
            check(same_number(seq.value, r) && seq.finite == f, "dot(x, y, sequential) is the sequential order", name_of<T>(), K, n);
            // A view of T (not const) is taken as well, and a view of the arrays of an SoA.
            kairn::SoA<T, K> s(n);
            for (std::size_t i = 0; i < n; ++i) s.set(i, x.get(i));
            const auto from_soa = kairn::sum(s.view(), kairn::sequential);
            const auto of_x = kairn::sum(x, kairn::sequential);
            check(same_number(from_soa.value, of_x.value.limb) && from_soa.finite == of_x.finite, "a view of an SoA",
                  name_of<T>(), K, n);
        }
    }
}

// A map against its sequential loop, and in place.
template <class T, int K>
void maps(Random& rnd) {
    using P = kairn::Packed<T, K>;
    const std::size_t w = std::size_t(P::lanes);
    const std::size_t lengths[] = {0, 1, w - 1, w, w + 1, 2 * w - 1, 2 * w + 1, 3 * w + 2, 97};
    for (std::size_t n : lengths) {
        for (int trial = 0; trial < 10; ++trial) {
            const Arrays<T, K> a(n, rnd), b(n, rnd);
            const auto x = a.view(), y = b.view();
            const T s = T(1.5) + T(rnd.below(8)), c = T(0.25);
            const T s2_limbs[2] = {T(1.5), T(1.5) * std::numeric_limits<T>::epsilon() / T(4)};
            const kairn::Expansion<T, 2> s2 = kairn::Expansion<T, 2>::from_limbs(s2_limbs);
            // op: 0 add, 1 sub, 2 scale, 3 mul_pow2, 4 axpy (a T), 5 axpy (a two-limb a).
            for (int op = 0; op < 6; ++op) {
                if (op == 5 && K == 1) continue;
                Arrays<T, K> z(n, rnd), ref(n, rnd);
                bool fz = false, fr = false;
                auto run = [&](kairn::SoAView<T, K> out, auto xx, auto yy) -> bool {
                    switch (op) {
                    case 0: return kairn::add(xx, yy, out);
                    case 1: return kairn::sub(xx, yy, out);
                    case 2: return kairn::scale(xx, s, out);
                    case 3: return kairn::mul_pow2(xx, c, out);
                    case 4: return kairn::axpy(s, xx, yy, out);
                    default:
                        if constexpr (K == 2) return kairn::axpy(s2, xx, yy, out);
                        return false;
                    }
                };
                fz = run(z.view(), x, y);
                // The sequential loop.
                auto o = ref.view();
                if constexpr (K == 1) {
                    switch (op) {
                    case 0: kairn::gen::add_1_entry_seq(x.limb(0), y.limb(0), n, o.limb(0), fr); break;
                    case 1: kairn::gen::sub_1_entry_seq(x.limb(0), y.limb(0), n, o.limb(0), fr); break;
                    case 2: kairn::gen::scale_1_seq(x.limb(0), n, s, o.limb(0), fr); break;
                    case 3: kairn::gen::mul_pow2_map_1_seq(x.limb(0), n, c, o.limb(0), fr); break;
                    default: kairn::gen::axpy_1_entry_seq(x.limb(0), y.limb(0), n, s, o.limb(0), fr);
                    }
                } else {
                    switch (op) {
                    case 0: kairn::gen::add_2_entry_seq(x.limb(0), x.limb(1), y.limb(0), y.limb(1), n, o.limb(0), o.limb(1), fr); break;
                    case 1: kairn::gen::sub_2_entry_seq(x.limb(0), x.limb(1), y.limb(0), y.limb(1), n, o.limb(0), o.limb(1), fr); break;
                    case 2: kairn::gen::scale_2_seq(x.limb(0), x.limb(1), n, s, o.limb(0), o.limb(1), fr); break;
                    case 3: kairn::gen::mul_pow2_map_2_seq(x.limb(0), x.limb(1), n, c, o.limb(0), o.limb(1), fr); break;
                    case 4: kairn::gen::axpy_2_1_entry_seq(x.limb(0), x.limb(1), y.limb(0), y.limb(1), n, s, o.limb(0), o.limb(1), fr); break;
                    default: kairn::gen::axpy_2_entry_seq(x.limb(0), x.limb(1), y.limb(0), y.limb(1), n, s2.limb[0], s2.limb[1], o.limb(0), o.limb(1), fr);
                    }
                }
                bool eq = fz == fr;
                for (int j = 0; j < K; ++j)
                    for (std::size_t i = 0; i < n; ++i) eq = eq && same(z.limb[j][i], ref.limb[j][i]);
                check(eq, "a map is its sequential loop", name_of<T>(), K, n, op);
                // In place: z = x, and z = y where the map reads y.
                for (int which = 0; which < (op == 2 || op == 3 ? 1 : 2); ++which) {
                    Arrays<T, K> in = which == 0 ? a : b;
                    const auto other = which == 0 ? y : x;
                    const bool f = which == 0 ? run(in.view(), kairn::SoAView<const T, K>(in.view()), other)
                                              : run(in.view(), other, kairn::SoAView<const T, K>(in.view()));
                    bool ok = which == 0 ? f == fz : true;
                    if (which == 0) {
                        for (int j = 0; j < K; ++j)
                            for (std::size_t i = 0; i < n; ++i) ok = ok && same(in.limb[j][i], z.limb[j][i]);
                    } else {
                        // y in place: the same as out of place on (x, y).
                        Arrays<T, K> z2(n, rnd);
                        const bool f2 = run(z2.view(), x, y);
                        ok = f == f2;
                        for (int j = 0; j < K; ++j)
                            for (std::size_t i = 0; i < n; ++i) ok = ok && same(in.limb[j][i], z2.limb[j][i]);
                    }
                    check(ok, which == 0 ? "a map in place, z = x" : "a map in place, z = y", name_of<T>(), K, n, op);
                }
            }
        }
    }
}

template <class T, int K>
void convolutions_and_norms(Random& rnd) {
    const std::size_t lengths[] = {0, 1, 2, 5, 13};
    for (std::size_t nx : lengths) {
        for (std::size_t ny : lengths) {
            const Arrays<T, K> a(nx, rnd), b(ny, rnd);
            const std::size_t nz = nx == 0 || ny == 0 ? 0 : nx + ny - 1;
            Arrays<T, K> z(nz, rnd), ref(nz, rnd);
            const bool f = kairn::conv(a.view(), b.view(), z.view());
            bool fr = false;
            if constexpr (K == 1) {
                kairn::gen::conv_1_seq(a.limb[0].data(), nx, b.limb[0].data(), ny, ref.limb[0].data(), fr);
            } else {
                kairn::gen::conv_2_seq(a.limb[0].data(), a.limb[1].data(), nx, b.limb[0].data(), b.limb[1].data(), ny,
                                       ref.limb[0].data(), ref.limb[1].data(), fr);
            }
            bool eq = f == fr && f;
            for (int j = 0; j < K; ++j)
                for (std::size_t i = 0; i < nz; ++i) eq = eq && same(z.limb[j][i], ref.limb[j][i]);
            check(eq, "conv is its loop (and finite)", name_of<T>(), K, nx * 100 + ny);
        }
    }
    for (std::size_t n : {std::size_t(0), std::size_t(1), std::size_t(7), std::size_t(40)}) {
        const Arrays<T, K> a(n, rnd);
        const kairn::Reduction<T> r = kairn::norm_upper(a.view());
        T m = T(0);
        bool f = false;
        if constexpr (K == 1) {
            kairn::gen::norm_upper_1_seq(a.limb[0].data(), n, m, f);
        } else {
            kairn::gen::norm_upper_2_seq(a.limb[0].data(), a.limb[1].data(), n, m, f);
        }
        check(same(r.value, m) && r.finite == f && f, "norm_upper is its loop", name_of<T>(), K, n);
        if (n == 0) {
            const T expected = K == 1 ? T(0) : std::numeric_limits<T>::denorm_min();
            check(r.value == expected, "norm_upper of no element", name_of<T>(), K, n);
        }
        bool above = true;
        for (std::size_t i = 0; i < n; ++i) above = above && std::fabs(a.limb[0][i]) <= r.value;
        check(above, "norm_upper is at least every leading limb's magnitude", name_of<T>(), K, n);
    }
}

// Infinities and NaN in every position, and overflows.
template <class T, int K>
void not_finite(Random& rnd) {
    using P = kairn::Packed<T, K>;
    const std::size_t w = std::size_t(P::lanes);
    const T specials[] = {std::numeric_limits<T>::infinity(), -std::numeric_limits<T>::infinity(),
                          std::numeric_limits<T>::quiet_NaN()};
    for (std::size_t n = 1; n <= 2 * w + 1; ++n) {
        for (std::size_t at = 0; at < n; ++at) {
            for (T v : specials) {
                Arrays<T, K> a(n, rnd);
                const Arrays<T, K> b(n, rnd);
                a.limb[0][at] = v;
                if constexpr (K == 2) a.limb[1][at] = v == v ? T(0) : v;  // canonical: (inf, 0), (NaN, NaN)
                const auto x = std::as_const(a).view();
                const auto y = b.view();
                const auto s = kairn::sum(x), q = kairn::sum(x, kairn::sequential), d = kairn::dot(x, y);
                const auto sf = kairn::sum_fast(x);
                check(!s.finite && canonical_nan(s.value), "a sum with an infinite or NaN element", name_of<T>(), K, n, long(at));
                check(!q.finite && canonical_nan(q.value), "a sequential sum with an infinite or NaN element", name_of<T>(), K, n, long(at));
                check(!sf.finite && canonical_nan(sf.value), "sum_fast with an infinite or NaN element", name_of<T>(), K, n, long(at));
                check(!d.finite && canonical_nan(d.value), "a dot product with an infinite or NaN element", name_of<T>(), K, n, long(at));
                const auto m = kairn::norm_upper(x);
                check(!m.finite && m.value != m.value, "norm_upper with an infinite or NaN element", name_of<T>(), K, n, long(at));
                // A map: exactly the element at `at` is the canonical NaN.
                Arrays<T, K> z(n, rnd);
                const bool f = kairn::add(x, y, z.view());
                bool ok = !f;
                for (std::size_t i = 0; i < n; ++i) {
                    bool nan = true;
                    for (int j = 0; j < K; ++j) nan = nan && z.limb[j][i] != z.limb[j][i];
                    ok = ok && (i == at ? nan : std::isfinite(z.limb[0][i]));
                }
                check(ok, "a map's flag and its canonical NaN", name_of<T>(), K, n, long(at));
            }
        }
    }
    // Overflow: n copies of the largest finite number.
    for (std::size_t n : {std::size_t(2), w + 1, 3 * w}) {
        Arrays<T, K> a(n, rnd);
        for (std::size_t i = 0; i < n; ++i) {
            a.limb[0][i] = std::numeric_limits<T>::max();
            if constexpr (K == 2) a.limb[1][i] = T(0);
        }
        const auto x = std::as_const(a).view();
        const auto s = kairn::sum(x), q = kairn::sum(x, kairn::sequential), d = kairn::dot(x, x);
        check(!s.finite && canonical_nan(s.value) && !q.finite && canonical_nan(q.value), "a sum that overflows", name_of<T>(), K, n);
        check(!d.finite && canonical_nan(d.value), "a dot product that overflows", name_of<T>(), K, n);
        Arrays<T, K> z(n, rnd);
        check(!kairn::scale(x, T(4), z.view()), "a scaling that overflows", name_of<T>(), K, n);
    }
}

template <class T, int K>
void edges() {
    const kairn::SoAView<const T, K> none;
    const auto s = kairn::sum(none), d = kairn::dot(none, none);
    check(s.finite && s.value.limb[0] == 0 && d.finite && d.value.limb[0] == 0, "the sum of no element is 0", name_of<T>(), K, 0);
    check(kairn::add(none, none, kairn::SoAView<T, K>()), "a map of no element", name_of<T>(), K, 0);
    check(kairn::conv(none, none, kairn::SoAView<T, K>()), "a convolution of empty polynomials", name_of<T>(), K, 0);
}

}  // namespace

int main() {
    // The types.
    static_assert(std::is_aggregate_v<kairn::Reduction<kairn::Expansion<double, 2>>>);
    static_assert(std::is_trivially_copyable_v<kairn::Reduction<kairn::Expansion<double, 2>>>);
    static_assert(std::is_trivially_copyable_v<kairn::Reduction<float>>);
    static_assert(std::is_trivially_copyable_v<kairn::Sequential> && std::is_empty_v<kairn::Sequential>);

    Random rnd{20261121};
    orders<double, 1>(rnd);
    orders<double, 2>(rnd);
    orders<float, 1>(rnd);
    orders<float, 2>(rnd);
    maps<double, 1>(rnd);
    maps<double, 2>(rnd);
    maps<float, 1>(rnd);
    maps<float, 2>(rnd);
    convolutions_and_norms<double, 1>(rnd);
    convolutions_and_norms<double, 2>(rnd);
    convolutions_and_norms<float, 1>(rnd);
    convolutions_and_norms<float, 2>(rnd);
    not_finite<double, 1>(rnd);
    not_finite<double, 2>(rnd);
    not_finite<float, 1>(rnd);
    not_finite<float, 2>(rnd);
    edges<double, 1>();
    edges<double, 2>();
    edges<float, 1>();
    edges<float, 2>();

    // A program with a plain array of T and a length.
    const double p[5] = {1.0, 0x1p-60, -1.0, 3.0, 0.5};
    const kairn::Reduction<kairn::Expansion<double, 1>> s = kairn::sum(kairn::SoAView<const double, 1>(p, 5));
    auto [value, finite] = kairn::dot(kairn::SoAView<const double, 1>(p, 5), kairn::SoAView<const double, 1>(p, 5));
    check(s.finite && s.value.limb[0] == 3.5 && finite && value.limb[0] == 11.25, "a view of a plain array", "double", 1, 5);

    if (failures) {
        std::printf("%d failures\n", failures);
        return 1;
    }
    std::printf("batch: every check passed (W = %d lanes of double, %d of float)\n", kairn::Packed<double, 1>::lanes,
                kairn::Packed<float, 1>::lanes);
    return 0;
}
