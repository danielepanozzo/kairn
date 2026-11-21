// What tests/api/arrays_exact.py checks in exact rational arithmetic, written as lines of text:
//
//   arrays_exact bounds    the bounds as functions of the length (kairn::traits<X>::sum(n), dot(n)),
//                          for float and double, one and two limbs, at the lengths where the count
//                          given to the kernel is converted to T exactly and where it is rounded
//                          up (around 2^p, and beyond), at powers of two, near the largest
//                          std::size_t and at random lengths: one line per bound,
//                          "sum|dot K T n unit tiny", the limbs as C99 hexadecimal literals.
//   arrays_exact accumulator   histories of kairn::Accumulator: random trees of add, add_product
//                          and merge; empty accumulators merged; counts around and beyond 2^p,
//                          where their conversion to T rounds (a history merged with itself);
//                          a count that saturates; overflow of the running sum and of the sum of
//                          magnitudes; terms that are not finite. Each as a line
//                          "acc K T WHAT NTERMS", the terms ("+ TIMES x..." or "* TIMES x... y...",
//                          TIMES its multiplicity), and the result "= COUNT s... a r FINITE
//                          center... radius" (the running sum, the magnitudes, error_bound(), the
//                          flag of sum(), and ball()).
//
// Every value is printed as a double (a float converts exactly), so that the checker reads it with
// float.fromhex.
#include <kairn/accumulator.hpp>
#include <kairn/kairn.hpp>

#include <cmath>

#include <cstdint>
#include <cstdio>
#include <cstring>
#include <initializer_list>
#include <limits>
#include <type_traits>
#include <vector>

