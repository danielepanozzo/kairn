#!/usr/bin/env python3
"""entry_check.py: a copy of the headers without the check of the environment at the batch entries.

    python3 bench/entry_check.py copy DEST [--variant nocheck|cold]

Every function of kairn/batch.hpp and every operation on whole ball vectors reads the floating-point
environment at entry, in every build (detail::check_batch_environment, include/kairn/environment.hpp),
and the headers have no macro to leave it out. To measure what it costs, this script copies
include/kairn to DEST/kairn and replaces, in the copy only, the body of check_batch_environment with
`return true;`, so that nothing is read; it refuses if the function in include/ is not the one it
expects. kairn-bench-m2-nocheck-LEVEL is the harness of Milestone 2 built against the copy
(-DKAIRN_BENCH_NOCHECK_INCLUDE=DEST, bench/CMakeLists.txt); the copy is never committed, and nothing
under include/ changes. bench/README.md, "Milestone 2", third part, says how the two programs are
compared. With --variant cold the check is kept and only its report moves: the hot path is one read
of the register and one test of a mask, and the message and the call of KAIRN_ENVIRONMENT_FAILURE are
in a function of their own, out of line and cold (-DKAIRN_BENCH_COLD_INCLUDE=DEST builds
kairn-bench-m2-cold-LEVEL against it): a candidate change of the header, measured, not made.
Standard library only.
"""
import argparse
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BODY = '''KAIRN_FORCEINLINE constexpr bool check_batch_environment(bool rounding = true) noexcept {
    bool ok = true;
    if (!__builtin_is_constant_evaluated()) {
        if (const char* problem = environment_problem(rounding)) {
            ok = false;
            KAIRN_ENVIRONMENT_FAILURE(problem);
        }
    }
    return ok;
}'''

NOCHECK = '''KAIRN_FORCEINLINE constexpr bool check_batch_environment(bool rounding = true) noexcept {
    // bench/entry_check.py: the check of the environment at the batch entries compiled out, for the
    // measurement of what it costs. Not the library's code.
    (void)rounding;
    return true;
}'''


# --variant cold: the check kept, its hot path one read of the register and one test of a mask, the
# message and the call of KAIRN_ENVIRONMENT_FAILURE moved into a function of their own that is out of
# line and cold. A candidate change of the header, measured against the header as it is (bench-
# milestone2.md, question 14); not the library's code.
COLD = '''// bench/entry_check.py, --variant cold: the bits of the control register that differ from the
// default environment (0 when it is the default one), one read and one test.
KAIRN_FORCEINLINE unsigned long long environment_bits(bool rounding) noexcept {
#if defined(KAIRN_DETAIL_MXCSR)
    return _mm_getcsr() & (rounding ? 0xE040u : 0x8040u);
#elif defined(KAIRN_DETAIL_FPCR)
#if defined(__clang__)
    const std::uint64_t fpcr = __builtin_arm_rsr64("fpcr");
#else
    const std::uint64_t fpcr = __builtin_aarch64_get_fpcr64();
#endif
    return fpcr & ((rounding ? (std::uint64_t{3} << 22) : 0) | (std::uint64_t{1} << 24) | std::uint64_t{3});
#else
    return environment_problem(rounding) != nullptr;
#endif
}
// The report, out of line and cold: the message, and KAIRN_ENVIRONMENT_FAILURE.
[[gnu::cold, gnu::noinline]] inline void batch_environment_report(bool rounding) noexcept {
    if (const char* problem = environment_problem(rounding)) KAIRN_ENVIRONMENT_FAILURE(problem);
}
KAIRN_FORCEINLINE constexpr bool check_batch_environment(bool rounding = true) noexcept {
    bool ok = true;
    if (!__builtin_is_constant_evaluated()) {
        if (__builtin_expect(environment_bits(rounding) != 0, 0)) {
            ok = false;
            batch_environment_report(rounding);
        }
    }
    return ok;
}'''


def copy(dest, variant='nocheck'):
    src = os.path.join(ROOT, 'include', 'kairn')
    out = os.path.join(dest, 'kairn')
    if os.path.exists(out):
        sys.exit('%s exists: give an empty directory' % out)
    shutil.copytree(src, out)
    path = os.path.join(out, 'environment.hpp')
    text = open(path).read()
    if text.count(BODY) != 1:
        sys.exit('check_batch_environment in include/kairn/environment.hpp is not the expected one: '
                 'update bench/entry_check.py')
    open(path, 'w').write(text.replace(BODY, NOCHECK if variant == 'nocheck' else COLD))
    print('wrote %s (check_batch_environment %s in the copy of environment.hpp)'
          % (out, 'compiled out' if variant == 'nocheck' else 'with its report out of line and cold'))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    c = sub.add_parser('copy')
    c.add_argument('dest')
    c.add_argument('--variant', choices=['nocheck', 'cold'], default='nocheck')
    a = ap.parse_args()
    if a.cmd == 'copy':
        copy(a.dest, a.variant)
    return 0


if __name__ == '__main__':
    sys.exit(main())
