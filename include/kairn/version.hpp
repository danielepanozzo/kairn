/// @file
/// Kairn's version. The top-level CMakeLists.txt states the same version, and configuring fails
/// when the two differ, so they are changed together.
#pragma once

/// The major version.
#define KAIRN_VERSION_MAJOR 0
/// The minor version.
#define KAIRN_VERSION_MINOR 0
/// The patch version.
#define KAIRN_VERSION_PATCH 0

/// "MAJOR.MINOR.PATCH", as a string literal.
#define KAIRN_VERSION_STRING "0.0.0"

/// MAJOR * 10000 + MINOR * 100 + PATCH, for comparisons in `#if`.
#define KAIRN_VERSION (KAIRN_VERSION_MAJOR * 10000 + KAIRN_VERSION_MINOR * 100 + KAIRN_VERSION_PATCH)
