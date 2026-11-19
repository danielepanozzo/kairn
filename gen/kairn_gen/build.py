"""What `build` writes and what `check` compares, paths relative to the repository root."""
import os

from . import claims, cpp, ir, library, rocq, rules, simd

# Every file in these directories must be one that build writes.
GENERATED_DIRS = ('proofs/gen', 'include/kairn/gen')


def load(root, kernel_dir=None):
    """The kernels and every refusal of the rules (an empty list when all are accepted)."""
    kernels = ir.load_kernels(kernel_dir or os.path.join(root, 'gen', 'kernels'))
    return kernels, rules.check_all(kernels)


def outputs(kernels):
    return {
        'proofs/gen/Model.v': rocq.model(kernels),
        'proofs/gen/Statements.v': rocq.statements(kernels),
        'proofs/gen/Audit.v': rocq.audit(kernels),
        'include/kairn/gen/prelude.hpp': cpp.prelude(kernels),
        'include/kairn/gen/scalar.hpp': cpp.scalar(kernels),
        'include/kairn/gen/avx2.hpp': simd.header(simd.AVX2, kernels),
        'include/kairn/gen/neon.hpp': simd.header(simd.NEON, kernels),
        'include/kairn/gen/bounds.hpp': library.bounds(kernels),
        'include/kairn/gen/selftest.hpp': library.selftest(kernels),
        'gen/claims.json': claims.claims(kernels),
        'gen/tests/runner_kernels.inc': cpp.runner_table(kernels),
    }


def _read(path):
    with open(path, encoding='utf-8', newline='') as f:
        return f.read().replace('\r\n', '\n')   # a checkout with CRLF line ends is still fresh


def write(root, files):
    """Writes every file whose content changed; returns [(path, 'written' or 'unchanged')]."""
    done = []
    for rel, text in files.items():
        path = os.path.join(root, rel)
        if os.path.exists(path) and _read(path) == text:
            done.append((rel, 'unchanged'))
            continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)
        done.append((rel, 'written'))
    return done


def compare(root, files):
    """[(problem, path)] for every committed file that differs from what build would write."""
    problems = []
    for rel, text in files.items():
        path = os.path.join(root, rel)
        if not os.path.exists(path):
            problems.append(('missing', rel))
        elif _read(path) != text:
            problems.append(('differs', rel))
    for d in GENERATED_DIRS:
        top = os.path.join(root, d)
        for dirpath, _, names in os.walk(top) if os.path.isdir(top) else ():
            for n in names:
                rel = os.path.relpath(os.path.join(dirpath, n), root).replace(os.sep, '/')
                if rel not in files and not _ignored(n):
                    problems.append(('not generated', rel))
    return sorted(problems, key=lambda p: p[1])


def _ignored(name):
    # Build products of Rocq next to the generated sources, and editor or OS litter.
    return name.startswith('.') or name.endswith(('.vo', '.vok', '.vos', '.glob', '.aux'))


def summary(kernels):
    """The lines build prints about the kernels: what is unverified, not constexpr, exempt."""
    def names(pred):
        found = [k.name for k in kernels.values() if pred(k)]
        return ', '.join(found) if found else 'none'
    return [
        f'kernels: {len(kernels)}',
        f'UNVERIFIED: {names(lambda k: k.status == "unverified")}',
        f'not constexpr: {names(lambda k: cpp.constexpr_kind(k, kernels) is None)}',
        f'constexpr through a constant-evaluation variant: '
        f'{", ".join(f"{k.name} ({k.ce_variant})" for k in kernels.values() if k.ce_variant) or "none"}',
        f'exempt from the non-finite cone: {names(lambda k: bool(k.cone_exempt))}',
    ]
