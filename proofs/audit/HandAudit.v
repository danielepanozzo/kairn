(* Audit of the theorems that the generated audits do not list.

   proofs/gen/Audit.v lists the theorem of every real-model statement, and
   proofs/gen/IeeeAudit.v the theorem of the IEEE-model statement of every kernel of the
   extended domain (the kernels with an ieee_theorem line). This file lists the rest:

   - theorems about generated statements that no kernel description names: the IEEE-model
     statements of the kernels of the finite domain, printed in
     proofs/gen/IeeeStatements.v (K_ieee_bridge_spec: the bridge to the real model;
     K_ieee_spec: correctness; K_ieee_finite_spec and K_ieee_finite_result_spec: no
     overflow below a threshold), the steps of the folds among them; and the statements
     of proofs/gen/IeeeFoldStatements.v, whose theorems no description of a kernel or of
     a fold names either: the folds in the IEEE model (F_seq_ieee_spec and
     F_lanes_ieee_spec, for the generated models of proofs/gen/IeeeFoldModel.v), and
     the leading limb of the result of each step and combination of a fold
     (K_ieee_lead_spec);
   - theorems whose statements are written by hand because the generator does not print
     them: two_sum in the IEEE model (the exact condition under which its error term is
     finite is not a claim), the guard (an operation, not a kernel), the threshold of
     mul_pow2_2 for a scalar that is not a power of two, and statements that say more
     about a kernel than its generated statement does (the parts of a split, the
     exactness of mul_pow2_2, further bounds on radd and rmul);
   - the theorems of summation, which are about no single kernel and have no generated
     statement: the tree theorem, the bounds of a sum and of a dot product in the two
     orders of a loop, and the kernels to which they apply;
   - the lemmas of the first building blocks of Milestone 2 that are not generated
     statements: what the directed sums and products return in more detail than their
     claims say, the error of a rounded product and the sign of the error term of
     two_prod, mul_dir_1 on a model of its listing written by hand (the kernel is not
     generated yet), the rectangle lemma of the product of intervals, the two
     executions of a product, and the two executions of the eight kernels whose only
     fused operations are products, on listings written by hand with the product as an
     argument (the generator does not emit the model of the plain-product execution);
   - the theorems about the folds that have no generated statement: that a fold of the
     model with overflow is the fold of the real model whenever its result is finite
     (theories/FoldTransfer.v), what holds of the bound kernels beyond their generated
     statements (theories/BoundKernels.v), that the exported bound covers the error
     of each fold in each order (theories/FoldGuarantee.v), and what
     theories/IeeeFolds.v proves of the generated models of the folds in the IEEE model
     beyond their generated statements: the two facts about one application of each
     step, a fold of such steps with its finish, and the state after every element in
     the sequential order.

   Same form as the generated audits: for every theorem, a silent definition that fails
   to compile unless the theorem has the stated type, then the axioms it depends on, for
   the audit script to compare with the allow-list. Nothing else is printed. *)
From Kairn.Gen Require Import Statements IeeeStatements.
From Kairn.Gen Require Import IeeeFoldStatements.
From Kairn Require Import IeeeVocabulary IeeeEFT IeeeAdd22 IeeeMul22 IeeeMore IeeeSub IeeeFinite.
From Kairn Require Import Split Directed MulPow2.
From Kairn Require Import Guard IeeeOps.
From Kairn Require Import Folds Summation SummationKernels.
From Kairn Require Import DirectedSum DirectedProd BallPow2 Rectangle IeeeProduct.
From Kairn Require Import IeeeDirected IeeeDirectedProd IeeeEntry.
From Kairn Require Import IeeeTwoExecutions.
From Kairn Require Import StepKernels FoldTransfer BoundKernels FoldGuarantee.
From Kairn Require Import IeeeSteps IeeeFolds.

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
Definition add_2_2_ieee_finite_result_audit : add_2_2_ieee_finite_result_spec :=
  add_2_2_ieee_finite_result.
