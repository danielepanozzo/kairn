"""build writes what check compares; check catches stale, hand-edited, missing and stray files."""
import os
import shutil
import subprocess
import sys
import unittest

import common
from kairn_gen import build


def copy_generator(dst):
    """A repository with only the generator in it, so that its kairn-gen works on dst."""
    shutil.copytree(common.GEN, os.path.join(dst, 'gen'),
                    ignore=shutil.ignore_patterns('__pycache__', 'claims.json', 'runner_kernels.inc'))


def kairn_gen(root, *args):
    return subprocess.run([sys.executable, os.path.join(root, 'gen', 'kairn-gen'), *args],
                          capture_output=True, text=True)


class Check(unittest.TestCase):
    def test_the_committed_files_are_fresh(self):
        problems = build.compare(common.ROOT, build.outputs(common.kernels()))
        self.assertEqual(problems, [], 'run python3 gen/kairn-gen build')

    def test_build_then_check_then_edit(self):
        root = common.scratch('check')
        copy_generator(root)
        r = kairn_gen(root, 'check')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('include/kairn/gen/scalar.hpp: missing', r.stderr)
        r = kairn_gen(root, 'build')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('UNVERIFIED: ', r.stdout)
        self.assertIn('not constexpr: ', r.stdout)
        # The pending guards of rule R3, and what is accepted only through them, are printed: none.
        self.assertIn('R3 GUARD PENDING: none\n', r.stdout)
        self.assertIn('accepted by R3 only through a pending guard: none\n', r.stdout)
        r = kairn_gen(root, 'check')
        self.assertEqual(r.returncode, 0, r.stderr)

        # A hand edit of any generated file is caught, and named.
        for rel in build.outputs(common.kernels()):
            path = os.path.join(root, rel)
            with open(path, encoding='utf-8') as f:
                text = f.read()
            edited = text.replace('\n', ' \n', 1)
            self.assertNotEqual(edited, text)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(edited)
            r = kairn_gen(root, 'check')
            self.assertNotEqual(r.returncode, 0, rel)
            self.assertIn(f'{rel}: differs', r.stderr)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(text)
        self.assertEqual(kairn_gen(root, 'check').returncode, 0)

        # Windows line ends are not a difference.
        path = os.path.join(root, 'include/kairn/gen/scalar.hpp')
        with open(path, encoding='utf-8') as f:
            text = f.read()
        with open(path, 'w', encoding='utf-8', newline='\r\n') as f:
            f.write(text)
        self.assertEqual(kairn_gen(root, 'check').returncode, 0)

        # A file nobody generates, in a generated directory.
        with open(os.path.join(root, 'proofs/gen/Extra.v'), 'w') as f:
            f.write('(* hand-written *)\n')
        r = kairn_gen(root, 'check')
        self.assertIn('proofs/gen/Extra.v: not generated', r.stderr)
        os.remove(os.path.join(root, 'proofs/gen/Extra.v'))

        # A kernel description changed but not rebuilt.
        kpath = os.path.join(root, 'gen/kernels/mul_2_2.kernel')
        with open(kpath, encoding='utf-8') as f:
            text = f.read()
        with open(kpath, 'w', encoding='utf-8') as f:
            f.write(text.replace('t=3/2', 't=3'))
        r = kairn_gen(root, 'check')
        self.assertIn('gen/claims.json: differs', r.stderr)
        self.assertIn('proofs/gen/Statements.v: differs', r.stderr)
        shutil.rmtree(root)

    def test_build_refuses_a_bad_kernel_and_writes_nothing(self):
        root = common.scratch('refuse')
        copy_generator(root)
        with open(os.path.join(root, 'gen/kernels/bad.kernel'), 'w') as f:
            f.write('kernel: bad\ninput: a\noutput: s\nvalue: a\nensures: error s R c=0 k=1 t=0\n'
                    'status: proved\ns = neg(a)\n')
        r = kairn_gen(root, 'build')
        self.assertEqual(r.returncode, 1)
        self.assertIn('kernel bad, value -: rule 5', r.stderr)
        self.assertFalse(os.path.exists(os.path.join(root, 'include')))
        shutil.rmtree(root)


if __name__ == '__main__':
    unittest.main()
