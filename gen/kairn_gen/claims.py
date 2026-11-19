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


def kernel_claims(k, kernels):
    errors = [e for e in k.ensures if e['kind'] == 'error']
    # Always a list, one object per error entry in the order of `ensures` (second wave).
    instances = {name: [instance(e, interp.parse_format(name)) for e in errors]
                 for name in INSTANCE_FORMATS}
    return {
        'name': k.name,
        'inputs': [_group(g) for g in k.inputs],
        'outputs': [_group(g) for g in k.outputs],
        'value': k.value,
        'requires': [_requires(r) for r in k.requires],
        'ensures': [dict(e) for e in k.ensures],
        'min_precision': k.min_precision,
        'status': k.status,
        'theorem': {'file': k.theorem[0], 'name': k.theorem[1]} if k.theorem else None,
        'source': {'cite': k.source, 'license': k.license},
        'flops': ir.flops(k, kernels),
        'instances': instances,
    }


def claims(kernels):
    doc = {'schema': SCHEMA, 'kernels': [kernel_claims(k, kernels) for k in kernels.values()]}
    return json.dumps(doc, indent=2) + '\n'
