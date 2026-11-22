/// @file
/// Kairn: floating-point expansions with ball and interval arithmetic, for one and two limbs.
///
/// Everything a program needs for Expansion<T, 1>, Expansion<T, 2>, Ball<T, k> and Interval<T, k>,
/// with T float or double, their constants from fractions of integers (rational.hpp), and the
/// building blocks on T (blocks.hpp: TwoSum, TwoProd, the neighbors of a number, the radius
/// helpers, sums and products rounded down and up), and the accumulator of a sum or a dot product
/// with its error bound (accumulator.hpp), which costs nothing measurable to include beyond the
/// rest. Including it checks the compiler's flags (config.hpp); a program should call
/// kairn::self_test() once at startup (environment.hpp). Not included, so that this one stays cheap
/// to include: Packed and the containers (packed.hpp, soa.hpp), the functions on arrays (batch.hpp)
/// and the ball vectors (ball_vector.hpp), which include the packed kernels of the target and double
/// the time to compile an empty program (docs/getting-started/index.md, "Use it from CMake", lists
/// what this header includes). Larger k and I/O are not written yet, and will be separate headers.
#pragma once

#include "version.hpp"

#include "config.hpp"
#include "environment.hpp"
#include "traits.hpp"
#include "expansion.hpp"
#include "ball.hpp"
#include "interval.hpp"
#include "rational.hpp"
#include "blocks.hpp"
#include "accumulator.hpp"
