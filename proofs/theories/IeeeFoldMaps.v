(* The maps in the IEEE model: the generated statements F_seq_ieee_spec and
   F_lanes_ieee_spec of the eighteen loops that write an array
   (proofs/gen/IeeeFoldStatements.v), add_k, sub_k, axpy_k, axpy_2_1 and their _entry
   forms, scale_k and mul_pow2_map_k.

   The model (proofs/gen/IeeeFoldModel.v). A map F writes ws = map F_step xs, the IEEE
   model of its step on the scalars and each element; keeps a mask, the and of the flag of
   F_check over the elements written, by fold_seq in the sequential order and by
   fold_lanes with andb in the lane order; and returns ws when the mask is true, and when
   it is false the elements that F_check returns of them (the second pass). F_check is
   fold_finish_k: its flag says that the leading limb is finite, and it returns the
   element when it is, and NaN in every limb when it is not (IeeeFoldFinish.v).

   The statement, entry by entry (Forall2) of the elements read and the elements returned:
   if the leading limb returned is finite, every limb of the scalars, of the element and
   of the element returned is finite, the values are those of the real-model step on the
   values given, and the claims of the step hold; otherwise every limb returned is a NaN
   and the mask is false; and the mask is true exactly when every leading limb returned is
   finite. For canonical elements and scalars (a pair of two limbs canonical_2, any value
   of one limb, a scalar that is a power of two finite).

   How.
   - The mask is forallb of the flag of the check, in both orders (fold_seq_and,
     fold_lanes_and of Folds.v), so the two orders have one proof, and a case analysis on
     its value splits it: true, every element written is finite and is the element
     returned (map_entries_mask_true); false, the elements returned are the check's, an
     element written that is finite is kept, and the others are NaN in every limb, of
     which there is at least one (map_entries_mask_false). The facts of the check that
     these ask are check_k_flag, check_k_kept and check_k_bad below.
   - Entry by entry, an element written with a finite leading limb: the theorem of the
     step's leading limb (K_ieee_lead, IeeeMapSteps.v and IeeeFolds.v) gives the leading
     limbs of the operands finite, and a canonical pair with a finite leading limb is
     finite and normalized (canonical_lead); then the bridge of the step (K_ieee_bridge)
     gives the values of the real model, and the real-model theorem of the step (or
     K_ieee_correct, for two limbs) its claims. These are the lemmas K_entry, one per
     step, stated as the statements print the claims; the steps add_2_2 and sub_2_2 have
     the bridges and claims of Milestone 1 (IeeeAdd22.v, IeeeSub.v).
   - The proof of each statement is the same few steps (masked_map below), given the
     entry lemma of its step. *)
From Stdlib Require Import Reals ZArith List Lia Lra.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements IeeeStatements FoldModel IeeeFoldStatements.
From Kairn Require Import Format IeeeBridge IeeeVocabulary IeeeOps Folds OneLimb Add22 Sign MapSteps
  IeeeAdd22 IeeeSub IeeeFoldFinish IeeeFolds IeeeMapSteps.
From Kairn Require IeeeOperations.
From Kairn.Gen Require IeeeModel IeeeFoldModel.
Import ListNotations.
Open Scope R_scope.

Section IeeeFoldMaps.
Variable prec emax : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Context {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}.

Notation float := (binary_float prec emax).
Notation nan_of := {x : float | is_nan prec emax x = true}.
Variable nan_plus : float -> float -> nan_of.
Variable nan_minus : float -> float -> nan_of.
Variable nan_opp : float -> nan_of.
Variable nan_abs : float -> nan_of.
Variable nan_fma : float -> float -> float -> nan_of.
Variable nan_const : nan_of.

Notation emin := (ieee_emin prec emax).

(** * The check of an element written *)

Definition check_1 (w : float) : float * bool :=
  IeeeModel.fold_finish_1 prec emax nan_abs nan_const w.

Definition check_2 (w : float * float) : float * float * bool :=
  IeeeModel.fold_finish_2 prec emax nan_abs nan_const (fst w) (snd w).

Lemma check_1_flag : forall w : float, snd (check_1 w) = true <-> finite w.
Proof.
intros w. unfold check_1.
generalize (fold_finish_1_correct prec emax prec_gt_0_ prec_lt_emax_ nan_abs nan_const w).
destruct (IeeeModel.fold_finish_1 prec emax nan_abs nan_const w) as [r flag].
intros [H _]. exact H.
Qed.

Lemma check_1_kept : forall w : float, finite w -> fst (check_1 w) = w.
Proof.
intros w Fw. unfold check_1.
generalize (fold_finish_1_correct prec emax prec_gt_0_ prec_lt_emax_ nan_abs nan_const w).
destruct (IeeeModel.fold_finish_1 prec emax nan_abs nan_const w) as [r flag].
intros [H1 [H2 _]]. exact (H2 (proj2 H1 Fw)).
Qed.

Lemma check_1_bad : forall w : float, ~ finite w -> nan (fst (check_1 w)).
Proof.
intros w Nw. unfold check_1.
generalize (fold_finish_1_correct prec emax prec_gt_0_ prec_lt_emax_ nan_abs nan_const w).
destruct (IeeeModel.fold_finish_1 prec emax nan_abs nan_const w) as [r flag].
intros [H1 [_ H3]]. apply H3. destruct flag; [|reflexivity]. exfalso. now apply Nw, H1.
Qed.

Lemma nan_1_not_finite : forall w : float, nan w -> ~ finite w.
Proof.
intros w N F. unfold nan, finite in *. rewrite (nan_not_finite prec emax w N) in F. discriminate F.
Qed.

Lemma check_2_flag : forall w : float * float, snd (check_2 w) = true <-> finite (fst w).
Proof.
intros [w0 w1]. unfold check_2. cbn [fst snd].
generalize (fold_finish_2_correct prec emax prec_gt_0_ prec_lt_emax_ nan_abs nan_const w0 w1).
destruct (IeeeModel.fold_finish_2 prec emax nan_abs nan_const w0 w1) as [[r0 r1] flag].
intros [H _]. exact H.
Qed.

Lemma check_2_kept : forall w : float * float, finite (fst w) -> fst (check_2 w) = w.
Proof.
intros [w0 w1] Fw. unfold check_2. cbn [fst snd] in *.
generalize (fold_finish_2_correct prec emax prec_gt_0_ prec_lt_emax_ nan_abs nan_const w0 w1).
destruct (IeeeModel.fold_finish_2 prec emax nan_abs nan_const w0 w1) as [[r0 r1] flag].
intros [H1 [H2 _]]. destruct (H2 (proj2 H1 Fw)) as [E0 E1]. cbn [fst]. now rewrite E0, E1.
Qed.

Lemma check_2_bad :
  forall w : float * float, ~ finite (fst w) ->
  nan (fst (fst (check_2 w))) /\ nan (snd (fst (check_2 w))).
Proof.
intros [w0 w1] Nw. unfold check_2. cbn [fst snd] in *.
generalize (fold_finish_2_correct prec emax prec_gt_0_ prec_lt_emax_ nan_abs nan_const w0 w1).
destruct (IeeeModel.fold_finish_2 prec emax nan_abs nan_const w0 w1) as [[r0 r1] flag].
intros [H1 [_ H3]]. cbn [fst snd]. apply H3.
destruct flag; [|reflexivity]. exfalso. now apply Nw, H1.
Qed.

