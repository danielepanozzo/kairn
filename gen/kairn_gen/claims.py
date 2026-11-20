"""gen/claims.json: what every kernel claims (architecture.md, "Claims").

The only thing the oracle and the documentation learn from the generator. The constants of each
error claim are also given per named format as exact fractions, computed here with the parser of
expr.py, so that the oracle never evaluates a `c` itself.
"""
import json
from fractions import Fraction

from . import expr, interp, ir

SCHEMA = 1
INSTANCE_FORMATS = ('binary64', 'binary32')


def _requires(r):
    return f'{r[0]}({", ".join(r[1:])})'


def instance(entry, fmt):
    """rel = c u^k and abs = t eta of one error entry, in format fmt, as exact fractions."""
    u = Fraction(1, 2 ** fmt.p)
    eta = Fraction(2) ** fmt.qmin
    rel = expr.evaluate(expr.parse(entry['c']), {'u': u}) * u ** entry['k']
    return {'rel': str(rel), 'abs': str(expr.evaluate(expr.parse(entry['t']), {}) * eta)}


def _group(g):
    # A limb group has no type, the default; a mask says so.
    out = {'name': g.name, 'limbs': len(g.limbs)}
    if g.kind == ir.MASK:
        out['type'] = 'mask'
    return out


def _theorem(t):
    return {'file': t[0], 'name': t[1]} if t else None


def kernel_claims(k, kernels):
    """One kernel's entry. A kernel of the extended domain (architecture.md, "Claims of the
    non-finite layer") says so with `domain`, and gives `ieee_status`, and `ieee_theorem` once
    that is proved; one of the finite domain has neither field, as before. A kernel without a
    real-model statement (ir.Kernel.real_model: the full kernels, the full Ball kernels, the
    constructors) says so with `"ieee_only": true` after `domain`; every other kernel has no such
    field. A kernel that makes a ball from its inputs has no `value`."""
    errors = [e for e in k.ensures if e['kind'] == 'error']
    # Always a list, one object per error entry in the order of `ensures` (second wave).
    instances = {name: [instance(e, interp.parse_format(name)) for e in errors]
                 for name in INSTANCE_FORMATS}
    out = {'name': k.name}
    if k.extended:
        out['domain'] = 'extended'
    if not k.real_model:
        out['ieee_only'] = True
    out.update(inputs=[_group(g) for g in k.inputs], outputs=[_group(g) for g in k.outputs])
    if k.value is not None:
        out['value'] = k.value
    out.update(requires=[_requires(r) for r in k.requires], ensures=[dict(e) for e in k.ensures],
               min_precision=k.min_precision, status=k.status)
    if k.extended:
        out['ieee_status'] = k.ieee_status
    out['theorem'] = _theorem(k.theorem)
    if k.ieee_theorem:
        out['ieee_theorem'] = _theorem(k.ieee_theorem)
    out.update(source={'cite': k.source, 'license': k.license}, flops=ir.flops(k, kernels),
               instances=instances)
    return out


# The lanes of the registers of the packed forms (simd.py): the number W of the lane order that
# F_packed computes, per format and backend. The claims hold for every W; these are the ones the
# library's packed code uses, which a judge should see most.
PACKED_LANES = {'binary64': {'avx2': 4, 'neon': 2}, 'binary32': {'avx2': 8, 'neon': 4}}


def fold_instance(entry, fmt, kernels):
    """eps, term and tau of a fold_error entry, in format fmt, as exact fractions."""
    from . import consts
    return {key: str(consts.evaluate(expr.parse(entry[key]), kernels, fmt.p, fmt.qmin)) for key in ('eps', 'term', 'tau')}


def fold_claims(fd, kernels):
    """One fold's entry (architecture.md, "Claims of Milestone 2", folds): the arrays and their
    roles, the results, the value of an element, the requirements of each element, the claims
    with the heights of the bound per order, the parts, the orders and the lanes of the packed
    forms, the statuses."""
    errors = [e for e in fd.ensures if e['kind'] == 'fold_error']
    out = {'name': fd.name}
    if fd.extended:
        out['domain'] = 'extended'
    out['arrays'] = [{'name': g.name, 'limbs': len(g.limbs), 'role': fd.roles[g.name]} for g in fd.arrays]
    out['outputs'] = [_group(g) for g in fd.results()]
    out['value'] = fd.value
    out['requires'] = [_requires(r) for r in fd.requires]
    ensures = []
    for e in fd.ensures:
        if e['kind'] == 'fold_error':
            ensures.append({'kind': 'fold_error', 'of': e['of'], 'eps': e['eps'], 'term': e['term'], 'tau': e['tau'],
                            'heights': {order: {'rel': e['rel'], 'abs': e['abs']} for order in fd.orders}})
        else:
            ensures.append(dict(e))
    out['ensures'] = ensures
    out['orders'] = list(fd.orders)
    out['packed_lanes'] = PACKED_LANES
    out['step'] = fd.step[0]
    out['combine'] = fd.combine[0] if fd.combine else None
    out['finish'] = fd.finish[0] if fd.finish else None
    out['min_precision'] = fd.min_precision
    out['status'] = fd.status
    out['theorems'] = {order: ({'file': fd.theorem, 'name': fd.theorem_name(order)} if fd.theorem else None)
                       for order in fd.orders}
    out['source'] = {'cite': fd.source, 'license': fd.license}
    out['instances'] = {name: [fold_instance(e, interp.parse_format(name), kernels) for e in errors]
                        for name in INSTANCE_FORMATS}
    return out


def claims(kernels):
    doc = {'schema': SCHEMA, 'kernels': [kernel_claims(k, kernels) for k in kernels.values()]}
    folds = getattr(kernels, 'folds', {})
    if folds:
        doc['folds'] = [fold_claims(fd, kernels) for fd in folds.values()]
    return json.dumps(doc, indent=2) + '\n'
