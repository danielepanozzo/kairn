// The checks of KAIRN_CHECKS (include/kairn/config.hpp), run. Built without NDEBUG, as a debug
// build is (tests/api/flags/, where KAIRN_TEST_DEFAULT_CHECKS says that KAIRN_CHECKS must come from
// that default), and with KAIRN_CHECKS defined to 1 and the build's own flags (tests/api/): every
// operation must check the floating-point environment and its operands, and stop the program with
// a message when one is wrong; what is right must pass.
//
//   checks --operations       the operations, one per line
//   checks --states           the states of the environment this target can set, one per line
//   checks --operand-cases    the operands the checks must refuse, each with the message expected
//   checks default            in the default environment: environment_ok() is true, and every
//                             operation runs, as does each operand the checks must let through
//                             (canonical infinities and NaN, the special balls, what a finite core
//                             returns given to kairn::finite); exits 0
//   checks STATE OPERATION    environment_ok() is true, then STATE is set and it is false, then
//                             OPERATION runs, which must stop the program
//   checks operand CASE       an operation given an operand that is not canonical, which must stop
//                             the program
//
// A check that lets the program go on is reported with a line that starts with FAILED and exit
// status 1; a stopped program exits through abort(). tests/api/checks.cmake runs every case and
// tells the two apart. Each line that says what the program is about to do is flushed first,
// since abort() discards what is buffered.
#if defined(KAIRN_TEST_DEFAULT_CHECKS) && (defined(KAIRN_CHECKS) || defined(NDEBUG))
#error "the debug build of checks.cpp must leave KAIRN_CHECKS to its default, without NDEBUG"
#endif
#include <kairn/kairn.hpp>
#if KAIRN_CHECKS != 1
#error "checks.cpp tests KAIRN_CHECKS: build it without NDEBUG, or with KAIRN_CHECKS defined to 1"
#endif

#include "no_crash_reports.hpp"

#include <cfenv>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <iterator>
#include <limits>

#if defined(__x86_64__) || defined(_M_X64)
#include <xmmintrin.h>
#endif

