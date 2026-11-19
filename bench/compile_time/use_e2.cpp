// kairn/kairn.hpp, and every public operation of Expansion<double, 2> and Ball<double, 2> once,
// each in a function of its own (use.hpp; bench/compile_time.py).
#include "use.hpp"

template struct kct::UseE2<double>;
template struct kct::UseBall<double, 2>;

KCT_NOINLINE bool kct_environment_ok() { return kairn::environment_ok(); }