Print Assumptions add_2_2_ieee_finite_result.

Definition add_fast_2_2_ieee_finite_audit : add_fast_2_2_ieee_finite_spec :=
  add_fast_2_2_ieee_finite.
Print Assumptions add_fast_2_2_ieee_finite.

Definition add_fast_2_2_ieee_finite_result_audit : add_fast_2_2_ieee_finite_result_spec :=
  add_fast_2_2_ieee_finite_result.
Print Assumptions add_fast_2_2_ieee_finite_result.

Definition sub_2_2_ieee_finite_audit : sub_2_2_ieee_finite_spec := sub_2_2_ieee_finite.
Print Assumptions sub_2_2_ieee_finite.

Definition sub_2_2_ieee_finite_result_audit : sub_2_2_ieee_finite_result_spec :=
  sub_2_2_ieee_finite_result.
Print Assumptions sub_2_2_ieee_finite_result.

Definition add_2_1_ieee_finite_audit : add_2_1_ieee_finite_spec := add_2_1_ieee_finite.
Print Assumptions add_2_1_ieee_finite.

Definition add_2_1_ieee_finite_result_audit : add_2_1_ieee_finite_result_spec :=
  add_2_1_ieee_finite_result.
Print Assumptions add_2_1_ieee_finite_result.

Definition sub_2_1_ieee_finite_audit : sub_2_1_ieee_finite_spec := sub_2_1_ieee_finite.
Print Assumptions sub_2_1_ieee_finite.

Definition sub_2_1_ieee_finite_result_audit : sub_2_1_ieee_finite_result_spec :=
  sub_2_1_ieee_finite_result.
Print Assumptions sub_2_1_ieee_finite_result.

Definition sub_1_2_ieee_finite_audit : sub_1_2_ieee_finite_spec := sub_1_2_ieee_finite.
Print Assumptions sub_1_2_ieee_finite.

Definition sub_1_2_ieee_finite_result_audit : sub_1_2_ieee_finite_result_spec :=
  sub_1_2_ieee_finite_result.
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

(* Milestone 2, real model. The theorems of the generated statements of the building
   blocks are listed by proofs/gen/Audit.v; these are the lemmas beside them: what the
   last lines of a directed sum compute, and the error term of two_sum_ord
   (theories/DirectedSum.v). *)
Print Assumptions two_sum_ord_facts.
Print Assumptions two_sum_ord_error.
Print Assumptions down_of_normalized.
Print Assumptions up_of_normalized.

(* Rounding a product down and up (theories/DirectedProd.v): when the error of a rounded
   product is a number of the format, the sign of the error term of two_prod, what
   mul_down_1 and mul_up_1 return for every positive precision and every tie rule, and
   mul_dir_1 on a model of its listing written by hand (the kernel is not generated
   yet). *)
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
Print Assumptions up_mul_down_1_0_eq.
Print Assumptions mul_down_1_facts.
Print Assumptions mul_up_1_facts.
Print Assumptions mul_down_1_cases.
Print Assumptions mul_up_1_cases.
Print Assumptions mul_dir_1_listing_eq.
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
Print Assumptions mul_1_1_two_executions.

(* The two executions of the kernels whose only fused operations are products
   (theories/IeeeTwoExecutions.v). Limbs of the same value: equal, two zeros or two NaN,
   and what they share. *)
Print Assumptions same_value_iff.
Print Assumptions same_finite.
Print Assumptions same_nan.
Print Assumptions same_val.

(* The value of the result of each operation, as a function of the values of its
   operands, on all operands. *)
Print Assumptions xval_add.
Print Assumptions xval_sub.
Print Assumptions xval_prod.
Print Assumptions xval_mult.
Print Assumptions xval_abs.
Print Assumptions xval_times_inf.

