#!/usr/bin/env python3
"""brute_code.py [--check]: which code each stored brute-force run exercised and which claims it
judged, kernel by kernel and loop by loop, written to results/brute-code.json so that
docs/tools/reference.py can tell, without the repository's history, whether a stored run is of
the code a kernel has now, and whether it judged the claims the kernel has now. Python 3 standard
library only.

  python3 docs/tools/brute_code.py           write results/brute-code.json from the history
  python3 docs/tools/brute_code.py --check   change nothing; exit 1 if the file differs from what
                                             would be written, 2 if the history is not there
  python3 docs/tools/brute_code.py --show NAME [--at COMMIT]
                                             print the code of a kernel or loop as the fingerprint
                                             reads it, in the tree or at a commit

The code of a kernel or a loop, as this script reads it, is its generated C++: its definitions in
include/kairn/gen/scalar.hpp, avx2.hpp and neon.hpp (a kernel's function of each limb type and the
function of its fix-up; a loop's functions NAME_seq, NAME_lanes, NAME_end, NAME_packed and
NAME_packed_end), with the definitions of every function they call by name, the helpers of
prelude.hpp and of the header (abs_bits, fma_rn, next_up_bits, ...) included, transitively. The
generator inlines every call of one kernel by another (gen/README.md, "A kernel description"),
so these definitions hold the code of every kernel the listing calls. Comment lines, comments at
the end of a line, blank lines and the indentation are not code and are left out; nothing else is.
The fingerprint is the SHA-256 of that text, header by header and function by function.

For every commit that a stored summary (results/*/brute/**/*.json) names as the code of its runs,
the file holds the fingerprint of the code of every kernel and loop of gen/claims.json at that
commit, read with `git show`, and that of its claims: its entry of gen/claims.json without the
fields of NOT_JUDGED (below), which is what the runs judged. reference.py compares them with the
fingerprints of the tree it runs in: a stored run counts on a page only when the code is the same,
and the page says that it judged other claims when the claims are not. Run this script after
storing a summary of a commit that the file does not have yet; reference.py refuses to run until
then.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
MANIFEST = "results/brute-code.json"
SCHEMA = 1
HEADERS = ("scalar", "avx2", "neon")
PRELUDE = "prelude"
# The functions of a loop: its orders in scalar.hpp, the end of a ball vector (its radius and its
# finish, a function of its own), and its packed form in avx2.hpp and neon.hpp.
LOOP_FUNCTIONS = ("seq", "lanes", "end", "packed", "packed_end")


class CodeError(Exception):
    pass


def fail(msg):
    raise CodeError(msg)


def header_path(name):
    return "include/kairn/gen/%s.hpp" % name


# --- The code of a header -------------------------------------------------------------------------

def strip_comment(line):
    """The line without a comment that starts with // outside a string or character literal."""
    quote, i = None, 0
    while i < len(line):
        ch = line[i]
        if quote:
            if ch == "\\":
                i += 1
            elif ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif line.startswith("//", i):
            return line[:i]
        i += 1
    return line


def braces(line):
    """The number of { less the number of } of a line of code, outside literals."""
    n, quote, i = 0, None, 0
    while i < len(line):
        ch = line[i]
        if quote:
            if ch == "\\":
                i += 1
            elif ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == "{":
            n += 1
        elif ch == "}":
            n -= 1
        i += 1
    return n


CALL = re.compile(r"\b([A-Za-z_]\w*)\s*\(")
# Words followed by a parenthesis in a declaration that are not its name.
NOT_NAMES = {"__attribute__", "__declspec", "alignas", "decltype", "noexcept", "requires"}


def declared_name(line):
    """The name of the function a line declares: the first word followed by a parenthesis that is
    not an attribute."""
    return next((n for n in CALL.findall(line) if n not in NOT_NAMES), None)


