/// @file
/// Reduction<X>: a number and whether it is finite, the result of the functions on arrays that
/// return one number (batch.hpp) and of Accumulator::sum() (accumulator.hpp). A header of its own so
/// that accumulator.hpp, which needs it, does not include batch.hpp and the packed headers with it.
#pragma once

#include "config.hpp"

KAIRN_GEN_PUSH_WARNINGS
namespace kairn {

/// The result of a function on arrays that returns one number: the number and whether it is
/// finite. An aggregate, so `auto [s, finite] = kairn::sum(x);` binds them in that order.
template <class X>
struct Reduction {
    /// The result when finite is true; the canonical NaN (every limb a NaN) when it is false.
    X value{};
    /// True exactly when value is finite: every element was finite and nothing overflowed.
    bool finite = true;
};

}  // namespace kairn
KAIRN_GEN_POP_WARNINGS
