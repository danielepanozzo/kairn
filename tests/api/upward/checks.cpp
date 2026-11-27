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
//   does: no report. And the checks of the interval type and the functions on arrays (type_reports
//   below): an operation that rounds reports outside any scope and in a NearestScope, once per
//   operation, and nothing in a Scope; the exact operations and the functions on arrays report
//   nothing outside a scope; a default type that rounds reports inside a Scope (its own check,
//   unchanged), and not in a NearestScope inside it; a state that is not canonical (one NaN lane, a
//   lane -inf, crossed lanes, signaling NaNs) reports when from_limbs builds it and when an
//   operation, exact or not, takes it, and a canonical one (the empty set, the whole line) does not;
//   so does a default interval that is not canonical given to the conversion; a function on arrays
//   reports views of different lengths, an array written that overlaps one read or the other one
//   written, and an element that is not canonical, and not the same view written and read.
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

// The checks of the interval type, the functions on arrays and the default types inside a scope.
// Every operation is written with the marker, which compiles whatever gen/upward.hpp says of its
// kernel. A result is stored to a volatile object, so that the operation is not removed.
using I = kairn::upward::Interval<double>;
using D = kairn::Interval<double, 1>;
using kairn::unverified;
volatile double sink = 0;
void keep(const I& z) {
    double p[2] = {};
    z.to_limbs(p);
    sink = p[0] + p[1];
}
const char* const not_canonical = "not canonical";

// The interval of the limbs (u, n), and whether building it reported (expected 0 or 1).
I limbs(const char* what, double u, double n, int expected) {
    const double p[2] = {u, n};
    const int before = calls;
    const I x = I::from_limbs(p);
    expect_reports(what, before, expected, "from_limbs");
    return x;
}