def definitions(text, where):
    """[(name, lines)] of every function defined at namespace scope of a generated header, in the
    order of the file: from the line that declares it to the line that closes its body, each line
    without its comment and its indentation, blank lines and comment lines left out. A function in
    a namespace inside the header's (kairn::gen::fixup) is at namespace scope too. A class, a
    preprocessor line or a declaration outside a body is no definition."""
    out = []
    scopes = []          # "namespace" or "other", one per open brace outside a definition
    current = None       # (name, lines, depth at which the definition closes)
    depth = 0
    for number, raw in enumerate(text.split("\n"), 1):
        line = strip_comment(raw).strip()
        if not line:
            continue
        delta = 0 if line.startswith("#") else braces(line)
        if current is not None:
            current[1].append(line)
            depth += delta
            if depth == current[2]:
                out.append((current[0], tuple(current[1])))
                current = None
            elif depth < current[2]:
                fail("%s:%d: a brace closes more than the definition of %s opened" % (where, number, current[0]))
            continue
        if line.startswith("#"):
            continue
        at_namespace = all(s == "namespace" for s in scopes)
        if at_namespace and "{" in line and not line.startswith(("namespace", "struct", "class", "union", "enum")):
            name = declared_name(line)
            if name is None:
                fail("%s:%d: cannot read the line %r: a brace opens at namespace scope, and the line "
                     "declares no function" % (where, number, line))
            current = (name, [line], depth)
            depth += delta
            if depth == current[2]:
                out.append((current[0], tuple(current[1])))
                current = None
            elif depth < current[2]:
                fail("%s:%d: a brace closes more than the definition of %s opened" % (where, number, name))
            continue
        if at_namespace and delta == 0 and "(" in line and not line.endswith(";"):
            # A declaration whose body would open on a later line: this reader takes a definition
            # only from the line that opens its body, and would miss it.
            fail("%s:%d: cannot read the line %r: a function whose body does not open on the line "
                 "that names it" % (where, number, line))
        if delta > 0:
            kind = "namespace" if line.startswith("namespace") else "other"
            scopes.extend([kind] * delta)
        elif delta < 0:
            if len(scopes) < -delta:
                fail("%s:%d: a brace closes a scope that is not open" % (where, number))
            del scopes[len(scopes) + delta:]
        depth += delta
    if current is not None:
        fail("%s: the definition of %s does not end" % (where, current[0]))
    if scopes:
        fail("%s: %d scopes are still open at the end of the file" % (where, len(scopes)))
    return out


def object_functions(name, loop):
    """The names of the functions that are the object's own: a kernel's is its name, a loop's are
    its name with the suffixes of LOOP_FUNCTIONS."""
    return {"%s_%s" % (name, s) for s in LOOP_FUNCTIONS} if loop else {name}


def fingerprints(files, kernels, loops, where=""):
    """{name: SHA-256 of its code, or None if no header defines it} for every name of kernels and
    loops; files is {"prelude": text, "scalar": text, "avx2": text, "neon": text} of one tree."""
    return {name: None if text is None else hashlib.sha256(text.encode("utf-8")).hexdigest()
            for name, text in code_texts(files, kernels, loops, where).items()}


def code_texts(files, kernels, loops, where=""):
    """{name: the text of its code, or None if no header defines it}: what fingerprints hashes."""
    kernels, loops = list(kernels), list(loops)
    own = {}
    for name in kernels:
        own[name] = object_functions(name, False)
    for name in loops:
        own[name] = object_functions(name, True)
    taken = {}
    for name, functions in own.items():
        for f in functions:
            if f in taken and taken[f] != name:
                fail("%sthe function %s would be the code of both %s and %s" % (where, f, taken[f], name))
            taken[f] = name
    prelude = definitions(files[PRELUDE], where + header_path(PRELUDE))
    parts = {name: [] for name in own}
    for h in HEADERS:
        defs = {}
        for name, lines in prelude + definitions(files[h], where + header_path(h)):
            defs.setdefault(name, []).append(lines)
        for name, functions in own.items():
            seen, todo = set(), sorted(f for f in functions if f in defs)
            while todo:
                f = todo.pop()
                if f in seen:
                    continue
                seen.add(f)
                for lines in defs[f]:
                    for line in lines:
                        for callee in CALL.findall(line):
                            if callee in defs and callee not in seen:
                                todo.append(callee)
            text = ["== %s" % header_path(h)]
            for f in sorted(seen):
                for lines in defs[f]:
                    text.append("-- %s" % f)
                    text.extend(lines)
            parts[name].append((bool(functions & set(defs)), "\n".join(text)))
    return {name: "\n".join(t for _, t in ps) if any(defined for defined, _ in ps) else None
            for name, ps in parts.items()}


