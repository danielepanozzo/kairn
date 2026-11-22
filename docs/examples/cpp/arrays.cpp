// Sums and dot products of arrays, and the accumulator: the program of the tutorial
// docs/tutorials/arrays.md. ctest builds
// it in each form of Packed the target has (AVX2, NEON, and the scalar form of one lane:
// tests/api/CMakeLists.txt), runs it, and compares what it prints with arrays.txt, which is the
// same for every form: it prints the results of the sequential order, whose bits are the same
// everywhere. The program checks every result, in both orders, against the bound that
// kairn::traits gives for its length, exactly, against a reference computed in integer
// arithmetic, and exits with 1 if one is outside it. What depends on the form (the lanes, the
// results of the lane order) goes to the standard error.
#include <kairn/batch.hpp>
#include <kairn/kairn.hpp>

#include <cmath>
#include <cstdint>
#include <cstdio>
#include <vector>

namespace {

// An exact sum of doubles that are multiples of 2^-112 below 2^78 in magnitude: an integer in two's
// complement over three 64-bit words, in units of 2^-112. The reference the results are checked
// against, with no floating-point operation that rounds.
struct Exact {
    static constexpr int lo = 112;
    std::uint64_t w[3] = {0, 0, 0};
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
        const double m = std::frexp(std::fabs(a), &e);
        add(std::uint64_t(std::ldexp(m, 53)), e - 53 + lo, (a < 0) != subtract);
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
        const int pos = 64 * top + bit;
        std::uint64_t mantissa = 0;
        bool rest = false;
        for (int p = pos, k = 0; p >= 0; --p, ++k) {
            const bool b = ((v[p / 64] >> (p % 64)) & 1) != 0;
            if (k < 53) mantissa = (mantissa << 1) | std::uint64_t(b);
            else rest = rest || b;
        }
        const int length = pos + 1 < 53 ? pos + 1 : 53;
        if (high && rest) ++mantissa;
        return std::ldexp(double(mantissa), pos + 1 - length - lo);
    }
};

// A deterministic generator (SplitMix64), so that every platform builds the same data: a random
// sign times a 26-bit significand times 2^e, e from lo to hi, so that the product of two is exact.
struct Random {
    std::uint64_t state;
    std::uint64_t next() {
        std::uint64_t z = (state += 0x9e3779b97f4a7c15u);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9u;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebu;
        return z ^ (z >> 31);
    }
    double number(int lo, int hi) {
        const double m = double((next() >> 38) | (std::uint64_t(1) << 25));
        const int e = lo + int(next() % std::uint64_t(hi - lo + 1)) - 25;
        return (next() & 1 ? -1.0 : 1.0) * std::ldexp(m, e);
    }
};

// Whether |result - exact| <= b.unit * magnitudes + b.tiny, decided exactly enough: the error and
// the sum of magnitudes in integers, the error rounded up, the right side computed from the sum of
// magnitudes rounded down and lowered by 2^-40 of itself, more than its own roundings. ratio: the
// error over the bound.
bool within(const Exact& exact_sum, const Exact& magnitudes, const double* limbs, int k, const kairn::Bound<double>& b,
            double& ratio) {
    Exact error = exact_sum;
    for (int j = 0; j < k; ++j) error.add(limbs[j], true);
    const double err = error.magnitude(true);
    const double bound = (b.unit * magnitudes.magnitude(false) + b.tiny) * (1 - 0x1p-40);
    ratio = bound > 0 ? err / bound : 0;
    return err <= bound;
}

}  // namespace

