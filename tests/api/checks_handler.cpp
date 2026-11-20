// KAIRN_ENVIRONMENT_FAILURE (include/kairn/config.hpp): a program that defines it before including
// Kairn gets its statement instead of the message and abort() when the check of the environment
// fails, and if the statement returns, the operation goes on without checking its operands. Built
// with KAIRN_CHECKS 1 (without NDEBUG, in the debug build of tests/api/flags/): in the default
// environment the handler is not called; under each state of the environment that checks.cpp sets
// (each directed rounding mode, and flush to zero), every operation and constructor of
// checks_cases.hpp calls it, with the reason, and returns. Their two-limb operands are canonical
// pairs whose test, x0 + x1 == x0, is false under a directed rounding mode: an operation that
// went on to check them there would stop the program with "an operand: is not canonical". So does,
// in the default environment, an operand that is not canonical; under each state, with the
// handler, it goes on too, since its check is skipped. Exits 0 when all of that holds.
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
#include "checks_cases.hpp"
#if KAIRN_CHECKS != 1
#error "checks_handler.cpp tests a check of KAIRN_CHECKS: build it without NDEBUG"
#endif

#include "no_crash_reports.hpp"

using namespace kairn_test;

namespace {
int failures = 0;
void expect(bool ok, const char* what, const char* where = nullptr) {
    if (where) {
        std::printf("%s: under %s, %s\n", ok ? "ok" : "FAILED", where, what);
    } else {
        std::printf("%s: %s\n", ok ? "ok" : "FAILED", what);
    }
    std::fflush(stdout);
    if (!ok) ++failures;
}
// Says what is about to run, flushed: if it stops the program, the line is the last one.
void calling(const char* what, const char* where) {
    std::printf("calling %s under %s\n", what, where);
    std::fflush(stdout);
}
}  // namespace

int main() {
    kairn_test::no_crash_reports();
    make_operands();
    for (const Operation& op : operations) sink = op.run();
    expect(calls == 0, "in the default environment the handler is not called");

    for (const State& state : states) {
        if (!state.set()) {
            state.restore();
            expect(false, "the state can be set", state.name);
            continue;
        }
        const bool env = kairn::environment_ok();
        state.restore();
        expect(!env, "environment_ok() is false", state.name);
        int quiet = 0, wrong = 0;
        for (const Operation& op : operations) {
            calling(op.name, state.name);
            const int before = calls;
            last_reason = nullptr;
            state.set();
            sink = op.run();
            state.restore();
            if (calls == before) ++quiet;
            if (!last_reason || !std::strstr(last_reason, state.reason)) ++wrong;
        }
        // An operand that is not canonical, whose check the failed environment skips.
        calling("x + y with an x that is not canonical", state.name);
        const int before = calls;
        state.set();
        sink = (unverified(raw(1.0, v_a)) + o.y).limb[1];
        state.restore();
        expect(calls > before, "x + y with an x that is not canonical calls the handler, and goes on", state.name);
        expect(quiet == 0, "every operation and constructor calls the handler, and goes on", state.name);
        expect(wrong == 0, "the handler is given the reason", state.name);
        if (last_reason) std::printf("the reason given: %s\n", last_reason);
    }
    expect(kairn::environment_ok(), "environment_ok() is true again once the environment is restored");
    std::printf("%d operations and constructors under %d states; %d calls of the handler; %d failed\n",
                int(sizeof(operations) / sizeof(operations[0])), int(sizeof(states) / sizeof(states[0])), calls,
                failures);
    return failures == 0 ? 0 : 1;
}