Lemma nan_2_not_finite : forall w : float * float, nan (fst w) /\ nan (snd w) -> ~ finite (fst w).
Proof. intros w [N _]. exact (nan_1_not_finite (fst w) N). Qed.

(* The two cases of the mask, for one limb and for two. *)
Theorem map_1_true :
  forall (A : Type) (f : A -> float) (Q : A -> Prop) (P : A -> float -> Prop) (xs : list A),
  forallb (fun w => snd (check_1 w)) (map f xs) = true -> Forall Q xs ->
  (forall (x : A) (w : float), Q x -> f x = w -> finite w -> P x w) ->
  Forall2 P xs (map f xs) /\ (true = true <-> Forall (fun w => finite w) (map f xs)).
Proof.
intros A f Q P xs E HQ G.
exact (map_entries_mask_true A float f (fun w => snd (check_1 w)) (fun w => finite w) Q P
         check_1_flag G xs E HQ).
Qed.

Theorem map_1_false :
  forall (A : Type) (f : A -> float) (Q : A -> Prop) (P : A -> float -> Prop) (xs : list A),
  forallb (fun w => snd (check_1 w)) (map f xs) = false -> Forall Q xs ->
  (forall (x : A) (w : float), Q x -> f x = w -> finite w -> P x w) ->
  (forall (x : A) (w : float), Q x -> ~ finite (f x) -> nan w -> P x w) ->
  Forall2 P xs (map (fun w => fst (check_1 w)) (map f xs)) /\
  (false = true <-> Forall (fun w => finite w) (map (fun w => fst (check_1 w)) (map f xs))).
Proof.
intros A f Q P xs E HQ G Bd.
exact (map_entries_mask_false A float f (fun w => snd (check_1 w)) (fun w => fst (check_1 w))
         (fun w => finite w) (fun w => nan w) Q P check_1_flag G check_1_kept check_1_bad
         nan_1_not_finite Bd xs E HQ).
Qed.

Theorem map_2_true :
  forall (A : Type) (f : A -> float * float) (Q : A -> Prop) (P : A -> float * float -> Prop)
         (xs : list A),
  forallb (fun w => snd (check_2 w)) (map f xs) = true -> Forall Q xs ->
  (forall (x : A) (w : float * float), Q x -> f x = w -> finite (fst w) -> P x w) ->
  Forall2 P xs (map f xs) /\ (true = true <-> Forall (fun w => finite (fst w)) (map f xs)).
Proof.
intros A f Q P xs E HQ G.
exact (map_entries_mask_true A (float * float) f (fun w => snd (check_2 w))
         (fun w => finite (fst w)) Q P check_2_flag G xs E HQ).
Qed.

Theorem map_2_false :
  forall (A : Type) (f : A -> float * float) (Q : A -> Prop) (P : A -> float * float -> Prop)
         (xs : list A),
  forallb (fun w => snd (check_2 w)) (map f xs) = false -> Forall Q xs ->
  (forall (x : A) (w : float * float), Q x -> f x = w -> finite (fst w) -> P x w) ->
  (forall (x : A) (w : float * float), Q x -> ~ finite (fst (f x)) ->
   nan (fst w) /\ nan (snd w) -> P x w) ->
  Forall2 P xs (map (fun w => fst (check_2 w)) (map f xs)) /\
  (false = true <-> Forall (fun w => finite (fst w)) (map (fun w => fst (check_2 w)) (map f xs))).
Proof.
intros A f Q P xs E HQ G Bd.
exact (map_entries_mask_false A (float * float) f (fun w => snd (check_2 w))
         (fun w => fst (check_2 w)) (fun w => finite (fst w)) (fun w => nan (fst w) /\ nan (snd w))
         Q P check_2_flag G check_2_kept check_2_bad nan_2_not_finite Bd xs E HQ).
Qed.

(** * The steps, entry by entry *)

(* A canonical pair with a finite leading limb is finite and normalized. *)
Lemma canonical_lead :
  forall x0 x1 : float, canonical_2 x0 x1 -> finite x0 ->
  finite x1 /\ normalized_2 emin prec (val x0) (val x1).
Proof.
intros x0 x1 C L. unfold finite in *.
destruct C as [[_ [F1 N]]|[[[s E] _]|[N _]]].
- split. exact F1. exact N.
- rewrite E in L. discriminate L.
- apply (nan_not_finite prec emax) in N. congruence.
Qed.

Lemma val_format : forall x : float, fmt emin prec (val x).
Proof. intros x. exact (b2r_format prec emax x). Qed.

(* NaN choices for the operations that a statement does not name. *)
Notation np := (fun x y : float => nan_plus x y).
Notation no := (fun x : float => nan_plus x x).
Notation nf := (fun x y _ : float => nan_plus x y).

(* One limb. *)

Lemma add_1_1_entry :
  (1 <= prec)%Z -> forall a b s : float, IeeeModel.add_1_1 prec emax nan_plus a b = s -> finite s ->
  finite a /\ finite b /\ val s = add_1_1 emin prec tie_even (val a) (val b) /\
  val s = RN emin prec (val a + val b) /\
  Rabs (val s - (val a + val b)) <= (1 / (1 + u prec)) * u prec ^ 1 * Rabs (val a + val b).
Proof.
intros Hp a b s <- Fs.
destruct (add_1_1_ieee_lead prec emax prec_gt_0_ prec_lt_emax_ nan_plus a b Fs) as [Fa Fb].
destruct (add_1_1_ieee_bridge prec emax prec_gt_0_ prec_lt_emax_ nan_plus np no nf Hp a b Fa Fb Fs)
  as [_ E].
destruct (add_1_1_correct emin prec Hp (val a) (val b) (val_format a) (val_format b)) as [_ [R B]].
rewrite <- E in R, B. repeat (split; [assumption|]). exact B.
Qed.

Lemma add_entry_step_1_entry :
  (1 <= prec)%Z ->
  forall x y z : float, IeeeModel.add_entry_step_1 prec emax nan_plus x y = z -> finite z ->
  finite x /\ finite y /\ val z = add_entry_step_1 emin prec tie_even (val x) (val y) /\
  val z = RN emin prec (val x + val y) /\
  Rabs (val z - (val x + val y)) <= (1 / (1 + u prec)) * u prec ^ 1 * Rabs (val x + val y).
Proof.
intros Hp x y z <- Fz.
destruct (add_entry_step_1_ieee_lead prec emax prec_gt_0_ prec_lt_emax_ nan_plus x y Fz) as [Fx Fy].
destruct (add_entry_step_1_ieee_bridge prec emax prec_gt_0_ prec_lt_emax_ nan_plus np no nf Hp
            x y Fx Fy Fz) as [_ E].
destruct (add_entry_step_1_correct emin prec Hp (val x) (val y) (val_format x) (val_format y))
  as [_ [R B]].
rewrite <- E in R, B. repeat (split; [assumption|]). exact B.
Qed.

