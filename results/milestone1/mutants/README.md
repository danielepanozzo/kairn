# Planted faults in the scalar kernels

What the tests catch of the 1 052 one-statement changes that `tests/kernel_mutants.py` plants, one
at a time, in the generated scalar kernels (`include/kairn/gen/scalar.hpp`). The summary and what it
means are in [Testing](../../../docs/developer/testing.md#time).

- `linux-x86-64.json`: one line per change, as `tests/kernel_mutants.py --bits` writes its
  `results.json`: the kernel, the kind of change (`op`), the statement before and after (`before`,
  `line`: the `double` code; the `float` code changes alike), whether it is a statement of a fix-up
  (`fixup`), the tests of each tier that fail (`quick`, `full`), per compiler the number of its 15
  builds of the generator's comparison with the interpreter that differ (`bits`), the largest number
  of cases that differ in one build (`bits_cases`), per compiler the builds that `-Werror` refuses
  (`werror`; then built without it), and the class (`class`): caught by the quick tier, by the full
  tier only, by the comparison only (`bits only`), or by nothing. Run on the Linux machine (a 2019
  x86-64 server) with GCC 13.3 for the tiers and GCC 13.3 and Clang 18.1 for the comparison, Python
  3.12, on the code of commit `4179d64`, before the special operands below were added to the
  comparison's cases.
- `survivors.json`: the 65 changes that nothing caught in that run, each judged by hand: an
  equivalent change (no operand can change a result, and why), a blind spot (an operand of the
  kernel's domain tells it from the kernel), or a blind spot outside the domain (only operands the
  kernel does not accept do); with the two searches for such an operand, and for each blind spot the
  operands that tell it apart, the interpreter's result and the fault's, the oracle's verdict on the
  fault's result, and whether the comparison catches it now (`caught_now`). Those operands are the
  cases that `gen/tests/test_cxx.py` adds to its comparison (`SPECIAL_CASES`); with them, a run of
  this commit puts the 17 blind spots in the class `bits only` and leaves the 48 equivalent changes
  in the class `nothing`.

To regenerate `linux-x86-64.json` on an x86-64 Linux machine with GCC and Clang (47 minutes with
`--jobs 32` on 32 hardware threads; the tiers alone take about 20 minutes on an Apple M3 Max with
`--jobs 12`, and the comparison alone, `--no-tiers`, about a minute per change and core):

```sh
python3 tests/kernel_mutants.py --jobs 32 --cxx g++ --bits g++ clang++ --work /tmp/kernel-mutants
cp /tmp/kernel-mutants/results.json results/milestone1/mutants/linux-x86-64.json
```

Every test uses fixed seeds, so the same commit and compilers give the same file. To check the
faults of `survivors.json` alone, without the tiers, give their ids:

```sh
python3 tests/kernel_mutants.py --no-tiers --bits g++ clang++ \
  --ids $(python3 -c "import json; print(','.join(f['id'] for f in json.load(open('results/milestone1/mutants/survivors.json'))['faults']))")
```

`survivors.json` itself is not written by a tool: the searches were scratch programs (the fault and
the original kernel compiled side by side on special, random and stratified operands; and the
oracle's generator), and the verdicts are reasoned by hand from the listing.
