(* The negation and the constructor of a ball vector in the real model: the generated
   statements of their kernels (proofs/gen/Statements.v) and of the folds bv_neg_k and
   bv_make_k (proofs/gen/FoldStatements.v).

   The kernels.
   - neg_1 (z = neg(x)): -x, a number of the format with x, its own rounding.
   - bv_neg_radius (rz = copy(rx)): rx.
   - bv_center_entry_1 (z = guard(c)): RN (c + 0) = c for a number of the format c.
   - bv_center_2 (a copy of a normalized pair): the pair.
   - bv_make_radius (g = guard(r); d = sub(m, m); rz = add(g, d)): g = r, d = RN 0 = 0, and
     rz = RN (r + 0) = r.

   The folds.
   - bv_neg_k: the centers written are the negated centers (neg_1, or neg_2 for two limbs,
     Sign.v), and the radius is rx whatever the largest magnitude m is. So the ball of
     each center written with radius rx is exactly the image of the operand's ball: a
     member x_ goes to -x_, within rx of -x, and a real v_ within rx of -x is -x_ for
     x_ = -v_, within rx of x.
   - bv_make_k: the centers written are those given (guard, or a copy) and the radius is
     the radius given (bv_make_radius at any m). *)
From Stdlib Require Import Reals ZArith List Lia Lra.
From Flocq Require Import Core.
From Kairn.Gen Require Import Model Statements FoldModel FoldStatements.
From Kairn Require Import Format Normalized Folds Guard Sign.
Import ListNotations.
Open Scope R_scope.

(** * The kernels *)

Theorem neg_1_correct : neg_1_spec.
Proof.
intros emin prec Hp x Fx. unfold neg_1. cbv zeta.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 1%Z; lia).
assert (F : fmt emin prec (- x)) by (apply generic_format_opp; exact Fx).
split. exact F. unfold RN. symmetry. apply round_generic; auto with typeclass_instances.
Qed.

Theorem bv_neg_radius_correct : bv_neg_radius_spec.
Proof.
intros emin prec Hp m rx Fm Frx. unfold bv_neg_radius. cbv zeta.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 1%Z; lia).
split. exact Frx. unfold RN. symmetry. apply round_generic; auto with typeclass_instances.
Qed.

Theorem bv_center_entry_1_correct : bv_center_entry_1_spec.
Proof.
intros emin prec Hp c Fc. unfold bv_center_entry_1. cbv zeta.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 1%Z; lia).
rewrite (guard_real_any emin prec tie_even c Fc).
split. exact Fc. unfold RN. symmetry. apply round_generic; auto with typeclass_instances.
Qed.

Theorem bv_center_2_correct : bv_center_2_spec.
Proof.
intros emin prec Hp x0 x1 H. unfold bv_center_2. cbv beta iota zeta.
split. exact H. reflexivity.
Qed.

(* bv_center_entry_2: bv_center_2 on the guarded limbs (rule R3). The guard of a number of the
   format is that number, and the limbs of a normalized pair are numbers of the format, so it is
   bv_center_2 on the pair given. *)
Theorem bv_center_entry_2_correct : bv_center_entry_2_spec.
Proof.
intros emin prec Hp c0 c1 H. unfold bv_center_entry_2. cbv zeta.
destruct H as [F0 [F1 E]].
rewrite (guard_real_any emin prec tie_even c0 F0), (guard_real_any emin prec tie_even c1 F1).
unfold bv_center_2. cbv beta iota zeta.
split. exact (conj F0 (conj F1 E)). reflexivity.
Qed.

(* The radius kernel of the constructor returns the radius given, whatever m is. *)
Lemma bv_make_radius_value :
  forall (emin prec : Z) (choice : Z -> bool) (m r : R), (1 <= prec)%Z ->
  generic_format radix2 (FLT_exp emin prec) r -> bv_make_radius emin prec choice m r = r.
Proof.
intros emin prec choice m r Hp Fr. unfold bv_make_radius. cbv zeta.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 1%Z; lia).
rewrite (guard_real_any emin prec choice r Fr).
replace (m - m) with 0 by ring. rewrite round_0 by auto with typeclass_instances.
exact (guard_real_any emin prec choice r Fr).
Qed.

