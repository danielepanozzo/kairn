#!/usr/bin/env python3
"""What the generator's rules (gen/kairn_gen/rules.py) say today of the kernels of kernels/.

The descriptions carry no claims: the statements of this milestone need vocabulary that the
generator does not have yet. What is checked is the rest: single assignment, the rules R1 to R3,
the non-finite cone, kinds and arity. Also printed: the operations of each kernel after inlining,
which is what the page counts.
"""
import os
import sys
from collections import Counter

from common import HERE, KERNELS, ir, rules


def main():
    mine = sorted(fn[:-7] for fn in os.listdir(os.path.join(HERE, 'kernels')) if fn.endswith('.kernel'))
    errors = rules.check_all(KERNELS)
    assert all(e.kernel in mine for e in errors), [str(e) for e in errors if e.kernel not in mine]
    # The claims are left out on purpose, and with them the rule that a kernel names its theorem.
    claims = [e for e in errors if e.rule.startswith('claims')]
    refused = [e for e in errors if e not in claims]
    for e in refused:
        print('refused:', e)
    print(f'{len(mine)} kernel descriptions; {len(claims)} remarks that a description has no claim '
          f'(expected); {len(refused)} refusals by the other rules (single assignment, R1, R2, R3, the '
          'non-finite cone, kinds, constants)')
    print()
    print(f'{"kernel":22} operations after inlining')
    for name in mine:
        ops = Counter(p.op for p in ir.prims(KERNELS[name], KERNELS))
        flops = sum(n for op, n in ops.items() if op in ('add', 'sub', 'fma', 'fms', 'fnma', 'prod', 'guard'))
        steps = ops.get('succ', 0) + ops.get('pred', 0)
        rest = sum(ops.values()) - flops - steps
        print(f'{name:22} {flops:3} rounded operations, {steps} steps to a neighbor, {rest:3} '
              'comparisons, selects, sign and mask operations')
    return 0


if __name__ == '__main__':
    sys.exit(main())
