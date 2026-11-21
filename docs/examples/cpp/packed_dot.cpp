// A vector loop with Packed: the program of the tutorial docs/tutorials/vector-loop.md, a dot
// product of two arrays of two-limb numbers with a packed accumulator and a reduction of its lanes
// at the end, written once for every target. ctest builds it in each form of Packed the target
// has (AVX2, NEON, and the scalar form of one lane: tests/api/CMakeLists.txt), runs it, and
// compares what it prints with packed_dot.txt, which is the same for every form. The program
// checks its results itself and exits with 1 if one is outside the bound the tutorial states:
// exactly, against a reference computed in integer arithmetic. What depends on the form (the number
// of lanes, the bound, the ratio of the error to it) goes to the standard error.
#include <kairn/kairn.hpp>
#include <kairn/soa.hpp>

#include <cmath>
#include <cstdint>
#include <cstdio>
#include <vector>

namespace {

using Number = kairn::Expansion<double, 2>;
using Pack = kairn::Packed<double, 2>;
using View = kairn::SoAView<const double, 2>;

// --8<-- [start:loop]
// The dot product of x and y, which have the same length: W products at a time, each lane with
// its own sum, then the lanes added in the order 0, 1, ..., W - 1.
Number dot(View x, View y) {
    constexpr int W = Pack::lanes;   // 4 with AVX2, 2 with NEON, 1 without either
    Pack sum;                        // zero in every lane
    std::size_t i = 0;
    for (; i + W <= x.size(); i += W) sum = sum + x.load(i) * y.load(i);
    if (i < x.size()) {              // the last x.size() % W elements; zero in the other lanes
        const int rest = int(x.size() - i);
        sum = sum + x.load_partial(i, rest) * y.load_partial(i, rest);
    }
    Number total;
    for (int lane = 0; lane < W; ++lane) total = total + sum.lane(lane);
    return total;
}
// --8<-- [end:loop]

// --8<-- [start:bound]
// The bound of dot(x, y) for n pairs, from the bound of each operation in each lane: a product
// has |z - xy| <= mul.unit |xy| + mul.tiny, a sum |z - (a + b)| <= add.unit |a + b|, and a
// product goes through at most d = ceil(n / W) + W sums: those of its lane, from its own on, and
// those of the reduction. With e the larger unit and gamma(m) = m e / (1 - m e):
//   |dot(x, y) - sum x_i y_i| <= gamma(d + 1) sum |x_i y_i| + (1 + gamma(d)) n mul.tiny,
// whenever the result is finite (an overflow anywhere makes it infinite or NaN).
double dot_bound(std::size_t n, double sum_of_magnitudes) {
    using traits = kairn::traits<Number>;
    const double e = traits::mul.unit > traits::add.unit ? traits::mul.unit : traits::add.unit;
    const double d = double((n + Pack::lanes - 1) / Pack::lanes + Pack::lanes);
    const auto gamma = [e](double m) { return m * e / (1 - m * e); };
    return gamma(d + 1) * sum_of_magnitudes + (1 + gamma(d)) * double(n) * traits::mul.tiny;
}
// --8<-- [end:bound]

// An exact sum of products of doubles, each a multiple of 2^-112 below 2^78 in magnitude: an
// integer in two's complement over three 64-bit words, in units of 2^-112. The reference the
// results are checked against, with no floating-point operation that rounds.
struct Exact {
    static constexpr int lo = 112;
    std::uint64_t w[3] = {0, 0, 0};
    // Adds m 2^(e - lo) for an integer m below 2^53 and 0 <= e < 128, negated if negative.
    void add(std::uint64_t m, int e, bool negative) {
        std::uint64_t v[3] = {0, 0, 0};
        const int word = e / 64, bit = e % 64;
        v[word] = m << bit;
        if (bit && word < 2) v[word + 1] = m >> (64 - bit);
        if (negative) {
            for (std::uint64_t& x : v) x = ~x;
            for (int k = 0; k < 3 && ++v[k] == 0; ++k) {}
        }
        std::uint64_t carry = 0;
        for (int k = 0; k < 3; ++k) {
            const std::uint64_t s = w[k] + v[k];
            const std::uint64_t c1 = s < w[k];
            w[k] = s + carry;
            carry = c1 | (w[k] < s);
        }
    }
    // Adds a double that is a multiple of 2^-lo (or subtracts it).
    void add(double a, bool subtract = false) {
        if (a == 0) return;
        int e = 0;
        const double m = std::frexp(std::fabs(a), &e);              // |a| = m 2^e, m in [1/2, 1)
        const std::uint64_t mantissa = std::uint64_t(std::ldexp(m, 53));  // exact
        add(mantissa, e - 53 + lo, (a < 0) != subtract);
    }
    bool negative() const { return (w[2] >> 63) != 0; }
    // The magnitude as a double, rounded toward zero (low), or a double at least as large (high).
    double magnitude(bool high) const {
        std::uint64_t v[3] = {w[0], w[1], w[2]};
        if (negative()) {
            for (std::uint64_t& x : v) x = ~x;
            for (int k = 0; k < 3 && ++v[k] == 0; ++k) {}
        }
        int top = 2;
        while (top >= 0 && v[top] == 0) --top;
        if (top < 0) return 0;
        int bit = 63;
        while (((v[top] >> bit) & 1) == 0) --bit;
        const int pos = 64 * top + bit;          // the highest bit set
        // The 53 bits from pos down, truncated, and whether any bit below them is set.
        std::uint64_t mantissa = 0;
        bool rest = false;
        for (int p = pos, k = 0; p >= 0; --p, ++k) {
            const bool b = ((v[p / 64] >> (p % 64)) & 1) != 0;
            if (k < 53) mantissa = (mantissa << 1) | std::uint64_t(b);
            else rest = rest || b;
        }
        const int length = pos + 1 < 53 ? pos + 1 : 53;
        if (high && rest) ++mantissa;            // at most 2^53: still exact as a double
        return std::ldexp(double(mantissa), pos + 1 - length - lo);
    }
};

// A deterministic generator (SplitMix64), so that every platform builds the same data.
struct Random {
    std::uint64_t state;
    std::uint64_t next() {
        std::uint64_t z = (state += 0x9e3779b97f4a7c15u);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9u;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebu;
        return z ^ (z >> 31);
    }
    // A random sign times a 26-bit significand times 2^e, e from lo to hi: the products of two
    // such numbers are exact in double.
    double number(int lo, int hi) {
        const double m = double((next() >> 38) | (std::uint64_t(1) << 25));   // in [2^25, 2^26)
        const int e = lo + int(next() % std::uint64_t(hi - lo + 1)) - 25;
        return (next() & 1 ? -1.0 : 1.0) * std::ldexp(m, e);
    }
};

// Whether |result - sum a_i b_i| is within dot_bound, decided exactly enough: the error and the
// sum of magnitudes exactly in integers, the error rounded up, the bound computed from a sum of
// magnitudes rounded down and lowered by 2^-40 of itself (more than its own rounding errors).
bool within_bound(const std::vector<double>& a, const std::vector<double>& b, const Number& result, double& ratio) {
    Exact error, magnitudes;
    for (std::size_t i = 0; i < a.size(); ++i) {
        error.add(a[i] * b[i], true);                          // exact: 26-bit significands
        magnitudes.add(std::fabs(a[i] * b[i]));
    }
    error.add(result.limb[0]);
    error.add(result.limb[1]);
    const double err = error.magnitude(true);
    const double bound = dot_bound(a.size(), magnitudes.magnitude(false)) * (1 - 0x1p-40);
    ratio = bound > 0 ? err / bound : 0;
    return std::isfinite(result.limb[0]) && err <= bound;
}

}  // namespace

