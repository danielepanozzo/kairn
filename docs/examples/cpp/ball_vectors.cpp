// The example of the tutorial "Polynomials as ball vectors" (docs/tutorials/ball-vectors.md):
// a polynomial in the Bernstein basis, known to within a radius, subdivided at 1/2 with sums and
// exact halvings of ball vectors; a bound of the polynomial on each half; and the product of two
// polynomials. Every result is checked against exact arithmetic on members of the operands: the
// exact result for those members must lie in the computed ball vector, coefficient by coefficient.
// It prints the same text on every platform (docs/examples/cpp/ball_vectors.txt).
#include <kairn/ball_vector.hpp>

#include <array>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <vector>

namespace {

// --- The check: exact numbers m 2^e, not part of Kairn -----------------------------------------
//
// Every value here is a sum or a product of doubles, so an integer m of any size times a power of
// two holds it exactly. m is a sign and a magnitude in base 2^32, least significant word first.
struct Dyadic {
    bool negative = false;
    std::vector<std::uint32_t> m;  // the magnitude; empty for zero
    int e = 0;

    Dyadic() = default;
    explicit Dyadic(double x) {
        int ex = 0;
        const double f = std::frexp(x, &ex);  // x = f 2^ex, 1/2 <= |f| < 1
        negative = f < 0;
        std::uint64_t bits = std::uint64_t(std::ldexp(std::fabs(f), 53));
        e = ex - 53;
        while (bits) {
            m.push_back(std::uint32_t(bits));
            bits >>= 32;
        }
    }
};
void trim(std::vector<std::uint32_t>& a) {
    while (!a.empty() && a.back() == 0) a.pop_back();
}
// a 2^s, s >= 0.
std::vector<std::uint32_t> shifted(const std::vector<std::uint32_t>& a, int s) {
    std::vector<std::uint32_t> r(std::size_t(s / 32), 0);
    std::uint32_t carry = 0;
    for (std::uint32_t w : a) {
        const std::uint64_t v = (std::uint64_t(w) << (s % 32)) | carry;
        r.push_back(std::uint32_t(v));
        carry = s % 32 ? std::uint32_t(v >> 32) : 0;
    }
    r.push_back(carry);
    trim(r);
    return r;
}
int compare_magnitudes(const std::vector<std::uint32_t>& a, const std::vector<std::uint32_t>& b) {
    if (a.size() != b.size()) return a.size() < b.size() ? -1 : 1;
    for (std::size_t i = a.size(); i-- > 0;)
        if (a[i] != b[i]) return a[i] < b[i] ? -1 : 1;
    return 0;
}
// a + b, or a - b for a >= b.
std::vector<std::uint32_t> add_magnitudes(const std::vector<std::uint32_t>& a, const std::vector<std::uint32_t>& b,
                                          bool subtract) {
    std::vector<std::uint32_t> r;
    std::int64_t carry = 0;
    for (std::size_t i = 0; i < a.size() || i < b.size(); ++i) {
        const std::int64_t x = i < a.size() ? a[i] : 0, y = i < b.size() ? b[i] : 0;
        std::int64_t v = x + (subtract ? -y : y) + carry;
        carry = v < 0 ? -1 : v >> 32;
        r.push_back(std::uint32_t(v - carry * (std::int64_t(1) << 32)));
    }
    if (carry > 0) r.push_back(std::uint32_t(carry));
    trim(r);
    return r;
}
Dyadic operator+(Dyadic a, Dyadic b) {
    if (a.m.empty()) return b;
    if (b.m.empty()) return a;
    const int e = a.e < b.e ? a.e : b.e;  // both at the smaller exponent
    a.m = shifted(a.m, a.e - e);
    b.m = shifted(b.m, b.e - e);
    Dyadic r;
    r.e = e;
    if (a.negative == b.negative) {
        r.negative = a.negative;
        r.m = add_magnitudes(a.m, b.m, false);
    } else if (compare_magnitudes(a.m, b.m) >= 0) {
        r.negative = a.negative;
        r.m = add_magnitudes(a.m, b.m, true);
    } else {
        r.negative = b.negative;
        r.m = add_magnitudes(b.m, a.m, true);
    }
    return r;
}
Dyadic operator-(Dyadic a) {
    a.negative = !a.negative;
    return a;
}
Dyadic operator*(const Dyadic& a, const Dyadic& b) {
    Dyadic r;
    if (a.m.empty() || b.m.empty()) return r;
    std::vector<std::uint64_t> w(a.m.size() + b.m.size() + 1, 0);
    for (std::size_t i = 0; i < a.m.size(); ++i) {
        std::uint64_t carry = 0;
        for (std::size_t j = 0; j < b.m.size(); ++j) {
            const std::uint64_t v = w[i + j] + std::uint64_t(a.m[i]) * b.m[j] + carry;
            w[i + j] = v & 0xffffffffu;
            carry = v >> 32;
        }
        w[i + b.m.size()] += carry;
    }
    for (std::uint64_t v : w) r.m.push_back(std::uint32_t(v));
    trim(r.m);
    r.negative = a.negative != b.negative;
    r.e = a.e + b.e;
    return r;
}
Dyadic half(Dyadic a) {
    a.e -= 1;
    return a;
}
// Whether |x - c| <= r, exactly.
bool within(const Dyadic& x, const Dyadic& c, const Dyadic& r) {
    const Dyadic d = x + -c, below = r + -d, above = r + d;  // r - (x - c) and r + (x - c)
    return (below.m.empty() || !below.negative) && (above.m.empty() || !above.negative);
}

// --- The polynomial ----------------------------------------------------------------------------

constexpr std::size_t degree = 4;
using Coefficients = kairn::BallVector<double, 1, degree + 1>;

// The halves of a polynomial in the Bernstein basis of degree n on [0, 1], on [0, 1/2] and
// [1/2, 1]: de Casteljau's triangle, each level the halves of the sums of the neighbours of the one
// before, b(j)_i = (b(j-1)_i + b(j-1)_(i+1)) / 2. The left half's coefficients are b(j)_0, the
// right half's b(n-j)_j. Each level is a ball vector of its own, in arrays of the program's, made
// from the shifted parts of the level before: two views of fewer entries. A half gathers one entry of
// each level, so its one radius is the largest of the levels' radii (a comparison: a ball of a
// larger radius contains the ball of each level).
// --8<-- [start:halves]
struct Halves {
    Coefficients left, right;
    std::array<double, degree + 1> level_radius;
};
Halves subdivide(const Coefficients& p) {
    // The arrays of the levels (c[j] and r[j]), and a view of each, which the operations write.
    std::array<std::vector<double>, degree + 1> c;
    std::array<double, degree + 1> r{};
    c[0].assign(p.limb(0), p.limb(0) + p.size());
    r[0] = p.radius();
    std::vector<kairn::BallVectorView<double, 1>> level;
    level.push_back(kairn::BallVectorView<double, 1>(kairn::SoAView<double, 1>(c[0].data(), degree + 1), r[0]));
    for (std::size_t j = 1; j <= degree; ++j) {
        const std::size_t m = degree + 1 - j;
        c[j].assign(m, 0.0);
        level.push_back(kairn::BallVectorView<double, 1>(kairn::SoAView<double, 1>(c[j].data(), m), r[j]));
        const kairn::BallVectorView<const double, 1> before = level[j - 1];
        kairn::add(before.subview(0, m), before.subview(1, m), level[j]);
        kairn::half(level[j], level[j]);
    }
    std::array<kairn::Expansion<double, 1>, degree + 1> left, right;
    double largest = 0;
    for (std::size_t j = 0; j <= degree; ++j) {
        left[j] = c[j][0];
        right[j] = c[degree - j][j];
        largest = r[j] > largest ? r[j] : largest;
    }
    return {Coefficients(left, largest), Coefficients(right, largest), r};
}
// --8<-- [end:halves]

// The same subdivision, exactly, of one member of the polynomial (its coefficients x).
std::array<std::array<Dyadic, degree + 1>, 2> subdivide_exactly(std::array<Dyadic, degree + 1> x) {
    std::array<std::array<Dyadic, degree + 1>, 2> out;
    std::array<std::array<Dyadic, degree + 1>, degree + 1> t;
    t[0] = x;
    for (std::size_t j = 1; j <= degree; ++j)
        for (std::size_t i = 0; i + j <= degree; ++i) t[j][i] = half(t[j - 1][i] + t[j - 1][i + 1]);
    for (std::size_t j = 0; j <= degree; ++j) {
        out[0][j] = t[j][0];
        out[1][j] = t[degree - j][j];
    }
    return out;
}

// Members of a ball vector to check: for each pattern, every entry moved from its center by s r,
// with s one of -1, -1/2, 0, 1/2, 1 chosen by the pattern and the entry.
template <class X>
std::vector<std::vector<Dyadic>> members(const X& x, int patterns) {
    const double steps[5] = {-1, -0.5, 0, 0.5, 1};
    std::vector<std::vector<Dyadic>> out;
    for (int k = 0; k < patterns; ++k) {
        std::vector<Dyadic> v;
        for (std::size_t i = 0; i < x.size(); ++i) {
            const double s = steps[(std::size_t(k) * 7 + i * 3 + std::size_t(k) / 5) % 5];
            v.push_back(Dyadic(x.center(i).limb[0]) + Dyadic(s) * Dyadic(x.radius()));
        }
        out.push_back(v);
    }
    return out;
}

// How many of the exact coefficients lie outside their balls.
template <class X, class E>
int outside(const X& z, const E& exact) {
    int n = 0;
    for (std::size_t i = 0; i < z.size(); ++i)
        n += !within(exact[i], Dyadic(z.center(i).limb[0]), Dyadic(z.radius()));
    return n;
}

}  // namespace

