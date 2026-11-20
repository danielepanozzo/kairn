// The checks of KAIRN_CHECKS (include/kairn/config.hpp), run. Built without NDEBUG, as a debug
// build is (tests/api/flags/, where KAIRN_TEST_DEFAULT_CHECKS says that KAIRN_CHECKS must come from
// that default), and with KAIRN_CHECKS defined to 1 and the build's own flags (tests/api/): every
// function that rounds, and every constructor that checks what it is given, must check the
// floating-point environment first and then its operands, and stop the program with a message
// when one is wrong, the environment's when it is the environment; what is right must pass. A
// function that does not round must not check the rounding mode: under every rounding mode it must
// run without a report and give the same bits as to nearest. The functions and the states of the
// environment are those of checks_cases.hpp.
//
//   checks --operations       the functions, one per line: the name, a tab, and its kind (rounds,
//                             exact or unchecked: checks_cases.hpp says what each means)
//   checks --states           the states of the environment this target can set, one per line
//   checks --operand-cases    the operands the checks must refuse, each with the message expected
//   checks default            in the default environment: environment_ok() is true, and every
//                             function runs, as does each operand the checks must let through
//                             (canonical infinities and NaN, the special balls, what a finite core
//                             returns given to kairn::finite); exits 0
//   checks STATE OPERATION    environment_ok() is true, then STATE is set and it is false, then
//                             OPERATION runs. A function that rounds must stop the program; one that
//                             does not, under a rounding mode, must return the same bits as it did
//                             to nearest just before (exit status 0, and a line that starts with ok)
//   checks operand CASE       an operation given an operand that is not canonical, which must stop
//                             the program
//
// A check that lets the program go on where it must stop, or a function that does not round whose
// results differ, is reported with a line that starts with FAILED and exit status 1; a stopped
// program exits through abort(). tests/api/checks.cmake runs every case and tells them apart. Each
// line that says what the program is about to do is flushed first, since abort() discards what is
// buffered.
#if defined(KAIRN_TEST_DEFAULT_CHECKS) && (defined(KAIRN_CHECKS) || defined(NDEBUG))
#error "the debug build of checks.cpp must leave KAIRN_CHECKS to its default, without NDEBUG"
#endif
#include <kairn/kairn.hpp>
#if KAIRN_CHECKS != 1
#error "checks.cpp tests KAIRN_CHECKS: build it without NDEBUG, or with KAIRN_CHECKS defined to 1"
#endif

#include "checks_cases.hpp"
#include "no_crash_reports.hpp"

#include <cstdio>
#include <cstring>
#include <iterator>