(* Each operation is compatible with "same value", with any NaN on either side. *)
Print Assumptions same_add.
Print Assumptions same_sub.
Print Assumptions same_prod.
Print Assumptions same_mult.
Print Assumptions same_mult_prod.
Print Assumptions same_prod_mult.
Print Assumptions same_abs.
Print Assumptions same_neg.
Print Assumptions same_succ.
Print Assumptions same_pred.
Print Assumptions same_times_inf.
Print Assumptions same_guard.
Print Assumptions same_lt.
Print Assumptions same_le.
Print Assumptions same_eq.
Print Assumptions same_select.
Print Assumptions mult_prod_products.

(* Each listing written by hand is the generated definition when its product is the
   fused one. *)
Print Assumptions split_with_prod.
Print Assumptions two_prod_dekker_with_prod.
Print Assumptions mul_pow2_2_with_prod.
Print Assumptions mul_pow2_2_full_with_prod.
Print Assumptions ball_mul_pow2_1_with_prod.
Print Assumptions ball_mul_pow2_1_full_with_prod.
Print Assumptions ball_mul_pow2_2_with_prod.
Print Assumptions ball_mul_pow2_2_full_with_prod.

(* Two products of the same value, on operands of the same value, give outputs of the
   same value. *)
Print Assumptions fast_two_sum_same.
Print Assumptions split_same.
Print Assumptions two_prod_dekker_same.
Print Assumptions mul_pow2_2_same.
Print Assumptions mul_pow2_2_full_same.
Print Assumptions ball_mul_pow2_1_same.
Print Assumptions ball_mul_pow2_1_full_same.
Print Assumptions ball_mul_pow2_2_same.
Print Assumptions ball_mul_pow2_2_full_same.

(* The listing with the plain product and the generated kernel return outputs of the same
   value, on all operands. *)
Print Assumptions split_two_executions.
Print Assumptions two_prod_dekker_two_executions.
Print Assumptions mul_pow2_2_two_executions.
Print Assumptions mul_pow2_2_full_two_executions.
Print Assumptions ball_mul_pow2_1_two_executions.
Print Assumptions ball_mul_pow2_1_full_two_executions.
Print Assumptions ball_mul_pow2_2_two_executions.
Print Assumptions ball_mul_pow2_2_full_two_executions.

(* Scaling a ball by a power of two (theories/BallPow2.v): the radius and the two claims
   for a center whose scaled value is exact when its test says so. *)
Print Assumptions ball_pow2_radius.

(* Milestone 2, IEEE model: the statements of the finite domain that no kernel
   description names (two_sum_ord and fast_two_sum_entry on finite operands). *)
Definition two_sum_ord_ieee_audit : two_sum_ord_ieee_spec := two_sum_ord_ieee_correct.
Print Assumptions two_sum_ord_ieee_correct.

Definition fast_two_sum_entry_ieee_audit : fast_two_sum_entry_ieee_spec :=
  fast_two_sum_entry_ieee_correct.
Print Assumptions fast_two_sum_entry_ieee_correct.

(* The directed sums in the IEEE model (theories/IeeeDirected.v, theories/IeeeEntry.v):
   the lemmas beside the theorems that proofs/gen/IeeeAudit.v lists. The neighbors of the
   infinities, the directed roundings of the format with overflow on a real number,
   two_sum_ord and the directed sums on finite operands and with an operand that is not
   finite, and the guard on extended real numbers. *)
Print Assumptions pred_pinf.
Print Assumptions succ_ninf.
Print Assumptions pred_ninf.
Print Assumptions xrd_real.
Print Assumptions xru_real.
Print Assumptions two_sum_ord_ieee_finite.
Print Assumptions two_sum_ord_ieee_nonfinite.
Print Assumptions add_down_1_ieee_finite.
Print Assumptions add_up_1_ieee_finite.
Print Assumptions add_down_1_ieee_nonfinite.
Print Assumptions add_up_1_ieee_nonfinite.
Print Assumptions xval_guard.
Print Assumptions guard_nonneg.

