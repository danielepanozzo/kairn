// For the test programs only: a program that stops through abort(), as the checks of KAIRN_CHECKS
// make it (tests/api/checks.cpp), stops at once, with Kairn's message on the standard error and an
// exit status other than 0, and nothing else happens:
//
// - with Microsoft's C runtime, abort() and the debug runtime's own checks open a dialog that waits
//   for someone to press a button (the debug runtime, which a debug build links, does so by
//   default), and abort() may also start Windows Error Reporting: on a CI machine that waits until
//   the test's timeout. Here they print to the standard error instead, and abort() ends the
//   process with exit status 3.
// - on Linux, a core dump handed to a handler (systemd-coredump, apport) took about 0.3 seconds
//   per abort() on the Linux machine of docs/developer/testing.md; the process is made not
//   dumpable, so that none is written.
#pragma once

#if defined(_MSC_VER)
#include <crtdbg.h>
#include <cstdlib>
#elif defined(__linux__)
#include <sys/prctl.h>
#endif

namespace kairn_test {

inline void no_crash_reports() {
#if defined(_MSC_VER)
    _set_abort_behavior(0, _CALL_REPORTFAULT);
#if defined(_DEBUG)
    _CrtSetReportMode(_CRT_WARN, _CRTDBG_MODE_FILE);
    _CrtSetReportFile(_CRT_WARN, _CRTDBG_FILE_STDERR);
    _CrtSetReportMode(_CRT_ERROR, _CRTDBG_MODE_FILE);
    _CrtSetReportFile(_CRT_ERROR, _CRTDBG_FILE_STDERR);
    _CrtSetReportMode(_CRT_ASSERT, _CRTDBG_MODE_FILE);
    _CrtSetReportFile(_CRT_ASSERT, _CRTDBG_FILE_STDERR);
#endif
#elif defined(__linux__)
    prctl(PR_SET_DUMPABLE, 0, 0, 0, 0);
#endif
}

}  // namespace kairn_test
