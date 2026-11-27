// api.upward.units and api.upward.dll: a scope in one file (units_a.cpp) and an operation in another
// (units_b.cpp, or the same file built into a DLL), the case of the design page's section "MSVC"
// where the barrier per scope reaches the operations through kairn::upward::detail::zero, an inline
// thread_local: the same object in every file of a module, which each scope writes after setting
// the mode and which the operation's pin reads. Requires the rounding mode upward set by
// kairn::upward::Scope and the options of docs/concepts/upward.md (GCC and Clang -frounding-math,
// MSVC /fp:strict).
//
// The operations are those of kairn::upward::Interval<double> on points, each a generated kernel
// whose first input is pinned (KAIRN_DETAIL_UPWARD_PIN), the other inputs and the result behind
// barriers (KAIRN_DETAIL_UPWARD_BARRIER): the product, the sum, the product by a number, and a
// function on arrays; two arrangements, the scope in the caller around calls into the other file,
// and the scope held by the function of the other file. The programs are built with KAIRN_CHECKS
// 0: some probes run an operation outside any scope on purpose, to see the result to nearest,
// which a checked build reports.
#pragma once

#if defined(UPWARD_TEST_DLL) && defined(_WIN32)
#if defined(UPWARD_TEST_BUILDING_DLL)
#define UPWARD_TEST_API __declspec(dllexport)
#else
#define UPWARD_TEST_API __declspec(dllimport)
#endif
#else
#define UPWARD_TEST_API
#endif

namespace units {

// Defined in the other file (or the DLL), each through kairn::upward::Interval<double> on points:
// the upper bound of the product of [x, x] and [y, y] (upward_mul_1), of the sum of [x, x] and
// [y, y] (upward_add_1), and of [x, x] times the number t (upward_mul_num_1), each to be called
// inside a scope of the caller's.
UPWARD_TEST_API double mul(double x, double y) noexcept;
UPWARD_TEST_API double add(double x, double y) noexcept;
UPWARD_TEST_API double mul_number(double x, double t) noexcept;

// Each holding its scope in the other file (or the DLL), so that it may be called from code that
// rounds to nearest: the upper bound of the product of [x, x] and [y, y] in a kairn::upward::Scope of
// its own, and kairn::upward::mul on n copies of [x, x] times themselves (the function on arrays,
// which holds its own scope), the upper bounds written to z.
UPWARD_TEST_API double held_mul(double x, double y) noexcept;
UPWARD_TEST_API void square_array(double x, double* z, int n) noexcept;

// The address of kairn::upward::detail::zero as the other file (or the DLL) sees it, on MSVC; nullptr
// elsewhere, where the barrier is on the values and there is no such object.
UPWARD_TEST_API const void* zero_address() noexcept;

}  // namespace units
