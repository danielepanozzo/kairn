/// @file
/// Kairn: floating-point expansions with ball arithmetic, for one and two limbs.
///
/// Everything a program needs for Expansion<T, 1>, Expansion<T, 2> and Ball<T, k>, with T float
/// or double. Including it checks the compiler's flags (config.hpp); a program should call
/// kairn::self_test() once at startup (environment.hpp). Larger k, intervals, vectors and I/O are
/// not written yet, and will be separate headers so that this one stays cheap to include.
#pragma once

#include "version.hpp"

#include "config.hpp"
#include "environment.hpp"
#include "traits.hpp"
#include "expansion.hpp"
#include "ball.hpp"
