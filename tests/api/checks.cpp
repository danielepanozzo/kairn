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
    // An interval that is not canonical cannot be made through the public constructors either: the
    // internal one makes reversed bounds, and a NaN bound, given to a sum and to a negation; a bound
    // of two limbs that is not canonical given to the constructor, and an interval with one to the
    // hull.
    {"interval.operand", "an interval: is not canonical",
     [] { return (unverified(I1(kairn::detail::kernel_result, E1(v_c), E1(v_a))) + o.iy).lower().limb[0]; }},
    {"interval.negation", "an interval: is not canonical",
     [] { return (-unverified(I1(kairn::detail::kernel_result, E1(not_a_number), E1(v_a)))).lower().limb[0]; }},
    {"interval.bound", not_canonical, [] { return I2(unverified(raw(1.0, double(v_a))), o.y).lower().limb[1]; }},
    {"interval.hull", "an interval: is not canonical",
     [] { return o.jx.hull(unverified(I2(kairn::detail::kernel_result, raw(1.0, double(v_a)), o.y))).lower().limb[1]; }},
    // Packed and the containers: a lane that is not canonical among canonical ones, given to a
    // load (the message of from_limbs), to an operator, a comparison and a finite core; and an
    // element of a view, read through get, the proxy and load.
    {"packed.load.unnormalized", not_a_pair, [] {
         Arrays a(o.y);
         a.h[P2::lanes - 1] = 1.0;
         a.l[P2::lanes - 1] = v_a;
         return P2::load(a.h, a.l).lane(0).limb[1];
     }},
    {"packed.from_limbs.unnormalized", not_a_pair, [] {
         P2 x = P2::broadcast(o.y);
         x.set_lane(0, raw(1.0, double(v_a)));
         return P2::from_limbs(x.limb[0], x.limb[1]).lane(0).limb[1];
     }},
    {"packed.operator.unnormalized", not_canonical, [] {
         P2 x = P2::broadcast(o.y);
         x.set_lane(P2::lanes - 1, raw(1.0, double(v_a)));
         return (x + P2::broadcast(o.y)).lane(0).limb[1];
     }},
    {"packed.comparison.unnormalized", not_canonical, [] {
         P2 x = P2::broadcast(o.y);
         x.set_lane(P2::lanes - 1, raw(1.0, double(v_a)));
         return double(kairn::any(P2::broadcast(o.x) < x));
     }},
    {"packed.finite.unnormalized", "an operand: is not normalized", [] {
         P2 x = P2::broadcast(o.y);
         x.set_lane(0, raw(1.0, double(v_a)));
         return kairn::finite::add(x, P2::broadcast(o.y)).lane(0).limb[1];
     }},
    {"soa.get.unnormalized", not_a_pair, [] {
         Arrays a(o.y);
         a.l[2] = v_a;
         a.h[2] = 1.0;
         return kairn::SoAView<const double, 2>(a.h, a.l, 16).get(2).limb[1];
     }},
    {"soa.element.unnormalized", not_a_pair, [] {
         Arrays a(o.y);
         a.l[7] = v_a;
         a.h[7] = 1.0;
         return E2(kairn::SoAView<double, 2>(a.h, a.l, 16)[7]).limb[1];
     }},
    {"soa.load.unnormalized", not_a_pair, [] {
         Arrays a(o.y);
         a.l[3] = v_a;
         a.h[3] = 1.0;
         return kairn::SoAView<const double, 2>(a.h, a.l, 16).load(3).lane(0).limb[1];
     }},
    // fast_two_sum's requirement, |a| >= |b|: 2^-60 and 1.5 in the wrong order.
    {"fast_two_sum.order", "fast_two_sum: [|]a[|] < [|]b[|]", [] { return kairn::fast_two_sum(double(v_b), double(v_a)).sum; }},
    // The corner of two_sum: b the largest finite number, a sum that is finite, and an error term
    // that is a NaN, which the conversion to a two-limb number refuses.
    {"sum_pair.not_canonical", "SumAndError: the sum and the error term are not a canonical pair", [] {
         const double omega = opaque(std::numeric_limits<double>::max());
         return E2(kairn::two_sum(-1.5 * 0x1p971 * opaque(1.0), omega)).limb[1];
     }},
    // The enclosure interface of stage B2 (headers-pred): an interval that is not canonical (made
    // by the internal constructor: reversed bounds, a NaN bound) given to a member test, a
    // comparison and a relation of IEEE 1788; a ball that is not canonical given to a member test
    // and to the hull; a point of two limbs that is not canonical given to the member tests.
    {"enclosure.interval_contains", "an interval: is not canonical",
     [] { return double(I1(kairn::detail::kernel_result, E1(v_c), E1(v_a)).contains(double(v_b))); }},
    {"enclosure.interval_less", "an interval: is not canonical",
     [] { return double(int(kairn::less(I1(kairn::detail::kernel_result, E1(not_a_number), E1(v_a)), o.iy))); }},
    {"enclosure.interval_subset", "an interval: is not canonical",
     [] { return double(kairn::ieee1788::subset(o.jx, I2(kairn::detail::kernel_result, o.y, o.x))); }},
    {"enclosure.interval_point", not_canonical, [] { return double(o.jy.contains(raw(1.0, double(v_a)))); }},
    {"enclosure.ball_contains", "a ball: is not canonical",
     [] { return double(B1(kairn::detail::kernel_result, E1(v_a), -v_r).contains(double(v_c))); }},
    {"enclosure.ball_hull", "a ball: is not canonical",
     [] { return o.bp.hull(B2(kairn::detail::kernel_result, raw(1.0, double(v_a)), v_r)).radius(); }},
    {"enclosure.ball_point", not_canonical, [] { return double(int(kairn::member(raw(1.0, double(v_a)), o.bp))); }},
    // The functions on arrays (kairn/batch.hpp): an element that is not canonical, lengths that
    // differ, arrays that overlap without being the same, a scalar that is not what the function
    // requires.
    {"batch.sum.unnormalized", "sum: an element of x is not canonical", [] {
         Arrays a(o.y);
         a.h[9] = 1.0;
         a.l[9] = v_a;
         return kairn::sum(kairn::SoAView<const double, 2>(a.h, a.l, 16)).value.limb[0];
     }},
    {"batch.dot.lengths", "dot: x and y have different lengths", [] {
         const Arrays a(o.x), c(o.y);
         return kairn::dot(kairn::SoAView<const double, 1>(a.h, 16), kairn::SoAView<const double, 1>(c.h, 15)).value.limb[0];
     }},
    {"batch.dot.unnormalized_y", "dot: an element of y is not canonical", [] {
         Arrays a(o.x), c(o.y);
         c.l[15] = v_a;
         c.h[15] = 1.0;
         return kairn::dot(kairn::SoAView<const double, 2>(a.h, a.l, 16), kairn::SoAView<const double, 2>(c.h, c.l, 16),
                           kairn::sequential).value.limb[0];
     }},
    {"batch.add.lengths", "add: x and z have different lengths", [] {
         const Arrays a(o.x), c(o.y);
         Arrays z(o.x);
         return double(kairn::add(kairn::SoAView<const double, 1>(a.h, 16), kairn::SoAView<const double, 1>(c.h, 16),
                                  kairn::SoAView<double, 1>(z.h, 12)));
     }},
    {"batch.add.y_lengths", "add: y and z have different lengths", [] {
         const Arrays a(o.x), c(o.y);
         Arrays z(o.x);
         return double(kairn::add(kairn::SoAView<const double, 1>(a.h, 12), kairn::SoAView<const double, 1>(c.h, 16),
                                  kairn::SoAView<double, 1>(z.h, 12)));
     }},
    {"batch.add.overlap", "add: z overlaps x without being x", [] {
         Arrays a(o.x);
         const Arrays c(o.y);
         return double(kairn::add(kairn::SoAView<const double, 2>(a.h, a.l, 15), kairn::SoAView<const double, 2>(c.h, c.l, 15),
                                  kairn::SoAView<double, 2>(a.h + 1, a.l + 1, 15)));
     }},
    {"batch.axpy.overlap_y", "axpy: z overlaps y without being y", [] {
         const Arrays a(o.x);
         Arrays c(o.y);
         return double(kairn::axpy(2.0, kairn::SoAView<const double, 1>(a.h, 15), kairn::SoAView<const double, 1>(c.h + 1, 15),
                                   kairn::SoAView<double, 1>(c.h, 15)));
     }},
    {"batch.add.limbs", "add: the limb arrays of z overlap each other", [] {
         const Arrays a(o.x), c(o.y);
         Arrays z(o.x);
         return double(kairn::add(kairn::SoAView<const double, 2>(a.h, a.l, 16), kairn::SoAView<const double, 2>(c.h, c.l, 16),
                                  kairn::SoAView<double, 2>(z.h, z.h, 16)));
     }},
    {"batch.axpy.a", "axpy: a is not canonical", [] {
         const Arrays a(o.x);
         Arrays c(o.y);
         const kairn::SoAView<double, 2> y(c.h, c.l, 16);
         return double(kairn::axpy(raw(1.0, double(v_a)), kairn::SoAView<const double, 2>(a.h, a.l, 16), y, y));
     }},
    {"batch.mul_pow2.c", "mul_pow2: c is not a positive power of two of T", [] {
         Arrays a(o.x);
         const kairn::SoAView<double, 2> x(a.h, a.l, 16);
         return double(kairn::mul_pow2(x, double(v_a), x));
     }},
    {"batch.mul_pow2.negative", "mul_pow2: c is not a positive power of two of T", [] {
         Arrays a(o.x);
         const kairn::SoAView<double, 1> x(a.h, 16);
         return double(kairn::mul_pow2(x, -0.5 * double(opaque(1.0)), x));
     }},
    {"batch.conv.length", "conv: z does not have the length of the product", [] {
         const Arrays a(o.x), c(o.y);
         double h[31], l[31];
         return double(kairn::conv(kairn::SoAView<const double, 2>(a.h, a.l, 16), kairn::SoAView<const double, 2>(c.h, c.l, 16),
                                   kairn::SoAView<double, 2>(h, l, 30)));
     }},
    {"batch.conv.overlap", "conv: z overlaps x or y", [] {
         Arrays a(o.x);
         const Arrays c(o.y);
         return double(kairn::conv(kairn::SoAView<const double, 1>(a.h, 8), kairn::SoAView<const double, 1>(c.h, 8),
                                   kairn::SoAView<double, 1>(a.h + 1, 15)));
     }},
    // The accumulator: an operand that is not canonical; a state given to from_state that is not
    // one (a sum that is not canonical, negative magnitudes).
    {"acc.add.unnormalized", not_canonical, [] {
         kairn::Accumulator<double, 2> a;
         a.add(raw(1.0, double(v_a)));
         return a.running_sum().limb[0];
     }},
    {"acc.add_product.unnormalized", not_canonical, [] {
         kairn::Accumulator<double, 2> a;
         a.add_product(o.x, raw(1.0, double(v_a)));
         return a.running_sum().limb[0];
     }},
    {"acc.from_state.unnormalized", "Accumulator::from_state: the running sum is not canonical",
     [] { return kairn::Accumulator<double, 2>::from_state(raw(1.0, double(v_a)), 1.0, 2).magnitudes(); }},
    {"acc.from_state.negative", "Accumulator::from_state: the sum of magnitudes is negative",
     [] { return kairn::Accumulator<double, 2>::from_state(o.x, -double(v_a), 2).magnitudes(); }},
    {"batch.norm_upper.unnormalized", "norm_upper: an element of x is not canonical", [] {
         Arrays a(o.y);
         a.h[4] = 1.0;
         a.l[4] = v_a;
         return kairn::norm_upper(kairn::SoAView<const double, 2>(a.h, a.l, 16)).value;
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
    // Intervals: bounds that are a NaN or reversed, which make the whole line and the empty set
    // without a report, and the two states as operands.
    {"Interval(NaN, 1)", [] { return I1(unverified(not_a_number), v_a).upper().limb[0]; }},
    {"Interval(2.25, 1.5)", [] { return I1(unverified(double(v_c)), v_a).lower().limb[0]; }},
    {"Interval((+inf, 0), (NaN, NaN))", [] { return I2(unverified(pair(infinity, 0.0)), pair(not_a_number, not_a_number)).upper().limb[0]; }},
    {"empty + interval", [] { return (unverified(I1::empty()) + o.iy).lower().limb[0]; }},
    {"whole * interval", [] { return (unverified(I2::whole()) * o.jy).upper().limb[0]; }},
    {"midpoint of the empty set", [] { return I1::empty().midpoint().limb[0]; }},
    {"the bounds of the empty ball", [] { return B2::empty().lower_as<double>(); }},
    // Packed and the views: canonical lanes that are not finite, and what a core returns.
    {"P2::load of (+inf, 0) and (NaN, NaN)", [] {
         Arrays a(pair(infinity, 0.0));
         a.h[0] = a.l[0] = not_a_number;
         return P2::load(a.h, a.l).lane(1).limb[0];
     }},
    {"a view of (-inf, -0)", [] {
         Arrays a(pair(-infinity, 0.0));
         a.l[1] = -0.0;
         return kairn::SoAView<const double, 2>(a.h, a.l, 16).get(1).limb[0];
     }},
    // The functions on arrays: canonical elements that are not finite, maps in place, empty arrays.
    {"sum of (+inf, 0) and (NaN, NaN)", [] {
         Arrays a(pair(infinity, 0.0));
         a.h[3] = a.l[3] = not_a_number;
         return kairn::sum(kairn::SoAView<const double, 2>(a.h, a.l, 16)).value.limb[0];
     }},
    {"axpy in place, z = x", [] {
         Arrays a(o.x);
         const Arrays c(o.y);
         const kairn::SoAView<double, 2> x(a.h, a.l, 16);
         return double(kairn::axpy(o.y, x, kairn::SoAView<const double, 2>(c.h, c.l, 16), x));
     }},
    {"an accumulator from the state (+inf, 0), +inf", [] {
         return kairn::Accumulator<double, 2>::from_state(pair(infinity, 0.0), infinity, 3).error_bound();
     }},
    {"conv of empty polynomials", [] {
         return double(kairn::conv(kairn::SoAView<const double, 2>(), kairn::SoAView<const double, 2>(),
                                   kairn::SoAView<double, 2>()));
     }},
    {"kairn::finite::add on a lane (inf, NaN)", [] {
         P2 x = P2::broadcast(o.y);
         x.set_lane(0, raw(infinity, not_a_number));
         return kairn::finite::add(x, P2::broadcast(o.y)).lane(1).limb[0];
     }},
    // The enclosure interface of stage B2 (headers-pred): the special states and points that are
    // not finite, which the member tests, the comparisons and the set operations take.
    {"the whole line contains a NaN", [] { return double(I2::whole().contains(not_a_number)); }},
    {"the empty ball contains (NaN, NaN)", [] { return double(B2::empty().contains(pair(not_a_number, not_a_number))); }},
    {"less of the empty set and the whole line", [] { return double(int(kairn::less(I1::empty(), I1::whole()))); }},
    {"the hull of the empty ball and the whole line", [] { return B2::empty().hull(B2::whole()).radius(); }},
    {"the split of the whole line", [] { return B1::whole().split().left.radius(); }},
    {"the ball of [NaN, 1]", [] { return B1::from_interval(not_a_number, double(v_a)).radius(); }},
    {"the midpoint of the empty interval of two limbs", [] { return I2::empty().midpoint().limb[0]; }},
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