(* The directed products in the IEEE model (theories/IeeeDirectedProd.v), likewise:
   mul_down_1 and mul_up_1 on finite operands and with an operand that is not finite, and
   the enclosure of a product of bounds by mul_dir_1, on an IEEE model of its listing
   written by hand (the kernel is not generated yet). *)
Print Assumptions mul_down_1_ieee_finite.
Print Assumptions mul_up_1_ieee_finite.
Print Assumptions mul_down_1_ieee_nonfinite.
Print Assumptions mul_up_1_ieee_nonfinite.
Print Assumptions xval_prod_nonfinite.
Print Assumptions mul_dir_1_ieee_eq.
Print Assumptions mul_dir_1_ieee_encloses.
(* A fold in two models (theories/FoldTransfer.v): lists only, no real number. *)
Print Assumptions fold_seq_transfer.
Print Assumptions fold_seq_transfer_prefix.
Print Assumptions fold_lanes_transfer.

(* The bound kernels (theories/BoundKernels.v): everything that holds of each, 0 <= g
   included, which the generated statements do not have. *)
Print Assumptions bound_sum_1_facts.
Print Assumptions bound_sum_2_facts.
Print Assumptions bound_dot_1_facts.
Print Assumptions bound_dot_2_facts.

(* The exported bound covers the error of the fold (theories/FoldGuarantee.v), for each
   fold of proofs/gen/FoldModel.v and each order. *)
Print Assumptions gamma_le_real.
Print Assumptions sum_1_seq_bound.
Print Assumptions sum_1_lanes_bound.
Print Assumptions sum_1_entry_seq_bound.
Print Assumptions sum_1_entry_lanes_bound.
Print Assumptions sum_2_seq_bound.
Print Assumptions sum_2_lanes_bound.
Print Assumptions sum_2_entry_seq_bound.
Print Assumptions sum_2_entry_lanes_bound.
Print Assumptions sum_fast_2_seq_bound.
Print Assumptions sum_fast_2_lanes_bound.
Print Assumptions sum_fast_2_entry_seq_bound.
Print Assumptions sum_fast_2_entry_lanes_bound.
Print Assumptions dot_1_seq_bound.
Print Assumptions dot_1_lanes_bound.
Print Assumptions dot_2_seq_bound.
Print Assumptions dot_2_lanes_bound.

(* The steps of the folds in the IEEE model (theories/IeeeSteps.v): the generated statements
   of proofs/gen/IeeeStatements.v, the bridge to the real model and, for the steps of two
   limbs, correctness. *)
Definition dot_step_1_ieee_bridge_audit : dot_step_1_ieee_bridge_spec := dot_step_1_ieee_bridge.
Print Assumptions dot_step_1_ieee_bridge.

Definition sum_entry_step_1_ieee_bridge_audit : sum_entry_step_1_ieee_bridge_spec :=
  sum_entry_step_1_ieee_bridge.
Print Assumptions sum_entry_step_1_ieee_bridge.

Definition dot_step_2_ieee_bridge_audit : dot_step_2_ieee_bridge_spec := dot_step_2_ieee_bridge.
Print Assumptions dot_step_2_ieee_bridge.

Definition dot_step_2_ieee_audit : dot_step_2_ieee_spec := dot_step_2_ieee_correct.
Print Assumptions dot_step_2_ieee_correct.

Definition sum_entry_step_2_ieee_bridge_audit : sum_entry_step_2_ieee_bridge_spec :=
  sum_entry_step_2_ieee_bridge.
Print Assumptions sum_entry_step_2_ieee_bridge.

Definition sum_entry_step_2_ieee_audit : sum_entry_step_2_ieee_spec :=
  sum_entry_step_2_ieee_correct.
Print Assumptions sum_entry_step_2_ieee_correct.

