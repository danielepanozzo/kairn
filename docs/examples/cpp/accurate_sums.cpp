// Accurate sums and dot products with two-limb numbers, and enclosures with balls: the program of
// the tutorial docs/tutorials/accurate-sums.md, which shows its sections and its output. ctest
// builds it with the build's flags and under each contraction setting of the compiler
// (tests/api/CMakeLists.txt), runs it, and compares what it prints with accurate_sums.txt; the
// program also checks its results itself and exits with 1 if one is wrong.
#include <kairn/kairn.hpp>

#include <cmath>
#include <cstdint>
#include <cstdio>
#include <utility>
#include <vector>

namespace {

// A small deterministic generator (SplitMix64), so that every platform builds the same data.
struct Random {
    std::uint64_t state;
    std::uint64_t next() {
        std::uint64_t z = (state += 0x9e3779b97f4a7c15u);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9u;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebu;
        return z ^ (z >> 31);
    }
    // A double with a random 53-bit significand and a random sign, between 2^lo and 2^hi in
    // magnitude.
    double number(int lo, int hi) {
        const double m = double(next() >> 11) + 0x1p52;  // in [2^52, 2^53), exactly
        const int e = lo + int(next() % std::uint64_t(hi - lo)) - 52;
        return (next() & 1 ? -1.0 : 1.0) * std::ldexp(m, e);
    }
    template <class V>
    void shuffle(V& v) {
        for (std::size_t i = v.size() - 1; i > 0; --i) std::swap(v[i], v[std::size_t(next() % (i + 1))]);
    }
};

// --8<-- [start:sum_data]
// 1, then n numbers between 2^-20 and 2^60 in magnitude, then the same n numbers negated, in
// another order. In exact arithmetic the sum is 1.
std::vector<double> sum_data(int n) {
    Random random{2026};
    std::vector<double> numbers, negated;
    for (int i = 0; i < n; ++i) numbers.push_back(random.number(-20, 60));
    for (double v : numbers) negated.push_back(-v);
    random.shuffle(negated);
    std::vector<double> x = {1.0};
    x.insert(x.end(), numbers.begin(), numbers.end());
    x.insert(x.end(), negated.begin(), negated.end());
    return x;
}
// --8<-- [end:sum_data]

// --8<-- [start:dot_data]
// Two vectors of float, as a single-precision source would store them: the pair (1, 1), then n
// pairs (a_i, b_i) between 2^-30 and 2^30 in magnitude, then the same pairs with b_i negated, in
// another order. In exact arithmetic the dot product is 1.
void dot_data(int n, std::vector<float>& a, std::vector<float>& b) {
    Random random{1788};
    std::vector<std::pair<float, float>> pairs, negated;
    for (int i = 0; i < n; ++i) pairs.push_back({float(random.number(-30, 30)), float(random.number(-30, 30))});
    for (auto [ai, bi] : pairs) negated.push_back({ai, -bi});
    random.shuffle(negated);
    a = {1.0f};
    b = {1.0f};
    for (auto [ai, bi] : pairs) a.push_back(ai), b.push_back(bi);
    for (auto [ai, bi] : negated) a.push_back(ai), b.push_back(bi);
}
// --8<-- [end:dot_data]

int failures = 0;
void check(bool ok, const char* what) {
    if (!ok) {
        std::fprintf(stderr, "FAILED: %s\n", what);
        ++failures;
    }
}

}  // namespace

