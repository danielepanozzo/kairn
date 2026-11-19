(* Audit of the theorems that the generated audits do not list.

   proofs/gen/Audit.v lists the theorem of every real-model statement, and
   proofs/gen/IeeeAudit.v the theorem of the IEEE-model statement of every kernel of the
   extended domain (the kernels with an ieee_theorem line). This file lists the rest:

   - theorems about generated statements that no kernel description names: the IEEE-model
     statements of the kernels of the finite domain, printed in
     proofs/gen/IeeeStatements.v (K_ieee_bridge_spec: the bridge to the real model;
     K_ieee_spec: correctness; K_ieee_finite_spec and K_ieee_finite_result_spec: no
     overflow below a threshold);
   - theorems whose statements are written by hand because the generator does not print
     them: two_sum in the IEEE model (the exact condition under which its error term is
     finite is not a claim), the guard (an operation, not a kernel), the threshold of
     mul_pow2_2 for a scalar that is not a power of two, and statements that say more
     about a kernel than its generated statement does (the parts of a split, the
     exactness of mul_pow2_2, further bounds on radd and rmul).

   Same form as the generated audits: for every theorem, a silent definition that fails
   to compile unless the theorem has the stated type, then the axioms it depends on, for
   the audit script to compare with the allow-list. Nothing else is printed. *)
From Kairn.Gen Require Import Statements IeeeStatements.
From Kairn Require Import IeeeVocabulary IeeeEFT IeeeAdd22 IeeeMul22 IeeeMore IeeeSub IeeeFinite.
From Kairn Require Import Split Directed MulPow2.
From Kairn Require Import Guard IeeeOps.

(* The IEEE model: error-free transformations (two_sum_ieee_spec is written by hand, in
   theories/IeeeEFT.v). *)
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

(* The IEEE model: add_2_1, mul_2_1, add_fast_2_2 (bridge and correctness). *)
Definition add_2_1_ieee_bridge_audit : add_2_1_ieee_bridge_spec := add_2_1_ieee_bridge.
Print Assumptions add_2_1_ieee_bridge.

Definition add_2_1_ieee_audit : add_2_1_ieee_spec := add_2_1_ieee_correct.
Print Assumptions add_2_1_ieee_correct.

Definition mul_2_1_ieee_bridge_audit : mul_2_1_ieee_bridge_spec := mul_2_1_ieee_bridge.
Print Assumptions mul_2_1_ieee_bridge.

Definition mul_2_1_ieee_audit : mul_2_1_ieee_spec := mul_2_1_ieee_correct.
Print Assumptions mul_2_1_ieee_correct.

Definition add_fast_2_2_ieee_bridge_audit : add_fast_2_2_ieee_bridge_spec := add_fast_2_2_ieee_bridge.
Print Assumptions add_fast_2_2_ieee_bridge.

Definition add_fast_2_2_ieee_audit : add_fast_2_2_ieee_spec := add_fast_2_2_ieee_correct.
Print Assumptions add_fast_2_2_ieee_correct.

(* split (real model): what the two parts are, beyond their sum. *)
Definition split_parts_audit : split_parts_spec := split_parts.
Print Assumptions split_parts.

Definition split_products_audit : split_products_spec := split_products.
Print Assumptions split_products.

(* mul_pow2_2 (real model): exactness when neither product is rounded in the subnormal
   range. *)
Definition mul_pow2_2_exact_audit : mul_pow2_2_exact_spec := mul_pow2_2_exact.
Print Assumptions mul_pow2_2_exact.

(* radd and rmul (real model): the result is a number of the format, strictly above the
   exact value, and the excess relative to the exact value. *)
Definition radd_facts_audit : radd_facts_spec := radd_facts.
Print Assumptions radd_facts.

Definition rmul_facts_audit : rmul_facts_spec := rmul_facts.
Print Assumptions rmul_facts.

(* Further bounds on radd and rmul, stated in theories/Directed.v. *)
Print Assumptions radd_excess_max.
Print Assumptions rmul_excess_max.
Print Assumptions radd_excess_sharp.
Print Assumptions rmul_excess_sharp.
Print Assumptions radd_excess_ulp_result.
Print Assumptions rmul_excess_ulp_result.

(* The guard: in the real model it returns a number of the format unchanged; in the IEEE
   model it keeps the value and the finiteness of its operand. *)
Definition guard_real_audit : guard_real_spec := guard_real.
Print Assumptions guard_real.

Definition guard_ieee_audit : guard_ieee_spec := guard_ieee.
Print Assumptions guard_ieee.