Definition sum_fast_entry_step_2_ieee_bridge_audit : sum_fast_entry_step_2_ieee_bridge_spec :=
  sum_fast_entry_step_2_ieee_bridge.
Print Assumptions sum_fast_entry_step_2_ieee_bridge.

Definition sum_fast_entry_step_2_ieee_audit : sum_fast_entry_step_2_ieee_spec :=
  sum_fast_entry_step_2_ieee_correct.
Print Assumptions sum_fast_entry_step_2_ieee_correct.

(* The leading limb of the result of each step and combination of a fold
   (theories/IeeeFolds.v): the generated statements of proofs/gen/IeeeFoldStatements.v. If it
   is finite, so is the leading limb of each operand. *)
Definition add_1_1_ieee_lead_audit : add_1_1_ieee_lead_spec := add_1_1_ieee_lead.
Print Assumptions add_1_1_ieee_lead.

Definition dot_step_1_ieee_lead_audit : dot_step_1_ieee_lead_spec := dot_step_1_ieee_lead.
Print Assumptions dot_step_1_ieee_lead.

Definition sum_entry_step_1_ieee_lead_audit : sum_entry_step_1_ieee_lead_spec :=
  sum_entry_step_1_ieee_lead.
Print Assumptions sum_entry_step_1_ieee_lead.

Definition add_2_2_ieee_lead_audit : add_2_2_ieee_lead_spec := add_2_2_ieee_lead.
Print Assumptions add_2_2_ieee_lead.

Definition add_fast_2_2_ieee_lead_audit : add_fast_2_2_ieee_lead_spec := add_fast_2_2_ieee_lead.
Print Assumptions add_fast_2_2_ieee_lead.

Definition dot_step_2_ieee_lead_audit : dot_step_2_ieee_lead_spec := dot_step_2_ieee_lead.
Print Assumptions dot_step_2_ieee_lead.

Definition sum_entry_step_2_ieee_lead_audit : sum_entry_step_2_ieee_lead_spec :=
  sum_entry_step_2_ieee_lead.
Print Assumptions sum_entry_step_2_ieee_lead.

Definition sum_fast_entry_step_2_ieee_lead_audit : sum_fast_entry_step_2_ieee_lead_spec :=
  sum_fast_entry_step_2_ieee_lead.
Print Assumptions sum_fast_entry_step_2_ieee_lead.

(* The folds in the IEEE model (theories/IeeeFolds.v): the generated statements of
   proofs/gen/IeeeFoldStatements.v, about the generated models of
   proofs/gen/IeeeFoldModel.v. If the flag is true, every element is finite and the result
   is that of the real model, valid and within its bound; otherwise every limb is a NaN. *)
Definition sum_1_seq_ieee_audit : sum_1_seq_ieee_spec := sum_1_seq_ieee_correct.
Print Assumptions sum_1_seq_ieee_correct.

Definition sum_1_lanes_ieee_audit : sum_1_lanes_ieee_spec := sum_1_lanes_ieee_correct.
Print Assumptions sum_1_lanes_ieee_correct.

Definition sum_1_entry_seq_ieee_audit : sum_1_entry_seq_ieee_spec := sum_1_entry_seq_ieee_correct.
Print Assumptions sum_1_entry_seq_ieee_correct.

Definition sum_1_entry_lanes_ieee_audit : sum_1_entry_lanes_ieee_spec :=
  sum_1_entry_lanes_ieee_correct.
Print Assumptions sum_1_entry_lanes_ieee_correct.

Definition dot_1_seq_ieee_audit : dot_1_seq_ieee_spec := dot_1_seq_ieee_correct.
Print Assumptions dot_1_seq_ieee_correct.

Definition dot_1_lanes_ieee_audit : dot_1_lanes_ieee_spec := dot_1_lanes_ieee_correct.
Print Assumptions dot_1_lanes_ieee_correct.

