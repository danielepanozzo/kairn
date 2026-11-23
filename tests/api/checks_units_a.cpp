// The first translation unit of api.checks.handler.units (checks_units.hpp), with the program's
// handler and main. Built with KAIRN_CHECKS 1 (api.checks.handler.units) and 0
// (api.checks.handler.units.off), the same in both units, as config.hpp requires.
//
// What must hold, in each unit:
// - the address of kairn::detail::report_environment is the same in both units: the report is one
//   function of the program, as config.hpp says;
// - in the default environment no function calls the handler;
// - under each directed rounding mode, the functions that round and are checked call it exactly
//   once, with the reason, and go on: sum, the constructor and the sum of ball vectors in every
//   build, x + y with KAIRN_CHECKS 1; norm_upper and the negation of a ball vector, which do not
//   round, do not call it;
// - under flush to zero (and DAZ on x86-64), every function on arrays and every operation on ball
//   vectors calls it once, and x + y with KAIRN_CHECKS 1.
// Exits 0 when all of that holds.
#include "checks_units.hpp"

#include <cfenv>
#include <cstdio>
#include <cstring>

#if defined(__x86_64__) || defined(_M_X64)
#include <xmmintrin.h>
#endif

#include "no_crash_reports.hpp"

namespace {
int calls = 0;
const char* last_reason = nullptr;
}  // namespace

void units::handler(const char* reason) noexcept {
    ++calls;
    last_reason = reason;
}

UNITS_FUNCTIONS("the first unit", units::unit_a)

namespace {

constexpr bool checks_on = KAIRN_CHECKS != 0;

int failures = 0;
void expect(bool ok, const char* what, const char* unit = nullptr, const char* state = nullptr) {
    if (unit) {
        std::printf("%s: %s, under %s: %s\n", ok ? "ok" : "FAILED", unit, state, what);
    } else {
        std::printf("%s: %s\n", ok ? "ok" : "FAILED", what);
    }
    std::fflush(stdout);
    if (!ok) ++failures;
}

// The states of the environment: set() changes it, restore() puts back what was found, reason is
// what Kairn's message says of it, and rounding whether it is a rounding mode.
struct State {
    const char* name;
    bool (*set)();
    void (*restore)();
    const char* reason;
    bool rounding;
};
int saved_round = FE_TONEAREST;
bool set_round(int mode) {
    saved_round = std::fegetround();
    return std::fesetround(mode) == 0 && std::fegetround() == mode;
}
void restore_round() { std::fesetround(saved_round); }
#if defined(__x86_64__) || defined(_M_X64)
unsigned saved_csr = 0;
bool set_csr(unsigned bits) {
    saved_csr = _mm_getcsr();
    _mm_setcsr(saved_csr | bits);
    return (_mm_getcsr() & bits) == bits;
}
void restore_csr() { _mm_setcsr(saved_csr); }
#elif defined(__aarch64__)
std::uint64_t saved_fpcr = 0;
std::uint64_t read_fpcr() {
#if defined(__clang__)
    return __builtin_arm_rsr64("fpcr");
#else
    return __builtin_aarch64_get_fpcr64();
#endif
}
void write_fpcr(std::uint64_t v) {
#if defined(__clang__)
    __builtin_arm_wsr64("fpcr", v);
#else
    __builtin_aarch64_set_fpcr64(v);
#endif
}
bool set_fpcr(std::uint64_t bits) {
    saved_fpcr = read_fpcr();
    write_fpcr(saved_fpcr | bits);
    return (read_fpcr() & bits) == bits;
}
void restore_fpcr() { write_fpcr(saved_fpcr); }
#endif
const char* const not_to_nearest = "the rounding mode is not to nearest";
const State states[] = {
    {"upward", [] { return set_round(FE_UPWARD); }, restore_round, not_to_nearest, true},
    {"downward", [] { return set_round(FE_DOWNWARD); }, restore_round, not_to_nearest, true},
    {"toward-zero", [] { return set_round(FE_TOWARDZERO); }, restore_round, not_to_nearest, true},
#if defined(__x86_64__) || defined(_M_X64)
    {"ftz", [] { return set_csr(0x8000u); }, restore_csr, "flushed to zero", false},  // MXCSR.FTZ
    {"daz", [] { return set_csr(0x0040u); }, restore_csr, "read as zero", false},     // MXCSR.DAZ
#elif defined(__aarch64__)
    {"fz", [] { return set_fpcr(std::uint64_t{1} << 24); }, restore_fpcr, "flushed to zero", false},  // FPCR.FZ
#endif
};

// One function of a unit: its name, and how many calls of the handler it must make under a rounding
// mode and under flush to zero.
struct Function {
    const char* name;
    double (*units::Unit::*run)();
    int under_rounding;
    int under_flush;
};
const Function functions[] = {
    {"sum (a function on arrays that rounds)", &units::Unit::sum, 1, 1},
    {"norm_upper (a function on arrays that does not round)", &units::Unit::norm, 0, 1},
    {"the constructor of BallVector<double, 1, 3>", &units::Unit::make, 1, 1},
    {"add of two BallVector<double, 2, 3>", &units::Unit::add, 1, 1},
    {"neg of a BallVector<double, 2, 3> (does not round)", &units::Unit::neg, 0, 1},
    {"x + y of Expansion<double, 2> (checked with KAIRN_CHECKS 1 only)", &units::Unit::scalar, checks_on ? 1 : 0,
     checks_on ? 1 : 0},
};

volatile double sink = 0;

}  // namespace

int main() {
    kairn_test::no_crash_reports();
    const units::Unit table[] = {units::unit_a(), units::unit_b()};
    std::printf("KAIRN_CHECKS %d; %d states of the environment\n", int(KAIRN_CHECKS), int(sizeof(states) / sizeof(states[0])));
    expect(table[0].report == table[1].report,
           "kairn::detail::report_environment has the same address in both units (one function of the program)");

    for (const units::Unit& u : table)
        for (const Function& f : functions) sink = (u.*f.run)();
    expect(calls == 0, "in the default environment no function calls the handler");

    int checked = 0;
    for (const State& state : states) {
        if (!state.set()) {
            state.restore();
            expect(false, "the state can be set", "the program", state.name);
            continue;
        }
        const bool env = kairn::environment_ok();
        state.restore();
        expect(!env, "environment_ok() is false", "the program", state.name);
        for (const units::Unit& u : table) {
            for (const Function& f : functions) {
                const int want = state.rounding ? f.under_rounding : f.under_flush;
                const int before = calls;
                last_reason = nullptr;
                std::printf("calling %s in %s under %s\n", f.name, u.name, state.name);
                std::fflush(stdout);
                state.set();
                const double r = (u.*f.run)();
                state.restore();
                sink = r;
                const int made = calls - before;
                char what[256];
                std::snprintf(what, sizeof what, "%s calls the handler %d time%s (%d), and goes on", f.name, want,
                              want == 1 ? "" : "s", made);
                expect(made == want, what, u.name, state.name);
                if (want > 0) {
                    ++checked;
                    std::snprintf(what, sizeof what, "%s gives the handler the reason (%s)", f.name,
                                  last_reason ? last_reason : "none");
                    expect(last_reason && std::strstr(last_reason, state.reason), what, u.name, state.name);
                }
            }
        }
    }
    expect(kairn::environment_ok(), "environment_ok() is true again once the environment is restored");
    std::printf("%d calls of the handler expected and made in %d checked runs; %d failed\n", calls, checked, failures);
    return failures == 0 ? 0 : 1;
}
