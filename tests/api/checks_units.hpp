// api.checks.handler.units and .off: a program of two translation units, checks_units_a.cpp (with
// main) and checks_units_b.cpp, each of which includes this file, which defines
// KAIRN_ENVIRONMENT_FAILURE the same way in both, as config.hpp requires of a program: as a call of
// units::handler, a function of the program with external linkage, defined once (in
// checks_units_a.cpp), which records the reason and returns. Kairn expands the macro in one
// function, kairn::detail::report_environment (environment.hpp), which is never inlined and of which
// the linker keeps one copy for the program; the program checks that each unit's checks reach the
// handler through it, under each state of the environment, and that every function goes on after
// the handler returned.
#pragma once

#include <cstdint>

namespace units {
// The program's handler (checks_units_a.cpp): counts its calls and keeps the last reason.
void handler(const char* reason) noexcept;
}  // namespace units

#define KAIRN_ENVIRONMENT_FAILURE(reason) ::units::handler(reason)

#include <kairn/ball_vector.hpp>
#include <kairn/batch.hpp>
#include <kairn/kairn.hpp>

namespace units {

// Operands read from volatile objects, so that nothing is computed before the program asks.
inline volatile double v_one = 1.5, v_two = 0x1p-60, v_three = 2.25, v_radius = 0x1p-20;

// What one unit runs, each a function of that unit, called through these pointers: a function on
// arrays that rounds (sum) and one that does not (norm_upper, checked without the rounding mode),
// the constructor of a ball vector, the sum of two ball vectors and the negation of one (checked
// without the rounding mode), and a scalar operation (x + y of two limbs), which is checked with
// KAIRN_CHECKS 1 only. Each returns a value of its result, which is not compared: in an
// environment that is not the default one no result has a guarantee. report is the address of
// kairn::detail::report_environment as the unit sees it.
struct Unit {
    const char* name;
    double (*sum)();
    double (*norm)();
    double (*make)();
    double (*add)();
    double (*neg)();
    double (*scalar)();
    void (*report)(std::uint64_t);
};

// The table of each unit, defined in that unit (checks_units_a.cpp, checks_units_b.cpp).
Unit unit_a();
Unit unit_b();

}  // namespace units

// The functions themselves, the same text in both units, each in an unnamed namespace of its own unit
// and never inlined, so that each unit compiles its own calls of the checks.
#if defined(_MSC_VER) && !defined(__clang__)
#define UNITS_NOINLINE __declspec(noinline)
#else
#define UNITS_NOINLINE __attribute__((noinline))
#endif
#define UNITS_FUNCTIONS(UNIT_NAME, TABLE)                                                             \
    namespace {                                                                                       \
    UNITS_NOINLINE double run_sum() {                                                                 \
        const double x[4] = {units::v_one, units::v_two, units::v_three, units::v_radius};            \
        return kairn::sum(kairn::SoAView<const double, 1>(x, 4)).value.limb[0];                       \
    }                                                                                                 \
    UNITS_NOINLINE double run_norm() {                                                                \
        const double x[4] = {units::v_one, -units::v_two, units::v_three, units::v_radius};           \
        return kairn::norm_upper(kairn::SoAView<const double, 1>(x, 4)).value;                        \
    }                                                                                                 \
    UNITS_NOINLINE double run_make() {                                                                \
        const std::array<kairn::Expansion<double, 1>, 3> c = {                                        \
            kairn::Expansion<double, 1>(units::v_one), kairn::Expansion<double, 1>(units::v_two),     \
            kairn::Expansion<double, 1>(units::v_three)};                                             \
        const kairn::BallVector<double, 1, 3> x(c, units::v_radius);                                  \
        return x.center(0).limb[0] + x.radius();                                                      \
    }                                                                                                 \
    kairn::BallVector<double, 2, 3> operand(double scale) {                                           \
        double hi[3] = {units::v_one * scale, units::v_three * scale, units::v_one};                  \
        double lo[3] = {units::v_two, -units::v_two, 0.0};                                            \
        const double r = units::v_radius;                                                             \
        return kairn::BallVector<double, 2, 3>(kairn::SoAView<const double, 2>(hi, lo, 3), r);        \
    }                                                                                                 \
    UNITS_NOINLINE double run_add(const kairn::BallVector<double, 2, 3>& x,                           \
                                  const kairn::BallVector<double, 2, 3>& y) {                         \
        kairn::BallVector<double, 2, 3> z;                                                            \
        kairn::add(x, y, z);                                                                          \
        return z.center(1).limb[0] + z.radius();                                                      \
    }                                                                                                 \
    UNITS_NOINLINE double run_neg(const kairn::BallVector<double, 2, 3>& x) {                         \
        kairn::BallVector<double, 2, 3> z;                                                            \
        kairn::neg(x, z);                                                                             \
        return z.center(0).limb[0] + z.radius();                                                      \
    }                                                                                                 \
    UNITS_NOINLINE double run_scalar(const kairn::Expansion<double, 2>& x,                            \
                                     const kairn::Expansion<double, 2>& y) {                          \
        return (x + y).limb[1];                                                                       \
    }                                                                                                 \
    /* The operands of the ball vectors and of x + y are made in the default environment. */         \
    const kairn::BallVector<double, 2, 3>& bv_x() {                                                   \
        static const kairn::BallVector<double, 2, 3> x = operand(1.0);                                \
        return x;                                                                                     \
    }                                                                                                 \
    const kairn::BallVector<double, 2, 3>& bv_y() {                                                   \
        static const kairn::BallVector<double, 2, 3> y = operand(-0.5);                               \
        return y;                                                                                     \
    }                                                                                                 \
    double call_add() { return run_add(bv_x(), bv_y()); }                                             \
    double call_neg() { return run_neg(bv_x()); }                                                     \
    double call_scalar() {                                                                            \
        static const kairn::Expansion<double, 2> x = kairn::Expansion<double, 2>(units::v_one);       \
        static const kairn::Expansion<double, 2> y = kairn::Expansion<double, 2>(units::v_two);       \
        return run_scalar(x, y);                                                                      \
    }                                                                                                 \
    }                                                                                                 \
    units::Unit TABLE() {                                                                             \
        (void)bv_x();                                                                                 \
        (void)bv_y();                                                                                 \
        (void)call_scalar();                                                                          \
        return {UNIT_NAME, run_sum, run_norm, run_make, call_add, call_neg, call_scalar,              \
                &kairn::detail::report_environment};                                                  \
    }
