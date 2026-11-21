(* The building blocks on T that become public in Milestone 2, in the real model (no
   overflow): next_up, next_down, and the entry forms two_sum_entry, fast_two_sum_entry
   and radd_entry (docs/developer/design/milestone2.md, "Building blocks on T",
   "Values that enter from the program", "next_up and next_down on every input").

   What is proved (the generated statements of proofs/gen/Statements.v):
   - next_up a is succ(a) and next_down a is pred(a), the neighbors of a in the format,
     and they are numbers of the format. These are the operations of the model; the
     statement that matters, on every input, is the one of the IEEE model (IeeeEntry.v);
   - an entry form guards its operands and calls the kernel of the same name. The guard
     of a number of the format is that number (Guard.v), so the entry form has the
     statement of the kernel it calls: two_sum_entry that of two_sum, fast_two_sum_entry
     that of fast_two_sum, radd_entry that of radd.
   The entry forms of the directed sums are in DirectedSum.v.
   - The entry forms of the products (rule R3, the factors of a fused operation): a compiler
     that sees a factor of a fused operation to be 1 fuses a product of the program into it,
     so the public products guard their operands too. two_prod_entry has the statement of
     two_prod, mul_down_entry and mul_up_entry those of mul_down_1 and mul_up_1, and
     mul_2_1_entry, which guards its scalar, that of mul_2_1, by the same argument. *)
From Stdlib Require Import Reals ZArith Lia Lra.
From Flocq Require Import Core.
From Kairn.Gen Require Import Model Statements.
From Kairn Require Import Format Guard EFT Directed DirectedProd Mul21.
Open Scope R_scope.

(* next_up: the next number of the format above a. *)
Theorem next_up_correct : next_up_spec.
Proof.
intros emin prec Hp a Fa r. unfold r, next_up. clear r. cbv zeta.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 1%Z; lia).
split; [limb_format|reflexivity].
Qed.

(* next_down: the next number of the format below a. *)
Theorem next_down_correct : next_down_spec.
Proof.
intros emin prec Hp a Fa r. unfold r, next_down. clear r. cbv zeta.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 1%Z; lia).
split; [limb_format|reflexivity].
Qed.

(* two_sum_entry: two_sum on its guarded operands. *)
Theorem two_sum_entry_correct : two_sum_entry_spec.
Proof.
intros emin prec Hp a b Fa Fb. unfold two_sum_entry. cbv zeta.
rewrite 2!guard_real_any by assumption.
generalize (two_sum_correct emin prec Hp a b Fa Fb).
destruct (two_sum emin prec tie_even a b) as [s e]. trivial.
Qed.

(* fast_two_sum_entry: fast_two_sum on its guarded operands, under the same requirement
   |b| <= |a|. *)
Theorem fast_two_sum_entry_correct : fast_two_sum_entry_spec.
Proof.
intros emin prec Hp a b Fa Fb Hab. unfold fast_two_sum_entry. cbv zeta.
rewrite 2!guard_real_any by assumption.
generalize (fast_two_sum_correct emin prec Hp a b Fa Fb Hab).
destruct (fast_two_sum emin prec tie_even a b) as [s e]. trivial.
Qed.

(* radd_entry: radd on its guarded operands. *)
Theorem radd_entry_correct : radd_entry_spec.
Proof.
intros emin prec Hp a b Fa Fb Pa Pb. unfold radd_entry. cbv zeta.
rewrite 2!guard_real_any by assumption.
exact (radd_correct emin prec Hp a b Fa Fb Pa Pb).
Qed.

(* two_prod_entry: two_prod on its guarded operands (rule R3, the factors of a fused
   operation). *)
Theorem two_prod_entry_correct : two_prod_entry_spec.
Proof.
intros emin prec Hp a b Fa Fb. unfold two_prod_entry. cbv zeta.
rewrite 2!guard_real_any by assumption.
generalize (two_prod_correct emin prec Hp a b Fa Fb).
destruct (two_prod emin prec tie_even a b) as [p e]. trivial.
Qed.

(* mul_down_entry and mul_up_entry: mul_down_1 and mul_up_1 on their guarded operands. *)
Theorem mul_down_entry_correct : mul_down_entry_spec.
Proof.
intros emin prec Hp a b Fa Fb. unfold mul_down_entry. cbv zeta.
rewrite 2!guard_real_any by assumption.
exact (mul_down_1_correct emin prec Hp a b Fa Fb).
Qed.

Theorem mul_up_entry_correct : mul_up_entry_spec.
Proof.
intros emin prec Hp a b Fa Fb. unfold mul_up_entry. cbv zeta.
rewrite 2!guard_real_any by assumption.
exact (mul_up_1_correct emin prec Hp a b Fa Fb).
Qed.

(* mul_2_1_entry: mul_2_1 on its guarded scalar; x is a number of the library. *)
Theorem mul_2_1_entry_correct : mul_2_1_entry_spec.
Proof.
intros emin prec Hp x0 x1 a Nx Fa. unfold mul_2_1_entry. cbv zeta.
rewrite guard_real_any by assumption.
generalize (mul_2_1_correct emin prec Hp x0 x1 a Nx Fa).
destruct (mul_2_1 emin prec tie_even x0 x1 a) as [z0 z1]. trivial.
Qed.
