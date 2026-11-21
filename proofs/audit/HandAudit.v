(* Audit of the theorems that the generated audits do not list.

   proofs/gen/Audit.v lists the theorem of every real-model statement, and
   proofs/gen/IeeeAudit.v the theorem of the IEEE-model statement of every kernel of the
   extended domain (the kernels with an ieee_theorem line), then the theorem of every
   other generated IEEE-model statement that a description names. This file lists the
   rest:

   - theorems about generated statements that no kernel description names: the IEEE-model
     statements of the kernels of the finite domain of Milestone 1 and of the first
     building blocks of Milestone 2, printed in proofs/gen/IeeeStatements.v
     (K_ieee_bridge_spec: the bridge to the real model; K_ieee_spec: correctness;
     K_ieee_finite_spec and K_ieee_finite_result_spec: no overflow below a threshold).
     A description can name the first two (ieee_bridge_theorem, ieee_spec_theorem), and
     those of the steps of the folds do, with the theorems of the leading limbs
     (ieee_lead_theorem) and of the folds in the IEEE model (ieee_theorem):
     proofs/gen/IeeeAudit.v lists these, and this file no longer does. The descriptions
     of the kernels of Milestone 1 and of the first building blocks do not name theirs
     yet, and nothing names the theorem of a threshold;
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
     two_prod, what mul_dir_1 returns beside its generated statements, the rectangle
     lemma of the product of intervals, the two executions of a product, and the two
     executions of the eight kernels whose only fused operations are products, on
     listings written by hand with the product as an argument (the generator does not
     emit the model of the plain-product execution);
   - what is proved of the interval kernels of Milestone 2 and of the conversions of a
     ball beside their generated statements, which the generated audits list: for the
     conversions of a ball, the lemmas their theorems rest on; for the interval kernels
     with bounds
     of one limb, the statements written by hand that say more or say it in another form
     (the special cases of the constructor, the negation as an exact image, the product
     in the least and the greatest of four products of bounds) and the lemmas about the
     bounds of the exact range of an operation; for the bounds of two limbs in the real
     model (a sum, a difference and a product moved outward by a bound of their own
     error), the same bounds in the values of the kernel and with the constants of the
     closed form by name, and the lemmas they rest on; and for the sum of two intervals
     with bounds of two limbs in the IEEE model, its finite cores, when they are finite,
     and its statement with the constants of the closed form by name; for the exact
     interval kernels of stage B1 (the negation and the constructor of two limbs, the hulls
     and the intersections), the hull and the intersection of intervals of extended real
     numbers and the lemmas that carry them to limbs and to 2-limb values; for the
     difference of two intervals of two limbs, the sum with the negated operand; for the
     conversions between an interval and a ball of one limb, the midpoint of a bounded
     interval over the real numbers and on limbs, and the cases of a canonical interval; and
     for the product of two intervals of two limbs, the finite core of the directed product,
     the facts of each product of bounds, and the statements with the constants by name; for
     the predicates, comparisons and relations of intervals of stage B2, each relation on the
     bounds as extended real numbers and the facts about members it rests on;
   - the theorems about the folds that have no generated statement: that a fold of the
     model with overflow is the fold of the real model whenever its result is finite
     (theories/FoldTransfer.v), what holds of the bound kernels beyond their generated
     statements (theories/BoundKernels.v), that the exported bound covers the error
     of each fold in each order (theories/FoldGuarantee.v), and what
     theories/IeeeFolds.v proves of the generated models of the folds in the IEEE model
     beyond their generated statements: the two facts about one application of each
     step, a fold of such steps with its finish, and the state after every element in
     the sequential order;
   - the arithmetic of the steps of the maps (theories/MapSteps.v), beside their theorems,
     which proofs/gen/Audit.v lists: the error of a product followed by a sum, and its
     three instances, with the constants of the steps of axpy;
   - the lemmas of theories/Folds.v about a loop that writes an array, beside the
     theorems of the maps (theories/FoldMaps.v), which the descriptions of the maps
     name and proofs/gen/Audit.v lists;
   - the folds of maxima, beside the theorems of their generated statements, which the
     generated audits list: the lemma of theories/Folds.v they rest on, that a
     combination which is associative and commutative on the states of a loop makes the
     lane order return the state of the sequential order; in the real model
     (theories/FoldNorm.v), that the two orders return the same state, what that state
     is, and the facts about a normalized pair behind the bound of two limbs; in the
     IEEE model (theories/IeeeFoldNorm.v), that the two orders return the same result
     and the same flag on every input, the statements of the sequential order with the
     elements as finite normalized pairs, and when the flag is true;
   - the convolutions (theories/FoldConv.v), beside their theorems, which
     proofs/gen/Audit.v lists: what the terms of a coefficient are, which the generated
     statements name and do not describe, how many there are, and that one answer of
     the bound kernel of the dot product covers every coefficient.

   Same form as the generated audits: for every theorem, a silent definition that fails
   to compile unless the theorem has the stated type, then the axioms it depends on, for
   the audit script to compare with the allow-list. Nothing else is printed. *)
