// The probe of kairn::self_test() for the exception of a square (docs/getting-started/guarantees.md,
// "The exception: a square"): Status::limitation says, for the translation unit that calls
// self_test, whether a square passed straight into an operation is rounded first. A report, not a
// failure: ok() must stay true under every flag set the headers accept.
//
// The probe passes one square on fixed operands to add_entry_step_1, the guarded sum of the scalar
// form of Packed<T, 1>. This test computes the same kernel in this translation unit on 4000
// operands chosen so that the sum cancels, with the square written in the call and with it rounded
// first (through a volatile, in a function that is not inlined), and counts the differences: the
// direct form. It also prints, for information, the same comparison for two_sum(c, a * a) and for
// Expansion<double, 2>(c) + a * a, which Clang fuses in fewer configurations. And under each
// directed rounding mode self_test() must fail while its probe says what it says to nearest.
//
//   square_probe --expect none          the probe reports nothing and the direct form never
//                                       differs (GCC, MSVC, Clang under off, on and its default)
//   square_probe --expect limitation    the probe reports the limitation and the direct form
//                                       differs (Apple clang at -O1 and -O2 and Clang 18 on x86-64,
//                                       under -ffp-contract=fast: measured)
//   square_probe --expect consistent    the probe reports the limitation exactly when the direct
//                                       form differs (a compiler whose behavior may change with its
//                                       version; tests/api/CMakeLists.txt); prints which it saw
#include <kairn/kairn.hpp>

#include <cfenv>
#include <cstdint>
#include <cstdio>
#include <cstring>

#if defined(_MSC_VER) && !defined(__clang__)
#define NOINLINE __declspec(noinline)
#else
#define NOINLINE __attribute__((noinline))
#endif

namespace {

NOINLINE double rounded_square(double a) {
    volatile double p = a * a;
    return p;
}

NOINLINE double probe_form_in_place(double c, double a) {
    double z = 0;
    kairn::gen::add_entry_step_1(c, a * a, z);
    return z;
}
NOINLINE double probe_form_rounded(double c, double p) {
    double z = 0;
    kairn::gen::add_entry_step_1(c, p, z);
    return z;
}
NOINLINE kairn::SumAndError<double> two_sum_in_place(double c, double a) { return kairn::two_sum(c, a * a); }
NOINLINE kairn::SumAndError<double> two_sum_rounded(double c, double p) { return kairn::two_sum(c, p); }
NOINLINE kairn::Expansion<double, 2> e2_in_place(double c, double a) { return kairn::Expansion<double, 2>(c) + a * a; }
NOINLINE kairn::Expansion<double, 2> e2_rounded(double c, double p) { return kairn::Expansion<double, 2>(c) + p; }

bool same(double x, double y) {
    std::uint64_t a, b;
    std::memcpy(&a, &x, sizeof a);
    std::memcpy(&b, &y, sizeof b);
    return a == b;
}

std::uint64_t state = 0x9E3779B97F4A7C15ull;
double unit() {  // in [1/2, 1)
    state ^= state << 13;
    state ^= state >> 7;
    state ^= state << 17;
    return 0.5 + double(state >> 11) * 0x1p-54;
}

}  // namespace

int main(int argc, char** argv) {
    const char* expect = argc == 3 && std::strcmp(argv[1], "--expect") == 0 ? argv[2] : "";
    if (std::strcmp(expect, "none") != 0 && std::strcmp(expect, "limitation") != 0 &&
        std::strcmp(expect, "consistent") != 0) {
        std::fprintf(stderr, "usage: square_probe --expect none|limitation|consistent\n");
        return 2;
    }
    const kairn::Status s = kairn::self_test();
    std::printf("self_test(): %s; limitation: %s\n", s.message(), s.limited() ? s.limitation : "none");

    constexpr long cases = 4000;
    long direct = 0, sum = 0, e2 = 0;
    for (long i = 0; i < cases; ++i) {
        const double a = unit();
        const double p = rounded_square(a);
        const double c = -p * (1 + double(i % 7) * 0x1p-30);
        direct += !same(probe_form_in_place(c, a), probe_form_rounded(c, p));
        const auto t1 = two_sum_in_place(c, a), t2 = two_sum_rounded(c, p);
        sum += !same(t1.sum, t2.sum) || !same(t1.error, t2.error);
        const auto x1 = e2_in_place(c, a), x2 = e2_rounded(c, p);
        e2 += !same(x1.limb[0], x2.limb[0]) || !same(x1.limb[1], x2.limb[1]);
    }
    std::printf("the direct form, add_entry_step_1(c, a * a): differs in %ld of %ld\n", direct, cases);
    std::printf("for information, two_sum(c, a * a): differs in %ld of %ld\n", sum, cases);
    std::printf("for information, Expansion<double, 2>(c) + a * a: differs in %ld of %ld\n", e2, cases);

    bool ok = s.ok();
    if (!s.ok()) std::printf("FAIL: self_test() failed, which no supported flag set may do\n");
    // Under a directed rounding mode self_test() fails, and the probe says what it says to nearest:
    // it reports only the exact value of a fused sum, which no rounding mode changes.
    const int modes[] = {FE_UPWARD, FE_DOWNWARD, FE_TOWARDZERO};
    for (const int mode : modes) {
        if (std::fesetround(mode) != 0) continue;
        const kairn::Status d = kairn::self_test();
        std::fesetround(FE_TONEAREST);
        if (d.ok() || d.limited() != s.limited()) {
            std::printf("FAIL: under a directed rounding mode self_test() %s and the probe %s\n",
                        d.ok() ? "passes" : "fails", d.limited() ? "reports the limitation" : "reports nothing");
            ok = false;
        }
    }
    const bool fused = direct > 0;
    if (std::strcmp(expect, "none") == 0) {
        if (s.limited()) std::printf("FAIL: the probe reports a limitation where none was measured\n");
        if (fused) std::printf("FAIL: the direct form differs where no compiler was measured to fuse a square\n");
        ok = ok && !s.limited() && !fused;
    } else if (std::strcmp(expect, "limitation") == 0) {
        if (!s.limited()) std::printf("FAIL: the probe reports no limitation where the fusion was measured\n");
        if (!fused) std::printf("FAIL: the direct form does not differ where the fusion was measured\n");
        ok = ok && s.limited() && fused;
    } else {
        std::printf("seen: %s\n", s.limited() == fused ? (fused ? "the probe and the direct form both see the fusion"
                                                                  : "neither the probe nor the direct form sees it")
                                                       : "the probe and the direct form disagree");
        if (s.limited() != fused) std::printf("FAIL: the probe and the direct form disagree\n");
        ok = ok && s.limited() == fused;
    }
    std::printf("%s\n", ok ? "ok" : "FAILED");
    return ok ? 0 : 1;
}
