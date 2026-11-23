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
- `milestone2/brute/`: the same for Milestone 2, with `supplementary/`; `emulated/` (the
  exhaustive tier on emulated formats) and `lengths/` (`tests/brute/lengths.py`), which the
  reference pages do not show.
- `brute-code.json`: for every commit that a summary under `*/brute/` names as the code of its
  runs, the SHA-256 of the code and of the claims of every kernel and loop at that commit, written
  from the repository's history by `docs/tools/brute_code.py`. A kernel's reference page shows the
  stored runs of every campaign whose fingerprint at the run's commit is that of the kernel's code
  now, and no other, and marks those whose claims were not the claims now. After storing the
  summary of a run of a new commit, run
  `python3 docs/tools/brute_code.py` and commit what it writes: `docs/tools/reference.py` refuses a
  summary whose commit the file does not have.
