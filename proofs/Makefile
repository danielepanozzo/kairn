# make -C proofs          build every proof, then run the axiom audit
# make -C proofs build    build only
# make -C proofs audit    audit only (builds first)
# make -C proofs gen      only the generated model and statement files and what they import
# make -C proofs clean
#
# Needs `rocq` (Rocq 9.x) with Flocq 4.2 on the PATH, and python3.
# Parallel build: make -C proofs -j N.

ROCQ   ?= rocq
PYTHON ?= python3

# The library paths are those of _CoqProject, so that the audit files see the same names.
LIBS   := $(shell grep -E '^-[QR] ' _CoqProject)
# Every file of the build: these are the "proof files" that the text scan reads.
VFILES := $(shell grep -E '\.v$$' _CoqProject)
AUDIT  := audit/audit.py
ALLOWED := audit/allowed_axioms.txt

all: audit

Makefile.rocq: _CoqProject
	$(ROCQ) makefile -f _CoqProject -o Makefile.rocq

build: Makefile.rocq
	+$(MAKE) --no-print-directory -f Makefile.rocq

audit: build
	@echo "== text scan of the proof files"
	@$(PYTHON) $(AUDIT) scan $(VFILES)
	@echo "== assumptions of every theorem that establishes a generated statement"
	@$(ROCQ) compile $(LIBS) gen/Audit.v > audit/Audit.out
	@$(PYTHON) $(AUDIT) assumptions gen/Audit.v audit/Audit.out $(ALLOWED)
	@echo "== assumptions of the theorems that the generated audits do not list (audit/HandAudit.v)"
	@$(ROCQ) compile $(LIBS) -Q audit KairnAudit audit/HandAudit.v > audit/HandAudit.out
	@$(PYTHON) $(AUDIT) assumptions audit/HandAudit.v audit/HandAudit.out $(ALLOWED)
	@echo "== negative control: a false theorem closed with Admitted must be rejected"
	@if $(PYTHON) $(AUDIT) scan audit/Bad.v; \
	  then echo "  ERROR: the text scan accepted audit/Bad.v"; exit 1; \
	  else echo "  rejected by the text scan, as it must be"; fi
	@$(ROCQ) compile -Q audit KairnAudit audit/Bad.v > audit/Bad.out
	@if $(PYTHON) $(AUDIT) assumptions audit/Bad.v audit/Bad.out $(ALLOWED); \
	  then echo "  ERROR: the assumption check accepted audit/Bad.v"; exit 1; \
	  else echo "  rejected by the assumption check, as it must be"; fi
	@echo "== assumptions of the IEEE-model theorem of every kernel of the extended domain"
	@$(ROCQ) compile $(LIBS) gen/IeeeAudit.v > audit/IeeeAudit.out
	@if grep -q "Print Assumptions" gen/IeeeAudit.v; \
	  then $(PYTHON) $(AUDIT) assumptions gen/IeeeAudit.v audit/IeeeAudit.out $(ALLOWED); \
	  else echo "  none yet"; fi
	@echo "== audit passed"

# The generated model and statement files and the files they import. (gen/Audit.v and
# gen/IeeeAudit.v name the theorems, so they need the whole build: the audit compiles them.)
GENERATED := gen/Model.vo gen/Statements.vo gen/IeeeModel.vo gen/IeeeStatements.vo gen/FoldModel.vo \
             gen/FoldStatements.vo gen/IeeeFoldModel.vo gen/IeeeFoldStatements.vo gen/IeeeWith.vo

gen: Makefile.rocq
	+$(MAKE) --no-print-directory -f Makefile.rocq $(GENERATED)

clean:
	@if [ -f Makefile.rocq ]; then $(MAKE) --no-print-directory -f Makefile.rocq cleanall; fi
	rm -f gen/IeeeAudit.vo* gen/IeeeAudit.glob gen/.IeeeAudit.aux
	rm -f Makefile.rocq Makefile.rocq.conf .Makefile.rocq.d audit/*.out audit/*.vo audit/*.vok audit/*.vos audit/*.glob audit/.*.aux

.PHONY: all build audit gen clean
