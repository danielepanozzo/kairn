// Whole computations, timed per run (bench/m2_data.hpp; bench/README.md, "Milestone 2", second part),
// backend m2r, KIND run, the time of one call:
//
// - the bisection of docs/tutorials/bisection.md, its program docs/examples/cpp/bisection.cpp
//   included here as it is (its main renamed), run with Interval<double, 1>, Interval<double, 2>,
//   Ball<double, 1> and Ball<double, 2> on the tutorial's polynomial x^4 - 10 x^2 + 1 in [-4, 4],
//   down to the tutorial's two widths, 1e-6 and 0 (kernels bisect_TYPE_w6, bisect_TYPE_w0): zeros()
//   and clusters() of the tutorial, the time to solution; each run is checked by the tutorial's own
//   verify() (four zeros, in order, near +-sqrt(2) +- sqrt(3), p not of one sign on any), and its
//   evaluations, parts kept, parts not narrowed by split() and the radii of the zeros found are
//   recorded (m2_run_json);
// - kairn::self_test(), every kernel for both limb types (self_test/op), checked by its result, and
//   its two parts: the checks of the environment and of the compiler's flags on T, both limb types
//   (self_test_limb/op), and the generated kernels on their fixed operands (self_test_kernels/op).
//
// The control of the bisection is the same algorithm on the other types, and of self_test() its own
// parts; neither has a plain form.
#include <kairn/kairn.hpp>

// The tutorial's program, as it is: its functions are in an anonymous namespace of this file.
#define main kb_bisection_tutorial_main
#include "../docs/examples/cpp/bisection.cpp"
#undef main

#include <cmath>
#include <cstdio>
#include <string>
#include <vector>

#include "m2_data.hpp"

namespace {

using kairn_bench::m2::Entry;
using I1 = kairn::Interval<double, 1>;
using I2 = kairn::Interval<double, 2>;
using B1 = kairn::Ball<double, 1>;
using B2 = kairn::Ball<double, 2>;

template <class X>
X domain();
template <>
I1 domain<I1>() {
    return I1(-4.0, 4.0);
}
template <>
I2 domain<I2>() {
    return I2(kairn::Expansion<double, 2>(-4.0), kairn::Expansion<double, 2>(4.0));
}
template <>
B1 domain<B1>() {
    return B1::from_interval(-4.0, 4.0);
}
template <>
B2 domain<B2>() {
    return B2::from_interval(-4.0, 4.0);
}

// What the last run of each bisection found, for the JSON and the check.
struct Found {
    long evaluations = 0, kept = 0, stalled = 0, zeros = 0;
    double radius_max = 0, radius_min = 0;
};
Found found[4][2];
volatile long sink = 0;

template <class X>
KAIRN_GEN_FORCEINLINE void bisect(int type, int w) {
    const Zeros<X> z = zeros(p, domain<X>(), w ? 0.0 : 1e-6);
    const std::vector<X> c = clusters(z.kept);
    Found& f = found[type][w];
    f.evaluations = z.evaluations;
    f.kept = long(z.kept.size());
    f.stalled = z.stalled;
    f.zeros = long(c.size());
    f.radius_max = 0;
    f.radius_min = c.empty() ? 0 : double(c[0].radius());
    for (const X& x : c) {
        f.radius_max = std::fmax(f.radius_max, double(x.radius()));
        f.radius_min = std::fmin(f.radius_min, double(x.radius()));
    }
    sink = sink + f.zeros;
}

}  // namespace