int main() {
    const kairn::Status status = kairn::self_test();
    if (!status) {
        std::fprintf(stderr, "kairn::self_test: %s\n", status.message());
        return 1;
    }

    // --8<-- [start:types]
    using Number = kairn::Expansion<double, 2>;  // two double limbs: about 106 bits
    using Ball = kairn::Ball<double, 2>;         // a two-limb center and a double radius
    // --8<-- [end:types]

    // The sum.
    const std::vector<double> x = sum_data(1000);
    double magnitude = 0.0;  // the sum of every |x_i|, rounded: for the condition number
    for (double v : x) magnitude += std::fabs(v);

    // --8<-- [start:sum_double]
    double s = 0.0;
    for (double v : x) s += v;
    // --8<-- [end:sum_double]

    // --8<-- [start:sum_two]
    Number t = 0.0;
    for (double v : x) t += v;
    // --8<-- [end:sum_two]

    // --8<-- [start:sum_ball]
    Ball z = 0.0;
    for (double v : x) z += v;
    // --8<-- [end:sum_ball]

    // --8<-- [start:radius]
    // Each addition of balls adds U |center| to the radius, rounded up: U is the proved bound of the
    // two-limb addition relative to its computed result.
    const double U = kairn::traits<Number>::add.unit_computed;
    Ball c = 0.0;
    double centers = 0.0;  // the sum of |center| over the steps
    for (double v : x) {
        c += v;
        centers += std::fabs(kairn::to_nearest(c.center()));
    }
    // --8<-- [end:radius]

    // --8<-- [start:uncertain]
    // The same sum, with each x_i known only to within half a unit in its last place.
    Ball y = 0.0;
    for (double v : x) y += Ball(Number(v), std::fabs(v) * 0x1p-53);
    // --8<-- [end:uncertain]

    const double t_error = kairn::to_nearest(t - 1.0);
    const double z_error = kairn::to_nearest(z.center() - 1.0);
    std::printf("Sum of %zu numbers: exact value 1, condition number %.1e\n", x.size(), magnitude);
    std::printf("  double                %.17g (error %.1e)\n", s, s - 1.0);
    std::printf("  Expansion<double, 2>  %.17g + %.17g (error %.1e)\n", t.limb[0], t.limb[1], t_error);
    std::printf("  Ball<double, 2>       center error %.1e, radius %.2e\n", z_error, z.radius());
    std::printf("    U = %.3e, times the sum of |center| %.3e: %.2e\n", U, centers, U * centers);
    std::printf("    with data known to half a unit in the last place: radius %.2e\n", y.radius());

    check(std::fabs(s - 1.0) > 1.0, "double keeps no digit of the sum");
    check(std::fabs(t_error) < 1e-9, "two limbs keep the sum");
    check(kairn::abs_upper(z.center() - 1.0) <= z.radius(), "the ball contains the exact sum");
    check(z.radius() >= U * centers && z.radius() <= 1.01 * U * centers, "the radius is U times the centers");
    check(kairn::abs_upper(y.center() - 1.0) <= y.radius() && y.radius() > 1.0, "the uncertain ball");

    // The dot product.
    std::vector<float> a, b;
    dot_data(1000, a, b);
    double dmagnitude = 0.0;
    for (std::size_t i = 0; i < a.size(); ++i) dmagnitude += std::fabs(double(a[i]) * b[i]);

    // --8<-- [start:dot_double]
    double d = 0.0;
    for (std::size_t i = 0; i < a.size(); ++i) d += double(a[i]) * b[i];
    // --8<-- [end:dot_double]

    // --8<-- [start:dot_two]
    Number e = 0.0;
    for (std::size_t i = 0; i < a.size(); ++i) e += Number(a[i]) * double(b[i]);
    // --8<-- [end:dot_two]

    // --8<-- [start:dot_ball]
    Ball w = 0.0;
    for (std::size_t i = 0; i < a.size(); ++i) w += Ball(a[i]) * double(b[i]);
    // --8<-- [end:dot_ball]

    const double e_error = kairn::to_nearest(e - 1.0);
    const double w_error = kairn::to_nearest(w.center() - 1.0);
    std::printf("Dot product of %zu pairs: exact value 1, condition number %.1e\n", a.size(), dmagnitude);
    std::printf("  double                %.17g (error %.1e)\n", d, d - 1.0);
    std::printf("  Expansion<double, 2>  %.17g + %.17g (error %.1e)\n", e.limb[0], e.limb[1], e_error);
    std::printf("  Ball<double, 2>       center error %.1e, radius %.2e\n", w_error, w.radius());

    check(std::fabs(d - 1.0) > 1.0, "double keeps no digit of the dot product");
    check(std::fabs(e_error) < 1e-9, "two limbs keep the dot product");
    check(kairn::abs_upper(w.center() - 1.0) <= w.radius(), "the ball contains the exact dot product");
    return failures == 0 ? 0 : 1;
}