namespace {

using E1 = kairn::Expansion<double, 1>;
using E2 = kairn::Expansion<double, 2>;
using F2 = kairn::Expansion<float, 2>;
using B1 = kairn::Ball<double, 1>;
using B2 = kairn::Ball<double, 2>;
using kairn::unverified;

// Operands read from volatile objects, so that nothing is computed before the program asks.
volatile double v_a = 1.5, v_b = 0x1p-60, v_c = 2.25, v_d = -0x1p-58, v_r = 0x1p-20;
volatile float v_fa = 1.5f, v_fb = 0x1p-30f;
volatile double sink = 0;
// Not named inf and nan: a global of either name is hidden by a local of Kairn's headers, which
// MSVC reports (C4459) at /W4.
constexpr double infinity = std::numeric_limits<double>::infinity();
constexpr double not_a_number = std::numeric_limits<double>::quiet_NaN();

E2 pair(double h, double l) {
    const double limbs[2] = {h, l};
    return E2::from_limbs(limbs);
}
// A pair whose limbs are written directly: the only way to make one that is not canonical.
E2 raw(double h, double l) {
    E2 x;
    x.limb[0] = h;
    x.limb[1] = l;
    return x;
}
// The operands of the operations, made in the default environment before any state is set: the
// constructors check their operands but not the environment, and the test of a canonical pair,
// x0 + x1 == x0, computed under a directed rounding mode, can fail for a canonical pair, so that
// a pair made under such a mode would be refused for the wrong reason.
struct Operands {
    E2 x, y;
    F2 fx;
    B1 p, q;
    B2 bp, bq;
};
Operands o;
void make_operands() {
    const float limbs[2] = {v_fa, v_fb};
    o.x = pair(v_a, v_b);
    o.y = pair(v_c, v_d);
    o.fx = F2::from_limbs(limbs);
    o.p = B1(unverified(E1(v_a)), v_r);
    o.q = B1(unverified(E1(v_c)), v_r);
    o.bp = B2(unverified(o.x), v_r);
    o.bq = B2(unverified(o.y), v_r);
}

// Every operation, written as a program writes it, with kairn::unverified on the first operand so
// that it compiles whatever gen/claims.json says (the marker changes nothing else).
struct Operation {
    const char* name;
    double (*run)();
};
const Operation operations[] = {
    {"e1.add", [] { return (unverified(E1(v_a)) + E1(v_c)).limb[0]; }},
    {"e1.mul", [] { return (unverified(E1(v_a)) * E1(v_c)).limb[0]; }},
    {"e1.ldexp", [] { return kairn::ldexp(unverified(E1(v_a)), 3).limb[0]; }},
    {"e1.less", [] { return double(unverified(E1(v_a)) < E1(v_c)); }},
    {"e2.add", [] { return (unverified(o.x) + o.y).limb[1]; }},
    {"e2.add_limb", [] { return (unverified(o.x) + double(v_c)).limb[1]; }},
    {"e2.sub", [] { return (unverified(o.x) - o.y).limb[1]; }},
    {"e2.limb_sub", [] { return (unverified(double(v_c)) - o.x).limb[1]; }},
    {"e2.mul", [] { return (unverified(o.x) * o.y).limb[1]; }},
    {"e2.mul_limb", [] { return (unverified(o.x) * double(v_c)).limb[1]; }},
    {"e2.add_fast", [] { return kairn::add_fast(unverified(o.x), o.y).limb[1]; }},
    {"e2.ldexp", [] { return kairn::ldexp(unverified(o.x), -5).limb[1]; }},
    {"e2.half", [] { return kairn::half(unverified(o.x)).limb[1]; }},
    {"e2.neg", [] { return (-unverified(o.x)).limb[1]; }},
    {"e2.abs", [] { return kairn::abs(unverified(o.x)).limb[1]; }},
    {"e2.less", [] { return double(unverified(o.x) < o.y); }},
    {"e2.equal_limb", [] { return double(unverified(o.x) == double(v_c)); }},
    {"e2.to_nearest", [] { return kairn::to_nearest(unverified(o.x)); }},
    {"e2.to_up", [] { return kairn::to_up(unverified(o.x)); }},
    {"e2.narrow", [] { return E1(unverified(o.x)).limb[0]; }},
    {"f2.add", [] { return double((unverified(o.fx) + o.fx).limb[1]); }},
    {"finite.add", [] { return kairn::finite::add(unverified(o.x), o.y).limb[1]; }},
    {"finite.mul", [] { return kairn::finite::mul(unverified(o.x), o.y).limb[1]; }},
    {"finite.ldexp", [] { return kairn::finite::ldexp(unverified(o.x), 7).limb[1]; }},
    {"ball1.add", [] { return (unverified(o.p) + o.q).radius(); }},
    {"ball1.scale", [] { return (unverified(o.p) * double(v_c)).radius(); }},
    {"ball1.neg", [] { return (-unverified(o.p)).radius(); }},
    {"ball2.mul", [] { return (unverified(o.bp) * o.bq).radius(); }},
    {"ball2.sub_point", [] { return (unverified(o.bp) - double(v_c)).radius(); }},
};

// Operands the checks must refuse, each with the message Kairn must print (after "kairn: ").
struct OperandCase {
    const char* name;
    const char* message;
    double (*run)();
};
const char* const not_canonical = "an operand: is not canonical";
const char* const not_a_pair = "from_limbs: the limbs are not a canonical pair";
const char* const negative = "a ball: has a negative radius";
const OperandCase operand_cases[] = {
    {"from_limbs.unnormalized", not_a_pair, [] { return pair(1.0, v_a).limb[1]; }},
    {"from_limbs.infinity", not_a_pair, [] { return pair(infinity, v_a).limb[1]; }},
    {"from_limbs.nan", not_a_pair, [] { return pair(not_a_number, v_a).limb[1]; }},
    {"operator.unnormalized", not_canonical, [] { return (unverified(raw(1.0, v_a)) + o.y).limb[1]; }},
    // What a finite core may return after an overflow: given to an operator, refused.
    {"operator.core_result", not_canonical, [] { return (unverified(raw(infinity, not_a_number)) * o.y).limb[1]; }},
    {"operator.second", not_canonical, [] { return (unverified(o.y) - raw(1.0, v_a)).limb[1]; }},
    {"comparison.unnormalized", not_canonical, [] { return double(unverified(raw(1.0, v_a)) < o.y); }},
    {"conversion.unnormalized", not_canonical, [] { return kairn::to_down(unverified(raw(1.0, v_a))); }},
    {"ldexp.unnormalized", not_canonical, [] { return kairn::ldexp(unverified(raw(1.0, v_a)), 2).limb[1]; }},
    {"finite.unnormalized", "an operand: is not normalized",
     [] { return kairn::finite::add(unverified(raw(1.0, v_a)), o.y).limb[1]; }},
    {"ball.negative_radius_1", negative, [] { return B1(unverified(E1(v_a)), -v_r).radius(); }},
    {"ball.negative_radius_2", negative, [] { return B2(unverified(o.x), -v_r).radius(); }},
    {"ball.minus_infinity_radius", negative, [] { return B1(unverified(E1(v_a)), -infinity).radius(); }},
    {"ball.center", "a ball: has a center that is not canonical",
     [] { return B2(unverified(raw(1.0, v_a)), v_r).radius(); }},
    // A ball that is not canonical cannot be made through the public constructors; the internal
    // one, which takes a kernel's result as it is, makes one.
    {"ball.operand", "a ball: is not canonical",
     [] { return (unverified(B1(kairn::detail::kernel_result, E1(v_a), -v_r)) + o.q).radius(); }},
};

// What the checks must let through: canonical values that are not finite, the special balls,
// a NaN radius, and what a finite core returns, given back to kairn::finite.
const Operation accepted[] = {
    {"from_limbs (+inf, 0)", [] { return pair(infinity, 0.0).limb[0]; }},
    {"from_limbs (-inf, -0)", [] { return pair(-infinity, -0.0).limb[0]; }},
    {"from_limbs (NaN, NaN)", [] { return pair(not_a_number, not_a_number).limb[0]; }},
    {"(+inf, 0) + y", [] { return (unverified(pair(infinity, 0.0)) + o.y).limb[0]; }},
    {"(NaN, NaN) * y", [] { return (unverified(pair(not_a_number, not_a_number)) * o.y).limb[0]; }},
    {"(+inf, 0) < y", [] { return double(unverified(pair(infinity, 0.0)) < o.y); }},
    {"kairn::finite::add on (inf, NaN)",
     [] { return kairn::finite::add(unverified(raw(infinity, not_a_number)), o.y).limb[0]; }},
    {"Ball(c, NaN)", [] { return B1(unverified(E1(v_a)), not_a_number).radius(); }},
    {"Ball(c, +inf)", [] { return B2(unverified(o.x), infinity).radius(); }},
    {"Ball(+inf, r)", [] { return B1(unverified(E1(infinity)), v_r).radius(); }},
    {"Ball(c, -0)", [] { return B1(unverified(E1(v_a)), -0.0).radius(); }},
    {"empty + ball", [] { return (unverified(B1::empty()) + o.q).radius(); }},
    {"whole * ball", [] { return (unverified(B2::whole()) * o.bq).radius(); }},
};

void say(const char* format, const char* a = "", const char* b = "") {
    std::printf(format, a, b);
    std::printf("\n");
    std::fflush(stdout);
}

// The states of the environment: set() changes it, restore() puts back what was found.
struct State {
    const char* name;
    bool (*set)();
    void (*restore)();
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
const State states[] = {
    {"upward", [] { return set_round(FE_UPWARD); }, restore_round},
    {"downward", [] { return set_round(FE_DOWNWARD); }, restore_round},
    {"toward-zero", [] { return set_round(FE_TOWARDZERO); }, restore_round},
#if defined(__x86_64__) || defined(_M_X64)
    {"ftz", [] { return set_csr(0x8000u); }, restore_csr},  // MXCSR.FTZ
    {"daz", [] { return set_csr(0x0040u); }, restore_csr},  // MXCSR.DAZ
#elif defined(__aarch64__)
    {"fz", [] { return set_fpcr(std::uint64_t{1} << 24); }, restore_fpcr},  // FPCR.FZ
#endif
};

int usage() {
    std::fprintf(stderr, "usage: checks --operations | --states | --operand-cases | default | STATE OPERATION | "
                         "operand CASE\n");
    return 2;
}

int run_default() {
    if (!kairn::environment_ok()) {
        say("FAILED: environment_ok() is false in the default environment");
        return 1;
    }
    say("ok: environment_ok() is true in the default environment");
    for (const Operation& op : operations) {
        say("calling %s", op.name);
        sink = op.run();
    }
    for (const Operation& op : accepted) {
        say("calling %s", op.name);
        sink = op.run();
    }
    // Two results, to see that the checked operations still compute: 1.5 + 2^-60 + 2.25 - 2^-58
    // and the product of the two-limb operands, whose low limb is not zero.
    const E2 s = unverified(o.x) + o.y;
    if (s.limb[0] != 3.75 || s.limb[1] != 0x1p-60 - 0x1p-58) {
        say("FAILED: x + y is not (3.75, 2^-60 - 2^-58)");
        return 1;
    }
    if (!kairn::environment_ok()) {
        say("FAILED: environment_ok() is false after the operations");
        return 1;
    }
    std::printf("ok: %zu operations and %zu operands the checks must accept ran\n", std::size(operations),
                std::size(accepted));
    return 0;
}

int run_state(const char* state_name, const char* op_name) {
    const State* state = nullptr;
    for (const State& s : states)
        if (std::strcmp(s.name, state_name) == 0) state = &s;
    const Operation* op = nullptr;
    for (const Operation& candidate : operations)
        if (std::strcmp(candidate.name, op_name) == 0) op = &candidate;
    if (!state || !op) return usage();
    if (!kairn::environment_ok()) {
        say("FAILED: environment_ok() is false in the default environment");
        return 1;
    }
    say("ok: environment_ok() is true in the default environment");
    if (!state->set()) {
        state->restore();
        say("FAILED: %s cannot be set here", state_name);
        return 1;
    }
    if (kairn::environment_ok()) {
        state->restore();
        say("FAILED: environment_ok() is true under %s", state_name);
        return 1;
    }
    say("ok: environment_ok() is false under %s", state_name);
    say("calling %s under %s", op_name, state_name);
    sink = op->run();
    state->restore();
    say("FAILED: %s returned under %s: no check stopped it", op_name, state_name);
    return 1;
}

int run_operand(const char* case_name) {
    for (const OperandCase& c : operand_cases) {
        if (std::strcmp(c.name, case_name) != 0) continue;
        say("calling %s", case_name);
        sink = c.run();
        say("FAILED: %s returned: no check stopped it", case_name);
        return 1;
    }
    return usage();
}

}  // namespace

int main(int argc, char** argv) {
    kairn_test::no_crash_reports();
    make_operands();
    if (argc == 2 && std::strcmp(argv[1], "--operations") == 0) {
        for (const Operation& op : operations) std::printf("%s\n", op.name);
        return 0;
    }
    if (argc == 2 && std::strcmp(argv[1], "--states") == 0) {
        for (const State& s : states) std::printf("%s\n", s.name);
        return 0;
    }
    if (argc == 2 && std::strcmp(argv[1], "--operand-cases") == 0) {
        for (const OperandCase& c : operand_cases) std::printf("%s\t%s\n", c.name, c.message);
        return 0;
    }
    if (argc == 2 && std::strcmp(argv[1], "default") == 0) return run_default();
    if (argc == 3 && std::strcmp(argv[1], "operand") == 0) return run_operand(argv[2]);
    if (argc == 3) return run_state(argv[1], argv[2]);
    return usage();
}
