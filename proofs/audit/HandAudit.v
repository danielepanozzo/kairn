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
     exactness of mul_pow2_2, further bounds on radd and rmul);
   - the theorems of summation, which are about no single kernel and have no generated
     statement: the tree theorem, the bounds of a sum and of a dot product in the two
     orders of a loop, and the kernels to which they apply;
   - the first building blocks of Milestone 2, proved before their kernels are generated:
     the directed sums and products on models of their listings written by hand (the
     generated models will replace them), the error of a rounded product and the sign of
     the error term of two_prod, the rectangle lemma of the product of intervals, and the
     two executions of a product.

   Same form as the generated audits: for every theorem, a silent definition that fails
   to compile unless the theorem has the stated type, then the axioms it depends on, for
   the audit script to compare with the allow-list. Nothing else is printed. *)
From Kairn.Gen Require Import Statements IeeeStatements.
From Kairn Require Import IeeeVocabulary IeeeEFT IeeeAdd22 IeeeMul22 IeeeMore IeeeSub IeeeFinite.
From Kairn Require Import Split Directed MulPow2.
From Kairn Require Import Guard IeeeOps.
From Kairn Require Import Folds Summation SummationKernels.
From Kairn Require Import DirectedSum DirectedProd Rectangle IeeeProduct.

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

(* Summation: the two orders of a loop over arrays as functions on lists
   (theories/Folds.v), then the tree theorem, its closed forms, and the bounds of the two
   orders (theories/Summation.v). Real arithmetic about an addition of which only an
   error bound is known; no kernel is named. *)
Print Assumptions lane_nth.
Print Assumptions fold_lanes_short.
Print Assumptions fold_seq_map.
Print Assumptions fold_lanes_map.
Print Assumptions height_le_leaves.
Print Assumptions pow_minus_1_le_gamma.
Print Assumptions div_one_minus_le.
Print Assumptions tree_sum_general.
Print Assumptions tree_sum.
Print Assumptions tree_sum_tau.
Print Assumptions tree_sum_weighted.
Print Assumptions tree_sum_approx.
Print Assumptions tree_sum_approx_gamma.
Print Assumptions fold_seq_tree_zero.
Print Assumptions fold_lanes_tree_zero.
Print Assumptions fold_seq_tree.
Print Assumptions fold_lanes_tree.
Print Assumptions fold_seq_sum.
Print Assumptions fold_lanes_sum_height.
Print Assumptions fold_lanes_sum.
Print Assumptions fold_seq_sum_gamma.
Print Assumptions fold_lanes_sum_gamma.
Print Assumptions fold_seq_sum_approx.
Print Assumptions fold_lanes_sum_approx.
Print Assumptions fold_seq_weighted.
Print Assumptions fold_lanes_weighted.

(* The additions and the product of Kairn in the summation theorems, and the sums and
   dot products of one and two limbs in the two orders (theories/SummationKernels.v). *)
Print Assumptions add_1_1_adds.
Print Assumptions add_1_1_zero.
Print Assumptions add_2_2_adds.
Print Assumptions add_2_2_zero.
Print Assumptions add_2_2_zero_l.
Print Assumptions add_2_2_zero_r.
Print Assumptions add_fast_2_2_adds.
Print Assumptions add_fast_2_2_zero.
Print Assumptions add_fast_2_2_zero_l.
Print Assumptions add_fast_2_2_zero_r.
Print Assumptions mul_2_2_leaf.
Print Assumptions fused_add_tau.
Print Assumptions fused_add_weighted.
Print Assumptions sum_1_seq.
Print Assumptions sum_1_lanes.
Print Assumptions sum_2_seq.
Print Assumptions sum_2_lanes.
Print Assumptions sum_fast_2_seq.
Print Assumptions sum_fast_2_lanes.
Print Assumptions dot_2_seq.
Print Assumptions dot_2_lanes.
Print Assumptions dot_2_seq_gamma.
Print Assumptions dot_2_lanes_gamma.
Print Assumptions dot_1_seq.
Print Assumptions dot_1_lanes.
Print Assumptions dot_1_seq_gamma.
Print Assumptions dot_1_lanes_gamma.

(* Rounding a sum down and up (theories/DirectedSum.v), on models of the listings
   two_sum_ord, add_down_1, add_up_1, sub_down_1 and sub_up_1 written by hand: the
   statements in the shape of a generated statement, and the two lemmas that say what the
   last lines of a directed sum compute. *)
Print Assumptions two_sum_ord_listing_correct.
Print Assumptions two_sum_ord_listing_facts.
Print Assumptions two_sum_ord_listing_error.
Print Assumptions add_down_1_listing_correct.
Print Assumptions add_up_1_listing_correct.
Print Assumptions sub_down_1_listing_correct.
Print Assumptions sub_up_1_listing_correct.
Print Assumptions down_of_normalized.
Print Assumptions up_of_normalized.

(* Rounding a product down and up (theories/DirectedProd.v): when the error of a rounded
   product is a number of the format, the sign of the error term of two_prod, and the
   models of the listings mul_down_1, mul_up_1 and mul_dir_1 written by hand. *)
Print Assumptions mult_error_multiple.
Print Assumptions mult_multiple_eta.
Print Assumptions mult_error_format.
Print Assumptions mult_error_format_pred.
Print Assumptions mult_error_format_pred_even.
Print Assumptions mult_error_format_ge.
Print Assumptions two_prod_error_sign.
Print Assumptions two_prod_error_pos.
Print Assumptions two_prod_error_neg.
Print Assumptions two_prod_error_exact.
Print Assumptions two_prod_error_exact_large.
Print Assumptions two_prod_error_exact_pred.
Print Assumptions two_prod_error_zero.
Print Assumptions two_prod_error_zero_iff.
Print Assumptions two_prod_sign.
Print Assumptions const_P_eq.
Print Assumptions mul_down_1_listing_facts.
Print Assumptions mul_up_1_listing_facts.
Print Assumptions mul_dir_1_listing_eq.
Print Assumptions mul_down_1_listing_correct.
Print Assumptions mul_up_1_listing_correct.
Print Assumptions mul_dir_1_listing_correct.

(* The product of two intervals (theories/Rectangle.v): the rectangle lemma on extended
   real numbers, the minimum of four lower bounds and the maximum of four upper bounds,
   and the same on limbs for the selections of interval_mul_1. *)
Print Assumptions rectangle.
Print Assumptions rectangle_lower_bound.
Print Assumptions rectangle_upper_bound.
Print Assumptions member_nonempty.
Print Assumptions nonempty_member.
Print Assumptions select_lt_xmin.
Print Assumptions select_lt_xmax.
Print Assumptions interval_mul_lower.
Print Assumptions interval_mul_upper.

(* The two executions of a product in the IEEE model (theories/IeeeProduct.v): the plain
   product and the fused product with a zero addend. *)
Print Assumptions mult_prod_xval.
Print Assumptions mult_prod_nan.
Print Assumptions mult_prod_eq.
Print Assumptions mult_prod_zero.
Print Assumptions mult_prod_same.
Print Assumptions succ_mult_prod.
Print Assumptions rmul_two_executions.
