// The zeros of a polynomial by bisection, written once for intervals and balls: the program of the
// tutorial docs/tutorials/bisection.md, which shows its sections and its output. ctest builds it
// with the build's flags and under each contraction setting of the compiler
// (tests/api/CMakeLists.txt), runs it, and compares what it prints with bisection.txt; the program
// also checks its results itself and exits with 1 if one is wrong.
#include <kairn/kairn.hpp>

#include <cmath>
#include <cstdio>
#include <type_traits>
#include <vector>

namespace {

int failures = 0;

void check(bool ok, const char* what) {
    if (!ok) {
        std::printf("FAILED: %s\n", what);
        ++failures;
    }
}

// --8<-- [start:evaluate]
// p(x) = c[0] + c[1] x + ... + c[n] x^n by Horner's rule, for X an interval or a ball: a set that
// contains p(x) for every x in X. A coefficient is a number of the program, made the set of one
// point, X(c[i]).
template <class X>
X evaluate(const std::vector<double>& c, const X& x) {
    X y(c.back());
    for (std::size_t i = c.size() - 1; i-- > 0;) y = y * x + X(c[i]);
    return y;
}
// --8<-- [end:evaluate]

// --8<-- [start:bisect]
// The parts of X in which p may have a zero: a part is discarded when p is certainly positive or
// certainly negative on it, kept when its radius is at most `width`, and split otherwise. split()
// claims two parts that cover X, not two halves, so the test of progress is the program's own: a
// split is used only when each part has at most 3/4 of the radius of X. Otherwise X is kept as it
// is (counted in `stalled`): parts no smaller than X would be split forever, and parts barely
// smaller, both kept, would double the work at each step for little gain.
template <class X>
struct Zeros {
    std::vector<X> kept;
    long evaluations = 0;
    long stalled = 0;
};
template <class X>
Zeros<X> zeros(const std::vector<double>& c, const X& domain, double width) {
    Zeros<X> z;
    std::vector<X> todo{domain};
    while (!todo.empty()) {
        const X x = todo.back();
        todo.pop_back();
        const X y = evaluate(c, x);
        ++z.evaluations;
        if (y.certainly_positive() || y.certainly_negative()) continue;  // no zero in x
        if (x.radius() <= width) {
            z.kept.push_back(x);
            continue;
        }
        const kairn::Split<X> s = x.split();
        const double most = 0.75 * x.radius();
        if (!(s.left.radius() <= most && s.right.radius() <= most)) {  // no progress
            z.kept.push_back(x);
            ++z.stalled;
            continue;
        }
        todo.push_back(s.right);  // the left part is taken first: the parts kept are in order
        todo.push_back(s.left);
    }
    return z;
}
// --8<-- [end:bisect]

// --8<-- [start:clusters]
// The parts kept, joined where they may meet: equal(a, b) is no when a and b are disjoint, so
// possibly(equal(a, b)) is true when they may share a point, and the hull covers both.
template <class X>
std::vector<X> clusters(const std::vector<X>& kept) {
    std::vector<X> out;
    for (const X& x : kept) {
        if (!out.empty() && kairn::possibly(kairn::equal(out.back(), x))) {
            out.back() = out.back().hull(x);
        } else {
            out.push_back(x);
        }
    }
    return out;
}
// --8<-- [end:clusters]

// The midpoint of a set: its leading limb, and for two limbs the second.
template <class X>
void print_midpoint(const X& x) {
    const auto m = x.midpoint();
    if constexpr (std::is_same_v<std::remove_cvref_t<decltype(m)>, kairn::Expansion<double, 2>>) {
        std::printf("%.17g %+.2e", m.limb[0], m.limb[1]);
    } else {
        std::printf("%.17g", m.limb[0]);
    }
}

// --8<-- [start:run]
// The four zeros of p(x) = x^4 - 10 x^2 + 1, the numbers +-sqrt(2) +- sqrt(3), searched in [-4, 4]
// with one algorithm and three types.
const std::vector<double> p = {1, 0, -10, 0, 1};

template <class X>
std::vector<X> run(const char* name, const X& domain, double width) {
    const Zeros<X> z = zeros(p, domain, width);
    const std::vector<X> found = clusters(z.kept);
    std::printf("%s, width %g: %ld evaluations, %zu parts kept (%ld not narrowed by split), %zu zeros\n", name,
                width, z.evaluations, z.kept.size(), z.stalled, found.size());
    for (const X& x : found) {
        std::printf("  radius %.2e  midpoint ", x.radius());
        print_midpoint(x);
        std::printf("\n");
    }
    return found;
}
// --8<-- [end:run]

// Four zeros, in order, each near one of the four numbers, and p not of one sign on any.
template <class X>
void verify(const std::vector<X>& found) {
    const double s2 = std::sqrt(2.0), s3 = std::sqrt(3.0);
    const double r[4] = {-s2 - s3, s2 - s3, s3 - s2, s2 + s3};
    check(found.size() == 4, "four zeros");
    for (std::size_t i = 0; i < found.size() && i < 4; ++i) {
        check(std::fabs(found[i].midpoint().limb[0] - r[i]) < 1e-5, "a zero near +-sqrt(2) +- sqrt(3)");
        check(!evaluate(p, found[i]).certainly_positive() && !evaluate(p, found[i]).certainly_negative(),
              "p may vanish on a zero's set");
    }
}

}  // namespace

int main() {
    // --8<-- [start:main]
    using I = kairn::Interval<double, 1>;
    using B1 = kairn::Ball<double, 1>;
    using B2 = kairn::Ball<double, 2>;
    for (double width : {1e-6, 0.0}) {
        verify(run("Interval<double, 1>", I(-4.0, 4.0), width));
        verify(run("Ball<double, 1>", B1::from_interval(-4.0, 4.0), width));
        verify(run("Ball<double, 2>", B2::from_interval(-4.0, 4.0), width));
    }
    // --8<-- [end:main]
    return failures ? 1 : 0;
}
