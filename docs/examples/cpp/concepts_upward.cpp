// The example of "The round-up interval" (docs/concepts/upward.md), which requires the rounding
// mode upward set by kairn::upward::Scope and the options of docs/concepts/upward.md (GCC and Clang
// -frounding-math, MSVC /fp:strict): a Scope with sums and products next to the default interval; a
// NearestScope inside a Scope, and pass(); a filter that decides a sign; the self-check; the
// functions on arrays. ctest builds it with kairn::upward, with the build's flags and, but with
// MSVC, under each contraction setting (tests/api/CMakeLists.txt, api.example.concepts_upward), and
// compares what it prints with concepts_upward.txt, which the page shows; it also checks each
// result itself, against the default kairn::Interval<double, 1>, and exits with 1 if one is not
// what the page says.
#include <kairn/upward.hpp>

#include <cstdio>
#include <string>

#include "concepts_print.hpp"

namespace {

int failures = 0;

void check(bool ok, const char* what) {
    if (!ok) {
        std::printf("FAILED: %s\n", what);
        ++failures;
    }
}

using concepts::hex;
using Up = kairn::upward::Interval<double>;
using Default = kairn::Interval<double, 1>;

std::string text(double lo, double hi) { return "[" + hex(lo) + ", " + hex(hi) + "]"; }
std::string text(const Up& x) { return x.is_empty() ? "empty" : text(x.lower(), x.upper()); }
std::string text(const Default& x) {
    return x.is_empty() ? "empty" : text(x.lower().limb[0], x.upper().limb[0]);
}
// The same set: the same bounds as numbers (a zero of either sign), or both empty.
bool same(const Up& x, const Default& y) {
    return (x.is_empty() && y.is_empty()) || (x.lower() == y.lower().limb[0] && x.upper() == y.upper().limb[0]);
}

// --8<-- [start:filter]
// The sign of a d - b c, or 0 where the filter cannot tell: the interval of a d - b c computed in
// one upward scope, whose sign is certain when it excludes zero. The program decides the rest with
// something slower and exact.
int filter_sign(double a, double b, double c, double d) {
    kairn::upward::Scope up;
    const Up det = Up(a) * d - Up(b) * c;
    if (det.certainly_positive()) return +1;
    if (det.certainly_negative()) return -1;
    return 0;
}
// --8<-- [end:filter]

}  // namespace