From Kairn.Gen Require Import Statements IeeeStatements.
From Kairn Require Import IeeeVocabulary IeeeEFT IeeeAdd22 IeeeMul22 IeeeMore IeeeSub IeeeFinite.
From Kairn Require Import Split Directed MulPow2.
From Kairn Require Import Guard IeeeOps.
From Kairn Require Import Folds Summation SummationKernels.
From Kairn Require Import DirectedSum DirectedProd BallPow2 Rectangle IeeeProduct.
From Kairn Require Import IeeeDirected IeeeDirectedProd IeeeEntry.
From Kairn Require Import IeeeTwoExecutions.
From Kairn Require Import StepKernels FoldTransfer BoundKernels FoldGuarantee.
From Kairn Require Import MapSteps.
From Kairn Require Import IeeeFolds.
From Kairn Require Import FoldNorm IeeeFoldNorm FoldConv.

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

(* Summation: the two orders of a loop over arrays as functions on lists, and a loop
   that writes an array: the list it writes, entry by entry, and its mask in the two
   orders (theories/Folds.v); then the tree theorem, its closed forms, and the bounds of
   the two orders (theories/Summation.v). Real arithmetic about an addition of which only
   an error bound is known; no kernel is named. *)
Print Assumptions lane_nth.
Print Assumptions fold_lanes_short.
Print Assumptions fold_seq_map.
Print Assumptions fold_lanes_map.
Print Assumptions Forall2_map_r.
Print Assumptions Forall2_map_r_inv.
Print Assumptions map_entries.
Print Assumptions Forall2_map_nth.
Print Assumptions fold_seq_and.
Print Assumptions fold_lanes_and.
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
   mul_dir_1 as the pair of the two, with which of the two values each output is (its
   generated statement is listed by proofs/gen/Audit.v). *)
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
Print Assumptions mul_dir_1_eq.
Print Assumptions mul_dir_1_cases.

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
   mul_dir_1: the listing as the two directed products with the literal zero for a zero
   factor, the test of that factor, and the enclosure of a product of bounds. *)
Print Assumptions mul_down_1_ieee_finite.
Print Assumptions mul_up_1_ieee_finite.
Print Assumptions mul_down_1_ieee_nonfinite.
Print Assumptions mul_up_1_ieee_nonfinite.
Print Assumptions xval_prod_nonfinite.
Print Assumptions mul_dir_1_ieee_eq.
Print Assumptions zero_factor_test.
Print Assumptions mul_dir_1_ieee_encloses.

(* The interval kernels with bounds of one limb, in the IEEE model
   (theories/IeeeInterval1.v, with the vocabulary of theories/IeeeIntervalVocabulary.v):
   the theorems of their generated statements are listed by proofs/gen/IeeeAudit.v. Here,
   what is stated by hand beside them: the two special cases of the constructor, the
   negation in the form "the result is the exact image, bounded exactly when the operand
   is", and the product without its tightness; then the lemmas they rest on: a set of
   real numbers has one lower bound and one upper bound, the bounds of the set of the
   members of an interval, the bounds of the exact range of a negation, of a sum and of
   a difference, and the last five lines that the sum, the difference and the product
   share. *)
