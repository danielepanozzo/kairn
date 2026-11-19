(* The audit of the hand-written drafts: for every kernel with a proof, check that the
   theorem has exactly the type of the kernel's statement, and print what it assumes.
   audit.py compares the printed assumptions with allowed_axioms.txt.

   This file stands in for the generated proofs/gen/Audit.v. It must print nothing but
   the output of Print Assumptions (so the type checks are silent definitions). *)
From Kairn Require Import SpecDraft EFT Add22 Add21 Mul22 Mul21.

Definition audit_two_sum : two_sum_spec := two_sum_correct.
Print Assumptions two_sum_correct.

Definition audit_fast_two_sum : fast_two_sum_spec := fast_two_sum_correct.
Print Assumptions fast_two_sum_correct.

Definition audit_two_prod : two_prod_spec := two_prod_correct.
Print Assumptions two_prod_correct.

Definition audit_add_2_2 : add_2_2_spec := add_2_2_correct.
Print Assumptions add_2_2_correct.

Definition audit_mul_2_2 : mul_2_2_spec := mul_2_2_correct.
Print Assumptions mul_2_2_correct.

Definition audit_add_2_1 : add_2_1_spec := add_2_1_correct.
Print Assumptions add_2_1_correct.

Definition audit_mul_2_1 : mul_2_1_spec := mul_2_1_correct.
Print Assumptions mul_2_1_correct.