Lemma sub_1_1_entry :
  (1 <= prec)%Z ->
  forall a b s : float, IeeeModel.sub_1_1 prec emax nan_minus a b = s -> finite s ->
  finite a /\ finite b /\ val s = sub_1_1 emin prec tie_even (val a) (val b) /\
  val s = RN emin prec (val a - val b) /\
  Rabs (val s - (val a - val b)) <= (1 / (1 + u prec)) * u prec ^ 1 * Rabs (val a - val b).
Proof.
intros Hp a b s <- Fs.
destruct (sub_1_1_ieee_lead prec emax prec_gt_0_ prec_lt_emax_ nan_minus a b Fs) as [Fa Fb].
destruct (sub_1_1_ieee_bridge prec emax prec_gt_0_ prec_lt_emax_ nan_minus nan_minus
            (fun x => nan_minus x x) (fun x y _ => nan_minus x y) Hp a b Fa Fb Fs) as [_ E].
destruct (sub_1_1_correct emin prec Hp (val a) (val b) (val_format a) (val_format b)) as [_ [R B]].
rewrite <- E in R, B. repeat (split; [assumption|]). exact B.
Qed.

Lemma sub_entry_step_1_entry :
  (1 <= prec)%Z ->
  forall x y z : float, IeeeModel.sub_entry_step_1 prec emax nan_plus nan_minus x y = z ->
  finite z ->
  finite x /\ finite y /\ val z = sub_entry_step_1 emin prec tie_even (val x) (val y) /\
  val z = RN emin prec (val x - val y) /\
  Rabs (val z - (val x - val y)) <= (1 / (1 + u prec)) * u prec ^ 1 * Rabs (val x - val y).
Proof.
intros Hp x y z <- Fz.
destruct (sub_entry_step_1_ieee_lead prec emax prec_gt_0_ prec_lt_emax_ nan_plus nan_minus x y Fz)
  as [Fx Fy].
destruct (sub_entry_step_1_ieee_bridge prec emax prec_gt_0_ prec_lt_emax_ nan_plus nan_minus no nf
            Hp x y Fx Fy Fz) as [_ E].
destruct (sub_entry_step_1_correct emin prec Hp (val x) (val y) (val_format x) (val_format y))
  as [_ [R B]].
rewrite <- E in R, B. repeat (split; [assumption|]). exact B.
Qed.

Lemma axpy_step_1_entry :
  (1 <= prec)%Z ->
  forall a x y z : float, IeeeModel.axpy_step_1 prec emax nan_plus nan_fma a x y = z -> finite z ->
  finite a /\ finite x /\ finite y /\
  val z = axpy_step_1 emin prec tie_even (val a) (val x) (val y) /\
  Rabs (val z - ((val a * val x) + val y)) <=
    ((2 + (3 * u prec)) / ((1 + u prec) * (1 + u prec))) * u prec ^ 1 *
    (Rabs (val a * val x) + Rabs (val y)) + (2 / 3) * eta emin.
Proof.
intros Hp a x y z <- Fz.
destruct (axpy_step_1_ieee_lead prec emax prec_gt_0_ prec_lt_emax_ nan_plus nan_fma a x y Fz)
  as [Fa [Fx Fy]].
destruct (axpy_step_1_ieee_bridge prec emax prec_gt_0_ prec_lt_emax_ nan_plus np no nan_fma Hp
            a x y Fa Fx Fy Fz) as [_ E].
destruct (axpy_step_1_correct emin prec Hp (val a) (val x) (val y) (val_format a) (val_format x)
            (val_format y)) as [_ B].
rewrite <- E in B. repeat (split; [assumption|]). exact B.
Qed.

Lemma axpy_entry_step_1_entry :
  (1 <= prec)%Z ->
  forall a x y z : float, IeeeModel.axpy_entry_step_1 prec emax nan_plus nan_fma a x y = z ->
  finite z ->
  finite a /\ finite x /\ finite y /\
  val z = axpy_entry_step_1 emin prec tie_even (val a) (val x) (val y) /\
  Rabs (val z - ((val a * val x) + val y)) <=
    ((2 + (3 * u prec)) / ((1 + u prec) * (1 + u prec))) * u prec ^ 1 *
    (Rabs (val a * val x) + Rabs (val y)) + (2 / 3) * eta emin.
Proof.
intros Hp a x y z <- Fz.
destruct (axpy_entry_step_1_ieee_lead prec emax prec_gt_0_ prec_lt_emax_ nan_plus nan_fma a x y Fz)
  as [Fa [Fx Fy]].
destruct (axpy_entry_step_1_ieee_bridge prec emax prec_gt_0_ prec_lt_emax_ nan_plus np no nan_fma
            Hp a x y Fa Fx Fy Fz) as [_ E].
destruct (axpy_entry_step_1_correct emin prec Hp (val a) (val x) (val y) (val_format a)
            (val_format x) (val_format y)) as [_ B].
rewrite <- E in B. repeat (split; [assumption|]). exact B.
Qed.

Lemma scale_step_1_entry :
  (1 <= prec)%Z ->
  forall x a z : float, IeeeModel.scale_step_1 prec emax nan_fma x a = z -> finite z ->
  finite x /\ finite a /\ val z = scale_step_1 emin prec tie_even (val x) (val a) /\
  val z = RN emin prec (val x * val a) /\
  Rabs (val z - (val x * val a)) <=
    (1 / (1 + u prec)) * u prec ^ 1 * Rabs (val x * val a) + (1 / 2) * eta emin.
Proof.
intros Hp x a z <- Fz.
destruct (scale_step_1_ieee_lead prec emax prec_gt_0_ prec_lt_emax_ nan_fma x a Fz) as [Fx Fa].
destruct (scale_step_1_ieee_bridge prec emax prec_gt_0_ prec_lt_emax_ (fun x y => nan_fma x y x)
            (fun x y => nan_fma x y x) (fun x => nan_fma x x x) nan_fma Hp x a Fx Fa Fz) as [_ E].
destruct (scale_step_1_correct emin prec Hp (val x) (val a) (val_format x) (val_format a))
  as [_ [R B]].
rewrite <- E in R, B. repeat (split; [assumption|]). exact B.
Qed.

Lemma mul_pow2_step_1_entry :
  (1 <= prec)%Z -> forall x c : float, finite c -> (exists n : Z, val c = bpow radix2 n) ->
  forall z : float, IeeeModel.mul_pow2_step_1 prec emax nan_fma x c = z -> finite z ->
  finite x /\ finite c /\ val z = mul_pow2_step_1 emin prec tie_even (val x) (val c) /\
  val z = RN emin prec (val x * val c) /\
  Rabs (val z - (val x * val c)) <= (1 / 2) * eta emin.
Proof.
intros Hp x c Fc Pc z <- Fz.
destruct (mul_pow2_step_1_ieee_lead prec emax prec_gt_0_ prec_lt_emax_ nan_fma x c Fz) as [Fx _].
destruct (mul_pow2_step_1_ieee_bridge prec emax prec_gt_0_ prec_lt_emax_ (fun x y => nan_fma x y x)
            (fun x y => nan_fma x y x) (fun x => nan_fma x x x) nan_fma Hp x c Fx Fc Pc Fz)
  as [_ E].