(* The IEEE model: sub_2_2, sub_2_1, sub_1_2, mul_pow2_2 (bridge and correctness). *)
Definition sub_2_2_ieee_bridge_audit : sub_2_2_ieee_bridge_spec := sub_2_2_ieee_bridge.
Print Assumptions sub_2_2_ieee_bridge.

Definition sub_2_2_ieee_audit : sub_2_2_ieee_spec := sub_2_2_ieee_correct.
Print Assumptions sub_2_2_ieee_correct.

Definition sub_2_1_ieee_bridge_audit : sub_2_1_ieee_bridge_spec := sub_2_1_ieee_bridge.
Print Assumptions sub_2_1_ieee_bridge.

Definition sub_2_1_ieee_audit : sub_2_1_ieee_spec := sub_2_1_ieee_correct.
Print Assumptions sub_2_1_ieee_correct.

Definition sub_1_2_ieee_bridge_audit : sub_1_2_ieee_bridge_spec := sub_1_2_ieee_bridge.
Print Assumptions sub_1_2_ieee_bridge.

Definition sub_1_2_ieee_audit : sub_1_2_ieee_spec := sub_1_2_ieee_correct.
Print Assumptions sub_1_2_ieee_correct.

Definition mul_pow2_2_ieee_bridge_audit : mul_pow2_2_ieee_bridge_spec := mul_pow2_2_ieee_bridge.
Print Assumptions mul_pow2_2_ieee_bridge.

Definition mul_pow2_2_ieee_audit : mul_pow2_2_ieee_spec := mul_pow2_2_ieee_correct.
Print Assumptions mul_pow2_2_ieee_correct.

(* The IEEE model: no overflow below a threshold, the other kernels
   (mul_pow2_2_ieee_finite_any_spec, for any finite scalar, is written by hand in
   theories/IeeeFinite.v). *)
Definition add_2_2_ieee_finite_result_audit : add_2_2_ieee_finite_result_spec := add_2_2_ieee_finite_result.
Print Assumptions add_2_2_ieee_finite_result.

Definition add_fast_2_2_ieee_finite_audit : add_fast_2_2_ieee_finite_spec := add_fast_2_2_ieee_finite.
Print Assumptions add_fast_2_2_ieee_finite.

Definition add_fast_2_2_ieee_finite_result_audit : add_fast_2_2_ieee_finite_result_spec := add_fast_2_2_ieee_finite_result.
Print Assumptions add_fast_2_2_ieee_finite_result.

Definition sub_2_2_ieee_finite_audit : sub_2_2_ieee_finite_spec := sub_2_2_ieee_finite.
Print Assumptions sub_2_2_ieee_finite.

Definition sub_2_2_ieee_finite_result_audit : sub_2_2_ieee_finite_result_spec := sub_2_2_ieee_finite_result.
Print Assumptions sub_2_2_ieee_finite_result.

Definition add_2_1_ieee_finite_audit : add_2_1_ieee_finite_spec := add_2_1_ieee_finite.
Print Assumptions add_2_1_ieee_finite.

Definition add_2_1_ieee_finite_result_audit : add_2_1_ieee_finite_result_spec := add_2_1_ieee_finite_result.
Print Assumptions add_2_1_ieee_finite_result.

Definition sub_2_1_ieee_finite_audit : sub_2_1_ieee_finite_spec := sub_2_1_ieee_finite.
Print Assumptions sub_2_1_ieee_finite.

Definition sub_2_1_ieee_finite_result_audit : sub_2_1_ieee_finite_result_spec := sub_2_1_ieee_finite_result.
Print Assumptions sub_2_1_ieee_finite_result.

Definition sub_1_2_ieee_finite_audit : sub_1_2_ieee_finite_spec := sub_1_2_ieee_finite.
Print Assumptions sub_1_2_ieee_finite.

Definition sub_1_2_ieee_finite_result_audit : sub_1_2_ieee_finite_result_spec := sub_1_2_ieee_finite_result.
Print Assumptions sub_1_2_ieee_finite_result.

Definition mul_2_1_ieee_finite_audit : mul_2_1_ieee_finite_spec := mul_2_1_ieee_finite.
Print Assumptions mul_2_1_ieee_finite.

Definition mul_pow2_2_ieee_finite_audit : mul_pow2_2_ieee_finite_spec := mul_pow2_2_ieee_finite.
Print Assumptions mul_pow2_2_ieee_finite.

Definition mul_pow2_2_ieee_finite_any_audit : mul_pow2_2_ieee_finite_any_spec :=
  mul_pow2_2_ieee_finite_any.
Print Assumptions mul_pow2_2_ieee_finite_any.