namespace {

void put(double v) {
    if (v != v) {
        std::printf(" nan");
    } else if (v == std::numeric_limits<double>::infinity()) {
        std::printf(" inf");
    } else {
        std::printf(" %a", v);
    }
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
};

template <class T, int K>
void bounds(const char* type, const std::vector<std::uint64_t>& lengths) {
    using X = std::conditional_t<K == 1, T, kairn::Expansion<T, 2>>;
    for (std::uint64_t n64 : lengths) {
        if (n64 > std::uint64_t(std::numeric_limits<std::size_t>::max())) continue;
        const std::size_t n = std::size_t(n64);
        const kairn::Bound<T> s = kairn::traits<X>::sum(n), d = kairn::traits<X>::dot(n);
        std::printf("sum %d %s %llu", K, type, static_cast<unsigned long long>(n64));
        put(double(s.unit));
        put(double(s.tiny));
        std::printf("\ndot %d %s %llu", K, type, static_cast<unsigned long long>(n64));
        put(double(d.unit));
        put(double(d.tiny));
        std::printf("\n");
    }
}

int run_bounds() {
    std::vector<std::uint64_t> lengths = {0, 1, 2, 3, 4, 5, 7, 8, 9, 1000, 1001};
    // Around 2^p, where the conversion of n - 1 and n to T starts to round, for both limb types,
    // and around a few multiples above.
    for (int p : {24, 53}) {
        for (int k = 0; k < 4; ++k) {
            const std::uint64_t base = (std::uint64_t{1} << (p + k)) * (k == 3 ? 3 : 1);
            for (std::uint64_t d = 0; d < 6; ++d) {
                lengths.push_back(base + d);
                lengths.push_back(base - d);
            }
        }
    }
    // Every power of two, and its neighbors.
    for (int e = 4; e < 64; ++e) {
        const std::uint64_t b = std::uint64_t{1} << e;
        lengths.push_back(b - 1);
        lengths.push_back(b);
        lengths.push_back(b + 1);
    }
    // The largest lengths, whose count rounds up to 2^64.
    for (std::uint64_t d = 0; d < 4; ++d) lengths.push_back(~std::uint64_t{0} - d);
    lengths.push_back(~std::uint64_t{0} - (std::uint64_t{1} << 11));
    lengths.push_back(~std::uint64_t{0} - (std::uint64_t{1} << 40));
    // Random lengths, log-uniform.
    Random r{0x6b61697266};
    for (int i = 0; i < 400; ++i) {
        const int e = int(r.next() % 64);
        lengths.push_back(r.next() >> (63 - e));
    }
    bounds<double, 1>("binary64", lengths);
    bounds<double, 2>("binary64", lengths);
    bounds<float, 1>("binary32", lengths);
    bounds<float, 2>("binary32", lengths);
    return 0;
}

// A term of an accumulator's history: x (add) or x y (add_product), each of K limbs, with the number
// of times it was added (a merge with itself doubles every multiplicity).
template <class T, int K>
struct Term {
    bool product = false;
    T x[K] = {}, y[K] = {};
    std::uint64_t times = 1;
};
template <class T, int K>
struct History {
    kairn::Accumulator<T, K> acc;
    std::vector<Term<T, K>> terms;
};

// A random number of K limbs: a canonical pair for two limbs, with a second limb below half a unit
// of the first; magnitudes from 2^lo to 2^hi, zeros, subnormal numbers and near opposites among
// them.
template <class T, int K>
kairn::Expansion<T, K> random_number(Random& r, int lo, int hi) {
    T h;
    switch (r.next() % 8) {
    case 0: h = T(0); break;
    case 1: h = std::numeric_limits<T>::denorm_min() * T(1 + r.next() % 1000); break;
    default:
        h = std::ldexp(T(1) + T(r.next() % (1u << 20)) / T(1 << 20), lo + int(r.next() % std::uint64_t(hi - lo + 1)));
        if (r.next() & 1) h = -h;
    }
    T limbs[2] = {h, T(0)};
    if constexpr (K == 2) {
        if (h != 0 && std::isnormal(h)) {
            const T l = std::ldexp(T(r.next() % 4096) / T(8192), std::ilogb(h) - std::numeric_limits<T>::digits);
            if (h + l == h) limbs[1] = (r.next() & 1) ? l : -l;
        }
    }
    return kairn::Expansion<T, K>::from_limbs(limbs);
}

template <class T, int K>
void print_history(const char* type, const char* what, const History<T, K>& h) {
    std::printf("acc %d %s %s %zu\n", K, type, what, h.terms.size());
    for (const Term<T, K>& t : h.terms) {
        std::printf("%s %llu", t.product ? "*" : "+", static_cast<unsigned long long>(t.times));
        for (int j = 0; j < K; ++j) put(double(t.x[j]));
        if (t.product)
            for (int j = 0; j < K; ++j) put(double(t.y[j]));
        std::printf("\n");
    }
    const kairn::Reduction<kairn::Expansion<T, K>> s = h.acc.sum();
    const kairn::Ball<T, K> b = h.acc.ball();
    std::printf("= %llu", static_cast<unsigned long long>(h.acc.count()));
    for (int j = 0; j < K; ++j) put(double(h.acc.running_sum().limb[j]));
    put(double(h.acc.magnitudes()));
    put(double(h.acc.error_bound()));
    std::printf(" %d", int(s.finite));
    for (int j = 0; j < K; ++j) put(double(b.center().limb[j]));
    put(double(b.radius()));
    std::printf("\n");
}

template <class T, int K>
void add_random(History<T, K>& h, Random& r, int lo, int hi) {
    Term<T, K> t;
    const kairn::Expansion<T, K> x = random_number<T, K>(r, lo, hi);
    for (int j = 0; j < K; ++j) t.x[j] = x.limb[j];
    switch (r.next() % 4) {
    case 0: h.acc.add(x); break;
    case 1:
        t.x[K - 1] = K == 2 ? T(0) : t.x[0];
        h.acc.add(x.limb[0]);
        break;
    default: {
        t.product = true;
        const kairn::Expansion<T, K> y = random_number<T, K>(r, lo / 2, hi / 2);
        for (int j = 0; j < K; ++j) t.y[j] = y.limb[j];
        h.acc.add_product(x, y);
    }
    }
    h.terms.push_back(t);
}
template <class T, int K>
void merge(History<T, K>& into, const History<T, K>& other) {
    into.acc.merge(other.acc);
    into.terms.insert(into.terms.end(), other.terms.begin(), other.terms.end());
}
// Merges h with itself k times: 2^k copies of every term.
template <class T, int K>
void double_up(History<T, K>& h, int k) {
    for (int i = 0; i < k; ++i) {
        h.acc.merge(h.acc);
        for (Term<T, K>& t : h.terms) t.times *= 2;
    }
}

template <class T, int K>
void accumulator_histories(const char* type, Random& r) {
    constexpr int p = std::numeric_limits<T>::digits;
    const int range = sizeof(T) == 8 ? 60 : 20;
    // Random trees: leaves of random histories, merged in a random order.
    for (int round = 0; round < 300; ++round) {
        std::vector<History<T, K>> leaves(1 + r.next() % 6);
        for (History<T, K>& h : leaves) {
            const int n = int(r.next() % 40);
            for (int i = 0; i < n; ++i) add_random(h, r, -range, range);
        }
        while (leaves.size() > 1) {
            const std::size_t i = std::size_t(r.next() % leaves.size()), j = (i + 1) % leaves.size();
            merge(leaves[i], leaves[j]);
            leaves.erase(leaves.begin() + std::ptrdiff_t(j));
        }
        print_history(type, "random", leaves[0]);
    }
    // Empty accumulators, merged: no term, a radius of a few smallest normal numbers.
    History<T, K> e1, e2;
    merge(e1, e2);
    print_history(type, "empty", e1);
    History<T, K> e3;
    add_random(e3, r, -4, 4);
    merge(e3, e1);
    print_history(type, "with_empty", e3);
    // Counts around and beyond 2^p, where their conversion to T rounds: a short history merged with
    // itself, then one term more, so that the count is 2^k + 1 or 3 2^k + 1.
    for (int k : {p - 4, p - 1, p, p + 1, p + 7, 2 * p - 6}) {
        for (int three = 0; three < 2; ++three) {
            if (k > 62) continue;
            History<T, K> h;
            add_random(h, r, -4, 4);
            if (three) {
                add_random(h, r, -4, 4);
                add_random(h, r, -4, 4);
            }
            double_up(h, k);
            add_random(h, r, -4, 4);
            print_history(type, three ? "count_3_2k" : "count_2k", h);
        }
    }
    // A count that saturates: no bound.
    History<T, K> s;
    add_random(s, r, -4, 4);
    s.acc.merge(s.acc);
    for (int i = 0; i < 64; ++i) s.acc.merge(s.acc);
    s.terms[0].times = 0;  // the multiplicity is beyond 2^64: the checker only needs the count
    print_history(type, "saturated", s);
    // The running sum overflows; the sum of magnitudes overflows while the running sum stays finite;
    // a term that is not finite.
    const T big = std::numeric_limits<T>::max();
    History<T, K> o;
    for (int i = 0; i < 3; ++i) {
        o.acc.add(big);
        Term<T, K> t;
        t.x[0] = big;
        o.terms.push_back(t);
    }
    print_history(type, "overflow", o);
    History<T, K> m;
    for (int i = 0; i < 4; ++i) {
        const T v = i % 2 ? -big : big;
        m.acc.add(v);
        Term<T, K> t;
        t.x[0] = v;
        m.terms.push_back(t);
    }
    print_history(type, "magnitudes_overflow", m);
    for (const T bad : {std::numeric_limits<T>::infinity(), std::numeric_limits<T>::quiet_NaN()}) {
        History<T, K> nf;
        add_random(nf, r, -4, 4);
        nf.acc.add(bad);
        Term<T, K> t;
        t.x[0] = bad;
        if constexpr (K == 2) t.x[1] = bad == bad ? T(0) : bad;
        nf.terms.push_back(t);
        add_random(nf, r, -4, 4);
        print_history(type, "not_finite", nf);
    }
    // inf times 0: a NaN term.
    History<T, K> z;
    z.acc.add_product(std::numeric_limits<T>::infinity(), T(0));
    Term<T, K> t;
    t.product = true;
    t.x[0] = std::numeric_limits<T>::infinity();
    z.terms.push_back(t);
    print_history(type, "not_finite", z);
}

int run_accumulator() {
    Random r{0x616363};
    accumulator_histories<double, 1>("binary64", r);
    accumulator_histories<double, 2>("binary64", r);
    accumulator_histories<float, 1>("binary32", r);
    accumulator_histories<float, 2>("binary32", r);
    return 0;
}

}  // namespace

int main(int argc, char** argv) {
    if (argc == 2 && std::strcmp(argv[1], "bounds") == 0) return run_bounds();
    if (argc == 2 && std::strcmp(argv[1], "accumulator") == 0) return run_accumulator();
    std::fprintf(stderr, "usage: arrays_exact bounds | accumulator\n");
    return 2;
}
