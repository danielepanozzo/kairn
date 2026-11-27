/// @file
/// Kairn's version. The top-level CMakeLists.txt states the same version, and configuring fails
/// when the two differ, so they are changed together.
///
/// What each version has. Until 1.0 a minor version may change the interface, and a version names
/// what a tree has, not a release.
///
/// - 0.4.1: in the NEON forms of kairn/upward.hpp, the test that an operand is empty (a NaN in a
///   lane of either operand, detail::unord) is the NaN test of their maximum, FMAX, instead of two
///   NaN tests and their or: the same result for every input, in fewer instructions. The listings,
///   the statements, the claims and every other form are unchanged.
/// - 0.4.0: the opt-in round-up interval, kairn/upward.hpp, which kairn/kairn.hpp does not include
///   and which requires the rounding mode upward set by kairn::upward::Scope and the options of
///   docs/concepts/upward.md (GCC and Clang -frounding-math, MSVC /fp:strict), with the CMake target
///   kairn::upward that adds them: kairn::upward::Interval<T>, an interval of one limb kept in one
///   register and computed under the mode upward, its operations, comparisons and relations, its
///   functions on arrays on views kairn::upward::View<T>, the scopes kairn::upward::Scope and
///   kairn::upward::NearestScope, kairn::upward::pass() and kairn::upward::self_test(), whose
///   kairn::Status sets kernel for every failure and gives advice in limitation. The default types
///   are unchanged.
/// - 0.3.2: kairn::Status has a third member, limitation, with limited(): kairn::self_test()
///   reports there, without failing, that a square the program passes straight into an operation
///   is not rounded first in the translation unit that calls it (Clang under -ffp-contract=fast).
/// - 0.3.1, the changes decided at the owner's review of Milestone 2 (2026-11-23): the operators
///   +, -, * and their compound forms of Packed<T, 1>; the constructors of a Ball and of an
///   Interval from numbers of two limbs guard every limb they are given, and
///   Accumulator::from_state of two limbs guards its running sum (of the values given, a limb -0
///   comes back +0, but with MSVC, where it may stay -0: the compiler removes the addition of
///   zero where it packs two guards; 0.3.0 kept those limbs bit for bit); the check of the
///   environment at a batch entry reports through one function that is never inlined, so
///   KAIRN_ENVIRONMENT_FAILURE is defined the same way in every translation unit of a program,
///   or in none.
/// - 0.3.0, the development line of Milestone 2 with the whole interface of its statements:
///   everything of 0.2.0 below, the interval and the enclosure interface whole (Interval of
///   interval.hpp, with Interval::is_finite(); the types of enclosure.hpp; the predicates, member
///   and subset tests, three-valued comparisons and relations of IEEE 1788 of both types), Packed
///   and the containers of packed.hpp and soa.hpp, the functions on arrays of batch.hpp (sum,
///   sum_fast, dot, the maps, conv, norm_upper, with kairn::sequential as their first argument),
///   the accumulator of accumulator.hpp, BallVector and its views of ball_vector.hpp, and:
///   X::from_bounds(lo, hi) of Interval and Ball, one spelling of a set from two bounds;
///   Interval::from_limbs and Ball::from_limbs, the constructors from limbs; ldexp and half of two
///   limbs in constant expressions; and the check of the floating-point environment at every batch
///   entry (the functions on arrays and the operations on whole ball vectors), in every build. 0.2.0
///   was not changed while Interval, the enclosure interface, Packed, the containers, the arrays and
///   the ball vectors were added, so KAIRN_VERSION_AT_LEAST(0, 2, 0) cannot tell whether a tree has
///   them; KAIRN_VERSION_AT_LEAST(0, 3, 0) can.
/// - 0.2.0, the first development line of Milestone 2: KAIRN_ENCLOSURE_CODE, the building blocks
///   on T of blocks.hpp, the constants of rational.hpp (kairn::rational, kairn::integer), the exact
///   scaling of a Ball by a power of two (ldexp, half) and a Ball from such a constant; a tree of
///   0.2.0 may or may not have the rest of the list above.
#pragma once

/// The major version.
#define KAIRN_VERSION_MAJOR 0
/// The minor version.
#define KAIRN_VERSION_MINOR 4
/// The patch version.
#define KAIRN_VERSION_PATCH 1

/// "MAJOR.MINOR.PATCH", as a string literal.
#define KAIRN_VERSION_STRING "0.4.1"

/// MAJOR * 10000 + MINOR * 100 + PATCH, for comparisons in `#if`.
#define KAIRN_VERSION (KAIRN_VERSION_MAJOR * 10000 + KAIRN_VERSION_MINOR * 100 + KAIRN_VERSION_PATCH)

/// 1 when this version of Kairn is MAJOR.MINOR.PATCH or later, 0 otherwise; usable in `#if`, with
/// a minor and a patch number below 100. A program that needs what 0.3.0 has (the functions on
/// arrays, BallVector, from_bounds, from_limbs of a set) writes
///
///     #include <kairn/version.hpp>
///     #if !defined(KAIRN_VERSION_AT_LEAST)
///     #error "this program needs Kairn 0.3.0 or later"
///     #elif !KAIRN_VERSION_AT_LEAST(0, 3, 0)
///     #error "this program needs Kairn 0.3.0 or later"
///     #endif
///
/// The test of defined() first, in a group of its own: a version older than 0.2.0 does not define
/// the macro, and an undefined function-like macro in an `#if` does not compile. KAIRN_VERSION,
/// which every version defines, can be compared directly: `#if KAIRN_VERSION >= 300`.
#define KAIRN_VERSION_AT_LEAST(major, minor, patch) \
    (KAIRN_VERSION >= ((major) * 10000 + (minor) * 100 + (patch)))
