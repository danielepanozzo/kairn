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
     difference of two intervals of two limbs, the sum with the negated operand.

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