destruct (mul_pow2_step_1_correct emin prec Hp (val x) (val c) (val_format x) (val_format c) Pc)
  as [_ [R B]].
rewrite <- E in R, B. repeat (split; [assumption|]). exact B.
Qed.

(* Two limbs. *)

Lemma add_2_2_entry :
  (3 <= prec)%Z ->
  forall x0 x1 y0 y1 : float, canonical_2 x0 x1 -> canonical_2 y0 y1 ->
  forall z0 z1 : float, IeeeModel.add_2_2 prec emax nan_plus nan_minus x0 x1 y0 y1 = (z0, z1) ->
  finite z0 ->
  finite x0 /\ finite x1 /\ finite y0 /\ finite y1 /\ finite z1 /\
  (val z0, val z1) = add_2_2 emin prec tie_even (val x0) (val x1) (val y0) (val y1) /\
  normalized_2 emin prec (val z0) (val z1) /\
  Rabs ((val z0 + val z1) - ((val x0 + val x1) + (val y0 + val y1))) <=
    (3 / (1 - (4 * u prec))) * u prec ^ 2 * Rabs ((val x0 + val x1) + (val y0 + val y1)).
Proof.
intros Hp x0 x1 y0 y1 Cx Cy z0 z1 E Fz.
generalize (add_2_2_ieee_lead prec emax prec_gt_0_ prec_lt_emax_ nan_plus nan_minus x0 x1 y0 y1).
rewrite E. intros L. destruct (L Fz) as [F0 G0].
destruct (canonical_lead x0 x1 Cx F0) as [F1 Nx]. destruct (canonical_lead y0 y1 Cy G0) as [G1 Ny].
generalize (add_2_2_ieee_bridge prec emax prec_gt_0_ prec_lt_emax_ nan_plus nan_minus no nf Hp
              x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny).
rewrite E. intros Br. destruct (Br Fz) as [_ [Fz1 V]].
generalize (add_2_2_ieee_correct prec emax prec_gt_0_ prec_lt_emax_ nan_plus nan_minus Hp
              x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny).
rewrite E. intros C. destruct (C Fz) as [_ [Nz B]].
repeat (split; [assumption|]). exact B.
Qed.

Lemma add_entry_step_2_entry :
  (3 <= prec)%Z ->
  forall x0 x1 y0 y1 : float, canonical_2 x0 x1 -> canonical_2 y0 y1 ->
  forall z0 z1 : float,
  IeeeModel.add_entry_step_2 prec emax nan_plus nan_minus x0 x1 y0 y1 = (z0, z1) -> finite z0 ->
  finite x0 /\ finite x1 /\ finite y0 /\ finite y1 /\ finite z1 /\
  (val z0, val z1) = add_entry_step_2 emin prec tie_even (val x0) (val x1) (val y0) (val y1) /\
  normalized_2 emin prec (val z0) (val z1) /\
  Rabs ((val z0 + val z1) - ((val x0 + val x1) + (val y0 + val y1))) <=
    (3 / (1 - (4 * u prec))) * u prec ^ 2 * Rabs ((val x0 + val x1) + (val y0 + val y1)).
Proof.
intros Hp x0 x1 y0 y1 Cx Cy z0 z1 E Fz.
generalize (add_entry_step_2_ieee_lead prec emax prec_gt_0_ prec_lt_emax_ nan_plus nan_minus
              x0 x1 y0 y1).
rewrite E. intros L. destruct (L Fz) as [F0 G0].
destruct (canonical_lead x0 x1 Cx F0) as [F1 Nx]. destruct (canonical_lead y0 y1 Cy G0) as [G1 Ny].
generalize (add_entry_step_2_ieee_bridge prec emax prec_gt_0_ prec_lt_emax_ nan_plus nan_minus no nf
              Hp x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny).
rewrite E. intros Br. destruct (Br Fz) as [_ [Fz1 V]].
generalize (add_entry_step_2_ieee_correct prec emax prec_gt_0_ prec_lt_emax_ nan_plus nan_minus Hp
              x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny).
rewrite E. intros C. destruct (C Fz) as [_ [Nz B]].
repeat (split; [assumption|]). exact B.
Qed.

Lemma sub_2_2_entry :
  (3 <= prec)%Z ->
  forall x0 x1 y0 y1 : float, canonical_2 x0 x1 -> canonical_2 y0 y1 ->
  forall z0 z1 : float,
  IeeeModel.sub_2_2 prec emax nan_plus nan_minus nan_opp x0 x1 y0 y1 = (z0, z1) -> finite z0 ->
  finite x0 /\ finite x1 /\ finite y0 /\ finite y1 /\ finite z1 /\
  (val z0, val z1) = sub_2_2 emin prec tie_even (val x0) (val x1) (val y0) (val y1) /\
  normalized_2 emin prec (val z0) (val z1) /\
  Rabs ((val z0 + val z1) - ((val x0 + val x1) - (val y0 + val y1))) <=
    (3 / (1 - (4 * u prec))) * u prec ^ 2 * Rabs ((val x0 + val x1) - (val y0 + val y1)).
Proof.
intros Hp x0 x1 y0 y1 Cx Cy z0 z1 E Fz.
generalize (sub_2_2_ieee_lead prec emax prec_gt_0_ prec_lt_emax_ nan_plus nan_minus nan_opp
              x0 x1 y0 y1).
rewrite E. intros L. destruct (L Fz) as [F0 G0].
destruct (canonical_lead x0 x1 Cx F0) as [F1 Nx]. destruct (canonical_lead y0 y1 Cy G0) as [G1 Ny].
generalize (sub_2_2_ieee_bridge prec emax prec_gt_0_ prec_lt_emax_ nan_plus nan_minus nan_opp nf
              Hp x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny).
rewrite E. intros Br. destruct (Br Fz) as [_ [Fz1 V]].
generalize (sub_2_2_ieee_correct prec emax prec_gt_0_ prec_lt_emax_ nan_plus nan_minus nan_opp Hp
              x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny).
rewrite E. intros C. destruct (C Fz) as [_ [Nz B]].
repeat (split; [assumption|]). exact B.
Qed.

Lemma sub_entry_step_2_entry :
  (3 <= prec)%Z ->
  forall x0 x1 y0 y1 : float, canonical_2 x0 x1 -> canonical_2 y0 y1 ->
  forall z0 z1 : float,
  IeeeModel.sub_entry_step_2 prec emax nan_plus nan_minus nan_opp x0 x1 y0 y1 = (z0, z1) ->
  finite z0 ->
  finite x0 /\ finite x1 /\ finite y0 /\ finite y1 /\ finite z1 /\
  (val z0, val z1) = sub_entry_step_2 emin prec tie_even (val x0) (val x1) (val y0) (val y1) /\
  normalized_2 emin prec (val z0) (val z1) /\
  Rabs ((val z0 + val z1) - ((val x0 + val x1) - (val y0 + val y1))) <=
    (3 / (1 - (4 * u prec))) * u prec ^ 2 * Rabs ((val x0 + val x1) - (val y0 + val y1)).
