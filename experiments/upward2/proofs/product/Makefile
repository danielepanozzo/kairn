# EXPERIMENTAL proof probe of the product of experiments/upward2 (not part of the library).
#
# make -C experiments/upward2/proofs/product          build, then the axiom audit
# make -C experiments/upward2/proofs/product build    build only
#
# Needs `rocq` (Rocq 9.x) with Flocq 4.2 on the PATH, python3, and the library's proofs built
# first (make -C proofs build; this probe imports only Format, Directed2, DirectedProd and what
# they import). KAIRN is the library's proofs directory; the paths of _CoqProject are the same
# ones for the default KAIRN (editors read them there).

KAIRN  ?= ../../../../proofs
ROCQ   ?= rocq
PYTHON ?= python3

LIBS   := -Q $(KAIRN)/theories Kairn -Q $(KAIRN)/gen Kairn.Gen -R $(KAIRN)/third_party/mr22 Double -Q . KairnX2P
VFILES := $(shell grep -E '\.v$$' _CoqProject)
AUDIT  := $(KAIRN)/audit/audit.py
ALLOWED := $(KAIRN)/audit/allowed_axioms.txt

all: audit

Makefile.rocq: _CoqProject Makefile
	$(ROCQ) makefile $(LIBS) $(VFILES) -o Makefile.rocq

build: Makefile.rocq
	+$(MAKE) --no-print-directory -f Makefile.rocq

audit: build
	@echo "== text scan of the proof files"
	@$(PYTHON) $(AUDIT) scan $(VFILES) X2Audit.v
	@echo "== assumptions of the main theorems (X2Audit.v)"
	@$(ROCQ) compile $(LIBS) X2Audit.v > X2Audit.out
	@$(PYTHON) $(AUDIT) assumptions X2Audit.v X2Audit.out $(ALLOWED)
	@echo "== audit passed"

clean:
	@if [ -f Makefile.rocq ]; then $(MAKE) --no-print-directory -f Makefile.rocq cleanall; fi
	rm -f Makefile.rocq Makefile.rocq.conf .Makefile.rocq.d X2Audit.out X2Audit.vo* X2Audit.glob .X2Audit.aux

.PHONY: all build audit clean
