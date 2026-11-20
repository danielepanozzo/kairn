#!/usr/bin/env python3
"""What the generator's rules (gen/kairn_gen/rules.py) say today of the proposed kernels: those
of kernels/, and those of the first wave that the generator now has (gen/kernels).

The descriptions of kernels/ carry no claims: the statements of this milestone need vocabulary
that the generator does not have yet. What is checked of them is the rest: single assignment, the
rules R1 to R3, the non-finite cone, kinds and arity. Those in gen/kernels have their claims, and
pass every rule. Also printed: the operations of each kernel after inlining, which is what the
page counts.
"""
import os
import sys
from collections import Counter

from common import HERE, KERNELS, ir, rules

# The proposals of the page that are in gen/kernels now, with their claims: wave 1, the bound
# kernels of the folds' stage, and the kernels of the intervals of wave 2 so far.
IN_GEN = ('two_sum_ord', 'add_down_1', 'add_up_1', 'sub_down_1', 'sub_up_1', 'mul_down_1', 'mul_up_1',
          'ball_mul_pow2_1', 'ball_mul_pow2_2', 'bound_sum_2', 'bound_dot_2', 'bound_dot_1',
          'mul_dir_1', 'interval_make_1', 'interval_neg_1', 'interval_add_1', 'interval_sub_1', 'interval_mul_1',
          'add_ball_2_2', 'mul_ball_2_2', 'add_down_2_2', 'add_up_2_2', 'mul_dir_2_2', 'interval_add_2',
          'ball_from_interval_2',
          # and of its stage B1: the product of intervals of two limbs, and two of the enclosure interface.
          'mul_ext_2_2', 'interval_mul_2', 'interval_mid_rad_1', 'ball_to_interval_1',
          # and the accumulator, acc_radius_k as proposed here (accumulator.py).
          'acc_add_1', 'acc_add_2', 'acc_mul_1', 'acc_mul_2', 'acc_merge_1', 'acc_merge_2', 'acc_radius_1',
          'acc_radius_2',
          # and the radii of BallVector, bv_add_radius_2 and bv_scale_radius_2 as proposed here, with
          # their forms of one limb.
          'bv_add_radius_1', 'bv_add_radius_2', 'bv_scale_radius_1', 'bv_scale_radius_2')


def main():
    here = sorted(fn[:-7] for fn in os.listdir(os.path.join(HERE, 'kernels')) if fn.endswith('.kernel'))
    mine = sorted(here + list(IN_GEN))
    errors = rules.check_all(KERNELS)
    assert all(e.kernel in here for e in errors), [str(e) for e in errors if e.kernel not in here]
    # The claims are left out on purpose, and with them the rule that a kernel names its theorem.
    claims = [e for e in errors if e.rule.startswith('claims')]
    refused = [e for e in errors if e not in claims]
    for e in refused:
        print('refused:', e)
    print(f'{len(mine)} kernel descriptions ({len(IN_GEN)} of them in gen/kernels, with their claims); '
          f'{len(claims)} remarks that a description has no claim (expected); {len(refused)} refusals by '
          'the other rules (single assignment, R1, R2, R3, the non-finite cone, kinds, constants)')
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