namespace {

using namespace kairn_test;

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
    {"operator.unnormalized", not_canonical, [] { return (unverified(raw(1.0, double(v_a))) + o.y).limb[1]; }},
    // What a finite core may return after an overflow: given to an operator, refused.
    {"operator.core_result", not_canonical,
     [] { return (unverified(raw(infinity, not_a_number)) * o.y).limb[1]; }},
    {"operator.second", not_canonical, [] { return (unverified(o.y) - raw(1.0, double(v_a))).limb[1]; }},
    // The functions that do not round check their operands too, in the default environment.
    {"comparison.unnormalized", not_canonical, [] { return double(unverified(raw(1.0, double(v_a))) < o.y); }},
    {"conversion.unnormalized", not_canonical, [] { return kairn::to_down(unverified(raw(1.0, double(v_a)))); }},
    {"negation.unnormalized", not_canonical, [] { return (-unverified(raw(1.0, double(v_a)))).limb[1]; }},
    {"ldexp.unnormalized", not_canonical, [] { return kairn::ldexp(unverified(raw(1.0, double(v_a))), 2).limb[1]; }},
    {"finite.unnormalized", "an operand: is not normalized",
     [] { return kairn::finite::add(unverified(raw(1.0, double(v_a))), o.y).limb[1]; }},
    {"ball.negative_radius_1", negative, [] { return B1(unverified(E1(v_a)), -v_r).radius(); }},
    {"ball.negative_radius_2", negative, [] { return B2(unverified(o.x), -v_r).radius(); }},
    {"ball.minus_infinity_radius", negative, [] { return B1(unverified(E1(v_a)), -infinity).radius(); }},
    {"ball.center", "a ball: has a center that is not canonical",
     [] { return B2(unverified(raw(1.0, double(v_a))), v_r).radius(); }},
    // A ball that is not canonical cannot be made through the public constructors; the internal
    // one, which takes a kernel's result as it is, makes one.
    {"ball.operand", "a ball: is not canonical",
     [] { return (unverified(B1(kairn::detail::kernel_result, E1(v_a), -v_r)) + o.q).radius(); }},
    {"ball.negation", "a ball: is not canonical",
     [] { return (-unverified(B2(kairn::detail::kernel_result, raw(1.0, double(v_a)), v_r))).radius(); }},
    // fast_two_sum's requirement, |a| >= |b|: 2^-60 and 1.5 in the wrong order.
    {"fast_two_sum.order", "fast_two_sum: [|]a[|] < [|]b[|]", [] { return kairn::fast_two_sum(double(v_b), double(v_a)).sum; }},
    // The corner of two_sum: b the largest finite number, a sum that is finite, and an error term
    // that is a NaN, which the conversion to a two-limb number refuses.
    {"sum_pair.not_canonical", "SumAndError: the sum and the error term are not a canonical pair", [] {
         const double omega = opaque(std::numeric_limits<double>::max());
         return E2(kairn::two_sum(-1.5 * 0x1p971 * opaque(1.0), omega)).limb[1];
     }},
};

// What the checks must let through: canonical values that are not finite, the special balls,
// a NaN radius, and what a finite core returns, given back to kairn::finite.
struct Accepted {
    const char* name;
    double (*run)();
};
const Accepted accepted[] = {
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
    {"fast_two_sum with a NaN operand", [] { return kairn::fast_two_sum(not_a_number, double(v_a)).sum; }},
    {"(NaN, NaN) of two_sum, converted", [] { return E2(kairn::two_sum(not_a_number, double(v_a))).limb[0]; }},
    {"half of the whole line", [] { return kairn::half(unverified(B2::whole())).radius(); }},
};

void say(const char* format, const char* a = "", const char* b = "") {
    std::printf(format, a, b);
    std::printf("\n");
    std::fflush(stdout);
}

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
    std::size_t results = 0;
    for (const Operation& op : operations) {
        say("calling %s", op.name);
        Bits bits;
        op.run(bits);
        results += bits.size();
    }
    for (const Accepted& op : accepted) {
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
    std::printf("ok: %zu functions (%zu results) and %zu operands the checks must accept ran\n", std::size(operations),
                results, std::size(accepted));
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
    // A function that does not round, under a rounding mode: its results to nearest first.
    const bool same = state->rounding && op->kind != Kind::rounds;
    Bits nearest, directed;
    if (same) op->run(nearest);
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
    op->run(directed);
    const bool still = !kairn::environment_ok();
    state->restore();
    if (!same) {
        say("FAILED: %s returned under %s: no check stopped it", op_name, state_name);
        return 1;
    }
    if (!still) {
        say("FAILED: %s is no longer set after %s", state_name, op_name);
        return 1;
    }
    const long at = first_difference(nearest, directed);
    if (nearest.empty() || at >= 0) {
        std::printf("FAILED: %s under %s: %zu results, %zu to nearest, the first that differs is %ld", op_name,
                    state_name, directed.size(), nearest.size(), at);
        if (at >= 0 && std::size_t(at) < nearest.size() && std::size_t(at) < directed.size())
            std::printf(" (bits %016llx to nearest, %016llx under %s)", (unsigned long long)nearest[at],
                        (unsigned long long)directed[at], state_name);
        std::printf("\n");
        return 1;
    }
    std::printf("ok: %s does not round: under %s, %zu results with the same bits as to nearest, and no check "
                "stopped it\n",
                op_name, state_name, directed.size());
    return 0;
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
        for (const Operation& op : operations) std::printf("%s\t%s\n", op.name, kind_name(op.kind));
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
