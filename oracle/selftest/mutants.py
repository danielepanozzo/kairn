#!/usr/bin/env python3
"""Tests the selftest: copies the oracle into a temporary directory once per mutant, plants one
deliberate bug, and runs `selftest --quick` on the copy, which must fail.  A mutant whose text no
longer occurs in the source is reported as stale rather than skipped silently.

    python3 oracle/selftest/mutants.py        # about five minutes
"""

import os
import shutil
import subprocess
import sys
import tempfile

ORACLE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# name: (file, text, replacement)
MUTANTS = {
    "rn ties away from zero": (
        "fmt.py", "if rem > half or (rem == half and m & 1):", "if rem >= half:"),
    "rn without gradual underflow": (
        "fmt.py", "    if q < fmt.qmin:\n        q = fmt.qmin\n    if q <= s:",
        "    if q < fmt.qmin - 3:\n        q = fmt.qmin - 3\n    if q <= s:"),
    "membership accepts p+1 bits": (
        "fmt.py", ".bit_length() <= fmt.p\n", ".bit_length() <= fmt.p + 1\n"),
    "requirements not checked": (
        "check.py", "        for r in pl.requires:\n", "        for r in []:\n"),
    "normalized entry always passes": (
        "check.py", "                if not F.normalized_limbs(fmt, zz):", "                if False:"),
    "bound lenient by a factor 2": (
        "check.py", "                if num > den:", "                if num > 2 * den:"),
    "when condition ignored": (
        "check.py", 'if e["when"] == "product_large" and not', "if False and not"),
    "outputs not checked for membership": (
        "check.py", "        for v in z:\n            if not F.is_member(fmt, v):",
        "        for v in []:\n            if not F.is_member(fmt, v):"),
    "leading_rounded not checked": (
        "check.py", '                if r != z[e["first"]]:', "                if False:"),
    "dropped lines not detected": (
        "check.py", "            if seen != want:", "            if False:"),
    "form A read as form R": (
        "check.py", '                if e["form"] == "R":', "                if True:"),
    "absolute term ignored": (
        "check.py", "                den = rn_ * rho * ad + an * rd", "                den = rn_ * rho * ad"),
}


def main():
    work = tempfile.mkdtemp(prefix="kairn-oracle-mutants-")
    survivors, stale = [], []
    try:
        for name, (fn, old, new) in MUTANTS.items():
            copy = os.path.join(work, "oracle")
            shutil.rmtree(copy, ignore_errors=True)
            shutil.copytree(ORACLE, copy, ignore=shutil.ignore_patterns("__pycache__"))
            path = os.path.join(copy, "kairn_oracle", fn)
            with open(path) as fh:
                src = fh.read()
            if src.count(old) != 1:
                stale.append(name)
                print("STALE    %s (the text to mutate is not in %s once)" % (name, fn))
                continue
            with open(path, "w") as fh:
                fh.write(src.replace(old, new))
            r = subprocess.run([sys.executable, os.path.join(copy, "kairn-oracle"), "selftest",
                                "--quick", "--workdir", os.path.join(work, "wd")],
                               capture_output=True, text=True)
            failing = [ln.split()[1] for ln in r.stdout.splitlines() if ln.startswith("FAIL")]
            if r.returncode == 0:
                survivors.append(name)
            print("%-8s %-36s %s" % ("caught" if r.returncode else "SURVIVED", name,
                                     ", ".join(failing)))
            sys.stdout.flush()
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print("mutants: %d caught, %d survived, %d stale" % (
        len(MUTANTS) - len(survivors) - len(stale), len(survivors), len(stale)))
    return 1 if survivors or stale else 0


if __name__ == "__main__":
    sys.exit(main())