int main() {
    std::fprintf(stderr, "Packed<double, 2>: %d lanes (KAIRN_PACKED_FORM %d)\n", Pack::lanes, KAIRN_PACKED_FORM);
    bool ok = true;

    // --8<-- [start:data]
    // 501 products of numbers near 2^25, then the same products negated, except one that is
    // a_0 b_0 - a_0, then 1 * 1: the exact dot product is a_0 + 1 = 33566778.
    const std::size_t n = 1003;
    std::vector<double> a(n), b(n), zero(n, 0.0);
    for (std::size_t i = 0; i < 501; ++i) {
        a[i] = a[i + 501] = 33566777.0 - double(i);
        b[i] = 33553432.0 + 7.0 * double(i);
        b[i + 501] = -b[i];
    }
    b[501] += 1;
    a[1002] = b[1002] = 1;
    // --8<-- [end:data]

    // --8<-- [start:call]
    // Two-limb numbers whose second limbs are zero: views of the program's own arrays.
    const View x(a.data(), zero.data(), n), y(b.data(), zero.data(), n);
    const Number p = dot(x, y);
    // --8<-- [end:call]
    double plain = 0;
    for (std::size_t i = 0; i < n; ++i) plain += a[i] * b[i];
    double ratio = 0;
    const bool exact = p.limb[0] == 33566778.0 && p.limb[1] == 0;
    ok = within_bound(a, b, p, ratio) && exact && ok;
    std::printf("Dot product of %zu pairs: exact value 33566778\n", n);
    std::printf("  double            %.17g (error %.2g)\n", plain, plain - 33566778.0);
    std::printf("  Packed<double, 2> %.17g + %.17g (%s)\n", p.limb[0], p.limb[1], exact ? "exact" : "NOT EXACT");
    std::fprintf(stderr, "  the integers: error / bound = %.3g\n", ratio);

    // Random data whose sums round: 26-bit significands, exponents from -30 to 30, so that each
    // product is exact in double and the sums need far more than two limbs.
    double worst = 0;
    for (std::uint64_t seed : {1u, 2u, 3u}) {
        Random random{seed};
        std::vector<double> u(n), v(n);
        for (std::size_t i = 0; i < n; ++i) {
            u[i] = random.number(-30, 30);
            v[i] = random.number(-30, 30);
        }
        const Number r = dot(View(u.data(), zero.data(), n), View(v.data(), zero.data(), n));
        const bool in = within_bound(u, v, r, ratio);
        ok = in && ok;
        worst = ratio > worst ? ratio : worst;
        std::fprintf(stderr, "  random set %d: %a + %a, error / bound = %.3g%s\n", int(seed), r.limb[0], r.limb[1], ratio,
                     in ? "" : "  OUTSIDE THE BOUND");
    }
    std::printf("  3 sets of %zu random pairs: %s\n", n,
                ok ? "every result within the bound of its operations" : "A RESULT OUTSIDE THE BOUND");
    std::fprintf(stderr, "  the largest error / bound: %.3g\n", worst);
    return ok ? 0 : 1;
}
