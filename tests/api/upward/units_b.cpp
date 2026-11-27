// The operation of api.upward.units and api.upward.dll (units.hpp): built into the same program as
// units_a.cpp, or into a DLL that the program loads. Requires the rounding mode upward set by
// kairn::upward::Scope and the options of docs/concepts/upward.md (GCC and Clang -frounding-math,
// MSVC /fp:strict).
#include <kairn/upward.hpp>

#include "units.hpp"

// The upper bound of the product of the points [x, x] and [y, y], through kairn::upward::Interval:
// from_limbs, the operator (kernel upward_mul_1, its first input pinned) and upper(), with the
// marker, which compiles whatever gen/upward.hpp says of the kernels.
double units::mul(double x, double y) noexcept {
    using I = kairn::upward::Interval<double>;
    const double a[2] = {x, -x}, b[2] = {y, -y};
    return kairn::unverified(kairn::unverified(I::from_limbs(a)) * I::from_limbs(b)).upper();
}

const void* units::zero_address() noexcept {
#if defined(KAIRN_DETAIL_UPWARD_MSVC)
    return &kairn::upward::detail::zero;
#else
    return nullptr;
#endif
}
