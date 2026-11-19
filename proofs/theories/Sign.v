(* Sign changes and subtractions of 2-limb numbers: neg_2, abs_2, sub_2_2, sub_2_1,
   sub_1_2.

   Notation: a 2-limb number x = (x0, x1) is normalized when x0 = RN (x0 + x1), where RN is
   rounding to nearest, ties to even; its value is x0 + x1.

   What is proved (the generated statements of proofs/gen/Statements.v):
   - neg_2: (-x0, -x1) is normalized and its value is -x, exactly. Reason: the format is
     symmetric and so is the tie rule, hence RN (-t) = - RN (t).
   - abs_2: the kernel negates both limbs when x0 < 0. The result is normalized and its
     value is |x|, exactly. Reason: a normalized x has the sign of its leading limb
     (Normalized.v, item 3), so "x0 < 0" is "x < 0", and x0 = 0 forces x = 0.
   - sub_2_2, sub_2_1, sub_1_2: the corresponding addition applied to the negated operand,
     which is normalized by the first item; the statement of the addition is inherited
     with x - y in place of x + y, with the same constant and the same minimum precision.

   None of this needs more than a positive precision, except through the additions. *)
From Stdlib Require Import Reals ZArith Lia Lra.
From Flocq Require Import Core.
From Kairn.Gen Require Import Model Statements.
From Kairn Require Import Format Normalized Add22 Add21.
Open Scope R_scope.

(** * Negation *)

Theorem neg_2_correct : neg_2_spec.
Proof.
intros emin prec Hp x0 x1 Hn. unfold neg_2. cbv beta iota zeta.
split.
- now apply normalized_2_opp.
- ring.
Qed.

(** * Absolute value *)

(* The value of a normalized pair with a nonnegative leading limb is nonnegative. *)
Lemma normalized_2_nonneg :
  forall emin prec {prec_gt_0_ : Prec_gt_0 prec} x0 x1,
  normalized_2 emin prec x0 x1 -> 0 <= x0 -> 0 <= x0 + x1.
Proof.
intros emin prec Hp x0 x1 Hn [H|H].
- apply Rlt_le. now apply (normalized_2_pos emin prec x0 x1 Hn).
- symmetry in H. rewrite (normalized_2_zero emin prec x0 x1 Hn H), H. lra.
Qed.

Theorem abs_2_correct : abs_2_spec.
Proof.
intros emin prec Hp x0 x1 Hn.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 1%Z; lia).
unfold abs_2. cbv beta iota zeta.
destruct (Rlt_bool_spec x0 0) as [H|H].
- (* x0 < 0: both limbs are negated, and x < 0 *)
  split.
  + now apply normalized_2_opp.
  + generalize (normalized_2_neg emin prec x0 x1 Hn H). intros Hs.
    rewrite (Rabs_left (x0 + x1) Hs). ring.
- (* 0 <= x0: the pair is returned, and 0 <= x *)
  split.
  + exact Hn.
  + generalize (normalized_2_nonneg emin prec x0 x1 Hn H). intros Hs.
    now rewrite (Rabs_pos_eq (x0 + x1) Hs).
Qed.

(** * Subtractions *)

(* x - y = x + (-y), and -y is normalized. *)
Theorem sub_2_2_correct : sub_2_2_spec.
Proof.
intros emin prec Hp x0 x1 y0 y1 Nx Ny.
unfold sub_2_2. cbv zeta.
generalize (add_2_2_correct emin prec Hp x0 x1 (- y0) (- y1) Nx
              (normalized_2_opp emin prec y0 y1 Ny)).
destruct (add_2_2 emin prec tie_even x0 x1 (- y0) (- y1)) as [z0 z1].
cbv beta iota.
intros [Hn Hb]. split. exact Hn.
replace (x0 + x1 - (y0 + y1)) with (x0 + x1 + (- y0 + - y1)) by ring.
exact Hb.
Qed.

(* x - a = x + (-a), and -a is a number of the format. *)
Theorem sub_2_1_correct : sub_2_1_spec.
Proof.
intros emin prec Hp x0 x1 a Nx Fa.
unfold sub_2_1. cbv zeta.
assert (Fn : fmt emin prec (- a)).
{ unfold fmt in *. now apply generic_format_opp. }
generalize (add_2_1_correct emin prec Hp x0 x1 (- a) Nx Fn).
destruct (add_2_1 emin prec tie_even x0 x1 (- a)) as [z0 z1].
cbv beta iota.
intros [Hn Hb]. split. exact Hn.
replace (x0 + x1 - a) with (x0 + x1 + - a) by ring.
exact Hb.
Qed.

(* a - y = (-y) + a. *)
Theorem sub_1_2_correct : sub_1_2_spec.
Proof.
intros emin prec Hp a y0 y1 Fa Ny.
unfold sub_1_2. cbv zeta.
generalize (add_2_1_correct emin prec Hp (- y0) (- y1) a
              (normalized_2_opp emin prec y0 y1 Ny) Fa).
destruct (add_2_1 emin prec tie_even (- y0) (- y1) a) as [z0 z1].
cbv beta iota.
intros [Hn Hb]. split. exact Hn.
replace (a - (y0 + y1)) with (- y0 + - y1 + a) by ring.
exact Hb.
Qed.
