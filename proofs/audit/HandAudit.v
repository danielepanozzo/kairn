(* Audit of the theorems whose statements are written by hand: the IEEE model of eight
   kernels (drafts of the model and of the statements are in theories/IeeeDraft.v and
   theories/IeeeStatementsDraft.v), and statements that say more about a kernel than its
   generated statement does (the parts of a split, the exactness of mul_pow2_2, further
   bounds on radd and rmul).

   The theorems that establish generated statements are audited by the generated
   proofs/gen/Audit.v, and are not repeated here.

   Same form as that file: for every theorem, a silent definition that fails to compile
   unless the theorem has the stated type, then the axioms it depends on, for the audit
   script to compare with the allow-list. Nothing else is printed. When a statement
   becomes generated, its lines move to gen/Audit.v. *)
From Kairn.Gen Require Import Statements.
From Kairn Require Import IeeeStatementsDraft IeeeEFT IeeeAdd22 IeeeMul22 IeeeMore.
From Kairn Require Import Split Directed MulPow2.

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

(* The IEEE model: add_2_1, mul_2_1, add_fast_2_2 (bridge and correctness). *)
Definition add_2_1_ieee_bridge_audit : add_2_1_ieee_bridge_spec := add_2_1_ieee_bridge.
Print Assumptions add_2_1_ieee_bridge.

Definition add_2_1_ieee_audit : add_2_1_ieee_spec := add_2_1_ieee_correct.
Print Assumptions add_2_1_ieee_correct.

Definition mul_2_1_ieee_bridge_audit : mul_2_1_ieee_bridge_spec := mul_2_1_ieee_bridge.
Print Assumptions mul_2_1_ieee_bridge.

Definition mul_2_1_ieee_audit : mul_2_1_ieee_spec := mul_2_1_ieee_correct.
Print Assumptions mul_2_1_ieee_correct.

Definition add_fast_2_2_ieee_bridge_audit : add_fast_2_2_ieee_bridge_spec :=
  add_fast_2_2_ieee_bridge.
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
