// The dot product of the tutorial docs/tutorials/vector-loop.md written three ways and timed: a
// plain loop of T for scale, a loop of kairn::Expansion<T, k> one number at a time, and the loop of
// the tutorial with kairn::Packed<T, k>, for T = double and float, k = 1 and 2, over arrays that fit
// in the first-level cache and arrays that do not. README.md says how to build and run it and
// what the numbers show. Not part of the library, and not a test.
#include <kairn/kairn.hpp>
#include <kairn/soa.hpp>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <limits>
#include <string>
#include <vector>

#if defined(__APPLE__)
#include <pthread.h>
#endif

#if defined(_MSC_VER) && !defined(__clang__)
#define DOT_NOINLINE __declspec(noinline)
#else
#define DOT_NOINLINE __attribute__((noinline))
#endif

namespace {

template <class T, int K>
using View = kairn::SoAView<const T, K>;

// The three loops, each a function of its own that no caller sees into.

// A plain loop of T on the leading limbs: s += a[i] * b[i].
template <class T>
DOT_NOINLINE T dot_plain(const T* a, const T* b, std::size_t n) {
    T s = 0;
    for (std::size_t i = 0; i < n; ++i) s += a[i] * b[i];
    return s;
}

// A loop of Expansion<T, K>, one number at a time, over the same arrays.
template <class T, int K>
DOT_NOINLINE kairn::Expansion<T, K> dot_expansion(View<T, K> x, View<T, K> y) {
    kairn::Expansion<T, K> s;
    for (std::size_t i = 0; i < x.size(); ++i) s = s + x.get(i) * y.get(i);
    return s;
}

// The loop of the tutorial.
template <class T, int K>
DOT_NOINLINE kairn::Expansion<T, K> dot_packed(View<T, K> x, View<T, K> y) {
    using P = kairn::Packed<T, K>;
    constexpr int W = P::lanes;
    P sum;
    std::size_t i = 0;
    for (; i + W <= x.size(); i += W) sum = sum + x.load(i) * y.load(i);
    if (i < x.size()) {
        const int rest = int(x.size() - i);
        sum = sum + x.load_partial(i, rest) * y.load_partial(i, rest);
    }
    kairn::Expansion<T, K> total;
    for (int lane = 0; lane < W; ++lane) total = total + sum.lane(lane);
    return total;
}

// SplitMix64, so that every platform builds the same data.
struct Random {
    std::uint64_t state;
    std::uint64_t next() {
        std::uint64_t z = (state += 0x9e3779b97f4a7c15u);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9u;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebu;
        return z ^ (z >> 31);
    }
    double unit() { return double(next() >> 11) * 0x1p-53; }
};

// n numbers of K limbs: leading limbs +-[1, 2) 2^e, e from -8 to 8, tails about u times them, as
// the inputs of bench/; nothing overflows or underflows in the loops.
template <class T, int K>
kairn::SoA<T, K> data(std::size_t n, std::uint64_t seed) {
    Random r{seed};
    kairn::SoA<T, K> s(n);
    const T u = std::numeric_limits<T>::epsilon() / 2;
    for (std::size_t i = 0; i < n; ++i) {
        const T a = T(std::ldexp((r.next() & 1 ? -1.0 : 1.0) * (1.0 + r.unit()), int(r.next() % 17) - 8));
        if constexpr (K == 1) {
            s[i] = kairn::Expansion<T, 1>(a);
        } else {
            s[i] = kairn::Expansion<T, 2>(a) + T(a * u * T(r.unit() - 0.5));
        }
    }
    return s;
}

volatile double sink = 0;

double now() {
    return std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count();
}

// Nanoseconds per element of f(): the median and the minimum of `reps` samples, each of `passes`
// calls over n elements.
struct Timing {
    double median, minimum;
};
template <class F>
Timing time_it(F f, std::size_t n, int reps, std::size_t passes) {
    std::vector<double> t;
    for (int k = 0; k < reps; ++k) {
        const double start = now();
        for (std::size_t p = 0; p < passes; ++p) sink = sink + f();
        t.push_back((now() - start) * 1e9 / double(n * passes));
    }
    std::sort(t.begin(), t.end());
    return {t[t.size() / 2], t[0]};
}

struct Row {
    std::string type;
    int k, w;
    std::size_t n, bytes;
    Timing plain, expansion, packed;
    double agreement;  // |packed - expansion| / |expansion|
};

template <class T, int K>
Row measure(std::size_t n, int reps, double sample_elements) {
    const kairn::SoA<T, K> xs = data<T, K>(n, 1), ys = data<T, K>(n, 2);
    const View<T, K> x = xs, y = ys;
    const std::size_t passes = std::max<std::size_t>(1, std::size_t(sample_elements / double(n)));
    Row row;
    row.type = sizeof(T) == 8 ? "double" : "float";
    row.k = K;
    row.w = kairn::Packed<T, K>::lanes;
    row.n = n;
    row.bytes = 2 * K * n * sizeof(T);
    // The results, before anything is timed: the two loops of k limbs agree to within their
    // bounds, which are far below what the printout resolves.
    const kairn::Expansion<T, K> e = dot_expansion<T, K>(x, y), p = dot_packed<T, K>(x, y);
    const double ev = double(e.limb[0]) + (K == 2 ? double(e.limb[K - 1]) : 0.0);
    const double pv = double(p.limb[0]) + (K == 2 ? double(p.limb[K - 1]) : 0.0);
    row.agreement = std::fabs(pv - ev) / std::fabs(ev);
    // Each loop called through a pointer read from a volatile object, so that no compiler sees what
    // a call computes and hoists it out of the repetitions (bench/bench.hpp does the same).
    static T (*volatile plain)(const T*, const T*, std::size_t) = dot_plain<T>;
    static kairn::Expansion<T, K> (*volatile expansion)(View<T, K>, View<T, K>) = dot_expansion<T, K>;
    static kairn::Expansion<T, K> (*volatile packed)(View<T, K>, View<T, K>) = dot_packed<T, K>;
    row.plain = time_it([&] { return double(plain(x.limb(0), y.limb(0), n)); }, n, reps, passes);
    row.expansion = time_it([&] { return double(expansion(x, y).limb[0]); }, n, reps, passes);
    row.packed = time_it([&] { return double(packed(x, y).limb[0]); }, n, reps, passes);
    return row;
}

}  // namespace

