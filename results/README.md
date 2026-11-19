# Stored results

Summaries of brute-force runs and benchmark measurements, by milestone, as written by the tools
that produced them. The pages under `docs/developer/results/` are written from these files.
Nothing here is an input of the library, of the generator, or of the proofs.

- `milestone1/brute/`: summaries of brute-force runs (`tests/brute/brute.py collect`), one file
  per machine.
- `milestone1/bench/`: benchmark measurements.
- `milestone1/mutants/`: what the tests catch of the faults that `tests/kernel_mutants.py` plants
  in the generated scalar kernels, and the analysis of those that nothing caught (its `README.md`).
