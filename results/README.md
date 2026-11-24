# Stored results

Summaries of brute-force runs and benchmark measurements, by milestone, as written by the tools
that produced them. The pages under `docs/developer/results/` are written from these files, and so
is the section Measured of each kernel's reference page (`docs/tools/reference.py`). Nothing here
is an input of the library, of the generator, or of the proofs.

- `milestone1/brute/`: summaries of brute-force runs (`tests/brute/brute.py collect`), one file
  per machine; `supplementary/`, runs of a few kernels, at the commit of the others or a later
  one.
- `milestone1/bench/`: benchmark measurements.
- `milestone1/mutants/`: what the tests catch of the faults that `tests/kernel_mutants.py` plants
  in the generated scalar kernels, and the analysis of those that nothing caught (its `README.md`).
- `milestone1/costs/`: the costs of Milestone 1, which `docs/developer/results/costs-milestone1.md`
  reports: compile times (`compile/`), the check of the environment (`checks/`), MSVC's stack
  cookie (`gs/`) and the times of the quick tier in CI (`ci/`).
- `milestone2/brute/`: the summaries of the brute-force runs of Milestone 2, as for Milestone 1,
  with `supplementary/`; `emulated/` (the
  exhaustive tier on emulated formats) and `lengths/` (`tests/brute/lengths.py`), which the
  reference pages do not show.
- `milestone2/bench/`: benchmark measurements of Milestone 2, one JSON file per run of a harness
  of `bench/`, named by what was measured, the machine, the compiler and the optimization level;
  `bench/m2_report.py` prints the tables of `docs/developer/results/bench-milestone2.md` from them.
- `milestone2/costs/`: compile times and run times of the operations of `Ball` in each setting of
  `KAIRN_ENCLOSURE_CODE` (`bench/enclosure_costs.py`), which
  `docs/developer/results/costs-milestone2.md` reports.
- `milestone2/search/`: the adversarial search after the runs (`oracle/kairn-oracle search`), per
  kernel and format the best line of every quantity with its value, one file per run: from the
  strata alone, and with every seed through the interpreter and through a compiled runner;
  `docs/developer/results/brute-milestone2.md` reports it ("The adversarial search").
- `brute-code.json`: for every commit that a summary under `*/brute/` names as the code of its
  runs, the SHA-256 of the code and of the claims of every kernel and loop at that commit, written
  from the repository's history by `docs/tools/brute_code.py`. A kernel's reference page shows the
  stored runs of every campaign whose fingerprint at the run's commit is that of the kernel's code
  now, and no other, and marks those whose claims were not the claims now. After storing the
  summary of a run of a new commit, run
  `python3 docs/tools/brute_code.py` and commit what it writes: `docs/tools/reference.py` refuses a
  summary whose commit the file does not have.