int main() {
    std::fprintf(stderr, "Packed<double, 2>: %d lanes (KAIRN_PACKED_FORM %d)\n", kairn::Packed<double, 2>::lanes,
                 KAIRN_PACKED_FORM);
    bool ok = true;

    // --8<-- [start:data]
    // n pairs of doubles, held as plain arrays: a view of one limb is the array itself, and a view
    // of two limbs is the array of leading limbs with an array of zeros.
    const std::size_t n = 1000;
    std::vector<double> x(n), y(n), zero(n, 0.0);
    Random random{2026};
    for (std::size_t i = 0; i < n; ++i) {
        x[i] = random.number(-30, 30);
        y[i] = random.number(-30, 30);
    }
    const kairn::SoAView<const double, 1> x1(x.data(), n), y1(y.data(), n);
    const kairn::SoAView<const double, 2> x2(x.data(), zero.data(), n), y2(y.data(), zero.data(), n);
    // --8<-- [end:data]

    // The exact dot product, and the sum of the magnitudes of its terms.
    Exact exact, magnitudes;
    for (std::size_t i = 0; i < n; ++i) {
        exact.add(x[i] * y[i]);              // exact: 26-bit significands
        magnitudes.add(std::fabs(x[i] * y[i]));
    }

    // --8<-- [start:dot]
    // The dot product, one and two limbs, in the sequential order (the same bits everywhere) and in
    // the lane order of this build (the packed loop, the default); and the bound for n terms.
    const auto [d1, finite1] = kairn::dot(kairn::sequential, x1, y1);
    const auto [d2, finite2] = kairn::dot(kairn::sequential, x2, y2);
    const auto fast1 = kairn::dot(x1, y1);
    const auto fast2 = kairn::dot(x2, y2);
    const kairn::Bound<double> b1 = kairn::traits<double>::dot(n);
    const kairn::Bound<double> b2 = kairn::traits<kairn::Expansion<double, 2>>::dot(n);
    // Whenever finite: |d - sum x_i y_i| <= b.unit * sum |x_i y_i| + b.tiny, in either order.
    // --8<-- [end:dot]

    double r1 = 0, r2 = 0, rf1 = 0, rf2 = 0;
    ok = finite1 && finite2 && fast1.finite && fast2.finite && ok;
    ok = within(exact, magnitudes, d1.limb, 1, b1, r1) && within(exact, magnitudes, d2.limb, 2, b2, r2) && ok;
    ok = within(exact, magnitudes, fast1.value.limb, 1, b1, rf1) && within(exact, magnitudes, fast2.value.limb, 2, b2, rf2) && ok;
    std::printf("Dot product of %zu pairs, exact value %.17g\n", n, exact.magnitude(false) * (exact.negative() ? -1 : 1));
    std::printf("  one limb   %a, error / bound %.2g, bound %.3g of the magnitudes\n", d1.limb[0], r1, b1.unit);
    std::printf("  two limbs  %a + %a, error / bound %.2g, bound %.3g of the magnitudes\n", d2.limb[0], d2.limb[1], r2,
                b2.unit);
    std::fprintf(stderr, "  the lane order: one limb %a (error / bound %.2g), two limbs %a + %a (%.2g)\n",
                 fast1.value.limb[0], rf1, fast2.value.limb[0], fast2.value.limb[1], rf2);

    // --8<-- [start:sum]
    // The products, into an array the program fills, then summed: the sum guards what it adds, so
    // that a product the compiler could still fuse into the loop's first addition is not.
    std::vector<double> p(n);
    for (std::size_t i = 0; i < n; ++i) p[i] = x[i] * y[i];
    const auto s1 = kairn::sum(kairn::sequential, kairn::SoAView<const double, 1>(p.data(), n));
    const auto s2 = kairn::sum(kairn::sequential, kairn::SoAView<const double, 2>(p.data(), zero.data(), n));
    const kairn::Bound<double> c1 = kairn::traits<double>::sum(n);
    const kairn::Bound<double> c2 = kairn::traits<kairn::Expansion<double, 2>>::sum(n);
    // Whenever finite: |s - sum p_i| <= c.unit * sum |p_i|, in any order of the n - 1 additions.
    // --8<-- [end:sum]
    double q1 = 0, q2 = 0;
    ok = s1.finite && s2.finite && ok;
    ok = within(exact, magnitudes, s1.value.limb, 1, c1, q1) && within(exact, magnitudes, s2.value.limb, 2, c2, q2) && ok;
    std::printf("Sum of the %zu products\n", n);
    std::printf("  one limb   %a, error / bound %.2g\n", s1.value.limb[0], q1);
    std::printf("  two limbs  %a + %a, error / bound %.2g\n", s2.value.limb[0], s2.value.limb[1], q2);

    // --8<-- [start:map]
    // y = 2 x + y, element by element and in place, as two-limb numbers; then a NaN in x, which
    // makes the map's flag false and that element, and only it, the canonical NaN.
    std::vector<double> h(y), l(n, 0.0);
    const kairn::SoAView<double, 2> yy(h.data(), l.data(), n);
    const bool all_finite = kairn::axpy(2.0, x2, yy, yy);
    std::vector<double> bad(x);
    bad[7] = std::nan("");
    std::vector<double> bad_lo(n, 0.0);
    bad_lo[7] = bad[7];   // (NaN, NaN): the canonical NaN of two limbs
    const bool still_finite = kairn::axpy(2.0, kairn::SoAView<const double, 2>(bad.data(), bad_lo.data(), n), yy, yy);
    // --8<-- [end:map]
    ok = all_finite && !still_finite && std::isnan(h[7]) && std::isnan(l[7]) && std::isfinite(h[6]) && ok;
    std::printf("axpy in place: %s, then with a NaN at 7: %s, element 7 %s, element 6 %s\n",
                all_finite ? "every element finite" : "NOT FINITE", still_finite ? "FINITE" : "not every element finite",
                std::isnan(h[7]) ? "NaN" : "NOT NaN", std::isfinite(h[6]) ? "finite" : "NOT FINITE");

    // --8<-- [start:accumulator]
    // The same dot product in four parts, each in an accumulator of its own (as four threads would
    // compute it), merged at the end; its ball contains the exact value.
    kairn::Accumulator<double, 2> parts[4];
    for (std::size_t i = 0; i < n; ++i) parts[i % 4].add_product(x[i], y[i]);
    for (int k = 1; k < 4; ++k) parts[0].merge(parts[k]);
    const kairn::Ball<double, 2> ball = parts[0].ball();
    // --8<-- [end:accumulator]
    double ra = 0;
    const kairn::Bound<double> radius{0.0, ball.radius(), 0.0, 0.0, kairn::BoundForm::terms};
    ok = ball.is_finite() && within(exact, magnitudes, ball.center().limb, 2, radius, ra) && ok;
    std::printf("Accumulators in 4 parts, merged: %llu terms, radius %.3g, error / radius %.2g\n",
                static_cast<unsigned long long>(parts[0].count()), ball.radius(), ra);

    std::printf("%s\n", ok ? "every result within its bound" : "A RESULT OUTSIDE ITS BOUND");
    return ok ? 0 : 1;
}
