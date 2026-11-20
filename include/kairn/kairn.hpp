/// @file
/// Kairn: floating-point expansions with ball arithmetic, for one and two limbs.
///
/// Everything a program needs for Expansion<T, 1>, Expansion<T, 2> and Ball<T, k>, with T float
/// or double, their constants from fractions of integers (rational.hpp), and the building blocks
/// on T (blocks.hpp: TwoSum, TwoProd, the neighbors of a number, the radius helpers, sums and
/// products rounded down and up). Including it checks the compiler's flags (config.hpp); a program
/// should call kairn::self_test() once at startup (environment.hpp). Larger k, intervals, vectors
/// and I/O are not written yet, and will be separate headers so that this one stays cheap to
/// include.
#pragma once

#include "version.hpp"

#include "config.hpp"
#include "environment.hpp"
#include "traits.hpp"
#include "expansion.hpp"
#include "ball.hpp"
#include "rational.hpp"
#include "blocks.hpp"