From Kairn Require Import IeeeIntervalVocabulary IeeeInterval1.
Print Assumptions interval_make_1_reversed.
Print Assumptions interval_make_1_equal_infinities.
Print Assumptions interval_neg_1_exact.
Print Assumptions interval_mul_1_enclosure.
Print Assumptions range_lower_unique.
Print Assumptions range_upper_unique.
Print Assumptions range_member_lower.
Print Assumptions range_member_upper.
Print Assumptions range_neg_lower.
Print Assumptions range_neg_upper.
Print Assumptions range_add_lower.
Print Assumptions range_add_upper.
Print Assumptions range_sub_lower.
Print Assumptions range_sub_upper.
Print Assumptions interval_tail.

(* The bounds of two limbs, in the real model (theories/Directed2.v): the theorems of
   their generated statements are listed by proofs/gen/Audit.v. Here, the lemmas they
   rest on and the statements written by hand beside them: add_ball_2_2 and mul_ball_2_2
   are the ball kernels with radii zero; one rounding to nearest from above, the radius
   from above and the closed form of the outward move; the rule of the zero sum; the form
   in which the listings compute the second limb of a lower bound; and the directed sums,
   differences and product, in the values of the kernel and with the constants of the
   closed form by name. *)
From Kairn Require Import Directed2.
Print Assumptions add_ball_2_2_eq.
Print Assumptions mul_ball_2_2_eq.
Print Assumptions rnd_upper.
Print Assumptions rnd_upper_normal.
Print Assumptions radius_upper.
Print Assumptions outward_closed.
Print Assumptions add_2_2_zero_sum.
Print Assumptions RD_as_opp_RU.
Print Assumptions sub_down_1_as_add_up_1.
Print Assumptions outward_down.
Print Assumptions outward_up.
Print Assumptions add_down_2_2_values.
Print Assumptions add_up_2_2_values.
Print Assumptions add_down_2_2_outward.
Print Assumptions add_up_2_2_outward.
Print Assumptions sub_down_2_2_values.
Print Assumptions sub_up_2_2_values.
Print Assumptions sub_down_2_2_outward.
Print Assumptions sub_up_2_2_outward.
Print Assumptions mul_dir_2_2_values.
Print Assumptions mul_dir_2_2_outward.

(* The tightness of the product of intervals of one limb (theories/IeeeInterval1.v): the
   two outputs of mul_dir_1 against the directed roundings of a product of bounds, the
   bounds of the exact range of a product, and the bounds of the result against them. *)
Print Assumptions mul_dir_1_lower.
Print Assumptions mul_dir_1_upper.
Print Assumptions range_mul_lower.
Print Assumptions range_mul_upper.
Print Assumptions interval_mul_1_tight.
Print Assumptions interval_mul_1_tight_range.

(* The sum of two intervals with bounds of two limbs, in the IEEE model
   (theories/IeeeInterval2.v): the theorem of its generated statement is listed by
   proofs/gen/IeeeAudit.v. Here, the lemmas it rests on: the finite cores add_ball_2_2,
   add_down_2_2 and add_up_2_2, whose finite result is that of the real model; the two
   constants of the radius from above, and the cores finite when the exact sum is within
   a quarter of the range; the last lines of the listing; the bounds of the exact range;
   and the statement itself in two forms written by hand: I1 to I3 alone, and I1 to I5
   with the constants of the closed form by name. *)
From Kairn Require Import IeeeInterval2.
Print Assumptions add_ball_2_2_ieee_core.
Print Assumptions add_down_2_2_ieee_core.
Print Assumptions add_up_2_2_ieee_core.
Print Assumptions E_add_2_le_eighth.
Print Assumptions H_add_le_tiny.
Print Assumptions add_ball_2_2_ieee_small.
Print Assumptions add_down_2_2_ieee_small.
Print Assumptions add_up_2_2_ieee_small.
Print Assumptions interval_tail_2.
Print Assumptions range_add_2_lower.
Print Assumptions range_add_2_upper.
Print Assumptions interval_add_2_enclosure.
Print Assumptions interval_add_2_all.

