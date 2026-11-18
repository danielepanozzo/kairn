#!/bin/sh
# run.sh: generate, check the proofs, audit the axioms, and test the generated C++.
# Needs Rocq 9 with Flocq 4.2 (e.g. the rocq/rocq-prover:9.0 image + `opam install coq-flocq`),
# a C++ compiler with hardware FMA enabled, and python3.
set -e
python3 gen.py out
cd out && cp ../Proofs.v ../Audit.v ../Bad.v .
echo "== proofs"
rocq compile -Q . "" Model.v
rocq compile -Q . "" Proofs.v
echo "  Model.v, Proofs.v: checked"
echo "== axioms used by the theorems"
rocq compile -Q . "" Audit.v > audit.txt
python3 ../audit.py audit.txt ../allowed_axioms.txt
echo "== negative control (a theorem closed with Admitted must be rejected)"
rocq compile -Q . "" Bad.v > bad.txt
if python3 ../audit.py bad.txt ../allowed_axioms.txt; then echo "  ERROR: the audit accepted it"; exit 1; else echo "  rejected, as it must be"; fi
cd ..
echo "== generated C++ against exact rational arithmetic"
${CXX:-g++} -std=c++20 -O2 ${CXXFLAGS:--mavx2 -mfma} test.cpp -o out/test && out/test | python3 check.py