Proof.
intros Hp x0 x1 y0 y1 Cx Cy z0 z1 E Fz.
generalize (sub_entry_step_2_ieee_lead prec emax prec_gt_0_ prec_lt_emax_ nan_plus nan_minus nan_opp
              x0 x1 y0 y1).
rewrite E. intros L. destruct (L Fz) as [F0 G0].
destruct (canonical_lead x0 x1 Cx F0) as [F1 Nx]. destruct (canonical_lead y0 y1 Cy G0) as [G1 Ny].
generalize (sub_entry_step_2_ieee_bridge prec emax prec_gt_0_ prec_lt_emax_ nan_plus nan_minus
              nan_opp nf Hp x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny).
rewrite E. intros Br. destruct (Br Fz) as [_ [Fz1 V]].
generalize (sub_entry_step_2_ieee_correct prec emax prec_gt_0_ prec_lt_emax_ nan_plus nan_minus
              nan_opp Hp x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny).
rewrite E. intros C. destruct (C Fz) as [_ [Nz B]].
repeat (split; [assumption|]). exact B.
Qed.

Lemma scale_step_2_entry :
  (2 <= prec)%Z ->
  forall x0 x1 a : float, canonical_2 x0 x1 ->
  forall z0 z1 : float,
  IeeeModel.scale_step_2 prec emax nan_plus nan_minus nan_opp nan_fma x0 x1 a = (z0, z1) ->
  finite z0 ->
  finite x0 /\ finite x1 /\ finite a /\ finite z1 /\
  (val z0, val z1) = scale_step_2 emin prec tie_even (val x0) (val x1) (val a) /\
  normalized_2 emin prec (val z0) (val z1) /\
  Rabs ((val z0 + val z1) - ((val x0 + val x1) * val a)) <=
    2 * u prec ^ 2 * Rabs ((val x0 + val x1) * val a) + 1 * eta emin.
Proof.
intros Hp x0 x1 a Cx z0 z1 E Fz.
generalize (scale_step_2_ieee_lead prec emax prec_gt_0_ prec_lt_emax_ nan_plus nan_minus nan_opp
              nan_fma x0 x1 a).
rewrite E. intros L. destruct (L Fz) as [F0 Fa].
destruct (canonical_lead x0 x1 Cx F0) as [F1 Nx].
generalize (scale_step_2_ieee_bridge prec emax prec_gt_0_ prec_lt_emax_ nan_plus nan_minus nan_opp
              nan_fma Hp x0 x1 a F0 F1 Fa Nx).
rewrite E. intros Br. destruct (Br Fz) as [_ [Fz1 V]].
generalize (scale_step_2_ieee_correct prec emax prec_gt_0_ prec_lt_emax_ nan_plus nan_minus nan_opp
              nan_fma Hp x0 x1 a F0 F1 Fa Nx).
rewrite E. intros C. destruct (C Fz) as [_ [Nz B]].
repeat (split; [assumption|]). exact B.
Qed.

Lemma mul_pow2_step_2_entry :
  (2 <= prec)%Z ->
  forall x0 x1 c : float, finite c -> (exists n : Z, val c = bpow radix2 n) -> canonical_2 x0 x1 ->
  forall z0 z1 : float,
  IeeeModel.mul_pow2_step_2 prec emax nan_plus nan_minus nan_fma x0 x1 c = (z0, z1) ->
  finite z0 ->
  finite x0 /\ finite x1 /\ finite c /\ finite z1 /\
  (val z0, val z1) = mul_pow2_step_2 emin prec tie_even (val x0) (val x1) (val c) /\
  normalized_2 emin prec (val z0) (val z1) /\
  Rabs ((val z0 + val z1) - ((val x0 + val x1) * val c)) <= 1 * eta emin.
Proof.
intros Hp x0 x1 c Fc Pc Cx z0 z1 E Fz.
generalize (mul_pow2_step_2_ieee_lead prec emax prec_gt_0_ prec_lt_emax_ nan_plus nan_minus nan_fma
              x0 x1 c).
rewrite E. intros L. destruct (L Fz) as [F0 _].
destruct (canonical_lead x0 x1 Cx F0) as [F1 Nx].
generalize (mul_pow2_step_2_ieee_bridge prec emax prec_gt_0_ prec_lt_emax_ nan_plus nan_minus no
              nan_fma Hp x0 x1 c F0 F1 Fc Nx Pc).
rewrite E. intros Br. destruct (Br Fz) as [_ [Fz1 V]].
generalize (mul_pow2_step_2_ieee_correct prec emax prec_gt_0_ prec_lt_emax_ nan_plus nan_minus
              nan_fma Hp x0 x1 c F0 F1 Fc Nx Pc).
rewrite E. intros C. destruct (C Fz) as [_ [Nz B]].
repeat (split; [assumption|]). exact B.
Qed.

Lemma axpy_step_2_entry :
  (4 <= prec)%Z ->
  forall a0 a1 x0 x1 y0 y1 : float, canonical_2 a0 a1 -> canonical_2 x0 x1 -> canonical_2 y0 y1 ->
  forall z0 z1 : float,
  IeeeModel.axpy_step_2 prec emax nan_plus nan_minus nan_opp nan_fma a0 a1 x0 x1 y0 y1 = (z0, z1) ->
  finite z0 ->
  finite a0 /\ finite a1 /\ finite x0 /\ finite x1 /\ finite y0 /\ finite y1 /\ finite z1 /\
  (val z0, val z1) =
    axpy_step_2 emin prec tie_even (val a0) (val a1) (val x0) (val x1) (val y0) (val y1) /\
  normalized_2 emin prec (val z0) (val z1) /\
  Rabs ((val z0 + val z1) - (((val a0 + val a1) * (val x0 + val x1)) + (val y0 + val y1))) <=
    (((3 * (1 + ((4 * u prec) * u prec))) / (1 - (4 * u prec))) + 4) * u prec ^ 2 *
    (Rabs ((val a0 + val a1) * (val x0 + val x1)) + Rabs (val y0 + val y1)) + 2 * eta emin.
Proof.
intros Hp a0 a1 x0 x1 y0 y1 Ca Cx Cy z0 z1 E Fz.
generalize (axpy_step_2_ieee_lead prec emax prec_gt_0_ prec_lt_emax_ nan_plus nan_minus nan_opp
              nan_fma a0 a1 x0 x1 y0 y1).
rewrite E. intros L. destruct (L Fz) as [A0 [F0 G0]].
destruct (canonical_lead a0 a1 Ca A0) as [A1 Na].
destruct (canonical_lead x0 x1 Cx F0) as [F1 Nx]. destruct (canonical_lead y0 y1 Cy G0) as [G1 Ny].
generalize (axpy_step_2_ieee_bridge prec emax prec_gt_0_ prec_lt_emax_ nan_plus nan_minus nan_opp
              nan_fma Hp a0 a1 x0 x1 y0 y1 A0 A1 F0 F1 G0 G1 Na Nx Ny).