(* The conversions of a ball, in the IEEE model (theories/IeeeBallConvert.v): the bounds
   of a ball as numbers of T, the narrowing of a ball of two limbs and the ball made from
   an interval of two values of T. The theorems of the generated statements of the six
   kernels are listed by proofs/gen/IeeeAudit.v. Here, the lemmas they rest on: the
   bounds of a segment and of the whole line; the center of a ball of two limbs rounded
   down and up; two roundings, each within the gap of the format; the radius of the
   narrowed ball, finite within a quarter of the range; halving a number of the format,
   and doubling it back; and the finite ball made from a bounded interval. *)
From Kairn Require Import IeeeBallConvert.
Print Assumptions range_segment_lower.
Print Assumptions range_segment_upper.
Print Assumptions range_line_lower.
Print Assumptions range_line_upper.
Print Assumptions to_down_2_le.
Print Assumptions to_up_2_ge.
Print Assumptions two_gaps.
Print Assumptions radd_small.
Print Assumptions half_error.
Print Assumptions half_inexact_small.
Print Assumptions format_double.
Print Assumptions half_of_bound.
Print Assumptions ball_from_interval_2_eq.
Print Assumptions ball_from_interval_2_finite.

(* The exact interval kernels of stage B1, in the IEEE model (theories/IeeeIntervalExact.v):
   the negation and the constructor of an interval of two limbs, and the hulls and the
   intersections of intervals of one and of two limbs. The theorems of their generated
   statements are listed by proofs/gen/IeeeAudit.v. Here, the lemmas they rest on: the hull
   and the intersection of two intervals of extended real numbers; a canonical interval of
   two limbs and its emptiness, by what its bounds stand for; the selection of a 2-limb
   value by lt_2_2; the negated interval of two limbs; and the four kernels of the set
   operations for any limbs that stand for the minimum and the maximum of the bounds. *)
From Kairn Require Import IeeeIntervalExact.
Print Assumptions xhull.
Print Assumptions xinter.
Print Assumptions interval_2_iff.
Print Assumptions select_lt_2_xmin.
Print Assumptions select_lt_2_xmax.
Print Assumptions xval_2_neg.
Print Assumptions interval_neg_2_facts.
Print Assumptions interval_neg_2_all.
Print Assumptions interval_make_2_all.
Print Assumptions hull_1_of.
Print Assumptions intersection_1_of.
Print Assumptions hull_2_of.
Print Assumptions intersection_2_of.

(* The difference of two intervals with bounds of two limbs, in the IEEE model
   (theories/IeeeIntervalSub2.v): the theorem of its generated statement is listed by
   proofs/gen/IeeeAudit.v. Here, the lemmas it rests on: the directed differences are the
   directed sums on the negated operand, the listing is interval_add_2 on the negated
   operand, the exact range of the difference is that of the sum, and the statement with the
   constants of the closed form by name. *)
From Kairn Require Import IeeeIntervalSub2.
Print Assumptions sub_down_2_2_as_add.
Print Assumptions sub_up_2_2_as_add.
Print Assumptions sub_test.
Print Assumptions interval_sub_2_as_add.
Print Assumptions range_sub_2_as_add.
Print Assumptions interval_sub_2_all.

(* The conversions between an interval and a ball of one limb, the midpoint and the radius of
   an interval and its split, in the IEEE model (theories/IeeeIntervalConvert.v). The theorems
   of their generated statements are listed by proofs/gen/IeeeAudit.v. Here, the lemmas they
   rest on: the cases of a canonical interval of one limb; the bounds of the members of a
   ball; the halvings that are exact; the error of the rounded sum of the halves, and its
   distance to the bounds; the rounding up of the larger of two numbers; the two selects
   that move the midpoint into the interval; the midpoint and the radius of a bounded
   interval; and the four statements written with the names of this file. *)
From Kairn Require Import IeeeIntervalConvert.
Print Assumptions interval_1_cases.
Print Assumptions ball_1_bounds.
Print Assumptions half_exact_large.
Print Assumptions mid_error.
Print Assumptions mid_above.
Print Assumptions mid_below.
Print Assumptions RU_max.
Print Assumptions clamp_facts.
Print Assumptions prod_half.
Print Assumptions sub_up_value.
Print Assumptions mid_rad_bounded.
Print Assumptions interval_mid_rad_1_eq.
Print Assumptions ball_to_interval_1_all.
Print Assumptions interval_mid_rad_1_all.
Print Assumptions interval_to_ball_1_all.
Print Assumptions interval_split_1_all.

