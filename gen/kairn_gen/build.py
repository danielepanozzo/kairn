"""What `build` writes and what `check` compares, paths relative to the repository root."""
import os
import re

from . import claims, cpp, ieee, ir, library, objcode, rocq, rules, simd

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
        'proofs/gen/FoldModel.v': rocq.fold_model(kernels),
        'proofs/gen/FoldStatements.v': rocq.fold_statements(kernels),
        'proofs/gen/IeeeModel.v': ieee.model(kernels),
        'proofs/gen/IeeeStatements.v': ieee.statements(kernels),
        'proofs/gen/IeeeAudit.v': ieee.audit(kernels),
        'proofs/gen/IeeeFoldModel.v': ieee.fold_model(kernels),
        'proofs/gen/IeeeFoldStatements.v': ieee.fold_statements(kernels),
        'proofs/gen/IeeeWith.v': ieee.with_model(kernels),
        'include/kairn/gen/prelude.hpp': cpp.prelude(kernels),
        'include/kairn/gen/scalar.hpp': cpp.scalar(kernels),
        'include/kairn/gen/avx2.hpp': simd.header(simd.AVX2, kernels),
        'include/kairn/gen/neon.hpp': simd.header(simd.NEON, kernels),
        'include/kairn/gen/bounds.hpp': library.bounds(kernels),
        'include/kairn/gen/selftest.hpp': library.selftest(kernels),
        'gen/claims.json': claims.claims(kernels),
        'gen/constant_names.json': rocq.constant_names_file(kernels),
        'gen/objcode.json': objcode.objcode(kernels),
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


_GEN_CALL = re.compile(r'\bgen::(\w+)\(')
_CONTROL = ('if', 'for', 'while', 'switch', 'else', 'do', 'catch', 'try', 'return')
_SCOPES = re.compile(r'(?:^|[\s>])(namespace|class|struct|union|enum)\b\s*([A-Za-z_][\w:]*)?[^(){};]*$')


def _strip(text):
    """The text with comments, string and character literals and preprocessor lines blanked
    (offsets kept), for the brace scan of header_calls."""
    out, i, n = list(text), 0, len(text)
    while i < n:
        c = text[i]
        if text.startswith('//', i) or (c == '#' and text[text.rfind('\n', 0, i) + 1:i].strip() == ''):
            j = i
            while True:     # to the end of the line, and of the lines a backslash continues
                j = text.find('\n', j)
                if j < 0 or c != '#' or text[j - 1] != '\\':
                    break
                j += 1
            j = n if j < 0 else j
            out[i:j] = [ch if ch == '\n' else ' ' for ch in text[i:j]]
            i = j
        elif text.startswith('/*', i):
            j = text.find('*/', i + 2)
            j = n if j < 0 else j + 2
            out[i:j] = [ch if ch == '\n' else ' ' for ch in text[i:j]]
            i = j
        elif c in '"\'':
            j = i + 1
            while j < n and text[j] != c:
                j += 2 if text[j] == '\\' else 1
            out[i + 1:j] = ' ' * (j - i - 1)
            i = j + 1
        else:
            i += 1
    return ''.join(out)


def _signature(head):
    """name(parameters) of the function whose head (the text before its body) is `head`: the first
    line with a parenthesis that is not a template or requires line, to its matching parenthesis."""
    lines = [ln.strip() for ln in head.split('\n') if ln.strip()]
    for i, ln in enumerate(lines):
        if '(' in ln and not ln.startswith(('template', 'requires', '&&', '||')):
            text = ' '.join(lines[i:])
            open_ = text.index('(')
            m = re.search(r'(operator\s*\S+?|[A-Za-z_~]\w*)\s*$', text[:open_])
            depth, j = 0, open_
            for j in range(open_, len(text)):
                depth += {'(': 1, ')': -1}.get(text[j], 0)
                if depth == 0:
                    break
            return (m.group(1) if m else '?') + text[open_:j + 1]
    return None


def header_calls(root, kernels):
    """{name of a kernel or of a fold: sorted [header and function]}: where the public headers
    (include/kairn/*.hpp, not the generated ones) call each kernel, and each fold's loops (F_seq,
    F_lanes, F_packed), as `FILE SCOPE::NAME(PARAMETERS)` of the function whose body has the call.
    A call through a macro (gen::NAME##_2_2) is not seen."""
    loops = {f'{f}_{suffix}': f for f in getattr(kernels, 'folds', {}) for suffix in ('seq', 'lanes', 'packed')}
    found = {}
    include = os.path.join(root, 'include', 'kairn')
    for name in sorted(os.listdir(include)):
        if not name.endswith('.hpp'):
            continue
        text = _strip(_read(os.path.join(include, name)))
        stack, last = [], 0   # (kind, scope name or signature)
        events = sorted([(m.start(), 'call', m.group(1)) for m in _GEN_CALL.finditer(text)] +
                        [(i, c, None) for i, c in enumerate(text) if c in '{};'])
        for pos, what, called in events:
            if what == 'call':
                target = called if called in kernels else loops.get(called)
                if target:
                    fn = next((s for kind, s in reversed(stack) if kind == 'function'), None)
                    scope = '::'.join(s for kind, s in stack if kind == 'scope' and s not in ('kairn', ''))
                    where = f'{name} ' + (f'{scope}::' if scope else '') + (fn or '(outside a function)')
                    found.setdefault(target, set()).add(where)
                continue
            if what == '{':
                head = text[last:pos].strip()
                m = _SCOPES.search(' '.join(head.split()))
                if m and m.group(1) in ('namespace', 'class', 'struct', 'union'):
                    stack.append(('scope', re.sub(r'^kairn(::|$)', '', m.group(2) or '')))
                elif '(' in head and not head.split()[0].startswith(_CONTROL) and \
                        not any(kind == 'function' for kind, _ in stack):
                    stack.append(('function', _signature(head) or '?'))
                else:
                    stack.append(('block', None))
            elif what == '}' and stack:
                stack.pop()
            last = pos + 1
    return {k: sorted(v) for k, v in found.items()}