rewrite E. intros Br. destruct (Br Fz) as [_ [Fz1 V]].
generalize (axpy_step_2_ieee_correct prec emax prec_gt_0_ prec_lt_emax_ nan_plus nan_minus nan_opp
              nan_fma Hp a0 a1 x0 x1 y0 y1 A0 A1 F0 F1 G0 G1 Na Nx Ny).
rewrite E. intros C. destruct (C Fz) as [_ [Nz B]].
repeat (split; [assumption|]). exact B.
Qed.

Lemma axpy_entry_step_2_entry :
  (4 <= prec)%Z ->
  forall a0 a1 x0 x1 y0 y1 : float, canonical_2 a0 a1 -> canonical_2 x0 x1 -> canonical_2 y0 y1 ->
  forall z0 z1 : float,
  IeeeModel.axpy_entry_step_2 prec emax nan_plus nan_minus nan_opp nan_fma a0 a1 x0 x1 y0 y1 =
    (z0, z1) ->
  finite z0 ->
  finite a0 /\ finite a1 /\ finite x0 /\ finite x1 /\ finite y0 /\ finite y1 /\ finite z1 /\
  (val z0, val z1) =
    axpy_entry_step_2 emin prec tie_even (val a0) (val a1) (val x0) (val x1) (val y0) (val y1) /\
  normalized_2 emin prec (val z0) (val z1) /\
  Rabs ((val z0 + val z1) - (((val a0 + val a1) * (val x0 + val x1)) + (val y0 + val y1))) <=
    (((3 * (1 + ((4 * u prec) * u prec))) / (1 - (4 * u prec))) + 4) * u prec ^ 2 *
    (Rabs ((val a0 + val a1) * (val x0 + val x1)) + Rabs (val y0 + val y1)) + 2 * eta emin.
Proof.
intros Hp a0 a1 x0 x1 y0 y1 Ca Cx Cy z0 z1 E Fz.
generalize (axpy_entry_step_2_ieee_lead prec emax prec_gt_0_ prec_lt_emax_ nan_plus nan_minus
              nan_opp nan_fma a0 a1 x0 x1 y0 y1).
rewrite E. intros L. destruct (L Fz) as [A0 [F0 G0]].
destruct (canonical_lead a0 a1 Ca A0) as [A1 Na].
destruct (canonical_lead x0 x1 Cx F0) as [F1 Nx]. destruct (canonical_lead y0 y1 Cy G0) as [G1 Ny].
generalize (axpy_entry_step_2_ieee_bridge prec emax prec_gt_0_ prec_lt_emax_ nan_plus nan_minus
              nan_opp nan_fma Hp a0 a1 x0 x1 y0 y1 A0 A1 F0 F1 G0 G1 Na Nx Ny).
rewrite E. intros Br. destruct (Br Fz) as [_ [Fz1 V]].
generalize (axpy_entry_step_2_ieee_correct prec emax prec_gt_0_ prec_lt_emax_ nan_plus nan_minus
              nan_opp nan_fma Hp a0 a1 x0 x1 y0 y1 A0 A1 F0 F1 G0 G1 Na Nx Ny).
rewrite E. intros C. destruct (C Fz) as [_ [Nz B]].
repeat (split; [assumption|]). exact B.
Qed.

Lemma axpy_step_2_1_entry :
  (3 <= prec)%Z ->
  forall a x0 x1 y0 y1 : float, canonical_2 x0 x1 -> canonical_2 y0 y1 ->
  forall z0 z1 : float,
  IeeeModel.axpy_step_2_1 prec emax nan_plus nan_minus nan_opp nan_fma a x0 x1 y0 y1 = (z0, z1) ->
  finite z0 ->
  finite a /\ finite x0 /\ finite x1 /\ finite y0 /\ finite y1 /\ finite z1 /\
  (val z0, val z1) = axpy_step_2_1 emin prec tie_even (val a) (val x0) (val x1) (val y0) (val y1) /\
  normalized_2 emin prec (val z0) (val z1) /\
  Rabs ((val z0 + val z1) - ((val a * (val x0 + val x1)) + (val y0 + val y1))) <=
    (((3 * (1 + ((2 * u prec) * u prec))) / (1 - (4 * u prec))) + 2) * u prec ^ 2 *
    (Rabs (val a * (val x0 + val x1)) + Rabs (val y0 + val y1)) + (5 / 4) * eta emin.
Proof.
intros Hp a x0 x1 y0 y1 Cx Cy z0 z1 E Fz.
generalize (axpy_step_2_1_ieee_lead prec emax prec_gt_0_ prec_lt_emax_ nan_plus nan_minus nan_opp
              nan_fma a x0 x1 y0 y1).
rewrite E. intros L. destruct (L Fz) as [Fa [F0 G0]].
destruct (canonical_lead x0 x1 Cx F0) as [F1 Nx]. destruct (canonical_lead y0 y1 Cy G0) as [G1 Ny].
generalize (axpy_step_2_1_ieee_bridge prec emax prec_gt_0_ prec_lt_emax_ nan_plus nan_minus nan_opp
              nan_fma Hp a x0 x1 y0 y1 Fa F0 F1 G0 G1 Nx Ny).
rewrite E. intros Br. destruct (Br Fz) as [_ [Fz1 V]].
generalize (axpy_step_2_1_ieee_correct prec emax prec_gt_0_ prec_lt_emax_ nan_plus nan_minus nan_opp
              nan_fma Hp a x0 x1 y0 y1 Fa F0 F1 G0 G1 Nx Ny).
rewrite E. intros C. destruct (C Fz) as [_ [Nz B]].
repeat (split; [assumption|]). exact B.
Qed.

Lemma axpy_entry_step_2_1_entry :
  (3 <= prec)%Z ->
  forall a x0 x1 y0 y1 : float, canonical_2 x0 x1 -> canonical_2 y0 y1 ->
  forall z0 z1 : float,
  IeeeModel.axpy_entry_step_2_1 prec emax nan_plus nan_minus nan_opp nan_fma a x0 x1 y0 y1 =
    (z0, z1) ->
  finite z0 ->
  finite a /\ finite x0 /\ finite x1 /\ finite y0 /\ finite y1 /\ finite z1 /\
  (val z0, val z1) =
    axpy_entry_step_2_1 emin prec tie_even (val a) (val x0) (val x1) (val y0) (val y1) /\
  normalized_2 emin prec (val z0) (val z1) /\
  Rabs ((val z0 + val z1) - ((val a * (val x0 + val x1)) + (val y0 + val y1))) <=
    (((3 * (1 + ((2 * u prec) * u prec))) / (1 - (4 * u prec))) + 2) * u prec ^ 2 *
    (Rabs (val a * (val x0 + val x1)) + Rabs (val y0 + val y1)) + (5 / 4) * eta emin.
Proof.
intros Hp a x0 x1 y0 y1 Cx Cy z0 z1 E Fz.
generalize (axpy_entry_step_2_1_ieee_lead prec emax prec_gt_0_ prec_lt_emax_ nan_plus nan_minus
              nan_opp nan_fma a x0 x1 y0 y1).
