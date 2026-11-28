# EXPERIMENTAL proof probe of the two-limb interval rounded upward (not part of the library).
#
#   make -C experiments/upward2/proofs              build, then audit
#   make -C experiments/upward2/proofs KAIRN=DIR    DIR: the library's proofs directory, whose
#                                                   theories must be compiled (default ../../../proofs)
#   make -C experiments/upward2/proofs clean
#
# Each file ends with one Print Assumptions per main theorem; compiling it writes them to
# FILE.out, and the library's audit script checks them against the allowed axioms (and scans the
# files for Admitted, admit, Axiom, Parameter).
KAIRN  ?= ../../../proofs
ROCQ   ?= rocq
PYTHON ?= python3

FLAGS  := -Q $(KAIRN)/theories Kairn -Q $(KAIRN)/gen Kairn.Gen -Q . KairnX2
VFILES := $(shell grep -E '\.v$$' _CoqProject)
AUDIT  := $(KAIRN)/audit/audit.py
ALLOWED := $(KAIRN)/audit/allowed_axioms.txt

all: audit

%.vo: %.v
	$(ROCQ) compile $(FLAGS) $< > $*.out

audit: $(VFILES:.v=.vo)
	@echo "== text scan"
	@$(PYTHON) $(AUDIT) scan $(VFILES)
	@for f in $(VFILES:.v=); do \
	  echo "== assumptions of $$f.v"; \
	  $(PYTHON) $(AUDIT) assumptions $$f.v $$f.out $(ALLOWED) || exit 1; \
	done
	@echo "== audit passed"

clean:
	rm -f *.vo *.vos *.vok *.glob *.out .*.aux .lia.cache .nia.cache

.PHONY: all audit clean
