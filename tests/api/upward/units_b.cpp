// The operation of api.upward.units and api.upward.dll (units.hpp): built into the same program as
// units_a.cpp, or into a DLL that the program loads. Requires the rounding mode upward set by
// kairn::upward::Scope and the options of docs/concepts/upward.md (GCC and Clang -frounding-math,
// MSVC /fp:strict).
#include <kairn/upward.hpp>

#include "units.hpp"

double units::mul(double x, double y) noexcept {
    KAIRN_DETAIL_UPWARD_PIN(x);
    KAIRN_DETAIL_UPWARD_BARRIER(y);
    double z = x * y;
    KAIRN_DETAIL_UPWARD_BARRIER(z);
    return z;
}

const void* units::zero_address() noexcept {
#if defined(KAIRN_DETAIL_UPWARD_MSVC)
    return &kairn::upward::detail::zero;
#else
    return nullptr;
#endif
}