(* The product of two intervals with bounds of two limbs, in the IEEE model
   (theories/IeeeIntervalMul2.v): the theorems of the generated statements of mul_ext_2_2 and
   interval_mul_2 are listed by proofs/gen/IeeeAudit.v. Here, the lemmas they rest on: the
   bound of the least and of the greatest of four values; the constants of the closed form
   (E at most 1/8, A at most 1, B nonnegative); the finite core of mul_ball_2_2 and
   mul_dir_2_2, and the core finite within a quarter of the range; the sign of a normalized
   pair and the product with an infinite factor; the facts of a product of bounds; and the
   two statements with the constants by name. *)
From Kairn Require Import IeeeIntervalMul2.
Print Assumptions below_mono.
Print Assumptions min_tight.
Print Assumptions max_tight.
Print Assumptions xmin4_mono.
Print Assumptions xmax4_mono.
Print Assumptions xmul0_xmul.
Print Assumptions E_mul_2_le_eighth.
Print Assumptions mul_rel_bounds.
Print Assumptions mul_abs_ge_0.
Print Assumptions mul_ball_2_2_ieee_core.
Print Assumptions mul_dir_2_2_ieee_core.
Print Assumptions mul_dir_2_2_ieee_small.
Print Assumptions normalized_sign.
Print Assumptions xval_2_lead_class.
Print Assumptions xmul_2_lead.
Print Assumptions mul_ext_2_2_all.
Print Assumptions mul_ext_2_2_small.
Print Assumptions mul_ext_corner.
Print Assumptions interval_mul_2_of.
Print Assumptions interval_mul_2_all.

(* The predicates, the three-valued comparisons and the relations of IEEE 1788 of intervals of
   one and of two limbs, in the IEEE model (theories/IeeeIntervalPredicates.v): the theorems of
   their generated statements are listed by proofs/gen/IeeeAudit.v. Here, the lemmas they rest
   on: the order of the extended real numbers; the members of a nonempty interval below or
   above a number, and of two nonempty intervals in every choice; each relation on the bounds
   as extended real numbers; and the tests of the leading limb of a canonical 2-limb value. *)
From Kairn Require Import IeeeIntervalPredicates.
Print Assumptions xeq_eq.
Print Assumptions xeq_refl.
Print Assumptions xlt_le.
Print Assumptions xlt_le_trans.
Print Assumptions xle_lt_trans.
Print Assumptions xlt_false_le.
Print Assumptions xle_false_lt.
Print Assumptions xupper_lt.
Print Assumptions xupper_le.
Print Assumptions xlower_gt.
Print Assumptions xlower_ge.
Print Assumptions xlower_ge_x.
Print Assumptions xupper_le_x.
Print Assumptions xinterval_ne_l.
Print Assumptions xinterval_ne_r.
Print Assumptions xall_lt.
Print Assumptions xall_le.
Print Assumptions xall_ne_common.
Print Assumptions xall_ne.
Print Assumptions xempty.
Print Assumptions xentire.
Print Assumptions xsubset.
Print Assumptions xpositive.
Print Assumptions xnegative.
Print Assumptions xzero.
Print Assumptions xless.
Print Assumptions xless_equal.
Print Assumptions xequal.
Print Assumptions xrel_equal.
Print Assumptions xopen.
Print Assumptions xinterior.
Print Assumptions xdisjoint.
Print Assumptions xcontains.
Print Assumptions lead_tests.
Print Assumptions interval_1_parts.
Print Assumptions interval_2_parts.

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

(* What theories/IeeeFolds.v proves beyond the generated statements of the folds in the IEEE
   model, written by hand about the same generated models. (The theorems of the generated
   statements themselves, F_seq_ieee_correct and F_lanes_ieee_correct, K_ieee_lead, and
   K_ieee_bridge and K_ieee_correct of the steps, are named by the descriptions and
   listed by proofs/gen/IeeeAudit.v.) The steps: a leading limb that is not finite stays
   not finite, and from finite operands a finite leading limb gives the values of the
   real model. *)
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

