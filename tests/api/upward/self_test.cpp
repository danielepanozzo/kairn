// api.upward.self_test, .checked, .numbers and .without_options: kairn::upward::self_test() as
// this file is built (the design page, "The self-check"). Requires the rounding mode upward set by
// kairn::upward::Scope and the options of docs/concepts/upward.md (GCC and Clang -frounding-math,
// MSVC /fp:strict): built with kairn::upward, but api.upward.self_test.without_options, which tests
// a file built without them (Clang only, where the header compiles without them; a release build,
// whose scopes do not check the build).
//
// - It passes (ok()), from rounding to nearest, inside a kairn::upward::Scope, inside a
//   NearestScope, and with the mode downward and flush to zero set by hand before the call.
// - It restores the caller's state each time: the register's mode and flush bits and the C
//   library's mode are what they were before the call.
// - Built without the options (UPWARD_TEST_WITHOUT_OPTIONS), it still passes, the header's
//   operations being right through their barriers, and its advice says that this file's own
//   arithmetic ignores the mode. With the options, its advice is printed and not checked: a product
//   of the file's own code contracted into a sum is advice that the default flags of GCC and Clang
//   give on most targets.
#include <kairn/upward.hpp>

#include "environment.hpp"

#include <cstring>

using namespace upward_test;

namespace {

char line[768];

struct State {
    int library;
    int mode;
    unsigned long long flush;
};
State state() {
    return {std::fegetround(), register_mode(), static_cast<unsigned long long>(register_flush())};
}
bool same(const State& a, const State& b) { return a.library == b.library && a.mode == b.mode && a.flush == b.flush; }

void call(const char* where) {
    const State before = state();
    const kairn::Status s = kairn::upward::self_test();
    const State after = state();
    std::snprintf(line, sizeof line, "self_test() %s: %s%s%s", where, s.message(), s.kernel ? ": " : "",
                  s.kernel ? s.kernel : "");
    expect(s.ok(), line);
    std::snprintf(line, sizeof line, "self_test() %s restores the caller's state (C library %s, register %s, flush bits %llx)",
                  where, mode_name(after.library), mode_name(after.mode), after.flush);
    expect(same(before, after), line);
    std::printf("note  : advice %s: %s\n", where, s.limitation ? s.limitation : "none");
#if defined(UPWARD_TEST_WITHOUT_OPTIONS)
    std::snprintf(line, sizeof line, "self_test() %s, built without the options, advises that the file's own arithmetic "
                  "ignores the mode", where);
    expect(s.limitation && std::strstr(s.limitation, "ignores the rounding mode"), line);
#endif
}

}  // namespace

int main() {
    std::printf("note  : KAIRN_UPWARD_FORM %d, KAIRN_UPWARD_ARRAYS %d, KAIRN_UPWARD_MAX_NM %d, KAIRN_CHECKS %d\n",
                KAIRN_UPWARD_FORM, KAIRN_UPWARD_ARRAYS, KAIRN_UPWARD_MAX_NM, KAIRN_CHECKS);
    call("from rounding to nearest");
    {
        kairn::upward::Scope s;
        call("inside a Scope");
        {
            kairn::upward::NearestScope n;
            call("inside a NearestScope inside a Scope");
        }
    }
    set_environment(FE_DOWNWARD, true);
    call("with the mode downward and flush to zero set by hand");
    set_environment(FE_TONEAREST, false);
#if defined(UPWARD_TEST_WITHOUT_OPTIONS)
    return summary("api.upward.self_test.without_options");
#else
    return summary("api.upward.self_test");
#endif
}
