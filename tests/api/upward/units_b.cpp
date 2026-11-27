// The operation of api.upward.units and api.upward.dll (units.hpp): built into the same program as
// units_a.cpp, or into a DLL that the program loads. Requires the rounding mode upward set by
// kairn::upward::Scope and the options of docs/concepts/upward.md (GCC and Clang -frounding-math,
// MSVC /fp:strict).
#include <kairn/upward.hpp>

#include "units.hpp"

// The upper bound of the product of the points [x, x] and [y, y], through kairn::upward::Interval:
// from_limbs, the operator (kernel upward_mul_1, its first input pinned) and upper(), with the
// marker, which compiles whatever gen/upward.hpp says of the kernels. The others likewise.
double units::mul(double x, double y) noexcept {
    using I = kairn::upward::Interval<double>;
    const double a[2] = {x, -x}, b[2] = {y, -y};
    return kairn::unverified(kairn::unverified(I::from_limbs(a)) * I::from_limbs(b)).upper();
}

double units::add(double x, double y) noexcept {
    using I = kairn::upward::Interval<double>;
    const double a[2] = {x, -x}, b[2] = {y, -y};
    return kairn::unverified(kairn::unverified(I::from_limbs(a)) + I::from_limbs(b)).upper();
}

double units::mul_number(double x, double t) noexcept {
    using I = kairn::upward::Interval<double>;
    const double a[2] = {x, -x};
    return kairn::unverified(kairn::unverified(I::from_limbs(a)) * t).upper();
}

// The scope in this file (or the DLL): its refresh writes this module's kairn::upward::detail::zero,
// which the product's pin reads.
double units::held_mul(double x, double y) noexcept {
    kairn::upward::Scope up;
    return mul(x, y);
}

void units::square_array(double x, double* z, int n) noexcept {
    using kairn::upward::View;
    constexpr int most = 16;
    double xu[most], xn[most], zn[most];
    const int m = n < most ? n : most;
    for (int i = 0; i < m; ++i) {
        xu[i] = x;
        xn[i] = -x;
    }
    const View<const double> v(xu, xn, static_cast<std::size_t>(m));
    kairn::upward::mul(View<double>(z, zn, static_cast<std::size_t>(m)), kairn::unverified(v), v);
}

const void* units::zero_address() noexcept {
#if defined(KAIRN_DETAIL_UPWARD_MSVC)
    return &kairn::upward::detail::zero;
#else
    return nullptr;
#endif
}
