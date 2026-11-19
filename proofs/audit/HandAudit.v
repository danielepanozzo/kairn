(* Audit of the theorems whose statements are not generated yet: the IEEE model of five
   kernels (drafts of the model and of the statements are in theories/IeeeDraft.v and
   theories/IeeeStatementsDraft.v), add_fast_2_2, split, two_prod_dekker (proved with
   constants and minimum precisions that differ from the placeholders of the generated
   statements), and the directed steps radd and rmul.

   Same form as the generated proofs/gen/Audit.v: for every theorem, a silent definition
   that fails to compile unless the theorem has the stated type, then the axioms it
   depends on, for the audit script to compare with the allow-list. Nothing else is
   printed. When a kernel's statement becomes generated, its lines move to gen/Audit.v. *)
From Kairn.Gen Require Import Statements.
From Kairn Require Import IeeeStatementsDraft IeeeEFT IeeeAdd22 IeeeMul22.
From Kairn Require Import AddFast22 Split TwoProdDekker Directed.

(* The IEEE model: error-free transformations. *)
Definition fast_two_sum_ieee_audit : fast_two_sum_ieee_spec := fast_two_sum_ieee_correct.
Print Assumptions fast_two_sum_ieee_correct.

Definition two_prod_ieee_audit : two_prod_ieee_spec := two_prod_ieee_correct.
Print Assumptions two_prod_ieee_correct.

Definition two_sum_ieee_audit : two_sum_ieee_spec := two_sum_ieee_correct.
Print Assumptions two_sum_ieee_correct.

(* The IEEE model: add_2_2. *)
Definition add_2_2_ieee_bridge_audit : add_2_2_ieee_bridge_spec := add_2_2_ieee_bridge.
Print Assumptions add_2_2_ieee_bridge.

Definition add_2_2_ieee_audit : add_2_2_ieee_spec := add_2_2_ieee_correct.
Print Assumptions add_2_2_ieee_correct.

Definition add_2_2_ieee_finite_audit : add_2_2_ieee_finite_spec := add_2_2_ieee_finite.
Print Assumptions add_2_2_ieee_finite.

(* The IEEE model: mul_2_2. *)
Definition mul_2_2_ieee_bridge_audit : mul_2_2_ieee_bridge_spec := mul_2_2_ieee_bridge.
Print Assumptions mul_2_2_ieee_bridge.

Definition mul_2_2_ieee_audit : mul_2_2_ieee_spec := mul_2_2_ieee_correct.
Print Assumptions mul_2_2_ieee_correct.

Definition mul_2_2_ieee_finite_audit : mul_2_2_ieee_finite_spec := mul_2_2_ieee_finite.
Print Assumptions mul_2_2_ieee_finite.

(* add_fast_2_2 (real model). *)
Definition add_fast_2_2_c3_audit : add_fast_2_2_spec_c3 := add_fast_2_2_correct_c3.
Print Assumptions add_fast_2_2_correct_c3.

Definition add_fast_2_2_draft_audit : add_fast_2_2_spec_draft := add_fast_2_2_correct_draft.
Print Assumptions add_fast_2_2_correct_draft.

(* split and two_prod_dekker (real model). *)
Definition split_draft_audit : split_spec' := split_correct_draft.
Print Assumptions split_correct_draft.

Definition split_parts_audit : split_parts_spec := split_parts.
Print Assumptions split_parts.

Definition split_products_audit : split_products_spec := split_products.
Print Assumptions split_products.

Definition two_prod_dekker_draft_audit : two_prod_dekker_spec' := two_prod_dekker_correct_draft.
Print Assumptions two_prod_dekker_correct_draft.

Definition two_prod_dekker_7_2_audit : two_prod_dekker_spec_7_2 := two_prod_dekker_correct_7_2.
Print Assumptions two_prod_dekker_correct_7_2.

(* radd and rmul (real model). *)
Definition radd_audit : radd_spec := radd_correct.
Print Assumptions radd_correct.

Definition rmul_audit : rmul_spec := rmul_correct.
Print Assumptions rmul_correct.

(* Further bounds on radd and rmul, stated in theories/Directed.v. *)
Print Assumptions radd_excess_max.
Print Assumptions rmul_excess_max.
Print Assumptions radd_excess_sharp.
Print Assumptions rmul_excess_sharp.
Print Assumptions radd_excess_ulp_result.
Print Assumptions rmul_excess_ulp_result.
