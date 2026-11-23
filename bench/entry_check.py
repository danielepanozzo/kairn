#!/usr/bin/env python3
"""entry_check.py: copies of the headers for the measurement of the check of the environment at the batch entries.

    python3 bench/entry_check.py copy DEST            the headers without the check
    python3 bench/entry_check.py inline DEST LIMBS    the headers with another bound of forced inlining
    python3 bench/entry_check.py before DEST [--commit C]   the headers of an earlier commit
    python3 bench/entry_check.py check                whether the header has the expected form

Every function of kairn/batch.hpp and every operation on whole ball vectors reads the floating-point
environment at entry, in every build (detail::check_batch_environment, include/kairn/environment.hpp),
and the headers have no macro to leave it out. To measure what it costs, `copy` copies include/kairn
to DEST/kairn and replaces, in the copy only, the body of check_batch_environment with `return true;`,
so that nothing is read; it refuses if the function in include/ is not the one it expects (`check`
says whether it is). kairn-bench-m2-nocheck-LEVEL is the harness of Milestone 2 built against the copy
(-DKAIRN_BENCH_NOCHECK_INCLUDE=DEST, bench/CMakeLists.txt); the copy is never committed, and nothing
under include/ changes.

Since 2026-11-23 the header has the form that this script's variant `cold` wrote into a copy on
2026-11-22 (the third part of the benchmarks of Milestone 2): one read of the control register and
one test of a mask on the hot path, the message and the call of KAIRN_ENVIRONMENT_FAILURE in a
function of their own, never inlined and cold (detail::report_environment). The variant is gone; the
header itself is what `check` verifies. `inline DEST LIMBS` copies include/kairn with the check kept
and the bound of the forced inlining of the short constructors of BallVector (ball_vector.hpp,
detail::bv_inline_limbs) set to LIMBS: 0 forces none, a large number every size; kairn-bench-m2-NAME-LEVEL
is the harness built against such a copy (-DKAIRN_BENCH_EXTRA_INCLUDES=NAME=DEST). `before DEST` writes DEST/kairn from include/kairn of an
earlier commit (by default 25ebe3d6, the last with the report inline at every check), read with
`git archive` from this repository: -DKAIRN_BENCH_BEFORE_INCLUDE=DEST builds kairn-bench-m2-before-LEVEL
against it, the harness of this tree with the headers as they were. bench/README.md, "Milestone 2",
third part, says how the programs are compared. Standard library and git only.
"""
import argparse
import io
import re
import os
import shutil
import subprocess
import sys
import tarfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BODY = '''KAIRN_FORCEINLINE constexpr bool check_batch_environment(bool rounding = true) noexcept {
    bool ok = true;
    if (!__builtin_is_constant_evaluated()) ok = environment_checked(rounding);
    return ok;
}'''

NOCHECK = '''KAIRN_FORCEINLINE constexpr bool check_batch_environment(bool rounding = true) noexcept {
    // bench/entry_check.py: the check of the environment at the batch entries compiled out, for the
    // measurement of what it costs. Not the library's code.
    (void)rounding;
    return true;
}'''

# The report out of line and cold, which `check` also requires.
REPORT = '''KAIRN_DETAIL_COLD inline void report_environment(std::uint64_t b) noexcept {
    KAIRN_ENVIRONMENT_FAILURE(environment_message(b));
}'''

BEFORE = '25ebe3d6'

# The bound of forced inlining (ball_vector.hpp), which `inline` replaces in its copy.
BOUND = re.compile(r'^inline constexpr std::size_t bv_inline_limbs = \d+;$', re.M)


def header():
    return open(os.path.join(ROOT, 'include', 'kairn', 'environment.hpp')).read()


def check():
    text = header()
    ok = text.count(BODY) == 1 and text.count(REPORT) == 1
    print('include/kairn/environment.hpp: check_batch_environment %s' %
          ('has the expected form (one read and one test, the report out of line and cold)' if ok
           else 'is not the expected one: update bench/entry_check.py'))
    return 0 if ok else 1


def copy(dest):
    if check() != 0:
        sys.exit(1)
    src = os.path.join(ROOT, 'include', 'kairn')
    out = os.path.join(dest, 'kairn')
    if os.path.exists(out):
        sys.exit('%s exists: give an empty directory' % out)
    shutil.copytree(src, out)
    path = os.path.join(out, 'environment.hpp')
    text = open(path).read()
    open(path, 'w').write(text.replace(BODY, NOCHECK))
    print('wrote %s (check_batch_environment compiled out in the copy of environment.hpp)' % out)


def inline(dest, limbs):
    if check() != 0:
        sys.exit(1)
    src = os.path.join(ROOT, 'include', 'kairn')
    out = os.path.join(dest, 'kairn')
    if os.path.exists(out):
        sys.exit('%s exists: give an empty directory' % out)
    shutil.copytree(src, out)
    path = os.path.join(out, 'ball_vector.hpp')
    text = open(path).read()
    if len(BOUND.findall(text)) != 1:
        sys.exit('detail::bv_inline_limbs in include/kairn/ball_vector.hpp is not the expected one: update bench/entry_check.py')
    open(path, 'w').write(BOUND.sub('inline constexpr std::size_t bv_inline_limbs = %d;' % limbs, text))
    print('wrote %s (detail::bv_inline_limbs = %d in the copy of ball_vector.hpp)' % (out, limbs))


def before(dest, commit):
    out = os.path.join(dest, 'kairn')
    if os.path.exists(out):
        sys.exit('%s exists: give an empty directory' % out)
    data = subprocess.run(['git', '-C', ROOT, 'archive', '--format=tar', commit, 'include/kairn'],
                          check=True, capture_output=True).stdout
    os.makedirs(out)
    with tarfile.open(fileobj=io.BytesIO(data)) as t:
        for m in t.getmembers():
            if m.isfile() and m.name.startswith('include/kairn/'):
                rel = m.name[len('include/kairn/'):]
                path = os.path.join(out, rel)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, 'wb') as f:
                    f.write(t.extractfile(m).read())
    print('wrote %s (include/kairn of %s)' % (out, commit))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    c = sub.add_parser('copy')
    c.add_argument('dest')
    i = sub.add_parser('inline')
    i.add_argument('dest')
    i.add_argument('limbs', type=int)
    b = sub.add_parser('before')
    b.add_argument('dest')
    b.add_argument('--commit', default=BEFORE)
    sub.add_parser('check')
    a = ap.parse_args()
    if a.cmd == 'copy':
        copy(a.dest)
    elif a.cmd == 'inline':
        inline(a.dest, a.limbs)
    elif a.cmd == 'before':
        before(a.dest, a.commit)
    else:
        return check()
    return 0


if __name__ == '__main__':
    sys.exit(main())