Definition sum_2_seq_ieee_audit : sum_2_seq_ieee_spec := sum_2_seq_ieee_correct.
Print Assumptions sum_2_seq_ieee_correct.

Definition sum_2_lanes_ieee_audit : sum_2_lanes_ieee_spec := sum_2_lanes_ieee_correct.
Print Assumptions sum_2_lanes_ieee_correct.

Definition sum_2_entry_seq_ieee_audit : sum_2_entry_seq_ieee_spec := sum_2_entry_seq_ieee_correct.
Print Assumptions sum_2_entry_seq_ieee_correct.

Definition sum_2_entry_lanes_ieee_audit : sum_2_entry_lanes_ieee_spec :=
  sum_2_entry_lanes_ieee_correct.
Print Assumptions sum_2_entry_lanes_ieee_correct.

Definition sum_fast_2_seq_ieee_audit : sum_fast_2_seq_ieee_spec := sum_fast_2_seq_ieee_correct.
Print Assumptions sum_fast_2_seq_ieee_correct.

Definition sum_fast_2_lanes_ieee_audit : sum_fast_2_lanes_ieee_spec :=
  sum_fast_2_lanes_ieee_correct.
Print Assumptions sum_fast_2_lanes_ieee_correct.

Definition sum_fast_2_entry_seq_ieee_audit : sum_fast_2_entry_seq_ieee_spec :=
  sum_fast_2_entry_seq_ieee_correct.
Print Assumptions sum_fast_2_entry_seq_ieee_correct.

Definition sum_fast_2_entry_lanes_ieee_audit : sum_fast_2_entry_lanes_ieee_spec :=
  sum_fast_2_entry_lanes_ieee_correct.
Print Assumptions sum_fast_2_entry_lanes_ieee_correct.

Definition dot_2_seq_ieee_audit : dot_2_seq_ieee_spec := dot_2_seq_ieee_correct.
Print Assumptions dot_2_seq_ieee_correct.

Definition dot_2_lanes_ieee_audit : dot_2_lanes_ieee_spec := dot_2_lanes_ieee_correct.
Print Assumptions dot_2_lanes_ieee_correct.

(* What theories/IeeeFolds.v proves beyond those statements, written by hand about the same
   generated models. The steps: a leading limb that is not finite stays not finite, and from
   finite operands a finite leading limb gives the values of the real model. *)
Print Assumptions add_1_1_dead.
Print Assumptions add_1_1_live.
Print Assumptions sum_entry_step_1_dead.
Print Assumptions sum_entry_step_1_live.
Print Assumptions dot_step_1_dead.
Print Assumptions dot_step_1_live.
Print Assumptions add22i_lead.
Print Assumptions add22i_live.
Print Assumptions addfast22i_lead.
Print Assumptions addfast22i_live.
Print Assumptions mul22i_lead.
Print Assumptions mul22i_live.
Print Assumptions sum_2_entry_step_ieee_live.
Print Assumptions sum_fast_2_entry_step_ieee_live.
Print Assumptions dot_2_step_ieee_dead.
Print Assumptions dot_2_step_ieee_live.

(* A fold of such steps with its finish, for one and two limbs and both orders. *)
Print Assumptions seq_1.
Print Assumptions lanes_1.
Print Assumptions seq_2.
Print Assumptions lanes_2.

(* Each fold in the sequential order, with what its generated statement does not say: the
   state after every element was finite (and a normalized pair, for two limbs). *)
Print Assumptions sum_1_seq_ieee_facts.
Print Assumptions sum_1_entry_seq_ieee_facts.
Print Assumptions dot_1_seq_ieee_facts.
Print Assumptions sum_2_seq_ieee_facts.
Print Assumptions sum_2_entry_seq_ieee_facts.
Print Assumptions sum_fast_2_seq_ieee_facts.
Print Assumptions sum_fast_2_entry_seq_ieee_facts.
Print Assumptions dot_2_seq_ieee_facts.