def objects(claims_text, where):
    """(kernels, loops): the names of gen/claims.json."""
    data = json.loads(claims_text)
    if data.get("schema") != 1:
        fail("%s has schema %r; this script reads schema 1" % (where, data.get("schema")))
    return [k["name"] for k in data["kernels"]], [f["name"] for f in data.get("folds", [])]


# --- The claims -----------------------------------------------------------------------------------
#
# What a run judged is the claims of the commit it names as its code (tests/brute/brute.py:
# CODE_PATHS, which include gen/): the entry of gen/claims.json of each kernel and loop. The fields
# of an entry that say where its algorithm comes from, which theorem proves it, whether that is
# proved, and how many operations its code has are not judged; every other field is: what it
# computes and requires, what it ensures, its domain, its smallest precision, the exact constants
# per format.
NOT_JUDGED = ("source", "theorem", "ieee_theorem", "status", "ieee_status", "flops")


def claims_fingerprint(entry):
    """The SHA-256 of a claims entry without the fields of NOT_JUDGED."""
    kept = {k: v for k, v in entry.items() if k not in NOT_JUDGED}
    return hashlib.sha256(json.dumps(kept, sort_keys=True).encode("utf-8")).hexdigest()


def claims_fingerprints(claims_text, where):
    """{name: fingerprint of its claims} for every kernel and loop of a gen/claims.json."""
    data = json.loads(claims_text)
    objects(claims_text, where)
    return {e["name"]: claims_fingerprint(e) for e in data["kernels"] + data.get("folds", [])}


def read(path):
    with open(path, encoding="utf-8", newline="") as f:
        return f.read().replace("\r\n", "\n")   # a checkout with CRLF line ends has the same code


