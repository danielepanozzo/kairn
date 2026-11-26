// api.upward.checks, api.upward.checks.off, api.upward.checks.unhonored: the assertions of a checked
// build of <kairn/upward.hpp> that its environment part makes (the design page, "Checks"), reported
// through a KAIRN_ENVIRONMENT_FAILURE of the program's own that records the reason and returns.
// Requires the rounding mode upward set by kairn::upward::Scope and the options of
// docs/concepts/upward.md (GCC and Clang -frounding-math, MSVC /fp:strict), but in the third build.
//
// - api.upward.checks (KAIRN_CHECKS 1, with the options): the assertion before an operation that
//   rounds (detail::check_upward) reports outside any scope and inside a NearestScope, and not in a
//   Scope or the register-only scope; with flush to zero set by hand inside a Scope it reports, and
//   so does the assertion before an exact operation (detail::check_exact), which reports nothing
//   else; an upward scope that writes the mode checks that this file's build honors it, which it
//   does: no report.
// - api.upward.checks.off (KAIRN_CHECKS 0, KAIRN_TEST_CHECKS_OFF): none of them reports, and every
//   assertion says that the operation's checks may go on.
// - api.upward.checks.unhonored (KAIRN_CHECKS 1, KAIRN_TEST_UNHONORED, compiled without the options,
//   where the compiler lets the header be included: Clang and Apple clang as they are, GCC and MSVC
//   with KAIRN_UPWARD_OPTIONS_UNCHECKED): an upward scope that writes the mode reports that the file
//   ignores the mode (1 + 2^-60 computed at compile time, to nearest, which each compiler measured
//   does without the options at every level of optimization, -O0 and /Od included); one that writes
//   nothing (inside a Scope, or with the mode already upward) does not check, and a NearestScope
//   never does.
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
// Without the options, GCC and MSVC need the macro to include the header; Clang includes it as it is.
#if defined(KAIRN_TEST_UNHONORED) && !defined(__clang__) && (defined(__GNUC__) || defined(_MSC_VER))
#define KAIRN_UPWARD_OPTIONS_UNCHECKED
#endif
#include <kairn/upward.hpp>

#include "environment.hpp"

#if defined(KAIRN_TEST_CHECKS_OFF)
#if KAIRN_CHECKS != 0
#error "checks.cpp built with KAIRN_TEST_CHECKS_OFF tests a build without the checks: KAIRN_CHECKS must be 0"
#endif
[[maybe_unused]] constexpr bool checks_on = false;
#else
#if KAIRN_CHECKS != 1
#error "checks.cpp tests the checks of KAIRN_CHECKS: build it with KAIRN_CHECKS 1"
#endif
[[maybe_unused]] constexpr bool checks_on = true;
#endif

using namespace upward_test;
using kairn::upward::NearestScope;
using kairn::upward::Scope;
using kairn::upward::detail::RegisterScope;

namespace {

// The two assertions, each called where an operation would call it (forced inline: GCC refuses a
// call of it through a pointer).
[[maybe_unused]] bool check_upward() { return kairn::upward::detail::check_upward(); }
[[maybe_unused]] bool check_exact() { return kairn::upward::detail::check_exact(); }

char line[512];

// What ran reports exactly `expected` times (0 or 1), each reason containing `words`, and the
// assertion's result says whether the operation's checks may go on (not after a report).
void expect_reports(const char* what, int before, int expected, const char* words) {
    const int made = calls - before;
    const bool reason_ok = expected == 0 || (last_reason && std::strstr(last_reason, words));
    std::snprintf(line, sizeof line, "%s: %s (%d made%s%s)", what,
                  expected ? "one report" : "no report", made, made ? ": " : "", made && last_reason ? last_reason : "");
    expect(made == expected && reason_ok, line);
}

void assertion(const char* what, bool (*check)(), int expected, const char* words) {
    const int before = calls;
    const bool go_on = check();
    expect_reports(what, before, expected, words);
    std::snprintf(line, sizeof line, "%s: the assertion says the operation's checks %s", what,
                  expected ? "do not go on" : "go on");
    expect(go_on == (expected == 0), line);
}

#if !defined(KAIRN_TEST_UNHONORED)
const char* const not_upward = "not upward";
const char* const flushed = "flushed to zero";

void assertions() {
    const int r = checks_on ? 1 : 0;
    assertion("check_upward() outside any scope", check_upward, r, not_upward);
    assertion("check_exact() outside any scope", check_exact, 0, "");
    {
        const int before = calls;
        Scope s;
        expect_reports("a Scope that writes the mode, in a file built with the options", before, 0, "");
        assertion("check_upward() in a Scope", check_upward, 0, "");
        assertion("check_exact() in a Scope", check_exact, 0, "");
        {
            NearestScope n;
            assertion("check_upward() in a NearestScope inside a Scope", check_upward, r, not_upward);
            assertion("check_exact() in a NearestScope inside a Scope", check_exact, 0, "");
        }
        assertion("check_upward() in the Scope after the NearestScope", check_upward, 0, "");
        if constexpr (has_register) {
            set_register_flush(true);
            assertion("check_upward() in a Scope with flush to zero set by hand", check_upward, r, flushed);
            assertion("check_exact() in a Scope with flush to zero set by hand", check_exact, r, flushed);
            set_register_flush(false);
        }
    }
    {
        RegisterScope s;
        assertion("check_upward() in the register-only scope", check_upward, 0, "");
    }
    if constexpr (has_register) {
        set_register_flush(true);
        assertion("check_exact() outside any scope with flush to zero", check_exact, r, flushed);
        set_register_flush(false);
    }
    set_register_mode(FE_DOWNWARD);
    assertion("check_upward() outside any scope, rounding downward", check_upward, r, not_upward);
    set_register_mode(FE_TONEAREST);
}
#else
const char* const ignored = "-frounding-math";

void unhonored() {
    {
        int before = calls;
        Scope s;
        expect_reports("a Scope that writes the mode, in a file built without the options", before, 1, ignored);
        before = calls;
        {
            Scope inner;
            expect_reports("a Scope inside it, which writes nothing", before, 0, "");
        }
        before = calls;
        {
            NearestScope n;
            expect_reports("a NearestScope inside it", before, 0, "");
        }
        assertion("check_upward() in that Scope", check_upward, 0, "");
    }
    {
        const int before = calls;
        RegisterScope s;
        expect_reports("the register-only scope, which writes the mode", before, 1, ignored);
    }
    {
        int before = calls;
        NearestScope n;
        expect_reports("a NearestScope", before, 0, "");
    }
    set_environment(FE_UPWARD, false);
    {
        const int before = calls;
        Scope s;
        expect_reports("a Scope with the mode already upward, which writes nothing", before, 0, "");
    }
    set_environment(FE_TONEAREST, false);
}
#endif

}  // namespace

int main() {
#if defined(KAIRN_TEST_UNHONORED)
    unhonored();
    return summary("api.upward.checks.unhonored");
#else
    assertions();
    return summary(checks_on ? "api.upward.checks" : "api.upward.checks.off");
#endif
}
