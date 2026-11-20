/// @file
/// The definitions of the operations that KAIRN_ENCLOSURE_CODE_EXTERNAL only declares (config.hpp,
/// KAIRN_ENCLOSURE_CODE): the operations of Ball that round, + - *, the scaling by a T and the
/// scaling by a power of two of ldexp and half, and the operations of Interval that round, + - *,
/// for float and double with one and two limbs. Include it in exactly one translation unit of the
/// program, a file of the program's own, compiled with the same settings as every other one
/// (KAIRN_ENCLOSURE_CODE, KAIRN_CHECKS, KAIRN_ENVIRONMENT_FAILURE, and the compiler and its flags),
/// for example
///
///     // kairn_definitions.cpp
///     #include <kairn/definitions.hpp>
///
/// With another setting of KAIRN_ENCLOSURE_CODE it defines nothing, so that a program can keep the
/// file whatever setting it is built with. Without it, with KAIRN_ENCLOSURE_CODE_EXTERNAL, the
/// program does not link: the operations are undefined (kairn::detail::external::add<double>, or
/// external_checked:: when KAIRN_CHECKS is 1).
#pragma once

#include "kairn.hpp"

#if KAIRN_ENCLOSURE_CODE == KAIRN_ENCLOSURE_CODE_EXTERNAL
#include "ball_operations.hpp"
#include "interval_operations.hpp"

KAIRN_GEN_PUSH_WARNINGS
namespace kairn::detail {
KAIRN_DETAIL_ENCLOSURE_BEGIN
KAIRN_DETAIL_BALL_INSTANCES(KAIRN_DETAIL_NOTHING, double)
KAIRN_DETAIL_BALL_INSTANCES(KAIRN_DETAIL_NOTHING, float)
KAIRN_DETAIL_INTERVAL_INSTANCES(KAIRN_DETAIL_NOTHING, double)
KAIRN_DETAIL_INTERVAL_INSTANCES(KAIRN_DETAIL_NOTHING, float)
KAIRN_DETAIL_ENCLOSURE_END
}  // namespace kairn::detail
KAIRN_GEN_POP_WARNINGS
#endif
