// The consumer checks' program of kairn::upward (tests/CMakeLists.txt): <kairn/upward.hpp>, which
// requires the rounding mode upward set by kairn::upward::Scope and the options of
// docs/concepts/upward.md (GCC and Clang -frounding-math, MSVC /fp:strict). It compiles only if
// linking kairn::upward (with kairn::fma) is enough to include the header: kairn::upward links
// kairn::kairn, and its option is what lets the header compile with GCC and MSVC, whose guard
// stops the build without it. The consumer checks build it; they run only consume.cpp.
#include <kairn/upward.hpp>

int main() {
    volatile double a = 1.0, b = 0x1p-60;
    volatile double sum = 0;
    {
        kairn::upward::Scope scope;
        sum = kairn::upward::pass(a + b);
    }
    return sum > 1 ? 0 : 1;
}
