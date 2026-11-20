// KAIRN_ENVIRONMENT_FAILURE (include/kairn/config.hpp): a program that defines it before including
// Kairn gets its statement instead of the message and abort() when the check of the environment
// fails, and if the statement returns, the operation goes on without checking its operands. Built
// with KAIRN_CHECKS 1 (without NDEBUG, in the debug build of tests/api/flags/): in the default
// environment the handler is not called; under each state of the environment that checks.cpp sets
// (each directed rounding mode, and flush to zero), every function of checks_cases.hpp that
// rounds calls it, with the reason, and returns; a function that does not round does not call it
// under a rounding mode, and gives the same bits as to nearest, and under flush to zero calls it if
// it is checked at all (kind exact). The two-limb operands of the functions that round are
// canonical pairs whose test, x0 + x1 == x0, is false under a directed rounding mode: an operation
// that went on to check them there would stop the program with "an operand: is not canonical". So
// does, in the default environment, an operand that is not canonical; under each state, with the
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
    for (const Operation& op : operations) {
        Bits bits;
        op.run(bits);
    }
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
        int quiet = 0, wrong = 0, reported = 0, differ = 0, checked = 0, exempt = 0;
        for (const Operation& op : operations) {
            // Which functions call the handler here: every one that rounds; under flush to zero,
            // every one that is checked; under a rounding mode, none that does not round, which
            // must give the same bits as to nearest.
            const bool must_call = op.kind == Kind::rounds || (!state.rounding && op.kind == Kind::exact);
            if (!state.rounding && op.kind == Kind::unchecked) continue;
            Bits nearest, here;
            if (!must_call) op.run(nearest);
            calling(op.name, state.name);
            const int before = calls;
            last_reason = nullptr;
            state.set();
            op.run(here);
            state.restore();
            if (must_call) {
                ++checked;
                if (calls == before) ++quiet;
                if (!last_reason || !std::strstr(last_reason, state.reason)) ++wrong;
            } else {
                ++exempt;
                if (calls != before) ++reported;
                if (first_difference(nearest, here) >= 0) ++differ;
            }
        }
        // An operand that is not canonical, whose check the failed environment skips.
        calling("x + y with an x that is not canonical", state.name);
        const int before = calls;
        state.set();
        sink = (unverified(raw(1.0, double(v_a))) + o.y).limb[1];
        state.restore();
        expect(calls > before, "x + y with an x that is not canonical calls the handler, and goes on", state.name);
        expect(quiet == 0, "every function that is checked here calls the handler, and goes on", state.name);
        expect(wrong == 0, "the handler is given the reason", state.name);
        expect(reported == 0, "no function that does not round calls the handler", state.name);
        expect(differ == 0, "every function that does not round gives the same bits as to nearest", state.name);
        std::printf("under %s: %d functions call the handler, %d that do not round do not\n", state.name, checked,
                    exempt);
        if (last_reason) std::printf("the reason given: %s\n", last_reason);
    }
    expect(kairn::environment_ok(), "environment_ok() is true again once the environment is restored");
    std::printf("%d functions under %d states; %d calls of the handler; %d failed\n",
                int(sizeof(operations) / sizeof(operations[0])), int(sizeof(states) / sizeof(states[0])), calls,
                failures);
    return failures == 0 ? 0 : 1;
}

// With KAIRN_ENCLOSURE_CODE_EXTERNAL (the full tier's full.api.checks.handler.external), the
// operations of Ball are defined here, in the one translation unit of this program, where
// KAIRN_ENVIRONMENT_FAILURE is the handler above; with any other setting this defines nothing.
#include <kairn/definitions.hpp>
