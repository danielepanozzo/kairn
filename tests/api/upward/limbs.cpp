// api.upward.limbs.O2, api.upward.limbs.O3 (api.upward.limbs with MSVC): Interval<T>::from_limbs
// and to_limbs on an array that the program also reads and writes as T around the call, built at
// -O2 and at -O3 whatever the build's flags (the design page, "The interface"). Requires the
// rounding mode upward set by kairn::upward::Scope and the options of docs/concepts/upward.md (GCC
// and Clang -frounding-math, MSVC /fp:strict): built with kairn::upward.
//
// The case a user meets: one load or store of the register, of two floats through a pointer of
// another type, which GCC's type-based alias analysis took apart from the float accesses of the
// same array (an earlier form of gen/upward.hpp loaded and stored the two floats of the x86-64 form
// as a double: with GCC 13 at -O2 and -O3, a float written before to_limbs read back the old value
// after it). Each probe is a function of its own, not inlined into main, in which the stores and
// loads of T and the call are all visible to the compiler, for float and double: a store of T,
// from_limbs, and the state read back; a store of T, to_limbs over it, and a load of T; and an
// array of pairs updated in place, element by element, through from_limbs, an operation and
// to_limbs, read back as T.
#include <kairn/upward.hpp>

#include "environment.hpp"

using namespace upward_test;

namespace {

template <class T>
using I = kairn::upward::Interval<T>;

// A store of T, from_limbs of the same array, and the state written to another: what was stored.
template <class T>
KAIRN_DETAIL_NOINLINE bool load_after_store(T* buf, T u, T n) {
    buf[0] = u;
    buf[1] = n;
    const I<T> x = I<T>::from_limbs(buf);
    T out[2] = {};
    x.to_limbs(out);
    return same_bits(out[0], u) && same_bits(out[1], n);
}
// A store of T, to_limbs over it, and a load of T: what to_limbs wrote.
template <class T>
KAIRN_DETAIL_NOINLINE bool read_after_store(T* buf, const I<T>& x, T u, T n) {
    buf[0] = T(7);
    buf[1] = T(9);
    x.to_limbs(buf);
    return same_bits(buf[0], u) && same_bits(buf[1], n);
}
// An array of pairs, each written as T, loaded, negated (an exact operation), stored in place and
// read back as T.
template <class T>
KAIRN_DETAIL_NOINLINE bool in_place(T* pairs, int count) {
    bool ok = true;
    for (int i = 0; i < count; ++i) {
        pairs[2 * i] = T(i + 2);
        pairs[2 * i + 1] = T(-i - 1);
        const I<T> x = I<T>::from_limbs(pairs + 2 * i);
        (-kairn::unverified(x)).to_limbs(pairs + 2 * i);
        ok = ok && pairs[2 * i] == T(-i - 1) && pairs[2 * i + 1] == T(i + 2);
    }
    return ok;
}

template <class T>
void probes(const char* name) {
    volatile T vu = T(3), vn = T(-1);
    const T u = vu, n = vn;
    T buf[2] = {T(0), T(0)};
    char what[160];
    std::snprintf(what, sizeof what, "%s: a store of T, then from_limbs of the same array", name);
    expect(load_after_store<T>(buf, u, n), what);
    T src[2] = {u, n};
    const I<T> x = I<T>::from_limbs(src);
    std::snprintf(what, sizeof what, "%s: a store of T, then to_limbs over it, then a load of T", name);
    expect(read_after_store<T>(buf, x, u, n), what);
    T pairs[2 * 9] = {};
    std::snprintf(what, sizeof what, "%s: an array of pairs updated in place through from_limbs and to_limbs", name);
    expect(in_place<T>(pairs, 9), what);
}

}  // namespace

int main() {
    probes<float>("float");
    probes<double>("double");
    return summary("api.upward.limbs");
}
