// kairn/kairn.hpp and one call of kairn::self_test(), which runs every generated kernel for both
// limb types: what the one translation unit of a program that calls it at startup pays
// (bench/compile_time.py).
#include <kairn/kairn.hpp>

bool kct_self_test() { return kairn::self_test().ok(); }