rewrite E. intros L. destruct (L Fz) as [Fa [F0 G0]].
destruct (canonical_lead x0 x1 Cx F0) as [F1 Nx]. destruct (canonical_lead y0 y1 Cy G0) as [G1 Ny].
generalize (axpy_entry_step_2_1_ieee_bridge prec emax prec_gt_0_ prec_lt_emax_ nan_plus nan_minus
              nan_opp nan_fma Hp a x0 x1 y0 y1 Fa F0 F1 G0 G1 Nx Ny).
rewrite E. intros Br. destruct (Br Fz) as [_ [Fz1 V]].
generalize (axpy_entry_step_2_1_ieee_correct prec emax prec_gt_0_ prec_lt_emax_ nan_plus nan_minus
              nan_opp nan_fma Hp a x0 x1 y0 y1 Fa F0 F1 G0 G1 Nx Ny).
rewrite E. intros C. destruct (C Fz) as [_ [Nz B]].
repeat (split; [assumption|]). exact B.
Qed.

End IeeeFoldMaps.

(** * The generated statements *)

(* Every element of a list satisfies True: the requirement of a map of one limb. *)
Lemma Forall_True : forall (A : Type) (xs : list A), Forall (fun _ => True) xs.
Proof. intros A xs. apply Forall_forall. intros _ _. exact I. Qed.

(* The steps of a proof of a map, after the binders of its statement: the mask written as
   forallb (fold_seq_and or fold_lanes_and), a case analysis on it, and in each case
   map_k_true or map_k_false with, entry by entry, the entry lemma of the step (for an
   element written with a finite leading limb) or the NaN it returns (otherwise). The
   requirements of the elements are HQ; those of the scalars are hypotheses of the context,
   which the entry lemma takes. *)
Ltac pairs := repeat match goal with x : (_ * _)%type |- _ => destruct x end.
Ltac conjs := repeat match goal with H : _ /\ _ |- _ => destruct H end.

Ltac entry_good entry :=
  intros ? ? ? ? ?; pairs; cbn [fst snd] in *; cbv beta iota zeta; conjs;
  split; [intros _; eapply entry; eassumption | intros; contradiction].

Ltac entry_bad :=
  intros ? ? ? ? ?; pairs; cbn [fst snd] in *; cbv beta iota zeta; conjs;
  split;
  [ intros; exfalso;
    match goal with H : nan ?w, F : finite ?w |- _ => exact (nan_1_not_finite _ _ w H F) end
  | intros _; repeat split; assumption ].

Ltac masked_map HQ entry :=
  cbv zeta; first [rewrite fold_seq_and | rewrite fold_lanes_and];
  match goal with |- context [forallb ?t (map ?f ?xs)] => destruct (forallb t (map f xs)) eqn:? end;
  cbv beta iota;
  [ first [ eapply map_1_true | eapply map_2_true ]; try exact HQ; try eassumption;
    [ entry_good entry ]
  | first [ eapply map_1_false | eapply map_2_false ]; try exact HQ; try eassumption;
    [ entry_good entry | entry_bad ] ].

Theorem add_1_seq_ieee_correct : add_1_seq_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_abs nan_const Hp' xys.
unfold IeeeFoldModel.add_1_seq. masked_map (Forall_True _ xys) (add_1_1_entry prec emax nan_plus).
Qed.

Theorem add_1_lanes_ieee_correct : add_1_lanes_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_abs nan_const Hp' W xys.
unfold IeeeFoldModel.add_1_lanes. masked_map (Forall_True _ xys) (add_1_1_entry prec emax nan_plus).
Qed.

Theorem add_1_entry_seq_ieee_correct : add_1_entry_seq_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_abs nan_const Hp' xys.
unfold IeeeFoldModel.add_1_entry_seq. masked_map (Forall_True _ xys)
    (add_entry_step_1_entry prec emax nan_plus).
Qed.

Theorem add_1_entry_lanes_ieee_correct : add_1_entry_lanes_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_abs nan_const Hp' W xys.
unfold IeeeFoldModel.add_1_entry_lanes. masked_map (Forall_True _ xys)
    (add_entry_step_1_entry prec emax nan_plus).
Qed.

Theorem sub_1_seq_ieee_correct : sub_1_seq_ieee_spec.
Proof.
intros prec emax Hp He nan_minus nan_abs nan_const Hp' xys.
unfold IeeeFoldModel.sub_1_seq. masked_map (Forall_True _ xys) (sub_1_1_entry prec emax nan_minus).
Qed.

Theorem sub_1_lanes_ieee_correct : sub_1_lanes_ieee_spec.
Proof.
intros prec emax Hp He nan_minus nan_abs nan_const Hp' W xys.
unfold IeeeFoldModel.sub_1_lanes. masked_map (Forall_True _ xys)
    (sub_1_1_entry prec emax nan_minus).
Qed.

Theorem sub_1_entry_seq_ieee_correct : sub_1_entry_seq_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_abs nan_const Hp' xys.
unfold IeeeFoldModel.sub_1_entry_seq. masked_map (Forall_True _ xys)
    (sub_entry_step_1_entry prec emax nan_plus nan_minus).
Qed.

Theorem sub_1_entry_lanes_ieee_correct : sub_1_entry_lanes_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_abs nan_const Hp' W xys.
unfold IeeeFoldModel.sub_1_entry_lanes. masked_map (Forall_True _ xys)
    (sub_entry_step_1_entry prec emax nan_plus nan_minus).
Qed.

Theorem axpy_1_seq_ieee_correct : axpy_1_seq_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_abs nan_fma nan_const Hp' a xys.
unfold IeeeFoldModel.axpy_1_seq. masked_map (Forall_True _ xys)
    (axpy_step_1_entry prec emax nan_plus nan_fma).
Qed.

Theorem axpy_1_lanes_ieee_correct : axpy_1_lanes_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_abs nan_fma nan_const Hp' W a xys.
unfold IeeeFoldModel.axpy_1_lanes. masked_map (Forall_True _ xys)
    (axpy_step_1_entry prec emax nan_plus nan_fma).
Qed.

Theorem axpy_1_entry_seq_ieee_correct : axpy_1_entry_seq_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_abs nan_fma nan_const Hp' a xys.
unfold IeeeFoldModel.axpy_1_entry_seq. masked_map (Forall_True _ xys)
    (axpy_entry_step_1_entry prec emax nan_plus nan_fma).
Qed.

Theorem axpy_1_entry_lanes_ieee_correct : axpy_1_entry_lanes_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_abs nan_fma nan_const Hp' W a xys.
unfold IeeeFoldModel.axpy_1_entry_lanes. masked_map (Forall_True _ xys)
    (axpy_entry_step_1_entry prec emax nan_plus nan_fma).
Qed.

Theorem scale_1_seq_ieee_correct : scale_1_seq_ieee_spec.
Proof.
intros prec emax Hp He nan_abs nan_fma nan_const Hp' a xs.
unfold IeeeFoldModel.scale_1_seq. masked_map (Forall_True _ xs)
    (scale_step_1_entry prec emax nan_fma).
Qed.

Theorem scale_1_lanes_ieee_correct : scale_1_lanes_ieee_spec.
Proof.
intros prec emax Hp He nan_abs nan_fma nan_const Hp' W a xs.
unfold IeeeFoldModel.scale_1_lanes. masked_map (Forall_True _ xs)
    (scale_step_1_entry prec emax nan_fma).
