/// @file
/// Kairn's version. The top-level CMakeLists.txt states the same version, and configuring fails
/// when the two differ, so they are changed together.
///
/// 0.2.0 is the development line of Milestone 2, in progress: it has KAIRN_ENCLOSURE_CODE, the
/// building blocks on T of blocks.hpp, the exact scaling of a Ball by a power of two (ldexp, half),
/// a Ball from a kairn::rational constant, and the sign predicates of a Ball. Until 1.0 a minor
/// version may change the interface; 0.2.0 names what is there now, not a release.
#pragma once

/// The major version.
#define KAIRN_VERSION_MAJOR 0
/// The minor version.
#define KAIRN_VERSION_MINOR 2
/// The patch version.
#define KAIRN_VERSION_PATCH 0

/// "MAJOR.MINOR.PATCH", as a string literal.
#define KAIRN_VERSION_STRING "0.2.0"

/// MAJOR * 10000 + MINOR * 100 + PATCH, for comparisons in `#if`.
#define KAIRN_VERSION (KAIRN_VERSION_MAJOR * 10000 + KAIRN_VERSION_MINOR * 100 + KAIRN_VERSION_PATCH)

/// 1 when this version of Kairn is MAJOR.MINOR.PATCH or later, 0 otherwise; usable in `#if`, with
/// a minor and a patch number below 100. A program that needs what 0.2.0 has (KAIRN_ENCLOSURE_CODE,
/// the building blocks, ldexp and half of a Ball) writes
///
///     #include <kairn/version.hpp>
///     #if !defined(KAIRN_VERSION_AT_LEAST)
///     #error "this program needs Kairn 0.2.0 or later"
///     #elif !KAIRN_VERSION_AT_LEAST(0, 2, 0)
///     #error "this program needs Kairn 0.2.0 or later"
///     #endif
///
/// The test of defined() first, in a group of its own: a version older than 0.2.0 does not define
/// the macro, and an undefined function-like macro in an `#if` does not compile. KAIRN_VERSION,
/// which every version defines, can be compared directly: `#if KAIRN_VERSION >= 200`.
#define KAIRN_VERSION_AT_LEAST(major, minor, patch) \
    (KAIRN_VERSION >= ((major) * 10000 + (minor) * 100 + (patch)))
