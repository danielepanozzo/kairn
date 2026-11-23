"""unguard.py SRC DEST: copies SRC/kairn to DEST/kairn with every guard of gen/scalar.hpp taken out,
by the regular expressions of tests/api/CMakeLists.txt (the unguarded fixture); fails if it finds
none or leaves one. The control of guard_pair_r3.cpp (README.md beside this file). Python 3
standard library only."""
import re
import shutil
import sys

src, dest = sys.argv[1], sys.argv[2]
shutil.rmtree(f"{dest}/kairn", ignore_errors=True)
shutil.copytree(f"{src}/kairn", f"{dest}/kairn")
path = f"{dest}/kairn/gen/scalar.hpp"
text = open(path, encoding="utf-8").read()
guard = re.compile(r"__builtin_is_constant_evaluated\(\) \? ([A-Za-z0-9_]+) : ([A-Za-z0-9_]+) \+ 0\.0f?;")
n = len(guard.findall(text))
text = guard.sub(r"\1;", text)
fold = re.compile(r"= ([A-Za-z0-9_]+) \+ 0\.0f?;")
n += len(fold.findall(text))
text = fold.sub(r"= \1;", text)
if n == 0 or re.search(r"\+ 0\.0f?;", text):
    sys.exit(f"could not take the guard out of {path} ({n} found)")
open(path, "w", encoding="utf-8").write(text)
print(f"{n} guards taken out of {path}")
