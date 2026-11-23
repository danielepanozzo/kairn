// kairn::self_test() and kairn::environment_ok() compiled with this file's flags: prints the
// self-test's message. With a flag that the headers refuse, this file does not compile.
//   c++ -std=c++20 -O2 <flags> -I<kairn>/include self_test.cpp && ./a.out
#include <kairn/kairn.hpp>

#include <cstdio>

int main() {
    const kairn::Status s = kairn::self_test();
    std::printf("self_test: %s%s%s; environment_ok: %s\n", s.message(), s.kernel ? ": " : "", s.kernel ? s.kernel : "",
                kairn::environment_ok() ? "true" : "false");
    return s.ok() ? 0 : 1;
}