def exposed_report(kernels, root=None):
    """The lines of the report of rule R3 on the factors of fused operations (rules.exposed_operands):
    for each object with exposed operands, the operands and the operation each reaches, the
    operations today and with the guards, and the public functions that reach it (header_calls:
    directly, through a kernel that calls it, or through a loop that runs it)."""
    root = root or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    calls = header_calls(root, kernels)

    found = rules.exposed_operands(kernels)

    def reached(e):
        """The header functions that call the object itself (a kernel, or a loop's functions) and,
        for a kernel, the loops whose exposed part it is; and the other objects of the list whose
        exposed operands reach it through a call, or whose fold of coefficients it is."""
        sites = set(calls.get(e.name, ()))
        if e.kind == 'kernel':
            sites |= {s for o in found if o.kind == 'loop' and o.kernel == e.name for s in calls.get(o.name, ())}
            inside = {o.name for o in found if o.kind == 'kernel' and o is not e and
                      any(f' in {e.name} (called for ' in w for ws in o.operands.values() for w in ws)}
        else:
            inside = {o.name for o in found if o.kind == 'loop' and o.role == f'step of {e.name}'}
        text = '; '.join(sorted(sites)) or 'no public header'
        return text + (f' (and inside {", ".join(sorted(inside))})' if inside else '')

    lines = [f'R3, factors of a fused operation (rules.exposed_operands): {len(found)} objects with exposed '
             'operands (a value of the program that is a factor of fma, fms, fnma or muladd whose addend is '
             'not the literal zero, unguarded on that path), each accepted only while it is pending '
             '(rules.FACTOR_PENDING)']
    for e in found:
        what = f'{e.kind} {e.name}' + (f' ({e.role} {e.kernel})' if e.kind == 'loop' else '')
        ops = '; '.join(f'{v}: ' + ', '.join(ws) for v, ws in e.operands.items())
        per = ' per element' if e.kind == 'loop' else ''
        pending = rules.FACTOR_PENDING.get(rules._pending_key(e))
        lines.append(f'  {what}: {ops}; {e.ops} operations{per}, {e.guarded} with the guards; reached by '
                     f'{reached(e)}' + (f'; PENDING: {pending}' if pending else ''))
    return lines


def summary(kernels):
    """The lines build prints about the kernels: what is unverified, not constexpr, exempt, which
    guards of rule R3 are pending, and the report of R3 on the factors of fused operations."""
    def names(pred):
        found = [k.name for k in kernels.values() if pred(k)]
        return ', '.join(found) if found else 'none'
    pending, through = rules.r3_report(kernels)
    pending_text = '; '.join(f'{n} ({v}: {why})' for n, p in pending.items() for v, why in p.items())
    through_text = ', '.join('%s (%s)' % (n, ', '.join(by)) for n, by in through.items())
    return [
        f'kernels: {len(kernels)}',
        f'UNVERIFIED: {names(lambda k: k.status == "unverified")}',
        f'IEEE model UNVERIFIED: {names(lambda k: k.extended and k.ieee_status == "unverified")}',
        f'no real-model statement (IEEE model only): {names(lambda k: not k.real_model)}',
        f'not constexpr: {names(lambda k: cpp.constexpr_kind(k, kernels) is None)}',
        f'constexpr through a constant-evaluation variant: '
        f'{", ".join(f"{k.name} ({k.ce_variant})" for k in kernels.values() if k.ce_variant) or "none"}',
        f'constexpr by the rule of the product (each prod a plain product in constant evaluation): '
        f'{names(lambda k: cpp.product_rule(k, kernels))}',
        f'exempt from the non-finite cone: {names(lambda k: bool(k.cone_exempt))}',
        f'entry kernels (rule R3): {names(lambda k: k.entry)}',
        f'R3 GUARD PENDING: {pending_text or "none"}',
        f'accepted by R3 only through a pending guard: {through_text or "none"}',
        f'folds: {len(kernels.folds)} ({", ".join(kernels.folds) or "none"})',
        f'folds UNVERIFIED: {", ".join(n for n, f in kernels.folds.items() if f.status == "unverified") or "none"}',
    ] + exposed_report(kernels)