def git(root, *args):
    """The output of a git command in root, or None if it fails or there is no git."""
    try:
        r = subprocess.run(["git", "-C", root] + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError:
        return None
    if r.returncode != 0:
        return None
    return r.stdout.decode("utf-8").replace("\r\n", "\n")


def has_commit(root, commit):
    return git(root, "cat-file", "-e", commit + "^{commit}") is not None


def files_at(root, commit=None):
    """(files, kernels, loops, where) of the tree under root (commit None) or of a commit of its
    history: the text of the generated headers, and the names of gen/claims.json."""
    def show(rel):
        if commit is None:
            return read(os.path.join(root, *rel.split("/")))
        text = git(root, "show", "%s:%s" % (commit, rel))
        if text is None:
            fail("cannot read %s at commit %s" % (rel, commit))
        return text
    where = "" if commit is None else "%s:" % commit[:7]
    files = {h: show(header_path(h)) for h in (PRELUDE,) + HEADERS}
    files["claims"] = show("gen/claims.json")
    kernels, loops = objects(files["claims"], where + "gen/claims.json")
    return files, kernels, loops, where


def commit_fingerprints(root, commit=None):
    """(code, claims): the fingerprints of the code and of the claims of every kernel and loop of
    gen/claims.json at a commit, from the history, or of the tree (commit None)."""
    files, kernels, loops, where = files_at(root, commit)
    return (fingerprints(files, kernels, loops, where),
            claims_fingerprints(files["claims"], where + "gen/claims.json"))


def summary_commits(root):
    """{commit: [the summaries that name it]} for every stored brute-force summary,
    results/NAME/brute/ and the directories under it."""
    out = {}
    base = os.path.join(root, "results")
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames.sort()
        rel = os.path.relpath(dirpath, root).replace(os.sep, "/")
        parts = rel.split("/")
        if len(parts) < 3 or parts[2] != "brute":
            continue
        for f in sorted(filenames):
            if not f.endswith(".json"):
                continue
            data = json.loads(read(os.path.join(dirpath, f)))
            if data.get("kairn_brute_summary") != 1:
                continue
            for c in data.get("commit", []):
                out.setdefault(c, []).append("%s/%s" % (rel, f))
    return out


def manifest(root):
    """What results/brute-code.json holds, from the history: the text of the file."""
    commits = summary_commits(root)
    missing = [c for c in sorted(commits) if not has_commit(root, c)]
    if missing:
        fail("the history does not have commit%s %s, named by %s: this script needs a clone with the "
             "history (a shallow clone has none)" % ("s" if len(missing) > 1 else "", ", ".join(missing),
                                                       ", ".join(commits[missing[0]])))
    data = {"kairn_brute_code": SCHEMA,
            "about": ("The SHA-256 of the code (code) and of the claims (claims) of every kernel and loop "
                      "of gen/claims.json at each commit that a stored brute-force summary names as the "
                      "code of its runs, with those summaries. Written from the history by "
                      "docs/tools/brute_code.py, which says what the code and the claims are; read by "
                      "docs/tools/reference.py."),
            "commits": {}}
    for c in sorted(commits):
        code, claims = commit_fingerprints(root, c)
        data["commits"][c] = {"summaries": commits[c],
                              "code": {n: code[n] for n in sorted(code) if code[n] is not None},
                              "claims": {n: claims[n] for n in sorted(claims)}}
    return json.dumps(data, indent=1) + "\n"


def load(root):
    """{commit: {"code": {name: fingerprint}, "claims": {name: fingerprint}}} of
    results/brute-code.json, or {} if there is none."""
    path = os.path.join(root, *MANIFEST.split("/"))
    if not os.path.exists(path):
        return {}
    data = json.loads(read(path))
    if data.get("kairn_brute_code") != SCHEMA:
        fail("%s is not of version %d" % (MANIFEST, SCHEMA))
    for c, entry in data["commits"].items():
        if "code" not in entry or "claims" not in entry:
            fail("%s: commit %s has no fingerprints of the code and the claims" % (MANIFEST, c[:7]))
    return {c: {"code": entry["code"], "claims": entry["claims"]} for c, entry in data["commits"].items()}


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", help="change nothing; fail if %s is stale" % MANIFEST)
    ap.add_argument("--show", metavar="NAME", help="print the code of a kernel or loop that the fingerprint is "
                                                   "of, and its fingerprint; write nothing")
    ap.add_argument("--at", metavar="COMMIT", help="with --show: at that commit of the history, not in the tree")
    a = ap.parse_args(argv)
    path = os.path.join(ROOT, *MANIFEST.split("/"))
    try:
        if a.show:
            files, kernels, loops, where = files_at(ROOT, a.at)
            if a.show not in kernels and a.show not in loops:
                fail("%sgen/claims.json has no kernel or loop %s" % (where, a.show))
            text = code_texts(files, kernels, loops, where)[a.show]
            if text is None:
                fail("%sno generated header defines %s" % (where, a.show))
            print(text)
            print("== SHA-256 %s" % hashlib.sha256(text.encode("utf-8")).hexdigest())
            return 0
        text = manifest(ROOT)
    except CodeError as e:
        print("brute_code.py: error: %s" % e, file=sys.stderr)
        return 2
    if a.check:
        if not os.path.exists(path) or read(path) != text:
            print("brute_code.py: %s differs from what this script writes: run python3 docs/tools/brute_code.py"
                  % MANIFEST)
            return 1
        print("brute_code.py: %s is what the history gives" % MANIFEST)
        return 0
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print("brute_code.py: wrote %s" % MANIFEST)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
