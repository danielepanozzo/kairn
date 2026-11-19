// kairn/kairn.hpp, and every public operation of Expansion<T, K> and Ball<T, K> once, each in a
// function of its own, for T float and double and K one and two (use.hpp;
// bench/compile_time.py).
#include "use.hpp"

template struct kct::UseE1<float>;
template struct kct::UseE1<double>;
template struct kct::UseE2<float>;
template struct kct::UseE2<double>;
template struct kct::UseBall<float, 1>;
template struct kct::UseBall<double, 1>;
template struct kct::UseBall<float, 2>;
template struct kct::UseBall<double, 2>;

KCT_NOINLINE bool kct_environment_ok() { return kairn::environment_ok(); }