int main() {
    // --8<-- [start:self_test]
    // Once at startup, and once more in each file built with other options: the self-check of this
    // file's build. Its advice, in limitation, is about the file's own code; ok() does not depend on it.
    const kairn::Status status = kairn::upward::self_test();
    if (!status) {
        std::fprintf(stderr, "kairn::upward::self_test: %s (%s)\n", status.message(), status.kernel);
        return 1;
    }
    if (status.limited()) std::fprintf(stderr, "kairn::upward::self_test: advice: %s\n", status.limitation);
    // --8<-- [end:self_test]
    std::printf("kairn::upward::self_test(): %s\n", status.message());

    // --8<-- [start:scope]
    // Operands the compiler cannot see: p = 1 + 2^-52, the number after 1, and t = 2^-60.
    volatile double vp = 1 + 0x1p-52, vt = 0x1p-60;
    const double p = vp, t = vt;
    const Up x(p), y(1.0, p);  // [p, p] and [1, p]: the constructors are exact, in any mode
    Up sum, product;
    {
        kairn::upward::Scope up;  // the rounding mode upward, until the end of the block
        sum = x + t;              // [RD(p + t), RU(p + t)]
        product = x * y;          // [RD(p), RU(p^2)]
    }
    // The same with the default interval, which rounds to nearest: outside any upward scope.
    const Default default_sum = Default(p) + Default(t);
    const Default default_product = Default(p) * Default(1.0, p);
    // --8<-- [end:scope]
    std::printf("x + t:            %s\n", text(sum).c_str());
    std::printf("the default type: %s\n", text(default_sum).c_str());
    std::printf("x * y:            %s\n", text(product).c_str());
    std::printf("the default type: %s\n", text(default_product).c_str());
    check(same(sum, default_sum), "x + t is the default type's sum");
    check(same(product, default_product), "x y is the default type's product");
    check(sum.lower() == p && sum.upper() == 1 + 0x1p-51, "x + t = [p, the number after p]");
    check(product.lower() == p && product.upper() == 1 + 0x3p-52, "x y = [p, RU(p^2)]");

    // --8<-- [start:nearest]
    double midpoint = 0;
    Default bounds;
    {
        kairn::upward::Scope up;
        const Up z = x * y;  // rounds upward
        {
            kairn::upward::NearestScope nearest;  // to nearest, so that the default types may run
            const Default d = z.to_interval();    // its bounds after a barrier: computed on in here
            midpoint = d.midpoint().limb[0];      // the default type's midpoint, rounded to nearest
        }
        bounds = z.to_interval();  // exact, in any mode
    }
    // Out of the upward region: pass() puts the default product after the end of the scope.
    const Default scaled = kairn::upward::pass(bounds) * Default(3.0);
    // --8<-- [end:nearest]
    std::printf("midpoint of x * y:      %s\n", hex(midpoint).c_str());
    std::printf("3 (x * y), the default: %s\n", text(scaled).c_str());
    check(midpoint == 1 + 0x1p-51, "the midpoint of [p, RU(p^2)] to nearest is 1 + 2^-51");
    check(scaled.lower().limb[0] == 3 + 0x1p-51 && scaled.upper().limb[0] == 3 + 0x5p-51,
          "3 [p, RU(p^2)] rounded outward");

    // The filter: two signs it decides, and a product so close to the other that its interval
    // contains zero, although a d - b c = -2^-104 is not zero.
    const int decided_plus = filter_sign(2, 1, 1, 1), decided_minus = filter_sign(1, 2, 3, 1);
    volatile double va = 1 + 0x1p-52, vd = 1 - 0x1p-52;
    const int close = filter_sign(va, 1, 1, vd);
    const auto word = [](int s) { return s > 0 ? "positive" : s < 0 ? "negative" : "left to the program"; };
    std::printf("filter_sign: %s, %s, %s\n", word(decided_plus), word(decided_minus), word(close));
    check(decided_plus == 1 && decided_minus == -1, "the clear signs are decided");
    check(close == 0, "a d - b c = -2^-104 is left to the program");

    // --8<-- [start:arrays]
    // Four intervals as two plain arrays, the upper bounds and the lower bounds negated:
    // [1, 2], [-1, 3], [-2, -1] and [-1/2, 1/2]; and four times [1/3, 1/3], 1/3 rounded to double.
    const double third = 1.0 / 3;
    double xu[4] = {2, 3, -1, 0.5}, xn[4] = {-1, 1, 2, 0.5};
    double yu[4] = {third, third, third, third}, yn[4] = {-third, -third, -third, -third};
    double zu[4] = {}, zn[4] = {};
    const kairn::upward::View<const double> xs(xu, xn, 4), ys(yu, yn, 4);
    const kairn::upward::View<double> zs(zu, zn, 4);
    kairn::upward::mul(zs, xs, ys);  // z = x y: the function holds its own scope
    kairn::upward::add(zs, zs, 1.0); // z = z + 1, in place
    // --8<-- [end:arrays]
    for (int i = 0; i < 4; ++i) {
        std::printf("z[%d]: %s\n", i, text(-zn[i], zu[i]).c_str());
        const Default want = Default(-xn[i], xu[i]) * Default(third) + Default(1.0);
        check(-zn[i] == want.lower().limb[0] && zu[i] == want.upper().limb[0], "z = x y + 1 as the default type");
    }
    return failures == 0 ? 0 : 1;
}