int main() {
    // --8<-- [start:data]
    // The polynomial: Bernstein coefficients known to within 2^-30.
    const Coefficients p({1.5, -0.75, 0.3, 2.0, -1.0}, 0x1p-30);
    std::printf("p: %zu coefficients in the Bernstein basis, radius %a\n", p.size(), p.radius());
    // --8<-- [end:data]

    // --8<-- [start:subdivide]
    const Halves h = subdivide(p);
    for (std::size_t j = 1; j <= degree; ++j) std::printf("level %zu: radius %a\n", j, h.level_radius[j]);
    std::printf("left half:  radius %a, |p| <= %a on [0, 1/2]\n", h.left.radius(), kairn::norm_upper(h.left));
    std::printf("right half: radius %a, |p| <= %a on [1/2, 1]\n", h.right.radius(), kairn::norm_upper(h.right));
    // --8<-- [end:subdivide]

    // The check: the exact subdivision of members of p lies in the halves.
    int checked = 0, out = 0;
    for (const std::vector<Dyadic>& x : members(p, 40)) {
        std::array<Dyadic, degree + 1> a;
        for (std::size_t i = 0; i <= degree; ++i) a[i] = x[i];
        const auto exact = subdivide_exactly(a);
        out += outside(h.left, exact[0]) + outside(h.right, exact[1]);
        checked += 2 * int(degree + 1);
    }
    std::printf("subdivision: %d exact coefficients of members checked, %d outside their balls\n", checked, out);

    // An exact halving: the radius of half(x) is the radius of x halved, exactly.
    const Coefficients q = kairn::half(p);
    std::printf("half(p): radius %a, exactly half of %a: %s\n", q.radius(), p.radius(),
                q.radius() == p.radius() / 2 ? "yes" : "no");

    // --8<-- [start:product]
    // The product of two polynomials in the monomial basis: (1 + 2t - 3t^2)(0.5 - t), each known to
    // within its radius, has 3 + 2 - 1 = 4 coefficients.
    const kairn::BallVector<double, 1, 3> f({1.0, 2.0, -3.0}, 0x1p-40);
    const kairn::BallVector<double, 1, 2> g({0.5, -1.0}, 0x1p-45);
    const kairn::BallVector<double, 1, 4> fg = kairn::convolution(f, g);
    std::printf("f g: %zu coefficients, radius %a\n", fg.size(), fg.radius());
    // --8<-- [end:product]

    // The check: the exact product of members of f and g lies in f g.
    checked = out = 0;
    for (const std::vector<Dyadic>& x : members(f, 25))
        for (const std::vector<Dyadic>& y : members(g, 25)) {
            std::array<Dyadic, 4> exact;
            for (std::size_t i = 0; i < x.size(); ++i)
                for (std::size_t j = 0; j < y.size(); ++j) exact[i + j] = exact[i + j] + x[i] * y[j];
            out += outside(fg, exact);
            checked += 4;
        }
    std::printf("product: %d exact coefficients of products of members checked, %d outside their balls\n", checked,
                out);
    // The check checks: a point at one and a half radii from a center is outside its ball.
    const Dyadic far = Dyadic(fg.center(1).limb[0]) + Dyadic(1.5) * Dyadic(fg.radius());
    const bool control = !within(far, Dyadic(fg.center(1).limb[0]), Dyadic(fg.radius()));
    std::printf("the check finds a point at 1.5 radii outside: %s\n", control ? "yes" : "no");
    return out == 0 && control ? 0 : 1;
}
