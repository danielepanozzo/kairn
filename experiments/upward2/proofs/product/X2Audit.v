(* EXPERIMENTAL proof probe: the assumptions of the main theorems of the product's half, for the
   axiom audit of the Makefile (proofs/audit/audit.py assumptions). Each must show only axioms
   among those of proofs/audit/allowed_axioms.txt. *)
From KairnX2P Require Import X2Defs X2Order X2PairMul X2MulBranch X2Excess.

Print Assumptions X2Order.upper_normalized_order.
Print Assumptions X2Order.upper_normalized_unique.
Print Assumptions X2Order.lexmax_correct.
Print Assumptions X2Order.upper_normalized_sign.
Print Assumptions X2PairMul.fast2sum_up_exact.
Print Assumptions X2PairMul.fast_two_sum_upper.
Print Assumptions X2PairMul.fast_two_sum_normalized.
Print Assumptions X2PairMul.fast_two_sum_error.
Print Assumptions X2PairMul.pair_mul_upper.
Print Assumptions X2PairMul.pair_mul_normalized.
Print Assumptions X2PairMul.pair_mul_correct.
Print Assumptions X2PairMul.pair_mul_tight.
Print Assumptions X2MulBranch.mul_branch_nonneg.
Print Assumptions X2MulBranch.mul_branch_zero_zero.
Print Assumptions X2MulBranch.mul_branch_correct.
Print Assumptions X2Excess.pair_mul_excess.
