// KAIRN_ENVIRONMENT_FAILURE (include/kairn/config.hpp): a program that defines it before including
// Kairn gets its statement instead of the message and abort() when the check of the environment
// fails, and the operation goes on if the statement returns. Built with KAIRN_CHECKS 1 (without
// NDEBUG, in the debug build of tests/api/flags/): in the default environment the handler is not
// called; under rounding upward each operation below calls it, with the reason, and returns.
// Exits 0 when all of that holds.
//
// The operands are those whose check does not depend on the rounding mode: one limb, two limbs
// with a zero second limb, a ball of one limb. After the handler returns, an operation goes on to
// check that its two-limb operands are canonical, by computing x0 + x1 == x0 in the rounding mode
// in force; under rounding upward that fails for a canonical pair with a positive second limb, and
// the operation then stops the program with "an operand: is not canonical" instead of going on
// (docs/developer/testing.md, "The checks of a debug build").
#include <cstdio>
#include <cstring>

namespace {
int calls = 0;
const char* last_reason = nullptr;
void record(const char* reason) {
    ++calls;
    last_reason = reason;
}
}  // namespace

#define KAIRN_ENVIRONMENT_FAILURE(reason) record(reason)
#include <kairn/kairn.hpp>
#if KAIRN_CHECKS != 1
#error "checks_handler.cpp tests a check of KAIRN_CHECKS: build it without NDEBUG"
#endif

#include "no_crash_reports.hpp"

#include <cfenv>

int main() {
    kairn_test::no_crash_reports();
    using E1 = kairn::Expansion<double, 1>;
    using E2 = kairn::Expansion<double, 2>;
    using B1 = kairn::Ball<double, 1>;
    using kairn::unverified;
    volatile double a = 1.5, c = 2.25, r = 0x1p-20;
    const double la[2] = {a, 0.0}, lc[2] = {c, 0.0};
    const E2 x = E2::from_limbs(la), y = E2::from_limbs(lc);
    const B1 p(unverified(E1(a)), r), q(unverified(E1(c)), r);
    int failures = 0;
    auto expect = [&](bool ok, const char* what) {
        std::printf("%s: %s\n", ok ? "ok" : "FAILED", what);
        if (!ok) ++failures;
    };

    volatile double sink = (unverified(x) + y).limb[0];
    sink = (unverified(E1(a)) * E1(c)).limb[0];
    sink = (unverified(p) + q).radius();
    expect(calls == 0, "in the default environment the handler is not called");

    if (std::fesetround(FE_UPWARD) != 0) {
        std::printf("FAILED: rounding upward cannot be set here\n");
        return 1;
    }
    const bool env = kairn::environment_ok();
    int n[4] = {};
    sink = (unverified(E1(a)) * E1(c)).limb[0];
    n[0] = calls;
    sink = (unverified(x) + y).limb[0];
    n[1] = calls - n[0];
    sink = kairn::to_up(unverified(x));
    n[2] = calls - n[0] - n[1];
    sink = (unverified(p) + q).radius();
    n[3] = calls - n[0] - n[1] - n[2];
    std::fesetround(FE_TONEAREST);
    (void)sink;

    expect(!env, "environment_ok() is false under rounding upward");
    expect(n[0] >= 1, "a * b of one limb under rounding upward calls the handler, and returns");
    expect(n[1] >= 1, "x + y of two limbs under rounding upward calls the handler, and returns");
    expect(n[2] >= 1, "to_up(x) under rounding upward calls the handler, and returns");
    expect(n[3] >= 1, "p + q of balls under rounding upward calls the handler, and returns");
    std::printf("calls of the handler: %d, %d, %d and %d\n", n[0], n[1], n[2], n[3]);
    expect(last_reason && std::strstr(last_reason, "rounding mode is not to nearest"),
           "the handler is given the reason: the rounding mode");
    if (last_reason) std::printf("the reason given: %s\n", last_reason);
    expect(kairn::environment_ok(), "environment_ok() is true again once the rounding mode is restored");
    std::printf("%d failed\n", failures);
    return failures == 0 ? 0 : 1;
}