Theorem bv_make_radius_correct : bv_make_radius_spec.
Proof.
intros emin prec Hp m r Fm Fr. cbv zeta.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 1%Z; lia).
rewrite (bv_make_radius_value emin prec tie_even m r Hp Fr).
split. exact Fr. unfold RN. symmetry. apply round_generic; auto with typeclass_instances.
Qed.

(** * The negation of a ball vector *)

(* The ball of -x with radius r is exactly the image of the ball of x with radius r. *)
Lemma neg_ball_image :
  forall x z r : R, z = - x ->
  (forall x_ : R, Rabs (x_ - x) <= r -> Rabs ((- x_) - z) <= r) /\
  (forall v_ : R, Rabs (v_ - z) <= r -> exists x_ : R, Rabs (x_ - x) <= r /\ v_ = (- x_)).
Proof.
intros x z r ->. split.
- intros x_ H. replace (- x_ - - x) with (- (x_ - x)) by ring. rewrite Rabs_Ropp. exact H.
- intros v_ H. exists (- v_). split; [|ring].
  replace (- v_ - x) with (- (v_ - - x)) by ring. rewrite Rabs_Ropp. exact H.
Qed.

Theorem bv_neg_1_correct : bv_neg_1_spec.
Proof.
intros emin prec Hp rx xs Frx Hrx H. cbv zeta.
unfold bv_neg_1_radius, bv_neg_radius. split. exact Frx.
unfold bv_neg_1_map. apply Forall2_map_r. revert H. apply Forall_impl. intros x Fx.
unfold bv_neg_1_step, neg_1. cbv zeta. split.
- apply generic_format_opp. exact Fx.
- exact (neg_ball_image x (- x) rx eq_refl).
Qed.

Theorem bv_neg_2_correct : bv_neg_2_spec.
Proof.
intros emin prec Hp rx xs Frx Hrx H. cbv zeta.
unfold bv_neg_2_radius, bv_neg_radius. split. exact Frx.
unfold bv_neg_2_map. apply Forall2_map_r. revert H. apply Forall_impl. intros [x0 x1] N.
unfold bv_neg_2_step, neg_2. cbn [fst snd] in N |- *. cbv beta iota zeta. split.
- apply normalized_2_opp. exact N.
- apply neg_ball_image. ring.
Qed.

(** * The constructor of a ball vector *)

Theorem bv_make_1_correct : bv_make_1_spec.
Proof.
intros emin prec Hp r cs Fr H.
unfold bv_make_1_radius. rewrite (bv_make_radius_value emin prec tie_even _ r Hp Fr).
split. reflexivity.
unfold bv_make_1_map. apply Forall2_map_r. revert H. apply Forall_impl. intros c Fc.
unfold bv_make_1_step, bv_center_entry_1. cbv zeta.
exact (guard_real_any emin prec tie_even c Fc).
Qed.

Theorem bv_make_2_correct : bv_make_2_spec.
Proof.
intros emin prec Hp r cs Fr H.
unfold bv_make_2_radius. rewrite (bv_make_radius_value emin prec tie_even _ r Hp Fr).
split. reflexivity.
unfold bv_make_2_map. apply Forall2_map_r. apply Forall_forall. intros [c0 c1] _.
reflexivity.
Qed.

(* bv_make_2_entry: bv_make_2 with the step bv_center_entry_2, whose guards are the identity on
   the limbs of normalized pairs (numbers of the format). *)
Theorem bv_make_2_entry_correct : bv_make_2_entry_spec.
Proof.
intros emin prec Hp r cs Fr H.
unfold bv_make_2_entry_radius. rewrite (bv_make_radius_value emin prec tie_even _ r Hp Fr).
split. reflexivity.
unfold bv_make_2_entry_map. apply Forall2_map_r. revert H. apply Forall_impl. intros [c0 c1] N.
cbn [fst snd] in N. destruct N as [F0 [F1 _]].
unfold bv_make_2_entry_step, bv_center_entry_2. cbn [fst snd]. cbv zeta.
rewrite (guard_real_any emin prec tie_even c0 F0), (guard_real_any emin prec tie_even c1 F1).
reflexivity.
Qed.
