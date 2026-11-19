#!/usr/bin/env python3
"""The axiom audit of the Kairn proofs. Python 3, standard library only.

  audit.py scan FILE.v ...
      Text search. Fails if a proof file contains, outside comments and strings, one of the
      words that introduce an unproved statement: Admitted, admit, Axiom, Parameter (and
      their plural and synonymous forms: Axioms, Parameters, Conjecture, Conjectures,
      give_up). This check is early and readable; the next one is the one that counts.

  audit.py assumptions AUDIT.v OUTPUT ALLOWED
      AUDIT.v is a Rocq file with one `Print Assumptions NAME.` per theorem, and OUTPUT is
      what compiling it printed. Fails if any theorem depends on an assumption that is not
      listed in ALLOWED, if a theorem's report is missing, or if the output contains
      anything this script does not understand. A theorem closed with Admitted shows up
      here as an axiom named after itself.

Exit status: 0 when the audit passes, 1 when it fails, 2 on a usage error.
"""
import re
import sys

FORBIDDEN = re.compile(
    r"(?<![\w'])(Admitted|admit|Axiom|Axioms|Parameter|Parameters|Conjecture|Conjectures|give_up)(?![\w'])")


def strip_comments(text):
    """Replace Rocq comments (which nest) and string literals by spaces, keeping newlines,
    so that line numbers are preserved."""
    out, depth, i, n, in_string = [], 0, 0, len(text), False
    while i < n:
        c = text[i]
        if in_string:
            if c == '"':
                in_string = False
            out.append("\n" if c == "\n" else " ")
            i += 1
        elif text.startswith("(*", i):
            depth += 1
            out.append("  ")
            i += 2
        elif depth and text.startswith("*)", i):
            depth -= 1
            out.append("  ")
            i += 2
        elif c == '"':
            # A string, in code or inside a comment (Rocq lexes strings inside comments).
            in_string = True
            out.append(" ")
            i += 1
        elif depth:
            out.append("\n" if c == "\n" else " ")
            i += 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


def scan(paths):
    hits = 0
    for path in paths:
        with open(path, encoding="utf-8") as f:
            code = strip_comments(f.read())
        for lineno, line in enumerate(code.split("\n"), 1):
            for m in FORBIDDEN.finditer(line):
                print(f"  FORBIDDEN    {path}:{lineno}: {m.group(1)}")
                hits += 1
    if hits == 0:
        print(f"  {len(paths)} files: no Admitted, admit, Axiom or Parameter")
    return 1 if hits else 0


def assumptions(source, output, allowed_path):
    with open(allowed_path, encoding="utf-8") as f:
        allowed = {l.strip() for l in f if l.strip() and not l.startswith("#")}
    with open(source, encoding="utf-8") as f:
        theorems = re.findall(r"Print\s+Assumptions\s+([\w.']+?)\s*\.(?:\s|$)", strip_comments(f.read()))
    # One block per Print Assumptions, in order. A block is either the line
    # "Closed under the global context" or the line "Axioms:" followed by entries
    # "name : type"; the type may continue on lines that start with white space.
    blocks, current, unknown = [], None, []
    with open(output, encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n")
            if not line.strip():
                continue
            if line.strip() == "Closed under the global context":
                blocks.append([])
                current = None
            elif line.strip() == "Axioms:":
                current = []
                blocks.append(current)
            elif line[0].isspace():
                if current is None:
                    unknown.append(line)
            elif current is not None:
                current.append(re.split(r"[\s:]", line, maxsplit=1)[0])
            else:
                unknown.append(line)
    failed = False
    if unknown:
        failed = True
        print("  NOT UNDERSTOOD (the audit file must print nothing but assumptions):")
        for line in unknown[:10]:
            print(f"    {line}")
    if len(blocks) != len(theorems) or not theorems:
        failed = True
        print(f"  MISMATCH     {len(theorems)} theorems audited in {source}, {len(blocks)} reports in {output}")
    for name, axioms in zip(theorems, blocks):
        bad = sorted(a for a in axioms if a not in allowed)
        if bad:
            failed = True
        status = "REJECTED" if bad else "ok      "
        detail = "closed under the global context" if not axioms else f"{len(axioms)} axioms"
        print(f"  {status}     {name}: {detail}")
        for a in sorted(axioms):
            print(f"      {'allowed    ' if a in allowed else 'NOT ALLOWED'}  {a}")
    return 1 if failed else 0


def main(argv):
    if len(argv) >= 3 and argv[1] == "scan":
        return scan(argv[2:])
    if len(argv) == 5 and argv[1] == "assumptions":
        return assumptions(argv[2], argv[3], argv[4])
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