int main(int argc, char** argv) {
    int reps = 11;
    std::size_t small = 512, large = std::size_t(1) << 23;
    double sample = 1 << 24;
    std::string machine = "", compiler = "";
    for (int i = 1; i < argc; ++i) {
        const std::string a = argv[i];
        if (a == "--reps" && i + 1 < argc) reps = std::atoi(argv[++i]);
        else if (a == "--small" && i + 1 < argc) small = std::size_t(std::atoll(argv[++i]));
        else if (a == "--large" && i + 1 < argc) large = std::size_t(std::atoll(argv[++i]));
        else if (a == "--sample" && i + 1 < argc) sample = std::atof(argv[++i]);
        else if (a == "--machine" && i + 1 < argc) machine = argv[++i];
        else if (a == "--compiler" && i + 1 < argc) compiler = argv[++i];
        else {
            std::fprintf(stderr, "usage: dot [--reps R] [--small N] [--large N] [--sample ELEMENTS] [--machine TEXT] "
                                 "[--compiler TEXT]\n");
            return 2;
        }
    }
#if defined(__APPLE__)
    pthread_set_qos_class_self_np(QOS_CLASS_USER_INTERACTIVE, 0);
#endif
    const kairn::Status st = kairn::self_test();
    if (!st.ok()) {
        std::fprintf(stderr, "self_test: %s\n", st.message());
        return 1;
    }
    std::vector<Row> rows;
    for (std::size_t n : {small, large}) {
        rows.push_back(measure<double, 1>(n, reps, sample));
        rows.push_back(measure<double, 2>(n, reps, sample));
        rows.push_back(measure<float, 1>(n, reps, sample));
        rows.push_back(measure<float, 2>(n, reps, sample));
    }
    std::printf("Machine: %s\nCompiler: %s\nKAIRN_PACKED_FORM %d; %d samples, median (spread: median over minimum)\n\n",
                machine.c_str(), compiler.c_str(), KAIRN_PACKED_FORM, reps);
    std::printf("| T | k | W | n | bytes | plain T, ns/elem | Expansion loop, ns/elem | Packed loop, ns/elem | "
                "Expansion / Packed | agreement |\n|---|---|---|---|---|---|---|---|---|---|\n");
    double worst = 1;
    for (const Row& r : rows) {
        std::printf("| %s | %d | %d | %zu | %.3g MB | %.3f (%.2f) | %.3f (%.2f) | %.3f (%.2f) | %.2f | %.1e |\n",
                    r.type.c_str(), r.k, r.w, r.n, double(r.bytes) / 1e6, r.plain.median, r.plain.median / r.plain.minimum,
                    r.expansion.median, r.expansion.median / r.expansion.minimum, r.packed.median,
                    r.packed.median / r.packed.minimum, r.expansion.median / r.packed.median, r.agreement);
        worst = std::max({worst, r.plain.median / r.plain.minimum, r.expansion.median / r.expansion.minimum,
                          r.packed.median / r.packed.minimum});
    }
    std::printf("\nlargest spread: %.3f\n", worst);
    return 0;
}
