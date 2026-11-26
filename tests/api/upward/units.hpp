// api.upward.units and api.upward.dll: a scope in one file (units_a.cpp) and an operation in another
// (units_b.cpp, or the same file built into a DLL), the case of the design page's section "MSVC"
// where the barrier per scope reaches the operations through kairn::upward::detail::zero, an inline
// thread_local: the same object in every file of a module, which each scope writes after setting
// the mode and which the operation's pin reads. Requires the rounding mode upward set by
// kairn::upward::Scope and the options of docs/concepts/upward.md (GCC and Clang -frounding-math,
// MSVC /fp:strict).
//
// The operation is the product of two points through kairn::upward::Interval<double>: the generated
// kernel upward_mul_1, its first input pinned (KAIRN_DETAIL_UPWARD_PIN), the other input and the
// result behind barriers (KAIRN_DETAIL_UPWARD_BARRIER), and the upper bound of the result. The
// programs are built with KAIRN_CHECKS 0: some probes run the operation outside any scope on
// purpose, to see the result to nearest, which a checked build reports.
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

// The stand-in operation, x * y, defined in the other file (or the DLL).
UPWARD_TEST_API double mul(double x, double y) noexcept;

// The address of kairn::upward::detail::zero as the other file (or the DLL) sees it, on MSVC; nullptr
// elsewhere, where the barrier is on the values and there is no such object.
UPWARD_TEST_API const void* zero_address() noexcept;

}  // namespace units
