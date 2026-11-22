#!/usr/bin/env python3
"""entry_check.py: a copy of the headers without the check of the environment at the batch entries.

    python3 bench/entry_check.py copy DEST

Every function of kairn/batch.hpp and every operation on whole ball vectors reads the floating-point
environment at entry, in every build (detail::check_batch_environment, include/kairn/environment.hpp),
and the headers have no macro to leave it out. To measure what it costs, this script copies
include/kairn to DEST/kairn and replaces, in the copy only, the body of check_batch_environment with
`return true;`, so that nothing is read; it refuses if the function in include/ is not the one it
expects. kairn-bench-m2-nocheck-LEVEL is the harness of Milestone 2 built against the copy
(-DKAIRN_BENCH_NOCHECK_INCLUDE=DEST, bench/CMakeLists.txt); the copy is never committed, and nothing
under include/ changes. bench/README.md, "Milestone 2", third part, says how the two programs are
compared. Standard library only.
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


def copy(dest):
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
    open(path, 'w').write(text.replace(BODY, NOCHECK))
    print('wrote %s (check_batch_environment compiled out in the copy of environment.hpp)' % out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    c = sub.add_parser('copy')
    c.add_argument('dest')
    a = ap.parse_args()
    if a.cmd == 'copy':
        copy(a.dest)
    return 0


if __name__ == '__main__':
    sys.exit(main())