#define KB_RLIST(X)                                                                                \
    X(bisect_i1_w6, bisect<I1>(0, 0)) X(bisect_i1_w0, bisect<I1>(0, 1))                            \
    X(bisect_i2_w6, bisect<I2>(1, 0)) X(bisect_i2_w0, bisect<I2>(1, 1))                            \
    X(bisect_b1_w6, bisect<B1>(2, 0)) X(bisect_b1_w0, bisect<B1>(2, 1))                            \
    X(bisect_b2_w6, bisect<B2>(3, 0)) X(bisect_b2_w0, bisect<B2>(3, 1))                            \
    X(self_test, sink = sink + long(kairn::self_test().ok()))                                      \
    X(self_test_limb, sink = sink + long(kairn::detail::self_test_limb<double>() == nullptr) +    \
                             long(kairn::detail::self_test_limb<float>() == nullptr))              \
    X(self_test_kernels, sink = sink + long(kairn::gen::selftest::run() == nullptr))

#define KB_RDEF(KERNEL, ...)                                                                       \
    extern "C" KB_NOINLINE void kb_m2_r_run_##KERNEL##__op(void*) { __VA_ARGS__; }
KB_RLIST(KB_RDEF)

namespace {
bool check_run(const Entry& e, char* why, std::size_t size);
}

#define KB_RROW(KERNEL, ...) {"m2r/run/" #KERNEL "/op", kb_m2_r_run_##KERNEL##__op, 64, 1, 1, 0, 0, &check_run},

namespace kairn_bench::m2 {

const Entry m2_run_entries[] = {
    KB_RLIST(KB_RROW)
    {nullptr, nullptr, 0, 0, 0, 0, 0, nullptr},
};

// The counts of the bisections, from their last run (each is run by its check before anything is
// timed).
std::string m2_run_json() {
    static const char* const types[4] = {"Interval<double, 1>", "Interval<double, 2>", "Ball<double, 1>",
                                         "Ball<double, 2>"};
    std::string out = "[";
    for (int t = 0; t < 4; ++t)
        for (int w = 0; w < 2; ++w) {
            const Found& f = found[t][w];
            char buf[400];
            std::snprintf(buf, sizeof buf,
                          "%s\n    {\"type\": \"%s\", \"width\": %s, \"evaluations\": %ld, \"kept\": %ld, \"stalled\": %ld, "
                          "\"zeros\": %ld, \"radius_min\": %.4g, \"radius_max\": %.4g}",
                          (t || w) ? "," : "", types[t], w ? "0" : "1e-06", f.evaluations, f.kept, f.stalled, f.zeros,
                          f.radius_min, f.radius_max);
            out += buf;
        }
    return out + "\n  ]";
}

}  // namespace kairn_bench::m2

namespace {

template <class X>
bool verified(int type, int w, char* why, std::size_t size) {
    failures = 0;
    const Zeros<X> z = zeros(p, domain<X>(), w ? 0.0 : 1e-6);
    verify(clusters(z.kept));   // the tutorial's check: it counts its failures and prints them
    const Found& f = found[type][w];
    if (failures || f.zeros != 4 || f.evaluations != z.evaluations) {
        std::snprintf(why, size, "the bisection's check failed (%d failures, %ld zeros)", failures, f.zeros);
        return false;
    }
    return true;
}

bool check_run(const Entry& e, char* why, std::size_t size) {
    e.fn(nullptr);   // runs it once, and records what it found
    const std::string name = e.name;
    if (name.find("self_test") != std::string::npos) {
        if (!kairn::self_test().ok() || kairn::detail::self_test_limb<double>() || kairn::detail::self_test_limb<float>() ||
            kairn::gen::selftest::run()) {
            std::snprintf(why, size, "kairn::self_test() fails: %s", kairn::self_test().message());
            return false;
        }
        return true;
    }
    const int w = name.find("_w0") != std::string::npos ? 1 : 0;
    if (name.find("bisect_i1") != std::string::npos) return verified<I1>(0, w, why, size);
    if (name.find("bisect_i2") != std::string::npos) return verified<I2>(1, w, why, size);
    if (name.find("bisect_b1") != std::string::npos) return verified<B1>(2, w, why, size);
    return verified<B2>(3, w, why, size);
}

}  // namespace