void type_reports() {
    const int r = checks_on ? 1 : 0;
    volatile double v1 = 1, v2 = 2;
    const I x = limbs("from_limbs of [1, 2]", 2.0, -1.0, 0), y = limbs("from_limbs of [-1, 3]", 3.0, 1.0, 0);
    int before = calls;
    keep(unverified(x) + y);
    expect_reports("an interval sum outside any scope", before, r, not_upward);
    before = calls;
    keep(unverified(x) * 2.0);
    expect_reports("an interval times a number outside any scope", before, r, not_upward);
    before = calls;
    keep(1.0 - unverified(x));
    expect_reports("a number minus an interval outside any scope", before, r, not_upward);
    before = calls;
    keep(-unverified(x));
    keep(x.hull(unverified(y)));
    keep(x.intersection(unverified(y)));
    keep(I(unverified(double(v1)), double(v2)));
    sink = unverified(x).is_empty() ? 1.0 : 0.0;
    sink = unverified(x).certainly_positive() ? 1.0 : 0.0;
    sink = x.contains(unverified(1.5)) ? 1.0 : 0.0;
    sink = kairn::upward::less(unverified(x), y) == kairn::Trit::yes ? 1.0 : 0.0;
    sink = kairn::upward::ieee1788::disjoint(unverified(x), y) ? 1.0 : 0.0;
    sink = unverified(x).lower();
    sink = unverified(x).to_interval().upper().limb[0];
    expect_reports("the exact operations outside any scope", before, 0, "");
    {
        Scope s;
        before = calls;
        keep(unverified(x) + y);
        keep(unverified(x) - y);
        keep(unverified(x) * y);
        keep(unverified(x) + 0.5);
        keep(0.5 - unverified(x));
        keep(unverified(x) * 3.0);
        expect_reports("the operations that round, in a Scope", before, 0, "");
        {
            NearestScope n;
            before = calls;
            keep(unverified(x) * y);
            expect_reports("an interval product in a NearestScope inside a Scope", before, r, not_upward);
            before = calls;
            sink = D(unverified(double(v1)), double(v2)).midpoint().limb[0];
            expect_reports("a default interval's midpoint in a NearestScope inside a Scope", before, 0, "");
        }
        before = calls;
        sink = D(unverified(double(v1)), double(v2)).midpoint().limb[0];
        expect_reports("a default interval's midpoint inside a Scope (its own check)", before, r, "not to nearest");
    }

    // States that are not canonical, and the canonical ones next to them.
    const double inf = std::numeric_limits<double>::infinity(), nan = std::numeric_limits<double>::quiet_NaN();
    const double snan = std::numeric_limits<double>::signaling_NaN();
    limbs("from_limbs of the empty set (NaN, NaN)", nan, nan, 0);
    limbs("from_limbs of the whole line (+inf, +inf)", inf, inf, 0);
    limbs("from_limbs of (+inf, -1), [1, +inf]", inf, -1.0, 0);
    limbs("from_limbs of one NaN lane", 1.0, nan, r);
    limbs("from_limbs of a lane -inf", -inf, 0.0, r);
    limbs("from_limbs of signaling NaNs", snan, snan, r);
    const I crossed = limbs("from_limbs of crossed lanes, -n > u", 1.0, -3.0, r);
    {
        Scope s;
        before = calls;
        keep(unverified(crossed) + y);
        expect_reports("an interval sum of a state that is not canonical, in a Scope", before, r, not_canonical);
        before = calls;
        keep(y * unverified(crossed));
        expect_reports("an interval product with a state that is not canonical, in a Scope", before, r, not_canonical);
    }
    before = calls;
    sink = unverified(crossed).is_empty();
    expect_reports("is_empty() of a state that is not canonical", before, r, not_canonical);
    before = calls;
    keep(x.hull(unverified(crossed)));
    expect_reports("the hull with a state that is not canonical", before, r, not_canonical);
    before = calls;
    keep(I(unverified(D(kairn::detail::kernel_result, kairn::Expansion<double, 1>(2.0), kairn::Expansion<double, 1>(1.0)))));
    expect_reports("the conversion of a default interval [2, 1], not canonical", before, r, "converted is not canonical");

    // The functions on arrays: from code that rounds to nearest, so that their own scopes set the mode.
    double au[4] = {2, 3, inf, nan}, an[4] = {-1, 1, inf, nan}, zu[4] = {}, zn[4] = {};
    const kairn::upward::View<const double> a(au, an, 4), a3(au, an, 3);
    const kairn::upward::View<double> z(zu, zn, 4);
    before = calls;
    kairn::upward::add(z, unverified(a), a);
    kairn::upward::mul(z, unverified(a), 2.0);
    kairn::upward::neg(z, unverified(a));
    double bu[4] = {2, 3, inf, nan}, bn[4] = {-1, 1, inf, nan};
    const kairn::upward::View<double> b(bu, bn, 4);
    kairn::upward::sub(b, unverified(kairn::upward::View<const double>(b)), a);
    expect_reports("the functions on arrays, from rounding to nearest, and in place", before, 0, "");
    before = calls;
    kairn::upward::add(z, unverified(a3), a);
    expect_reports("a function on arrays with views of different lengths", before, r, "different lengths");
    before = calls;
    kairn::upward::neg(kairn::upward::View<double>(au + 1, zn, 3), unverified(kairn::upward::View<const double>(au, an, 3)));
    expect_reports("a function on arrays whose array written overlaps one read", before, r, "overlaps");
    before = calls;
    kairn::upward::neg(kairn::upward::View<double>(zu, zu + 1, 2), unverified(kairn::upward::View<const double>(au, an, 2)));
    expect_reports("a function on arrays whose two arrays written overlap", before, r, "overlaps");
    // (1, -3) crossed. Storage of four for a view of two: GCC 13 at -O3 with -mavx2 warns that the
    // AVX2 loop of the function, which runs on four elements or more, reads past an array of two
    // (-Warray-bounds, an error with -Werror), though it never runs here.
    double cu[4] = {1, 2}, cn[4] = {-3, -1};
    before = calls;
    kairn::upward::add(kairn::upward::View<double>(zu, zn, 2), unverified(kairn::upward::View<const double>(cu, cn, 2)), 1.0);
    expect_reports("a function on arrays with an element that is not canonical", before, r, "not a canonical state");
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
    type_reports();
    return summary(checks_on ? "api.upward.checks" : "api.upward.checks.off");
#endif
}