(* The steps of the maps (theories/MapSteps.v): the theorems of their generated statements
   are listed by proofs/gen/Audit.v; these are the lemmas beside them. A product within
   em |X| + tm of X, then a sum of relative error ea, is within
   (ea (1 + em) + em) (|X| + |Y|) + (1 + ea) tm of X + Y; the three instances have the
   constants that the steps of axpy claim; and the relative error of add_2_2 is at most
   3/32 from precision 3. *)
Print Assumptions axpy_compose.
Print Assumptions rel_add_2_2_le.
Print Assumptions axpy_step_1_arith.
Print Assumptions axpy_step_2_arith.
Print Assumptions axpy_step_2_1_arith.

(* A combination that is associative and commutative on the states of a loop
   (theories/Folds.v): lists only. The sequential order is the combination of the images
   of the elements, and the lane order returns its state, for every number of lanes; the
   second theorem is the case of a step that is the combination after a function of the
   element. *)
Print Assumptions fold_seq_combined.
Print Assumptions fold_lanes_aci_step.
Print Assumptions fold_lanes_aci.

(* The folds of maxima in the real model (theories/FoldNorm.v): the theorems of their
   generated statements are listed by proofs/gen/Audit.v; these are beside them. The two
   orders return the same state; the final state is the largest magnitude (of the leading
   limbs, for two limbs) with a true mask; a normalized pair is below the successor of
   the magnitude of its leading limb, and a number of the format above the pair is above
   that limb; and the bound of two limbs on the two largest magnitudes, the first
   inequality strictly. *)
Print Assumptions norm_upper_1_lanes_seq.
Print Assumptions norm_upper_2_lanes_seq.
Print Assumptions norm_upper_1_seq_value.
Print Assumptions norm_upper_2_seq_value.
Print Assumptions normalized_2_abs_lt_succ.
Print Assumptions normalized_2_lead_le.
Print Assumptions norm_upper_2_bound.
Print Assumptions norm_upper_2_strict.

(* The folds of maxima in the IEEE model (theories/IeeeFoldNorm.v): the theorems of the
   generated statements of the finishes and of the folds are listed by
   proofs/gen/IeeeAudit.v; these are beside them. The lane order returns the state, the
   result and the flag of the sequential order on every list, NaN and infinities
   included; the sequential order with what its generated statement does not say (for two
   limbs, the elements are finite normalized pairs); and the flag is true exactly when
   every element is finite (one limb), or every leading limb is finite and the step up
   from the final state is (two limbs). *)
Print Assumptions norm_upper_1_lanes_seq_state.
Print Assumptions norm_upper_2_lanes_seq_state.
Print Assumptions norm_upper_1_lanes_seq_ieee.
Print Assumptions norm_upper_2_lanes_seq_ieee.
Print Assumptions norm_upper_1_seq_ieee_facts.
Print Assumptions norm_upper_2_seq_ieee_facts.
Print Assumptions norm_upper_1_seq_ieee_flag.
Print Assumptions norm_upper_2_seq_ieee_flag.

(* The convolutions (theories/FoldConv.v): the theorems of their generated statements are
   listed by proofs/gen/Audit.v; these are beside them. The terms of coefficient j, the
   list conv_terms xs ys j of proofs/gen/FoldModel.v: they satisfy the requirements of
   the coefficients of the two polynomials; there are at most min (n_x, n_y) of them, at
   least one, and min (j + 1, n_x) - (j - (n_y - 1)) with at least one y; term k is
   (x_i, y_(j-i)) with i = j - (n_y - 1) + k, and the list is exactly those pairs in
   increasing i. A statement in the form of a convolution's, read index by index. And the
   exported bound of the dot product, for a count of at least min (n_x, n_y), on every
   coefficient. *)
Print Assumptions conv_terms_Forall.
Print Assumptions conv_terms_length_eq.
Print Assumptions conv_terms_length.
Print Assumptions conv_terms_count.
Print Assumptions conv_terms_nonempty.
Print Assumptions conv_terms_nth.
Print Assumptions conv_terms_eq.
Print Assumptions Forall2_seq_nth.
Print Assumptions conv_1_bound.
Print Assumptions conv_2_bound.