Qed.

Theorem mul_pow2_map_1_seq_ieee_correct : mul_pow2_map_1_seq_ieee_spec.
Proof.
intros prec emax Hp He nan_abs nan_fma nan_const Hp' c xs Fc Pc.
unfold IeeeFoldModel.mul_pow2_map_1_seq. masked_map (Forall_True _ xs)
    (mul_pow2_step_1_entry prec emax nan_fma).
Qed.

Theorem mul_pow2_map_1_lanes_ieee_correct : mul_pow2_map_1_lanes_ieee_spec.
Proof.
intros prec emax Hp He nan_abs nan_fma nan_const Hp' W c xs Fc Pc.
unfold IeeeFoldModel.mul_pow2_map_1_lanes. masked_map (Forall_True _ xs)
    (mul_pow2_step_1_entry prec emax nan_fma).
Qed.

Theorem add_2_seq_ieee_correct : add_2_seq_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_abs nan_const Hp' xys HQ.
unfold IeeeFoldModel.add_2_seq. masked_map HQ (add_2_2_entry prec emax nan_plus nan_minus).
Qed.

Theorem add_2_lanes_ieee_correct : add_2_lanes_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_abs nan_const Hp' W xys HQ.
unfold IeeeFoldModel.add_2_lanes. masked_map HQ (add_2_2_entry prec emax nan_plus nan_minus).
Qed.

Theorem add_2_entry_seq_ieee_correct : add_2_entry_seq_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_abs nan_const Hp' xys HQ.
unfold IeeeFoldModel.add_2_entry_seq. masked_map HQ
    (add_entry_step_2_entry prec emax nan_plus nan_minus).
Qed.

Theorem add_2_entry_lanes_ieee_correct : add_2_entry_lanes_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_abs nan_const Hp' W xys HQ.
unfold IeeeFoldModel.add_2_entry_lanes. masked_map HQ
    (add_entry_step_2_entry prec emax nan_plus nan_minus).
Qed.

Theorem sub_2_seq_ieee_correct : sub_2_seq_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_const Hp' xys HQ.
unfold IeeeFoldModel.sub_2_seq. masked_map HQ (sub_2_2_entry prec emax nan_plus nan_minus nan_opp).
Qed.

Theorem sub_2_lanes_ieee_correct : sub_2_lanes_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_const Hp' W xys HQ.
unfold IeeeFoldModel.sub_2_lanes. masked_map HQ
    (sub_2_2_entry prec emax nan_plus nan_minus nan_opp).
Qed.

Theorem sub_2_entry_seq_ieee_correct : sub_2_entry_seq_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_const Hp' xys HQ.
unfold IeeeFoldModel.sub_2_entry_seq. masked_map HQ
    (sub_entry_step_2_entry prec emax nan_plus nan_minus nan_opp).
Qed.

Theorem sub_2_entry_lanes_ieee_correct : sub_2_entry_lanes_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_const Hp' W xys HQ.
unfold IeeeFoldModel.sub_2_entry_lanes. masked_map HQ
    (sub_entry_step_2_entry prec emax nan_plus nan_minus nan_opp).
Qed.

Theorem scale_2_seq_ieee_correct : scale_2_seq_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const Hp' a xs HQ.
unfold IeeeFoldModel.scale_2_seq. masked_map HQ
    (scale_step_2_entry prec emax nan_plus nan_minus nan_opp nan_fma).
Qed.

Theorem scale_2_lanes_ieee_correct : scale_2_lanes_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const Hp' W a xs HQ.
unfold IeeeFoldModel.scale_2_lanes. masked_map HQ
    (scale_step_2_entry prec emax nan_plus nan_minus nan_opp nan_fma).
Qed.

Theorem mul_pow2_map_2_seq_ieee_correct : mul_pow2_map_2_seq_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_abs nan_fma nan_const Hp' c xs Fc Pc HQ.
unfold IeeeFoldModel.mul_pow2_map_2_seq. masked_map HQ
    (mul_pow2_step_2_entry prec emax nan_plus nan_minus nan_fma).
Qed.

Theorem mul_pow2_map_2_lanes_ieee_correct : mul_pow2_map_2_lanes_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_abs nan_fma nan_const Hp' W c xs Fc Pc HQ.
unfold IeeeFoldModel.mul_pow2_map_2_lanes. masked_map HQ
    (mul_pow2_step_2_entry prec emax nan_plus nan_minus nan_fma).
Qed.

Theorem axpy_2_seq_ieee_correct : axpy_2_seq_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const Hp' a0 a1 xys Ca HQ.
unfold IeeeFoldModel.axpy_2_seq. masked_map HQ
    (axpy_step_2_entry prec emax nan_plus nan_minus nan_opp nan_fma).
Qed.

Theorem axpy_2_lanes_ieee_correct : axpy_2_lanes_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const Hp' W a0 a1 xys Ca HQ.
unfold IeeeFoldModel.axpy_2_lanes. masked_map HQ
    (axpy_step_2_entry prec emax nan_plus nan_minus nan_opp nan_fma).
Qed.

Theorem axpy_2_entry_seq_ieee_correct : axpy_2_entry_seq_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const Hp' a0 a1 xys Ca HQ.
unfold IeeeFoldModel.axpy_2_entry_seq. masked_map HQ
    (axpy_entry_step_2_entry prec emax nan_plus nan_minus nan_opp nan_fma).
Qed.

Theorem axpy_2_entry_lanes_ieee_correct : axpy_2_entry_lanes_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const Hp' W a0 a1 xys Ca HQ.
unfold IeeeFoldModel.axpy_2_entry_lanes. masked_map HQ
    (axpy_entry_step_2_entry prec emax nan_plus nan_minus nan_opp nan_fma).
Qed.

Theorem axpy_2_1_seq_ieee_correct : axpy_2_1_seq_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const Hp' a xys HQ.
unfold IeeeFoldModel.axpy_2_1_seq. masked_map HQ
    (axpy_step_2_1_entry prec emax nan_plus nan_minus nan_opp nan_fma).
Qed.

Theorem axpy_2_1_lanes_ieee_correct : axpy_2_1_lanes_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const Hp' W a xys HQ.
unfold IeeeFoldModel.axpy_2_1_lanes. masked_map HQ
    (axpy_step_2_1_entry prec emax nan_plus nan_minus nan_opp nan_fma).
Qed.

Theorem axpy_2_1_entry_seq_ieee_correct : axpy_2_1_entry_seq_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const Hp' a xys HQ.
unfold IeeeFoldModel.axpy_2_1_entry_seq. masked_map HQ
    (axpy_entry_step_2_1_entry prec emax nan_plus nan_minus nan_opp nan_fma).
Qed.

Theorem axpy_2_1_entry_lanes_ieee_correct : axpy_2_1_entry_lanes_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const Hp' W a xys HQ.
unfold IeeeFoldModel.axpy_2_1_entry_lanes. masked_map HQ
    (axpy_entry_step_2_1_entry prec emax nan_plus nan_minus nan_opp nan_fma).
Qed.
