(* The ball vectors in the IEEE model: what the generated statements F_seq_ieee_spec and
   F_lanes_ieee_spec of bv_add_k, bv_sub_k and bv_scale_k (proofs/gen/IeeeFoldStatements.v)
   say, proved as lemmas of their own, for both orders. The statements themselves are to be
   restated (their fourth clause, V4: the form of the developer page is false for an empty
   vector; the printed form asks a nonempty vector, and for one limb, printed from precision
   1, it is false at precision 1, see bv_add_1_seq_ieee_v4), so these lemmas are not named
   by the descriptions yet; each is stated in the vocabulary and with the binders of the
   generated statements, so that the restated statements follow from them.

   The model (proofs/gen/IeeeFoldModel.v). A ball vector writes the centers by the step of
   a map, ws = map F_step xs; folds the record, the step of the fold of maxima norm_step_k,
   over the centers written, from (+0, true): the largest magnitude m of a (leading limb of
   a) center and the mask that none was a NaN; computes the radius rz by the radius kernel
   on m and the scalars; and tests it with norm_finish_1 under the mask. When the flag is
   true it returns the centers and rz; when it is false, zeros for the centers and +infinity
   for the radius: the whole space.

   The lemmas, for canonical operands (a finite nonnegative radius and finite centers, or
   the radius +infinity and zero centers) and any scalar a:
   - V1 (F_O_ieee_v1): the result is canonical, a finite ball vector or the whole space,
     and the flag is true exactly when the radius returned is finite;
   - V2 (F_O_ieee_v2): entry by entry, for all members of the balls of the operands'
     entries, the value of the operation is in the ball of the center written;
   - V3 (F_O_ieee_v3): if the radius returned is finite, so are the radii of the operands
     (and a), every center written is the real model's step on the values, and the radius
     is the real model's radius on the values;
   - V4 (F_O_ieee_v4), in the form ruled for the restatement: finite radii (and a finite
     scalar), the radii's own sum (|a| rx for a scaling) within 2^(emax - 2), and every entry
     within it, give a finite radius, for every length of the vector, none included; from
     precision 2 (3 for the sums of two limbs, the precision of their statements).
   And the lane order returns what the sequential order returns, bit for bit
   (F_lanes_seq_ieee), so the lemmas of the lane order are those of the sequential order.

   How.
   - The record is the step of norm_upper_1 (on the leading limbs for two limbs), and
     IeeeFoldNorm.v proves what its sequential order is: the state is a magnitude, and when
     it is finite with a true mask every element is finite and its value is the state of the
     real model (seq_1_state); the lane order returns the same state
     (norm_upper_k_lanes_seq_state).
   - The radius kernels (radius_k_ieee below): every value is nonnegative, +infinity or a
     NaN, and a finite radius means finite operands and the radius of the real model,
     operation by operation, as for the radius of the Ball kernels (IeeeBallCores.v), but
     for every precision: a constant that overflows only makes the radius infinite or NaN
     (const_of_cases).
   - The flag true: the radius kernel's result is finite, so m and the scalars are, so every
     center written is (the record), so it is the real model's step (the entry lemmas of
     IeeeFoldMaps.v), and the radius is the real model's. That is V3 and, with the
     nonnegativity of a finite radius, V1. V2 is then the real-model theorem of the ball
     vector (BvReal.v) read on the values: a canonical operand with a finite radius is a
     finite ball, and the containment of the real model is the containment asked.
   - The flag false: zeros and +infinity, which is the whole space, and contains
     everything.
   - V4: every center written is finite and, in magnitude, at most what the limit leaves
     once the radii are taken (the step's error within the limit; add_2_2_center,
     sub_2_2_center and scale_step_2_center for two limbs), so the record m is too, and the
     chain of the radius stays in range at m (radius2_range of IeeeBallFinite.v), as in the
     finiteness of the Ball kernels (ball_add_k_finite, ball_scale_k_finite). With no entry m
     is +0 and the radii's own condition is what is left. *)
From Stdlib Require Import Reals ZArith List Lia Lra Bool.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements IeeeStatements FoldModel FoldStatements
  IeeeFoldStatements.
From Kairn Require Import Format Normalized Folds FoldTransfer FoldNorm IeeeBridge IeeeVocabulary
  IeeeOps IeeeFoldFinish IeeeFolds IeeeFoldNorm IeeeMapSteps IeeeFoldMaps Ball2 BvRadius BvReal
  IeeeEFT IeeeBallCores IeeeBallFinite IeeeAdd22 IeeeMore IeeeFinite.
From Kairn Require IeeeOperations.
From Kairn.Gen Require IeeeModel IeeeFoldModel.
Import ListNotations.
Open Scope R_scope.

Section IeeeBv.
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

Notation emin := (3 - emax - prec)%Z.
Notation fexp := (FLT_exp emin prec).
Notation format := (generic_format radix2 fexp).
Notation rnd := (round radix2 fexp (Znearest tie_even)).
Notation fin x := (is_finite prec emax x = true).
Notation b2r := (B2R prec emax).
Notation const_of := (IeeeOperations.const_of prec emax).
Notation pzero := (IeeeOperations.pzero prec emax).
Notation pinf := (IeeeOperations.pinf prec emax).
Notation fabs := (IeeeOperations.abs prec emax nan_abs).
Notation step_1 := (IeeeFoldModel.norm_upper_1_step prec emax nan_abs).
Notation zero_state := (pzero, true).

(** * The constants of the radius kernels, at every precision *)

(* A nonnegative number of the format made a constant: nonnegative, +infinity when it
   overflows; and, when finite, of that value. *)
Lemma const_of_cases :
  forall r : R, format r -> 0 <= r ->
  nonneg_ext (const_of r) /\ (fin (const_of r) -> b2r (const_of r) = r).
Proof.
intros r Fr Hr. unfold IeeeOperations.const_of.
generalize (binary_normalize_correct prec emax prec_gt_0_ prec_lt_emax_ BinarySingleNaN.mode_NE
              (Ztrunc (scaled_mantissa radix2 fexp r)) (cexp radix2 fexp r) false).
assert (E : F2R (Float radix2 (Ztrunc (scaled_mantissa radix2 fexp r)) (cexp radix2 fexp r)) = r)
  by (symmetry; exact Fr).
rewrite E.
change (round radix2 (SpecFloat.fexp prec emax)
          (BinarySingleNaN.round_mode BinarySingleNaN.mode_NE) r) with (rnd r).
rewrite round_generic by (auto with typeclass_instances).
destruct (Rlt_bool_spec (Rabs r) (bpow radix2 emax)) as [L|L].
- intros [E1 [F1 _]]. split.
  + apply (nonneg_ext_finite prec emax). exact F1. rewrite E1. exact Hr.
  + intros _. exact E1.
- rewrite (Rlt_bool_false r 0) by lra. cbv beta iota.
  match goal with |- B2FF _ _ ?z = _ -> _ => destruct z as [s|s|s pl H|s mm ee H] end;
  cbn; intros E2; try discriminate E2.
  injection E2 as Es. subst s. split.
  + exact (nonneg_ext_pinf prec emax).
  + intros F. discriminate F.
Qed.

Lemma RU_const :
  forall t : R, 0 <= t ->
  nonneg_ext (const_of (RU emin prec t)) /\
  (fin (const_of (RU emin prec t)) -> b2r (const_of (RU emin prec t)) = RU emin prec t).
Proof.
intros t Ht. apply const_of_cases.
- apply generic_format_round; auto with typeclass_instances.
- exact (proj1 (RU_ge emin prec t Ht)).
Qed.

Lemma h2_nrm_ge_0 : forall V : R, 0 <= V -> 0 <= h2 emin prec V + nrm emin prec.
Proof. intros V HV. generalize (h2_ge_0 emin prec V HV) (nrm_ge_0 emin prec). lra. Qed.

Lemma pow3_ge_0 : 0 <= (1 + u prec) ^ 3.
Proof. exact (pow_ge_0' prec 3). Qed.

(** * The radius kernels in the IEEE model *)

(* On nonnegative operands (or +infinity, or NaN): the radius is nonnegative, +infinity or
   NaN; a finite radius means finite operands and the radius of the real model. *)
Lemma add_radius_1_ieee :
  forall m rx ry : float, nonneg_ext m -> nonneg_ext rx -> nonneg_ext ry ->
  let rz := IeeeModel.bv_add_radius_1 prec emax nan_plus nan_fma m rx ry in
  nonneg_ext rz /\
  (fin rz -> fin m /\ fin rx /\ fin ry /\
   b2r rz = Model.bv_add_radius_1 emin prec tie_even (b2r m) (b2r rx) (b2r ry)).
Proof.
intros m rx ry Hm Hrx Hry. cbv zeta.
unfold IeeeModel.bv_add_radius_1, Model.bv_add_radius_1. cbv zeta.
unfold IeeeModel.up_ball_add_1_0, IeeeModel.up_ball_add_1_1, IeeeModel.up_ball_add_1_2.
rewrite e_add_1_eq, g_add_1_eq, h_add_1_eq.
assert (Hrel : 0 <= rel_1 prec < 1) by exact (rel_one_limb prec).
destruct (RU_const _ (uq_ge_0 _ Hrel)) as [NE VE].
destruct (RU_const _ pow3_ge_0) as [NG VG].
replace ((1 + u prec) * ((1 + u prec) ^ 2 * eta emin + eta emin / 2)) with (h2 emin prec 0)
  by (unfold h2; ring).
destruct (RU_const _ (h2_nrm_ge_0 0 (Rle_refl 0))) as [NH VH].
destruct (add_nonneg prec emax nan_plus rx ry Hrx Hry) as [Hs [Es _]].
destruct (fma_nonneg prec emax nan_fma m _ _ Hm NE Hs) as [Ht Et].
destruct (fma_nonneg prec emax nan_fma _ _ _ Ht NG NH) as [Hrz Erz].
split. exact Hrz.
intros Frz. destruct (Erz Frz) as [Ft [FG [FH E1]]]. destruct (Et Ft) as [Fm [FE [Fs E2]]].
destruct (Es Fs) as [Frx [Fry E3]].
split. exact Fm. split. exact Frx. split. exact Fry.
rewrite E1, E2, E3, (VE FE), (VG FG), (VH FH). reflexivity.
Qed.

Lemma add_radius_2_ieee :
  (3 <= prec)%Z ->
  forall m rx ry : float, nonneg_ext m -> nonneg_ext rx -> nonneg_ext ry ->
  let rz := IeeeModel.bv_add_radius_2 prec emax nan_plus nan_fma m rx ry in
  nonneg_ext rz /\
  (fin rz -> fin m /\ fin rx /\ fin ry /\
   b2r rz = Model.bv_add_radius_2 emin prec tie_even (b2r m) (b2r rx) (b2r ry)).
Proof.
intros Hp m rx ry Hm Hrx Hry. cbv zeta.
unfold IeeeModel.bv_add_radius_2, Model.bv_add_radius_2. cbv zeta.
unfold IeeeModel.up_ball_add_2_0, IeeeModel.up_ball_add_1_1, IeeeModel.up_ball_add_1_2.
rewrite e_add_2_eq, g_add_1_eq, h_add_1_eq.
assert (Hrel : 0 <= rel_add_2 prec < 1) by exact (rel_add_2_2 prec Hp).
generalize (bpow_gt_0 radix2 (- prec)). fold (u prec). intros U0.
assert (K0 : 0 <= uq (rel_add_2 prec) * (1 + u prec)).
{ apply Rmult_le_pos. exact (uq_ge_0 _ Hrel). lra. }
destruct (RU_const _ K0) as [NE VE].
destruct (RU_const _ pow3_ge_0) as [NG VG].
replace ((1 + u prec) * ((1 + u prec) ^ 2 * eta emin + eta emin / 2)) with (h2 emin prec 0)
  by (unfold h2; ring).
destruct (RU_const _ (h2_nrm_ge_0 0 (Rle_refl 0))) as [NH VH].
destruct (add_nonneg prec emax nan_plus rx ry Hrx Hry) as [Hs [Es _]].
destruct (fma_nonneg prec emax nan_fma m _ _ Hm NE Hs) as [Ht Et].
destruct (fma_nonneg prec emax nan_fma _ _ _ Ht NG NH) as [Hrz Erz].
split. exact Hrz.
intros Frz. destruct (Erz Frz) as [Ft [FG [FH E1]]]. destruct (Et Ft) as [Fm [FE [Fs E2]]].
destruct (Es Fs) as [Frx [Fry E3]].
split. exact Fm. split. exact Frx. split. exact Fry.
rewrite E1, E2, E3, (VE FE), (VG FG), (VH FH). reflexivity.
Qed.

Lemma scale_radius_1_ieee :
  forall m rx a : float, nonneg_ext m -> nonneg_ext rx ->
  let rz := IeeeModel.bv_scale_radius_1 prec emax nan_abs nan_fma m rx a in
  nonneg_ext rz /\
  (fin rz -> fin m /\ fin rx /\ fin a /\
   b2r rz = Model.bv_scale_radius_1 emin prec tie_even (b2r m) (b2r rx) (b2r a)).
Proof.
intros m rx a Hm Hrx. cbv zeta.
unfold IeeeModel.bv_scale_radius_1, Model.bv_scale_radius_1. cbv zeta.
unfold IeeeModel.up_ball_mul_1_0, IeeeModel.up_ball_add_1_1, IeeeModel.up_ball_scale_1_2.
rewrite e_scale_1_eq, g_scale_1_eq, h_scale_1_eq.
assert (Hrel : 0 <= rel_1 prec < 1) by exact (rel_one_limb prec).
assert (Htiny : 0 <= 1 / 2 * eta emin) by (apply eta_ge_0; lra).
destruct (RU_const _ (uq_ge_0 _ Hrel)) as [NE VE].
destruct (RU_const _ pow3_ge_0) as [NG VG].
destruct (RU_const _ (h2_nrm_ge_0 _ (vq_ge_0 _ _ Hrel Htiny))) as [NH VH].
destruct (prod_nonneg prec emax nan_fma (fabs a) rx (abs_nonneg prec emax nan_abs a) Hrx)
  as [Hp Ep].
destruct (fma_nonneg prec emax nan_fma m _ _ Hm NE Hp) as [Ht Et].
destruct (fma_nonneg prec emax nan_fma _ _ _ Ht NG NH) as [Hrz Erz].
split. exact Hrz.
intros Frz. destruct (Erz Frz) as [Ft [FG [FH E1]]]. destruct (Et Ft) as [Fm [FE [Fp E2]]].
destruct (Ep Fp) as [Faa [Frx E3]].
split. exact Fm. split. exact Frx. split.
{ rewrite (abs_finite prec emax nan_abs) in Faa. exact Faa. }
rewrite E1, E2, E3, (VE FE), (VG FG), (VH FH), (abs_val prec emax nan_abs). reflexivity.
Qed.

Lemma scale_radius_2_ieee :
  (2 <= prec)%Z ->
  forall m rx a : float, nonneg_ext m -> nonneg_ext rx ->
  let rz := IeeeModel.bv_scale_radius_2 prec emax nan_abs nan_fma m rx a in
  nonneg_ext rz /\
  (fin rz -> fin m /\ fin rx /\ fin a /\
   b2r rz = Model.bv_scale_radius_2 emin prec tie_even (b2r m) (b2r rx) (b2r a)).
Proof.
intros Hp2 m rx a Hm Hrx. cbv zeta.
unfold IeeeModel.bv_scale_radius_2, Model.bv_scale_radius_2. cbv zeta.
unfold IeeeModel.up_ball_scale_2_0, IeeeModel.up_ball_add_1_1, IeeeModel.up_ball_scale_2_2.
rewrite e_scale_2_eq, g_scale_2_eq, h_scale_2_eq.
assert (Hrel : 0 <= rel_mul_21 prec < 1) by exact (rel_mul_2_1 prec Hp2).
assert (Htiny : 0 <= 1 * eta emin) by (apply eta_ge_0; lra).
generalize (bpow_gt_0 radix2 (- prec)). fold (u prec). intros U0.
assert (K0 : 0 <= uq (rel_mul_21 prec) * (1 + u prec)).
{ apply Rmult_le_pos. exact (uq_ge_0 _ Hrel). lra. }
destruct (RU_const _ K0) as [NE VE].
destruct (RU_const _ pow3_ge_0) as [NG VG].
destruct (RU_const _ (h2_nrm_ge_0 _ (vq_ge_0 _ _ Hrel Htiny))) as [NH VH].
destruct (prod_nonneg prec emax nan_fma (fabs a) rx (abs_nonneg prec emax nan_abs a) Hrx)
  as [Hp Ep].
destruct (fma_nonneg prec emax nan_fma m _ _ Hm NE Hp) as [Ht Et].
destruct (fma_nonneg prec emax nan_fma _ _ _ Ht NG NH) as [Hrz Erz].
split. exact Hrz.
intros Frz. destruct (Erz Frz) as [Ft [FG [FH E1]]]. destruct (Et Ft) as [Fm [FE [Fp E2]]].
destruct (Ep Fp) as [Faa [Frx E3]].
split. exact Fm. split. exact Frx. split.
{ rewrite (abs_finite prec emax nan_abs) in Faa. exact Faa. }
rewrite E1, E2, E3, (VE FE), (VG FG), (VH FH), (abs_val prec emax nan_abs). reflexivity.
Qed.

(** * V1, for centers of one limb and of two *)

(* The canonical radius of an operand: nonnegative or +infinity. *)
Lemma canonical_radius_1 :
  forall (r : float) (A B : Prop),
  (finite r /\ 0 <= val r /\ A) \/ (r = infinity prec emax false /\ B) -> nonneg_ext r.
Proof.
intros r A B [[F [N _]]|[E _]].
- right. right. split; assumption.
- right. left. exact E.
Qed.

(* The result of a ball vector of one limb, from the centers written ws and its radius
   kernel rad on the largest magnitude: the radius is nonnegative, +infinity or NaN on a
   magnitude, and finite only on a finite magnitude. *)
Lemma bv1_v1 :
  forall (ws : list float) (rad : float -> float),
  (forall m, IeeeFoldNorm.mag prec emax m -> nonneg_ext (rad m) /\ (fin (rad m) -> fin m)) ->
  let s := fold_seq step_1 zero_state ws in
  let f := IeeeModel.norm_finish_1 prec emax nan_abs nan_const (rad (fst s)) (snd s) in
  let '(ws_, r_, flag_) :=
    (if snd f then (ws, fst f) else (map (fun _ => pzero) ws, pinf), snd f) in
  ((finite r_ /\ 0 <= val r_ /\ Forall (fun w_ => ball_finite_1 w_ r_) ws_) \/
   (r_ = infinity prec emax false /\ Forall (fun w_ => ball_whole_1 w_ r_) ws_)) /\
  (flag_ = true <-> finite r_).
Proof.
intros ws rad Hrad. cbv zeta.
destruct (seq_1_state prec emax nan_abs ws) as [M HS].
set (s := fold_seq step_1 zero_state ws) in *.
destruct (Hrad (fst s) M) as [NN Lead].
generalize (norm_finish_1_correct prec emax prec_gt_0_ prec_lt_emax_ nan_abs nan_const
              (rad (fst s)) (snd s)).
destruct (IeeeModel.norm_finish_1 prec emax nan_abs nan_const (rad (fst s)) (snd s))
  as [r flag].
cbn [fst snd]. intros [H1 [H2 _]].
destruct flag; cbv beta iota.
- destruct (proj1 H1 eq_refl) as [Eok Frad]. rewrite (H2 eq_refl).
  destruct (HS (Lead Frad) Eok) as [Fws _].
  split.
  + left. split. exact Frad. split.
    * exact (nonneg_ext_fin prec emax _ NN Frad).
    * revert Fws. apply Forall_impl. intros w Fw. split. exact Fw. split. exact Frad.
      exact (nonneg_ext_fin prec emax _ NN Frad).
  + split; intros _; [exact Frad|reflexivity].
- split.
  + right. split. reflexivity. apply Forall_map. apply Forall_forall. intros w _.
    split. exists false. reflexivity. reflexivity.
  + split; intros H; discriminate H.
Qed.

(* The same for centers of two limbs: the record reads the leading limbs, and a center whose
   leading limb is finite has a finite normalized second limb (Hsec, from the step). *)
Lemma bv2_v1 :
  forall (ws : list (float * float)) (rad : float -> float),
  (forall m, IeeeFoldNorm.mag prec emax m -> nonneg_ext (rad m) /\ (fin (rad m) -> fin m)) ->
  Forall (fun w => finite (fst w) ->
                   finite (snd w) /\ normalized_2 (ieee_emin prec emax) prec (val (fst w))
                     (val (snd w)))
         ws ->
  let s := fold_seq (IeeeFoldModel.norm_upper_2_step prec emax nan_abs) zero_state ws in
  let f := IeeeModel.norm_finish_1 prec emax nan_abs nan_const (rad (fst s)) (snd s) in
  let '(ws_, r_, flag_) :=
    (if snd f then (ws, fst f) else (map (fun _ => (pzero, pzero)) ws, pinf), snd f) in
  ((finite r_ /\ 0 <= val r_ /\ Forall (fun w_ => ball_finite_2 (fst w_) (snd w_) r_) ws_) \/
   (r_ = infinity prec emax false /\ Forall (fun w_ => ball_whole_2 (fst w_) (snd w_) r_) ws_)) /\
  (flag_ = true <-> finite r_).
Proof.
intros ws rad Hrad Hsec. cbv zeta.
assert (E2 : fold_seq (IeeeFoldModel.norm_upper_2_step prec emax nan_abs) zero_state ws =
             fold_seq step_1 zero_state (map fst ws)).
{ rewrite <- (fold_seq_map _ _ _ step_1 fst zero_state ws).
  apply fold_seq_ext. intros t x. apply step_2_eq. }
rewrite E2.
destruct (seq_1_state prec emax nan_abs (map fst ws)) as [M HS].
set (s := fold_seq step_1 zero_state (map fst ws)) in *.
destruct (Hrad (fst s) M) as [NN Lead].
generalize (norm_finish_1_correct prec emax prec_gt_0_ prec_lt_emax_ nan_abs nan_const
              (rad (fst s)) (snd s)).
destruct (IeeeModel.norm_finish_1 prec emax nan_abs nan_const (rad (fst s)) (snd s))
  as [r flag].
cbn [fst snd]. intros [H1 [H2 _]].
destruct flag; cbv beta iota.
- destruct (proj1 H1 eq_refl) as [Eok Frad]. rewrite (H2 eq_refl).
  destruct (HS (Lead Frad) Eok) as [Fws _]. apply Forall_map_inv in Fws.
  split.
  + left. split. exact Frad. split.
    * exact (nonneg_ext_fin prec emax _ NN Frad).
    * apply Forall_forall. intros w Hw.
      pose proof (proj1 (Forall_forall _ ws) Fws w Hw) as F0.
      destruct (proj1 (Forall_forall _ ws) Hsec w Hw F0) as [F1 Nw].
      split. exact F0. split. exact F1. split. exact Nw. split. exact Frad.
      exact (nonneg_ext_fin prec emax _ NN Frad).
  + split; intros _; [exact Frad|reflexivity].
- split.
  + right. split. reflexivity. apply Forall_map. apply Forall_forall. intros w _. cbn [fst snd].
    split. exists false. reflexivity. split. exists false. reflexivity. reflexivity.
  + split; intros H; discriminate H.
Qed.

(** * V4: the centers of two limbs within the limit *)

(* A center written by add_2_2 on finite normalized operands whose sum is within 2^(emax - 2):
   its leading limb is finite and at most 5/3 of the sum in magnitude (the error of add_2_2 is
   at most a quarter of the sum from precision 3, and lead_le of IeeeBallFinite.v). *)
Lemma add_2_2_center :
  (3 <= prec)%Z ->
  forall x0 x1 y0 y1 : float, finite x0 -> finite x1 -> finite y0 -> finite y1 ->
  normalized_2 emin prec (val x0) (val x1) -> normalized_2 emin prec (val y0) (val y1) ->
  Rabs ((val x0 + val x1) + (val y0 + val y1)) <= bpow radix2 (emax - 2) ->
  finite (fst (IeeeModel.add_2_2 prec emax nan_plus nan_minus x0 x1 y0 y1)) /\
  3 * Rabs (val (fst (IeeeModel.add_2_2 prec emax nan_plus nan_minus x0 x1 y0 y1))) <=
    5 * Rabs ((val x0 + val x1) + (val y0 + val y1)).
Proof.
intros Hp3 x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny Hs.
assert (Hp2 : (2 <= prec)%Z) by lia.
generalize (add_2_2_ieee_finite_result prec emax prec_gt_0_ prec_lt_emax_ nan_plus nan_minus
              nan_opp nan_fma Hp3 x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny Hs)
           (add_2_2_values_correct prec emax nan_plus nan_minus nan_opp nan_fma Hp3
              x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny).
destruct (IeeeModel.add_2_2 prec emax nan_plus nan_minus x0 x1 y0 y1) as [z0 z1].
cbv beta iota zeta. intros [_ [Fz0 _]] V. destruct (V Fz0) as [_ [Nz Ez]].
cbn [fst]. split. exact Fz0.
destruct (rel_add_2_quarter prec Hp3) as [R0 R1].
unfold val in *.
generalize
    (Rabs_pos ((B2R prec emax x0 + B2R prec emax x1) + (B2R prec emax y0 + B2R prec emax y1))).
intros T0.
assert (RC : 3 / (1 - 4 * u prec) * u prec ^ 2 *
               Rabs ((B2R prec emax x0 + B2R prec emax x1) + (B2R prec emax y0 + B2R prec emax y1))
             <= / 4 * Rabs ((B2R prec emax x0 + B2R prec emax x1) +
                            (B2R prec emax y0 + B2R prec emax y1)))
  by (apply Rmult_le_compat_r; lra).
generalize (Rabs_le_plus_err (B2R prec emax z0 + B2R prec emax z1)
              ((B2R prec emax x0 + B2R prec emax x1) + (B2R prec emax y0 + B2R prec emax y1)))
           (lead_le prec emax Hp2 _ _ Nz).
lra.
Qed.

(* The same for sub_2_2, which is add_2_2 on the negated second operand. *)
Lemma sub_2_2_center :
  (3 <= prec)%Z ->
  forall x0 x1 y0 y1 : float, finite x0 -> finite x1 -> finite y0 -> finite y1 ->
  normalized_2 emin prec (val x0) (val x1) -> normalized_2 emin prec (val y0) (val y1) ->
  Rabs ((val x0 + val x1) - (val y0 + val y1)) <= bpow radix2 (emax - 2) ->
  finite (fst (IeeeModel.sub_2_2 prec emax nan_plus nan_minus nan_opp x0 x1 y0 y1)) /\
  3 * Rabs (val (fst (IeeeModel.sub_2_2 prec emax nan_plus nan_minus nan_opp x0 x1 y0 y1))) <=
    5 * Rabs ((val x0 + val x1) - (val y0 + val y1)).
Proof.
intros Hp3 x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny Hs.
unfold IeeeModel.sub_2_2. cbv zeta.
set (n0 := IeeeOperations.neg prec emax nan_opp y0).
set (n1 := IeeeOperations.neg prec emax nan_opp y1).
assert (Fn0 : finite n0) by (unfold n0, IeeeOperations.neg, finite; now rewrite is_finite_Bopp).
assert (Fn1 : finite n1) by (unfold n1, IeeeOperations.neg, finite; now rewrite is_finite_Bopp).
assert (E0 : val n0 = - val y0) by (unfold n0, IeeeOperations.neg, val; apply B2R_Bopp).
assert (E1 : val n1 = - val y1) by (unfold n1, IeeeOperations.neg, val; apply B2R_Bopp).
assert (Nn : normalized_2 emin prec (val n0) (val n1)).
{ rewrite E0, E1. now apply normalized_2_opp. }
assert (Ex : (val x0 + val x1) + (val n0 + val n1) = (val x0 + val x1) - (val y0 + val y1)).
{ rewrite E0, E1. ring. }
assert (Hs' : Rabs ((val x0 + val x1) + (val n0 + val n1)) <= bpow radix2 (emax - 2)).
{ rewrite Ex. exact Hs. }
destruct (add_2_2_center Hp3 x0 x1 n0 n1 F0 F1 Fn0 Fn1 Nx Nn Hs') as [Fz Lz].
rewrite Ex in Lz. revert Fz Lz.
destruct (IeeeModel.add_2_2 prec emax nan_plus nan_minus x0 x1 n0 n1) as [z0 z1].
cbn [fst]. intros Fz Lz. split. exact Fz. exact Lz.
Qed.

(* A center written by scale_step_2 (mul_2_1) on a finite normalized operand and a finite
   scalar whose product is within 2^(emax - 2): its leading limb is finite and at most 5/3 of
   the product, and 4/3 eta, in magnitude. *)
Lemma scale_step_2_center :
  (2 <= prec)%Z ->
  forall x0 x1 a : float, finite x0 -> finite x1 -> finite a ->
  normalized_2 emin prec (val x0) (val x1) ->
  Rabs (val x0 + val x1) * Rabs (val a) <= bpow radix2 (emax - 2) ->
  finite (fst (IeeeModel.scale_step_2 prec emax nan_plus nan_minus nan_opp nan_fma x0 x1 a)) /\
  3 * Rabs (val (fst (IeeeModel.scale_step_2 prec emax nan_plus nan_minus nan_opp nan_fma
                        x0 x1 a))) <=
    5 * (Rabs (val x0 + val x1) * Rabs (val a)) + 4 * eta emin.
Proof.
intros Hp x0 x1 a F0 F1 Fa Nx Hc.
generalize (Rabs_pos (val x0 + val x1)) (Rabs_pos (val a)). intros C0 A0.
assert (M0 : 0 <= Rabs (val x0 + val x1) * Rabs (val a)) by now apply Rmult_le_pos.
assert (Hs : Rabs ((val x0 + val x1) * val a) <= bpow radix2 (emax - 1)).
{ rewrite Rabs_mult. apply Rle_trans with (bpow radix2 (emax - 2)). lra. apply bpow_le. lia. }
unfold IeeeModel.scale_step_2.
generalize (mul_2_1_ieee_finite prec emax prec_gt_0_ prec_lt_emax_ nan_plus nan_minus
              nan_opp nan_fma Hp x0 x1 a F0 F1 Fa Nx Hs)
           (mul_2_1_values_correct prec emax nan_plus nan_minus nan_opp nan_fma Hp
              x0 x1 a F0 F1 Fa Nx).
destruct (IeeeModel.mul_2_1 prec emax nan_plus nan_minus nan_opp nan_fma x0 x1 a) as [z0 z1].
cbv beta iota zeta. intros [_ [Fz0 _]] V. destruct (V Fz0) as [_ [Nz Ez]].
cbn [fst]. split. exact Fz0.
unfold val in *. rewrite Rabs_mult in Ez.
destruct (rel_square_quarter 2 prec Hp ltac:(lra)) as [R0 R1].
generalize (bpow_gt_0 radix2 emin). fold (eta emin). intros Eta0.
assert (RC : 2 * u prec ^ 2 * (Rabs (B2R prec emax x0 + B2R prec emax x1) * Rabs (B2R prec emax a))
             <= / 4 * (Rabs (B2R prec emax x0 + B2R prec emax x1) * Rabs (B2R prec emax a)))
  by (apply Rmult_le_compat_r; lra).
assert (Hz : Rabs (B2R prec emax z0 + B2R prec emax z1)
             <= 5 / 4 * (Rabs (B2R prec emax x0 + B2R prec emax x1) * Rabs (B2R prec emax a))
                + eta emin).
{ generalize (Rabs_le_plus_err (B2R prec emax z0 + B2R prec emax z1)
                ((B2R prec emax x0 + B2R prec emax x1) * B2R prec emax a)).
  rewrite (Rabs_mult (B2R prec emax x0 + B2R prec emax x1)). lra. }
generalize (lead_le prec emax Hp _ _ Nz). lra.
Qed.

End IeeeBv.

(** * bv_add_1 *)

(* The lane order returns what the sequential order returns: the record is the step of the
   fold of maxima norm_upper_1 and the combination its combination. *)
Lemma bv_add_1_lanes_seq_ieee :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus : nan2 prec emax) (nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true})
         (W : nat) (rx ry : binary_float prec emax)
         (xys : list (binary_float prec emax * binary_float prec emax)),
  IeeeFoldModel.bv_add_1_lanes prec emax nan_plus nan_abs nan_fma nan_const W rx ry xys =
  IeeeFoldModel.bv_add_1_seq prec emax nan_plus nan_abs nan_fma nan_const rx ry xys.
Proof.
intros. unfold IeeeFoldModel.bv_add_1_lanes, IeeeFoldModel.bv_add_1_seq. cbv zeta.
change (IeeeFoldModel.bv_add_1_record prec emax nan_abs)
  with (IeeeFoldModel.norm_upper_1_step prec emax nan_abs).
change (IeeeFoldModel.bv_add_1_combine prec emax)
  with (IeeeFoldModel.norm_upper_1_combine prec emax).
now rewrite norm_upper_1_lanes_seq_state.
Qed.

Lemma bv_add_1_seq_ieee_v1 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus : nan2 prec emax) (nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (1 <= prec)%Z ->
  forall (rx ry : binary_float prec emax)
    (xys : list (binary_float prec emax * binary_float prec emax)),
  ((finite rx /\ 0 <= val rx /\ Forall (fun xy => ball_finite_1 (fst xy) rx) xys) \/
  (rx = infinity prec emax false /\ Forall (fun xy => ball_whole_1 (fst xy) rx) xys)) ->
  ((finite ry /\ 0 <= val ry /\ Forall (fun xy => ball_finite_1 (snd xy) ry) xys) \/
  (ry = infinity prec emax false /\ Forall (fun xy => ball_whole_1 (snd xy) ry) xys)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_add_1_seq prec emax nan_plus nan_abs nan_fma nan_const rx ry xys in
  ((finite r_ /\ 0 <= val r_ /\ Forall (fun w_ => ball_finite_1 w_ r_) ws_) \/
   (r_ = infinity prec emax false /\ Forall (fun w_ => ball_whole_1 w_ r_) ws_)) /\
  (flag_ = true <-> finite r_).
Proof.
intros prec emax Hp He nan_plus nan_abs nan_fma nan_const Hp1 rx ry xys HX HY.
pose proof (canonical_radius_1 prec emax rx _ _ HX) as Nrx.
pose proof (canonical_radius_1 prec emax ry _ _ HY) as Nry.
unfold IeeeFoldModel.bv_add_1_seq. cbv zeta.
apply (bv1_v1 prec emax nan_abs nan_const _
         (fun m => IeeeModel.bv_add_radius_1 prec emax nan_plus nan_fma m rx ry)).
intros m M.
destruct (add_radius_1_ieee prec emax nan_plus nan_fma m rx ry (mag_nonneg_ext prec emax m M)
            Nrx Nry) as [N E].
split. exact N. intros F. exact (proj1 (E F)).
Qed.

(* With a true mask and a finite radius: the radii are finite, every center written is finite
   and is the real model's, and the radius is nonnegative and the real model's. *)
Lemma bv_add_1_true :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus : nan2 prec emax) (nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax),
  (1 <= prec)%Z ->
  forall (rx ry : binary_float prec emax)
    (xys : list (binary_float prec emax * binary_float prec emax)),
  nonneg_ext rx -> nonneg_ext ry ->
  let ws := map (IeeeFoldModel.bv_add_1_step prec emax nan_plus) xys in
  let s := fold_seq (IeeeFoldModel.norm_upper_1_step prec emax nan_abs)
             (IeeeOperations.pzero prec emax, true) ws in
  let rz := IeeeModel.bv_add_radius_1 prec emax nan_plus nan_fma (fst s) rx ry in
  snd s = true -> finite rz ->
  finite rx /\ finite ry /\ 0 <= val rz /\
  Forall (fun xy => finite (IeeeFoldModel.bv_add_1_step prec emax nan_plus xy) /\
                    val (IeeeFoldModel.bv_add_1_step prec emax nan_plus xy) =
                    add_1_1 (ieee_emin prec emax) prec tie_even (val (fst xy)) (val (snd xy))) xys
                      /\
  val rz = FoldModel.bv_add_1_radius (ieee_emin prec emax) prec tie_even (val rx) (val ry)
             (map (fun xy => (val (fst xy), val (snd xy))) xys).
Proof.
intros prec emax Hp He nan_plus nan_abs nan_fma Hp1 rx ry xys Nrx Nry. cbv zeta. intros Eok Frz.
destruct (seq_1_state prec emax nan_abs (map (IeeeFoldModel.bv_add_1_step prec emax nan_plus) xys))
  as [M HS].
set (s := fold_seq (IeeeFoldModel.norm_upper_1_step prec emax nan_abs)
            (IeeeOperations.pzero prec emax, true)
            (map (IeeeFoldModel.bv_add_1_step prec emax nan_plus) xys)) in *.
destruct (add_radius_1_ieee prec emax nan_plus nan_fma (fst s) rx ry (mag_nonneg_ext prec emax _ M)
            Nrx Nry) as [Nr Er].
destruct (Er Frz) as [Fm [Frx [Fry Vr]]].
destruct (HS Fm Eok) as [Fws Vs].
assert (Hz : Forall (fun xy => finite (IeeeFoldModel.bv_add_1_step prec emax nan_plus xy) /\
                    val (IeeeFoldModel.bv_add_1_step prec emax nan_plus xy) =
                    add_1_1 (ieee_emin prec emax) prec tie_even (val (fst xy)) (val (snd xy))) xys).
{ apply Forall_map_inv in Fws. revert Fws. apply Forall_impl. intros [a b] Fz. split. exact Fz.
  exact (proj1 (proj2 (proj2 (add_1_1_entry prec emax nan_plus Hp1 a b _ eq_refl Fz)))). }
split. exact Frx. split. exact Fry. split. exact (nonneg_ext_fin prec emax _ Nr Frz).
split. exact Hz.
change (val (IeeeModel.bv_add_radius_1 prec emax nan_plus nan_fma (fst s) rx ry)) with
  (B2R prec emax (IeeeModel.bv_add_radius_1 prec emax nan_plus nan_fma (fst s) rx ry)).
rewrite Vr. unfold FoldModel.bv_add_1_radius.
change (B2R prec emax (fst s)) with (fst (IeeeFoldNorm.vals prec emax s)). rewrite Vs.
unfold FoldModel.norm_upper_1_seq.
change FoldModel.bv_add_1_record with FoldModel.norm_upper_1_step. f_equal. f_equal. f_equal.
unfold FoldModel.bv_add_1_map. rewrite !map_map. apply map_ext_in. intros [a b] Hin.
exact (proj2 (proj1 (Forall_forall _ xys) Hz (a, b) Hin)).
Qed.

Lemma bv_add_1_seq_ieee_v3 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus : nan2 prec emax) (nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (1 <= prec)%Z ->
  forall (rx ry : binary_float prec emax)
    (xys : list (binary_float prec emax * binary_float prec emax)),
  ((finite rx /\ 0 <= val rx /\ Forall (fun xy => ball_finite_1 (fst xy) rx) xys) \/
  (rx = infinity prec emax false /\ Forall (fun xy => ball_whole_1 (fst xy) rx) xys)) ->
  ((finite ry /\ 0 <= val ry /\ Forall (fun xy => ball_finite_1 (snd xy) ry) xys) \/
  (ry = infinity prec emax false /\ Forall (fun xy => ball_whole_1 (snd xy) ry) xys)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_add_1_seq prec emax nan_plus nan_abs nan_fma nan_const rx ry xys in
  (finite r_ ->
   finite rx /\ finite ry /\
   Forall2 (fun xy w_ =>
     let '(x, y) := xy in
     let z := w_ in
     val z = add_1_1 (ieee_emin prec emax) prec tie_even (val x) (val y)) xys ws_ /\
   val r_ = FoldModel.bv_add_1_radius (ieee_emin prec emax) prec tie_even (val rx) (val ry)
              (map (fun xy => (val (fst xy), val (snd xy))) xys)).
Proof.
intros prec emax Hp He nan_plus nan_abs nan_fma nan_const Hp1 rx ry xys HX HY.
pose proof (canonical_radius_1 prec emax rx _ _ HX) as Nrx.
pose proof (canonical_radius_1 prec emax ry _ _ HY) as Nry.
generalize (bv_add_1_true prec emax Hp He nan_plus nan_abs nan_fma Hp1 rx ry xys Nrx Nry).
unfold IeeeFoldModel.bv_add_1_seq. cbv zeta.
change (IeeeFoldModel.bv_add_1_record prec emax nan_abs)
  with (IeeeFoldModel.norm_upper_1_step prec emax nan_abs).
set (s := fold_seq (IeeeFoldModel.norm_upper_1_step prec emax nan_abs)
            (IeeeOperations.pzero prec emax, true)
            (map (IeeeFoldModel.bv_add_1_step prec emax nan_plus) xys)).
generalize (norm_finish_1_correct prec emax Hp He nan_abs nan_const
              (IeeeModel.bv_add_radius_1 prec emax nan_plus nan_fma (fst s) rx ry) (snd s)).
destruct (IeeeModel.norm_finish_1 prec emax nan_abs nan_const
            (IeeeModel.bv_add_radius_1 prec emax nan_plus nan_fma (fst s) rx ry) (snd s))
  as [r flag].
cbn [fst snd]. intros [H1 [H2 _]] T.
destruct flag; cbv beta iota.
- intros _. destruct (proj1 H1 eq_refl) as [Eok Frad]. rewrite (H2 eq_refl).
  destruct (T Eok Frad) as [Frx [Fry [_ [Hz Vr]]]].
  split. exact Frx. split. exact Fry. split.
  + apply Forall2_map_r. revert Hz. apply Forall_impl. intros [a b] [_ E]. exact E.
  + exact Vr.
- intros F. discriminate F.
Qed.

Lemma bv_add_1_seq_ieee_v2 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus : nan2 prec emax) (nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (1 <= prec)%Z ->
  forall (rx ry : binary_float prec emax)
    (xys : list (binary_float prec emax * binary_float prec emax)),
  ((finite rx /\ 0 <= val rx /\ Forall (fun xy => ball_finite_1 (fst xy) rx) xys) \/
  (rx = infinity prec emax false /\ Forall (fun xy => ball_whole_1 (fst xy) rx) xys)) ->
  ((finite ry /\ 0 <= val ry /\ Forall (fun xy => ball_finite_1 (snd xy) ry) xys) \/
  (ry = infinity prec emax false /\ Forall (fun xy => ball_whole_1 (snd xy) ry) xys)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_add_1_seq prec emax nan_plus nan_abs nan_fma nan_const rx ry xys in
  Forall2 (fun xy w_ =>
    let '(x, y) := xy in
    let z := w_ in
    forall x_ y_ : R, in_ball_1 x rx x_ -> in_ball_1 y ry y_ -> in_ball_1 z r_ (x_ + y_))
    xys ws_.
Proof.
intros prec emax Hp He nan_plus nan_abs nan_fma nan_const Hp1 rx ry xys HX HY.
pose proof (canonical_radius_1 prec emax rx _ _ HX) as Nrx.
pose proof (canonical_radius_1 prec emax ry _ _ HY) as Nry.
generalize (bv_add_1_true prec emax Hp He nan_plus nan_abs nan_fma Hp1 rx ry xys Nrx Nry).
unfold IeeeFoldModel.bv_add_1_seq. cbv zeta.
change (IeeeFoldModel.bv_add_1_record prec emax nan_abs)
  with (IeeeFoldModel.norm_upper_1_step prec emax nan_abs).
set (s := fold_seq (IeeeFoldModel.norm_upper_1_step prec emax nan_abs)
            (IeeeOperations.pzero prec emax, true)
            (map (IeeeFoldModel.bv_add_1_step prec emax nan_plus) xys)).
generalize (norm_finish_1_correct prec emax Hp He nan_abs nan_const
              (IeeeModel.bv_add_radius_1 prec emax nan_plus nan_fma (fst s) rx ry) (snd s)).
destruct (IeeeModel.norm_finish_1 prec emax nan_abs nan_const
            (IeeeModel.bv_add_radius_1 prec emax nan_plus nan_fma (fst s) rx ry) (snd s))
  as [r flag].
cbn [fst snd]. intros [H1 [H2 _]] T.
destruct flag; cbv beta iota.
- destruct (proj1 H1 eq_refl) as [Eok Frad]. rewrite (H2 eq_refl).
  destruct (T Eok Frad) as [Frx [Fry [Pr [Hz Vr]]]].
  assert (Bx : 0 <= val rx /\ Forall (fun xy => ball_finite_1 (fst xy) rx) xys).
  { destruct HX as [[_ [P B]]|[E _]]. split; assumption. rewrite E in Frx. discriminate Frx. }
  assert (By : 0 <= val ry /\ Forall (fun xy => ball_finite_1 (snd xy) ry) xys).
  { destruct HY as [[_ [P B]]|[E _]]. split; assumption. rewrite E in Fry. discriminate Fry. }
  destruct Bx as [Px Bx]. destruct By as [Py By].
  assert (Fv : Forall (fun xy => fmt (ieee_emin prec emax) prec (fst xy) /\
                                 fmt (ieee_emin prec emax) prec (snd xy))
                      (map (fun xy => (val (fst xy), val (snd xy))) xys)).
  { apply Forall_map. apply Forall_forall. intros xy _. split; apply val_format. }
  destruct (bv_add_1_correct (ieee_emin prec emax) prec Hp1 (val rx) (val ry)
              (map (fun xy => (val (fst xy), val (snd xy))) xys)
              (val_format prec emax rx) Px (val_format prec emax ry) Py Fv) as [_ R].
  unfold FoldModel.bv_add_1_map in R. apply Forall2_map_r_inv in R. apply Forall_map_inv in R.
  apply Forall2_map_r. apply Forall_forall. intros [a b] Hin.
  destruct (proj1 (Forall_forall _ xys) Hz (a, b) Hin) as [Fz Vz].
  pose proof (proj1 (Forall_forall _ xys) R (a, b) Hin) as Rab. cbn [fst snd] in Fz, Vz, Rab.
  cbv beta iota zeta. intros x_ y_ Ix Iy.
  destruct Ix as [[_ E]|[_ Dx]]. { rewrite E in Frx. discriminate Frx. }
  destruct Iy as [[_ E]|[_ Dy]]. { rewrite E in Fry. discriminate Fry. }
  right. split.
  + split. exact Fz. split. exact Frad. exact Pr.
  + rewrite Vz, Vr. exact (proj2 Rab x_ y_ Dx Dy).
- rewrite map_map. apply Forall2_map_r. apply Forall_forall. intros [a b] _.
  cbv beta iota zeta. intros x_ y_ _ _. left. split. exists false. reflexivity. reflexivity.
Qed.

(* The lane order: the same lemmas, since it returns what the sequential order returns. *)
Lemma bv_add_1_lanes_ieee_v1 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus : nan2 prec emax) (nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (1 <= prec)%Z ->
  forall (W : nat) (rx ry : binary_float prec emax)
         (xys : list (binary_float prec emax * binary_float prec emax)),
  ((finite rx /\ 0 <= val rx /\ Forall (fun xy => ball_finite_1 (fst xy) rx) xys) \/
  (rx = infinity prec emax false /\ Forall (fun xy => ball_whole_1 (fst xy) rx) xys)) ->
  ((finite ry /\ 0 <= val ry /\ Forall (fun xy => ball_finite_1 (snd xy) ry) xys) \/
  (ry = infinity prec emax false /\ Forall (fun xy => ball_whole_1 (snd xy) ry) xys)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_add_1_lanes prec emax nan_plus nan_abs nan_fma nan_const W rx ry xys in
  ((finite r_ /\ 0 <= val r_ /\ Forall (fun w_ => ball_finite_1 w_ r_) ws_) \/
   (r_ = infinity prec emax false /\ Forall (fun w_ => ball_whole_1 w_ r_) ws_)) /\
  (flag_ = true <-> finite r_).
Proof.
intros prec emax Hp He nan_plus nan_abs nan_fma nan_const Hp1 W rx ry xys HX HY.
rewrite bv_add_1_lanes_seq_ieee.
exact (bv_add_1_seq_ieee_v1 prec emax Hp He nan_plus nan_abs nan_fma nan_const Hp1 rx ry xys HX HY).
Qed.

Lemma bv_add_1_lanes_ieee_v2 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus : nan2 prec emax) (nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (1 <= prec)%Z ->
  forall (W : nat) (rx ry : binary_float prec emax)
         (xys : list (binary_float prec emax * binary_float prec emax)),
  ((finite rx /\ 0 <= val rx /\ Forall (fun xy => ball_finite_1 (fst xy) rx) xys) \/
  (rx = infinity prec emax false /\ Forall (fun xy => ball_whole_1 (fst xy) rx) xys)) ->
  ((finite ry /\ 0 <= val ry /\ Forall (fun xy => ball_finite_1 (snd xy) ry) xys) \/
  (ry = infinity prec emax false /\ Forall (fun xy => ball_whole_1 (snd xy) ry) xys)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_add_1_lanes prec emax nan_plus nan_abs nan_fma nan_const W rx ry xys in
  Forall2 (fun xy w_ =>
    let '(x, y) := xy in
    let z := w_ in
    forall x_ y_ : R, in_ball_1 x rx x_ -> in_ball_1 y ry y_ -> in_ball_1 z r_ (x_ + y_))
    xys ws_.
Proof.
intros prec emax Hp He nan_plus nan_abs nan_fma nan_const Hp1 W rx ry xys HX HY.
rewrite bv_add_1_lanes_seq_ieee.
exact (bv_add_1_seq_ieee_v2 prec emax Hp He nan_plus nan_abs nan_fma nan_const Hp1 rx ry xys HX HY).
Qed.

Lemma bv_add_1_lanes_ieee_v3 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus : nan2 prec emax) (nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (1 <= prec)%Z ->
  forall (W : nat) (rx ry : binary_float prec emax)
         (xys : list (binary_float prec emax * binary_float prec emax)),
  ((finite rx /\ 0 <= val rx /\ Forall (fun xy => ball_finite_1 (fst xy) rx) xys) \/
  (rx = infinity prec emax false /\ Forall (fun xy => ball_whole_1 (fst xy) rx) xys)) ->
  ((finite ry /\ 0 <= val ry /\ Forall (fun xy => ball_finite_1 (snd xy) ry) xys) \/
  (ry = infinity prec emax false /\ Forall (fun xy => ball_whole_1 (snd xy) ry) xys)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_add_1_lanes prec emax nan_plus nan_abs nan_fma nan_const W rx ry xys in
  (finite r_ ->
   finite rx /\ finite ry /\
   Forall2 (fun xy w_ =>
     let '(x, y) := xy in
     let z := w_ in
     val z = add_1_1 (ieee_emin prec emax) prec tie_even (val x) (val y)) xys ws_ /\
   val r_ = FoldModel.bv_add_1_radius (ieee_emin prec emax) prec tie_even (val rx) (val ry)
              (map (fun xy => (val (fst xy), val (snd xy))) xys)).
Proof.
intros prec emax Hp He nan_plus nan_abs nan_fma nan_const Hp1 W rx ry xys HX HY.
rewrite bv_add_1_lanes_seq_ieee.
exact (bv_add_1_seq_ieee_v3 prec emax Hp He nan_plus nan_abs nan_fma nan_const Hp1 rx ry xys HX HY).
Qed.

(* V4, in the form it will take: finite radii whose sum is within a quarter of the overflow
   threshold, and every entry within it, give a finite radius, for every length of the
   vector, none included. From precision 2: the constants of the radius lines are numbers of
   the format from there on (consts_ball_add_1 of IeeeBallCores.v); at precision 1 the
   constant G = RU ((1 + u)^3) = 4 is 2^emax itself when emax = 2, and every radius is then
   +infinity or a NaN. The proof is that of B4 for ball_add_1 (ball_add_1_finite of
   IeeeBallFinite.v) at the largest magnitude m of a center: every center is finite and within
   half an ulp of 2^(emax - 2) of its exact value, so m E stays within what the chain of the
   radius allows (radius2_range), with no entry at all m is +0. *)
Lemma bv_add_1_seq_ieee_v4 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus : nan2 prec emax) (nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (2 <= prec)%Z ->
  forall (rx ry : binary_float prec emax)
    (xys : list (binary_float prec emax * binary_float prec emax)),
  ((finite rx /\ 0 <= val rx /\ Forall (fun xy => ball_finite_1 (fst xy) rx) xys) \/
  (rx = infinity prec emax false /\ Forall (fun xy => ball_whole_1 (fst xy) rx) xys)) ->
  ((finite ry /\ 0 <= val ry /\ Forall (fun xy => ball_finite_1 (snd xy) ry) xys) \/
  (ry = infinity prec emax false /\ Forall (fun xy => ball_whole_1 (snd xy) ry) xys)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_add_1_seq prec emax nan_plus nan_abs nan_fma nan_const rx ry xys in
  (finite rx -> finite ry ->
   Rabs (val rx + val ry) <= bpow radix2 (emax - 2) ->
   Forall (fun xy =>
     let '(x, y) := xy in
     Rabs (((Rabs (val x + val y)) + val rx) + val ry) <= bpow radix2 (emax - 2)) xys ->
   finite r_).
Proof.
intros prec emax Hp He nan_plus nan_abs nan_fma nan_const Hp2 rx ry xys HX HY.
unfold IeeeFoldModel.bv_add_1_seq. cbv zeta.
change (IeeeFoldModel.bv_add_1_record prec emax nan_abs)
  with (IeeeFoldModel.norm_upper_1_step prec emax nan_abs).
set (ws := map (IeeeFoldModel.bv_add_1_step prec emax nan_plus) xys).
set (s := fold_seq (IeeeFoldModel.norm_upper_1_step prec emax nan_abs)
            (IeeeOperations.pzero prec emax, true) ws).
set (rz := IeeeModel.bv_add_radius_1 prec emax nan_plus nan_fma (fst s) rx ry).
assert (Main : finite rx -> finite ry -> Rabs (val rx + val ry) <= bpow radix2 (emax - 2) ->
               Forall (fun xy => let '(x, y) := xy in
                         Rabs (((Rabs (val x + val y)) + val rx) + val ry) <= bpow radix2
                           (emax - 2))
                      xys ->
               snd s = true /\ finite rz).
2: { generalize (norm_finish_1_correct prec emax Hp He nan_abs nan_const rz (snd s)).
     destruct (IeeeModel.norm_finish_1 prec emax nan_abs nan_const rz (snd s)) as [r flag].
     cbn [fst snd]. intros [K1 [K2 _]].
     destruct flag; cbv beta iota; intros Frx Fry Hr Hent.
     - rewrite (K2 eq_refl). exact (proj2 (Main Frx Fry Hr Hent)).
     - exfalso. destruct (Main Frx Fry Hr Hent) as [E F].
       assert (K : false = true) by (apply K1; split; assumption). discriminate K. }
intros Frx Fry Hr Hent.
assert (Bx : 0 <= val rx /\ Forall (fun xy => ball_finite_1 (fst xy) rx) xys).
{ destruct HX as [[_ [P B]]|[E _]]. split; assumption. rewrite E in Frx. discriminate Frx. }
assert (By : 0 <= val ry /\ Forall (fun xy => ball_finite_1 (snd xy) ry) xys).
{ destruct HY as [[_ [P B]]|[E _]]. split; assumption. rewrite E in Fry. discriminate Fry. }
destruct Bx as [Px Bx]. destruct By as [Py By].
set (d := bpow radix2 (emax - 2 - prec - 1)).
assert (D0 : 0 < d) by apply bpow_gt_0.
assert (Hel : (3 - emax - prec + prec <= emax - 2)%Z).
{ generalize He. unfold BinarySingleNaN.Prec_lt_emax. lia. }
(* Every center written is finite and within d of the exact sum, which is within the limit. *)
assert (Hz : Forall (fun xy =>
          finite (IeeeFoldModel.bv_add_1_step prec emax nan_plus xy) /\
          Rabs (val (IeeeFoldModel.bv_add_1_step prec emax nan_plus xy)) <=
            Rabs (val (fst xy) + val (snd xy)) + d) xys).
{ apply Forall_forall. intros [a b] Hin.
  destruct (proj1 (Forall_forall _ xys) Bx (a, b) Hin) as [Fa _].
  destruct (proj1 (Forall_forall _ xys) By (a, b) Hin) as [Fb _].
  pose proof (proj1 (Forall_forall _ xys) Hent (a, b) Hin) as Hab. cbv beta iota in Hab.
  cbn [fst snd] in Fa, Fb |- *.
  assert (Lab : Rabs (val a + val b) <= bpow radix2 (emax - 2)).
  { generalize (Rabs_pos (val a + val b)). intros A0.
    rewrite Rabs_pos_eq in Hab by lra. lra. }
  assert (Ic : IeeeBridge.inrange emax (round radix2 (FLT_exp (3 - emax - prec) prec)
                                         (Znearest tie_even) (val a + val b))).
  { apply (le_bpow_inrange emax) with (emax - 2)%Z. lia. apply
    (RN_abs_le_bpow (3 - emax - prec) prec).
    exact Lab. }
  destruct (add_spec prec emax nan_plus a b Fa Fb) as [S1 S2].
  assert (Fz : is_finite prec emax (IeeeOperations.add prec emax nan_plus a b) = true)
    by now apply S1.
  split. exact Fz.
  unfold IeeeFoldModel.bv_add_1_step, IeeeModel.add_1_1. cbn [fst snd]. cbv zeta.
  unfold val. rewrite (S2 Fz).
  exact (abs_rnd_le_half prec emax _ (emax - 2) Hel Lab). }
assert (Fws : Forall (fun w => finite w) ws).
{ unfold ws. apply Forall_map. revert Hz. apply Forall_impl. intros xy [F _]. exact F. }
destruct (seq_1_good prec emax nan_abs ws Fws) as [M [Fm Eok]]. fold s in M, Fm, Eok.
destruct (seq_1_state prec emax nan_abs ws) as [_ HS]. fold s in HS.
destruct (HS Fm Eok) as [_ Vs].
rewrite norm_upper_1_seq_value in Vs.
assert (Vm : val (fst s) = fold_right Rmax 0 (map (fun x => Rabs x) (map (@val prec emax) ws))).
{ change (val (fst s)) with (fst (IeeeFoldNorm.vals prec emax s)). now rewrite Vs. }
(* The largest magnitude, against the limit. *)
set (b := 4 * (bpow radix2 (emax - 2) + d / 4 - (val rx + val ry))).
assert (Hrxy : val rx + val ry <= bpow radix2 (emax - 2)).
{ rewrite Rabs_pos_eq in Hr by lra. exact Hr. }
assert (Mb : val (fst s) <= b).
{ rewrite Vm. apply maxl_le. unfold b. lra.
  rewrite map_map. unfold ws. rewrite map_map. apply Forall_map.
  apply Forall_forall. intros [a c] Hin.
  destruct (proj1 (Forall_forall _ xys) Hz (a, c) Hin) as [_ Za].
  pose proof (proj1 (Forall_forall _ xys) Hent (a, c) Hin) as Hac. cbv beta iota in Hac.
  cbn [fst snd] in Za |- *.
  generalize (Rabs_pos (val a + val c)). intros A0.
  rewrite Rabs_pos_eq in Hac by lra. unfold b. lra. }
assert (M0 : 0 <= val (fst s)) by exact (mag_nonneg prec emax _ M Fm).
(* The radius: the chain of radius2_range, the constants of ball_add_1. *)
destruct (consts_ball_add_1 prec emax Hp2) as [[FE [EE _]] [[FG [EG _]] [FH [EH _]]]].
destruct (E_add_1_le prec emax Hp2) as [E0 E1].
destruct (G_3_le prec emax Hp2) as [Gl Gu].
destruct (H_add_le prec emax Hp2) as [H0 H1].
assert (HX' : 0 <= val rx + val ry <= bpow radix2 (emax - 2)) by lra.
assert (Y0 : 0 <= val (fst s) * Model.up_ball_add_1_0 (3 - emax - prec) prec)
  by (apply Rmult_le_pos; lra).
assert (Y1 : val (fst s) * Model.up_ball_add_1_0 (3 - emax - prec) prec <= b * / 4).
{ apply Rmult_le_compat; lra. }
assert (HS' : val rx + val ry + val (fst s) * Model.up_ball_add_1_0 (3 - emax - prec) prec
              < bpow radix2 (emax - 2) + bpow radix2 (emax - 2 - prec - 1)).
{ fold d. unfold b in Y1. lra. }
destruct (radius2_range prec emax Hp2 _ _ _ _ HX' Y0 HS' (conj Gl Gu) (conj H0 H1))
  as [Is [It Ir]].
assert (Frz : finite rz).
{ unfold rz, IeeeModel.bv_add_radius_1. cbv zeta.
  apply (radius2_add_fin prec emax nan_plus nan_fma); trivial.
  - unfold val in It. rewrite EE. exact It.
  - unfold val in Ir. rewrite EE, EG, EH. exact Ir. }
split. exact Eok. exact Frz.
Qed.

(** * bv_sub_1: the same, with sub_1_1 *)

(* The lane order returns what the sequential order returns: the record is the step of the
   fold of maxima norm_upper_1 and the combination its combination. *)
Lemma bv_sub_1_lanes_seq_ieee :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true})
         (W : nat) (rx ry : binary_float prec emax)
         (xys : list (binary_float prec emax * binary_float prec emax)),
  IeeeFoldModel.bv_sub_1_lanes prec emax nan_plus nan_minus nan_abs nan_fma nan_const W rx ry xys =
  IeeeFoldModel.bv_sub_1_seq prec emax nan_plus nan_minus nan_abs nan_fma nan_const rx ry xys.
Proof.
intros. unfold IeeeFoldModel.bv_sub_1_lanes, IeeeFoldModel.bv_sub_1_seq. cbv zeta.
change (IeeeFoldModel.bv_sub_1_record prec emax nan_abs)
  with (IeeeFoldModel.norm_upper_1_step prec emax nan_abs).
change (IeeeFoldModel.bv_sub_1_combine prec emax)
  with (IeeeFoldModel.norm_upper_1_combine prec emax).
now rewrite norm_upper_1_lanes_seq_state.
Qed.

Lemma bv_sub_1_seq_ieee_v1 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (1 <= prec)%Z ->
  forall (rx ry : binary_float prec emax)
    (xys : list (binary_float prec emax * binary_float prec emax)),
  ((finite rx /\ 0 <= val rx /\ Forall (fun xy => ball_finite_1 (fst xy) rx) xys) \/
  (rx = infinity prec emax false /\ Forall (fun xy => ball_whole_1 (fst xy) rx) xys)) ->
  ((finite ry /\ 0 <= val ry /\ Forall (fun xy => ball_finite_1 (snd xy) ry) xys) \/
  (ry = infinity prec emax false /\ Forall (fun xy => ball_whole_1 (snd xy) ry) xys)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_sub_1_seq prec emax nan_plus nan_minus nan_abs nan_fma nan_const rx ry xys in
  ((finite r_ /\ 0 <= val r_ /\ Forall (fun w_ => ball_finite_1 w_ r_) ws_) \/
   (r_ = infinity prec emax false /\ Forall (fun w_ => ball_whole_1 w_ r_) ws_)) /\
  (flag_ = true <-> finite r_).
Proof.
intros prec emax Hp He nan_plus nan_minus nan_abs nan_fma nan_const Hp1 rx ry xys HX HY.
pose proof (canonical_radius_1 prec emax rx _ _ HX) as Nrx.
pose proof (canonical_radius_1 prec emax ry _ _ HY) as Nry.
unfold IeeeFoldModel.bv_sub_1_seq. cbv zeta.
apply (bv1_v1 prec emax nan_abs nan_const _
         (fun m => IeeeModel.bv_add_radius_1 prec emax nan_plus nan_fma m rx ry)).
intros m M.
destruct (add_radius_1_ieee prec emax nan_plus nan_fma m rx ry (mag_nonneg_ext prec emax m M)
            Nrx Nry) as [N E].
split. exact N. intros F. exact (proj1 (E F)).
Qed.

(* With a true mask and a finite radius: the radii are finite, every center written is finite
   and is the real model's, and the radius is nonnegative and the real model's. *)
Lemma bv_sub_1_true :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_abs : nan1 prec emax)
           (nan_fma : nan3 prec emax),
  (1 <= prec)%Z ->
  forall (rx ry : binary_float prec emax)
    (xys : list (binary_float prec emax * binary_float prec emax)),
  nonneg_ext rx -> nonneg_ext ry ->
  let ws := map (IeeeFoldModel.bv_sub_1_step prec emax nan_minus) xys in
  let s := fold_seq (IeeeFoldModel.norm_upper_1_step prec emax nan_abs)
             (IeeeOperations.pzero prec emax, true) ws in
  let rz := IeeeModel.bv_add_radius_1 prec emax nan_plus nan_fma (fst s) rx ry in
  snd s = true -> finite rz ->
  finite rx /\ finite ry /\ 0 <= val rz /\
  Forall (fun xy => finite (IeeeFoldModel.bv_sub_1_step prec emax nan_minus xy) /\
                    val (IeeeFoldModel.bv_sub_1_step prec emax nan_minus xy) =
                    sub_1_1 (ieee_emin prec emax) prec tie_even (val (fst xy)) (val (snd xy))) xys
                      /\
  val rz = FoldModel.bv_sub_1_radius (ieee_emin prec emax) prec tie_even (val rx) (val ry)
             (map (fun xy => (val (fst xy), val (snd xy))) xys).
Proof.
intros prec emax Hp He nan_plus nan_minus nan_abs nan_fma Hp1 rx ry xys Nrx Nry. cbv zeta. intros
    Eok Frz.
destruct (seq_1_state prec emax nan_abs (map (IeeeFoldModel.bv_sub_1_step prec emax nan_minus) xys))
  as [M HS].
set (s := fold_seq (IeeeFoldModel.norm_upper_1_step prec emax nan_abs)
            (IeeeOperations.pzero prec emax, true)
            (map (IeeeFoldModel.bv_sub_1_step prec emax nan_minus) xys)) in *.
destruct (add_radius_1_ieee prec emax nan_plus nan_fma (fst s) rx ry (mag_nonneg_ext prec emax _ M)
            Nrx Nry) as [Nr Er].
destruct (Er Frz) as [Fm [Frx [Fry Vr]]].
destruct (HS Fm Eok) as [Fws Vs].
assert (Hz : Forall (fun xy => finite (IeeeFoldModel.bv_sub_1_step prec emax nan_minus xy) /\
                    val (IeeeFoldModel.bv_sub_1_step prec emax nan_minus xy) =
                    sub_1_1 (ieee_emin prec emax) prec tie_even (val (fst xy)) (val (snd xy))) xys).
{ apply Forall_map_inv in Fws. revert Fws. apply Forall_impl. intros [a b] Fz. split. exact Fz.
  exact (proj1 (proj2 (proj2 (sub_1_1_entry prec emax nan_minus Hp1 a b _ eq_refl Fz)))). }
split. exact Frx. split. exact Fry. split. exact (nonneg_ext_fin prec emax _ Nr Frz).
split. exact Hz.
change (val (IeeeModel.bv_add_radius_1 prec emax nan_plus nan_fma (fst s) rx ry)) with
  (B2R prec emax (IeeeModel.bv_add_radius_1 prec emax nan_plus nan_fma (fst s) rx ry)).
rewrite Vr. unfold FoldModel.bv_sub_1_radius.
change (B2R prec emax (fst s)) with (fst (IeeeFoldNorm.vals prec emax s)). rewrite Vs.
unfold FoldModel.norm_upper_1_seq.
change FoldModel.bv_sub_1_record with FoldModel.norm_upper_1_step. f_equal. f_equal. f_equal.
unfold FoldModel.bv_sub_1_map. rewrite !map_map. apply map_ext_in. intros [a b] Hin.
exact (proj2 (proj1 (Forall_forall _ xys) Hz (a, b) Hin)).
Qed.

Lemma bv_sub_1_seq_ieee_v3 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (1 <= prec)%Z ->
  forall (rx ry : binary_float prec emax)
    (xys : list (binary_float prec emax * binary_float prec emax)),
  ((finite rx /\ 0 <= val rx /\ Forall (fun xy => ball_finite_1 (fst xy) rx) xys) \/
  (rx = infinity prec emax false /\ Forall (fun xy => ball_whole_1 (fst xy) rx) xys)) ->
  ((finite ry /\ 0 <= val ry /\ Forall (fun xy => ball_finite_1 (snd xy) ry) xys) \/
  (ry = infinity prec emax false /\ Forall (fun xy => ball_whole_1 (snd xy) ry) xys)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_sub_1_seq prec emax nan_plus nan_minus nan_abs nan_fma nan_const rx ry xys in
  (finite r_ ->
   finite rx /\ finite ry /\
   Forall2 (fun xy w_ =>
     let '(x, y) := xy in
     let z := w_ in
     val z = sub_1_1 (ieee_emin prec emax) prec tie_even (val x) (val y)) xys ws_ /\
   val r_ = FoldModel.bv_sub_1_radius (ieee_emin prec emax) prec tie_even (val rx) (val ry)
              (map (fun xy => (val (fst xy), val (snd xy))) xys)).
Proof.
intros prec emax Hp He nan_plus nan_minus nan_abs nan_fma nan_const Hp1 rx ry xys HX HY.
pose proof (canonical_radius_1 prec emax rx _ _ HX) as Nrx.
pose proof (canonical_radius_1 prec emax ry _ _ HY) as Nry.
generalize (bv_sub_1_true prec emax Hp He nan_plus nan_minus nan_abs nan_fma Hp1 rx ry xys Nrx Nry).
unfold IeeeFoldModel.bv_sub_1_seq. cbv zeta.
change (IeeeFoldModel.bv_sub_1_record prec emax nan_abs)
  with (IeeeFoldModel.norm_upper_1_step prec emax nan_abs).
set (s := fold_seq (IeeeFoldModel.norm_upper_1_step prec emax nan_abs)
            (IeeeOperations.pzero prec emax, true)
            (map (IeeeFoldModel.bv_sub_1_step prec emax nan_minus) xys)).
generalize (norm_finish_1_correct prec emax Hp He nan_abs nan_const
              (IeeeModel.bv_add_radius_1 prec emax nan_plus nan_fma (fst s) rx ry) (snd s)).
destruct (IeeeModel.norm_finish_1 prec emax nan_abs nan_const
            (IeeeModel.bv_add_radius_1 prec emax nan_plus nan_fma (fst s) rx ry) (snd s))
  as [r flag].
cbn [fst snd]. intros [H1 [H2 _]] T.
destruct flag; cbv beta iota.
- intros _. destruct (proj1 H1 eq_refl) as [Eok Frad]. rewrite (H2 eq_refl).
  destruct (T Eok Frad) as [Frx [Fry [_ [Hz Vr]]]].
  split. exact Frx. split. exact Fry. split.
  + apply Forall2_map_r. revert Hz. apply Forall_impl. intros [a b] [_ E]. exact E.
  + exact Vr.
- intros F. discriminate F.
Qed.

Lemma bv_sub_1_seq_ieee_v2 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (1 <= prec)%Z ->
  forall (rx ry : binary_float prec emax)
    (xys : list (binary_float prec emax * binary_float prec emax)),
  ((finite rx /\ 0 <= val rx /\ Forall (fun xy => ball_finite_1 (fst xy) rx) xys) \/
  (rx = infinity prec emax false /\ Forall (fun xy => ball_whole_1 (fst xy) rx) xys)) ->
  ((finite ry /\ 0 <= val ry /\ Forall (fun xy => ball_finite_1 (snd xy) ry) xys) \/
  (ry = infinity prec emax false /\ Forall (fun xy => ball_whole_1 (snd xy) ry) xys)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_sub_1_seq prec emax nan_plus nan_minus nan_abs nan_fma nan_const rx ry xys in
  Forall2 (fun xy w_ =>
    let '(x, y) := xy in
    let z := w_ in
    forall x_ y_ : R, in_ball_1 x rx x_ -> in_ball_1 y ry y_ -> in_ball_1 z r_ (x_ - y_))
    xys ws_.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_abs nan_fma nan_const Hp1 rx ry xys HX HY.
pose proof (canonical_radius_1 prec emax rx _ _ HX) as Nrx.
pose proof (canonical_radius_1 prec emax ry _ _ HY) as Nry.
generalize (bv_sub_1_true prec emax Hp He nan_plus nan_minus nan_abs nan_fma Hp1 rx ry xys Nrx Nry).
unfold IeeeFoldModel.bv_sub_1_seq. cbv zeta.
change (IeeeFoldModel.bv_sub_1_record prec emax nan_abs)
  with (IeeeFoldModel.norm_upper_1_step prec emax nan_abs).
set (s := fold_seq (IeeeFoldModel.norm_upper_1_step prec emax nan_abs)
            (IeeeOperations.pzero prec emax, true)
            (map (IeeeFoldModel.bv_sub_1_step prec emax nan_minus) xys)).
generalize (norm_finish_1_correct prec emax Hp He nan_abs nan_const
              (IeeeModel.bv_add_radius_1 prec emax nan_plus nan_fma (fst s) rx ry) (snd s)).
destruct (IeeeModel.norm_finish_1 prec emax nan_abs nan_const
            (IeeeModel.bv_add_radius_1 prec emax nan_plus nan_fma (fst s) rx ry) (snd s))
  as [r flag].
cbn [fst snd]. intros [H1 [H2 _]] T.
destruct flag; cbv beta iota.
- destruct (proj1 H1 eq_refl) as [Eok Frad]. rewrite (H2 eq_refl).
  destruct (T Eok Frad) as [Frx [Fry [Pr [Hz Vr]]]].
  assert (Bx : 0 <= val rx /\ Forall (fun xy => ball_finite_1 (fst xy) rx) xys).
  { destruct HX as [[_ [P B]]|[E _]]. split; assumption. rewrite E in Frx. discriminate Frx. }
  assert (By : 0 <= val ry /\ Forall (fun xy => ball_finite_1 (snd xy) ry) xys).
  { destruct HY as [[_ [P B]]|[E _]]. split; assumption. rewrite E in Fry. discriminate Fry. }
  destruct Bx as [Px Bx]. destruct By as [Py By].
  assert (Fv : Forall (fun xy => fmt (ieee_emin prec emax) prec (fst xy) /\
                                 fmt (ieee_emin prec emax) prec (snd xy))
                      (map (fun xy => (val (fst xy), val (snd xy))) xys)).
  { apply Forall_map. apply Forall_forall. intros xy _. split; apply val_format. }
  destruct (bv_sub_1_correct (ieee_emin prec emax) prec Hp1 (val rx) (val ry)
              (map (fun xy => (val (fst xy), val (snd xy))) xys)
              (val_format prec emax rx) Px (val_format prec emax ry) Py Fv) as [_ R].
  unfold FoldModel.bv_sub_1_map in R. apply Forall2_map_r_inv in R. apply Forall_map_inv in R.
  apply Forall2_map_r. apply Forall_forall. intros [a b] Hin.
  destruct (proj1 (Forall_forall _ xys) Hz (a, b) Hin) as [Fz Vz].
  pose proof (proj1 (Forall_forall _ xys) R (a, b) Hin) as Rab. cbn [fst snd] in Fz, Vz, Rab.
  cbv beta iota zeta. intros x_ y_ Ix Iy.
  destruct Ix as [[_ E]|[_ Dx]]. { rewrite E in Frx. discriminate Frx. }
  destruct Iy as [[_ E]|[_ Dy]]. { rewrite E in Fry. discriminate Fry. }
  right. split.
  + split. exact Fz. split. exact Frad. exact Pr.
  + rewrite Vz, Vr. exact (proj2 Rab x_ y_ Dx Dy).
- rewrite map_map. apply Forall2_map_r. apply Forall_forall. intros [a b] _.
  cbv beta iota zeta. intros x_ y_ _ _. left. split. exists false. reflexivity. reflexivity.
Qed.

(* The lane order: the same lemmas, since it returns what the sequential order returns. *)
Lemma bv_sub_1_lanes_ieee_v1 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (1 <= prec)%Z ->
  forall (W : nat) (rx ry : binary_float prec emax)
         (xys : list (binary_float prec emax * binary_float prec emax)),
  ((finite rx /\ 0 <= val rx /\ Forall (fun xy => ball_finite_1 (fst xy) rx) xys) \/
  (rx = infinity prec emax false /\ Forall (fun xy => ball_whole_1 (fst xy) rx) xys)) ->
  ((finite ry /\ 0 <= val ry /\ Forall (fun xy => ball_finite_1 (snd xy) ry) xys) \/
  (ry = infinity prec emax false /\ Forall (fun xy => ball_whole_1 (snd xy) ry) xys)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_sub_1_lanes prec emax nan_plus nan_minus nan_abs nan_fma nan_const W rx ry xys
      in
  ((finite r_ /\ 0 <= val r_ /\ Forall (fun w_ => ball_finite_1 w_ r_) ws_) \/
   (r_ = infinity prec emax false /\ Forall (fun w_ => ball_whole_1 w_ r_) ws_)) /\
  (flag_ = true <-> finite r_).
Proof.
intros prec emax Hp He nan_plus nan_minus nan_abs nan_fma nan_const Hp1 W rx ry xys HX HY.
rewrite bv_sub_1_lanes_seq_ieee.
exact (bv_sub_1_seq_ieee_v1 prec emax Hp He nan_plus nan_minus nan_abs nan_fma nan_const Hp1 rx ry
    xys HX HY).
Qed.

Lemma bv_sub_1_lanes_ieee_v2 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (1 <= prec)%Z ->
  forall (W : nat) (rx ry : binary_float prec emax)
         (xys : list (binary_float prec emax * binary_float prec emax)),
  ((finite rx /\ 0 <= val rx /\ Forall (fun xy => ball_finite_1 (fst xy) rx) xys) \/
  (rx = infinity prec emax false /\ Forall (fun xy => ball_whole_1 (fst xy) rx) xys)) ->
  ((finite ry /\ 0 <= val ry /\ Forall (fun xy => ball_finite_1 (snd xy) ry) xys) \/
  (ry = infinity prec emax false /\ Forall (fun xy => ball_whole_1 (snd xy) ry) xys)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_sub_1_lanes prec emax nan_plus nan_minus nan_abs nan_fma nan_const W rx ry xys
      in
  Forall2 (fun xy w_ =>
    let '(x, y) := xy in
    let z := w_ in
    forall x_ y_ : R, in_ball_1 x rx x_ -> in_ball_1 y ry y_ -> in_ball_1 z r_ (x_ - y_))
    xys ws_.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_abs nan_fma nan_const Hp1 W rx ry xys HX HY.
rewrite bv_sub_1_lanes_seq_ieee.
exact (bv_sub_1_seq_ieee_v2 prec emax Hp He nan_plus nan_minus nan_abs nan_fma nan_const Hp1 rx ry
    xys HX HY).
Qed.

Lemma bv_sub_1_lanes_ieee_v3 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (1 <= prec)%Z ->
  forall (W : nat) (rx ry : binary_float prec emax)
         (xys : list (binary_float prec emax * binary_float prec emax)),
  ((finite rx /\ 0 <= val rx /\ Forall (fun xy => ball_finite_1 (fst xy) rx) xys) \/
  (rx = infinity prec emax false /\ Forall (fun xy => ball_whole_1 (fst xy) rx) xys)) ->
  ((finite ry /\ 0 <= val ry /\ Forall (fun xy => ball_finite_1 (snd xy) ry) xys) \/
  (ry = infinity prec emax false /\ Forall (fun xy => ball_whole_1 (snd xy) ry) xys)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_sub_1_lanes prec emax nan_plus nan_minus nan_abs nan_fma nan_const W rx ry xys
      in
  (finite r_ ->
   finite rx /\ finite ry /\
   Forall2 (fun xy w_ =>
     let '(x, y) := xy in
     let z := w_ in
     val z = sub_1_1 (ieee_emin prec emax) prec tie_even (val x) (val y)) xys ws_ /\
   val r_ = FoldModel.bv_sub_1_radius (ieee_emin prec emax) prec tie_even (val rx) (val ry)
              (map (fun xy => (val (fst xy), val (snd xy))) xys)).
Proof.
intros prec emax Hp He nan_plus nan_minus nan_abs nan_fma nan_const Hp1 W rx ry xys HX HY.
rewrite bv_sub_1_lanes_seq_ieee.
exact (bv_sub_1_seq_ieee_v3 prec emax Hp He nan_plus nan_minus nan_abs nan_fma nan_const Hp1 rx ry
    xys HX HY).
Qed.

(** * bv_scale_1 *)

Lemma bv_scale_1_lanes_seq_ieee :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true})
         (W : nat) (rx a : binary_float prec emax) (xs : list (binary_float prec emax)),
  IeeeFoldModel.bv_scale_1_lanes prec emax nan_abs nan_fma nan_const W rx a xs =
  IeeeFoldModel.bv_scale_1_seq prec emax nan_abs nan_fma nan_const rx a xs.
Proof.
intros. unfold IeeeFoldModel.bv_scale_1_lanes, IeeeFoldModel.bv_scale_1_seq. cbv zeta.
change (IeeeFoldModel.bv_scale_1_record prec emax nan_abs)
  with (IeeeFoldModel.norm_upper_1_step prec emax nan_abs).
change (IeeeFoldModel.bv_scale_1_combine prec emax)
  with (IeeeFoldModel.norm_upper_1_combine prec emax).
now rewrite norm_upper_1_lanes_seq_state.
Qed.

Lemma bv_scale_1_seq_ieee_v1 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (1 <= prec)%Z ->
  forall (rx a : binary_float prec emax) (xs : list (binary_float prec emax)),
  ((finite rx /\ 0 <= val rx /\ Forall (fun x => ball_finite_1 x rx) xs) \/
  (rx = infinity prec emax false /\ Forall (fun x => ball_whole_1 x rx) xs)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_scale_1_seq prec emax nan_abs nan_fma nan_const rx a xs in
  ((finite r_ /\ 0 <= val r_ /\ Forall (fun w_ => ball_finite_1 w_ r_) ws_) \/
   (r_ = infinity prec emax false /\ Forall (fun w_ => ball_whole_1 w_ r_) ws_)) /\
  (flag_ = true <-> finite r_).
Proof.
intros prec emax Hp He nan_abs nan_fma nan_const Hp1 rx a xs HX.
pose proof (canonical_radius_1 prec emax rx _ _ HX) as Nrx.
unfold IeeeFoldModel.bv_scale_1_seq. cbv zeta.
apply (bv1_v1 prec emax nan_abs nan_const _
         (fun m => IeeeModel.bv_scale_radius_1 prec emax nan_abs nan_fma m rx a)).
intros m M.
destruct (scale_radius_1_ieee prec emax nan_abs nan_fma m rx a (mag_nonneg_ext prec emax m M) Nrx)
  as [N E].
split. exact N. intros F. exact (proj1 (E F)).
Qed.

Lemma bv_scale_1_true :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax),
  (1 <= prec)%Z ->
  forall (rx a : binary_float prec emax) (xs : list (binary_float prec emax)),
  nonneg_ext rx ->
  let ws := map (IeeeFoldModel.bv_scale_1_step prec emax nan_fma a) xs in
  let s := fold_seq (IeeeFoldModel.norm_upper_1_step prec emax nan_abs)
             (IeeeOperations.pzero prec emax, true) ws in
  let rz := IeeeModel.bv_scale_radius_1 prec emax nan_abs nan_fma (fst s) rx a in
  snd s = true -> finite rz ->
  finite rx /\ finite a /\ 0 <= val rz /\
  Forall (fun x => finite (IeeeFoldModel.bv_scale_1_step prec emax nan_fma a x) /\
                   val (IeeeFoldModel.bv_scale_1_step prec emax nan_fma a x) =
                   scale_step_1 (ieee_emin prec emax) prec tie_even (val x) (val a)) xs /\
  val rz = FoldModel.bv_scale_1_radius (ieee_emin prec emax) prec tie_even (val rx) (val a)
             (map (fun x => val x) xs).
Proof.
intros prec emax Hp He nan_abs nan_fma Hp1 rx a xs Nrx. cbv zeta. intros Eok Frz.
destruct (seq_1_state prec emax nan_abs
    (map (IeeeFoldModel.bv_scale_1_step prec emax nan_fma a) xs))
  as [M HS].
set (s := fold_seq (IeeeFoldModel.norm_upper_1_step prec emax nan_abs)
            (IeeeOperations.pzero prec emax, true)
            (map (IeeeFoldModel.bv_scale_1_step prec emax nan_fma a) xs)) in *.
destruct (scale_radius_1_ieee prec emax nan_abs nan_fma (fst s) rx a (mag_nonneg_ext prec emax _ M)
            Nrx) as [Nr Er].
destruct (Er Frz) as [Fm [Frx [Fa Vr]]].
destruct (HS Fm Eok) as [Fws Vs].
assert (Hz : Forall (fun x => finite (IeeeFoldModel.bv_scale_1_step prec emax nan_fma a x) /\
                   val (IeeeFoldModel.bv_scale_1_step prec emax nan_fma a x) =
                   scale_step_1 (ieee_emin prec emax) prec tie_even (val x) (val a)) xs).
{ apply Forall_map_inv in Fws. revert Fws. apply Forall_impl. intros x Fz. split. exact Fz.
  exact (proj1 (proj2 (proj2 (scale_step_1_entry prec emax nan_fma Hp1 x a _ eq_refl Fz)))). }
split. exact Frx. split. exact Fa. split. exact (nonneg_ext_fin prec emax _ Nr Frz).
split. exact Hz.
change (val (IeeeModel.bv_scale_radius_1 prec emax nan_abs nan_fma (fst s) rx a)) with
  (B2R prec emax (IeeeModel.bv_scale_radius_1 prec emax nan_abs nan_fma (fst s) rx a)).
rewrite Vr. unfold FoldModel.bv_scale_1_radius.
change (B2R prec emax (fst s)) with (fst (IeeeFoldNorm.vals prec emax s)). rewrite Vs.
unfold FoldModel.norm_upper_1_seq.
change FoldModel.bv_scale_1_record with FoldModel.norm_upper_1_step. f_equal. f_equal. f_equal.
unfold FoldModel.bv_scale_1_map. rewrite !map_map. apply map_ext_in. intros x Hin.
exact (proj2 (proj1 (Forall_forall _ xs) Hz x Hin)).
Qed.

Lemma bv_scale_1_seq_ieee_v3 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (1 <= prec)%Z ->
  forall (rx a : binary_float prec emax) (xs : list (binary_float prec emax)),
  ((finite rx /\ 0 <= val rx /\ Forall (fun x => ball_finite_1 x rx) xs) \/
  (rx = infinity prec emax false /\ Forall (fun x => ball_whole_1 x rx) xs)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_scale_1_seq prec emax nan_abs nan_fma nan_const rx a xs in
  (finite r_ ->
   finite rx /\ finite a /\
   Forall2 (fun x w_ =>
     let z := w_ in
     val z = scale_step_1 (ieee_emin prec emax) prec tie_even (val x) (val a)) xs ws_ /\
   val r_ = FoldModel.bv_scale_1_radius (ieee_emin prec emax) prec tie_even (val rx) (val a)
              (map (fun x => val x) xs)).
Proof.
intros prec emax Hp He nan_abs nan_fma nan_const Hp1 rx a xs HX.
pose proof (canonical_radius_1 prec emax rx _ _ HX) as Nrx.
generalize (bv_scale_1_true prec emax Hp He nan_abs nan_fma Hp1 rx a xs Nrx).
unfold IeeeFoldModel.bv_scale_1_seq. cbv zeta.
change (IeeeFoldModel.bv_scale_1_record prec emax nan_abs)
  with (IeeeFoldModel.norm_upper_1_step prec emax nan_abs).
set (s := fold_seq (IeeeFoldModel.norm_upper_1_step prec emax nan_abs)
            (IeeeOperations.pzero prec emax, true)
            (map (IeeeFoldModel.bv_scale_1_step prec emax nan_fma a) xs)).
generalize (norm_finish_1_correct prec emax Hp He nan_abs nan_const
              (IeeeModel.bv_scale_radius_1 prec emax nan_abs nan_fma (fst s) rx a) (snd s)).
destruct (IeeeModel.norm_finish_1 prec emax nan_abs nan_const
            (IeeeModel.bv_scale_radius_1 prec emax nan_abs nan_fma (fst s) rx a) (snd s))
  as [r flag].
cbn [fst snd]. intros [H1 [H2 _]] T.
destruct flag; cbv beta iota.
- intros _. destruct (proj1 H1 eq_refl) as [Eok Frad]. rewrite (H2 eq_refl).
  destruct (T Eok Frad) as [Frx [Fa [_ [Hz Vr]]]].
  split. exact Frx. split. exact Fa. split.
  + apply Forall2_map_r. revert Hz. apply Forall_impl. intros x [_ E]. exact E.
  + exact Vr.
- intros F. discriminate F.
Qed.

Lemma bv_scale_1_seq_ieee_v2 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (1 <= prec)%Z ->
  forall (rx a : binary_float prec emax) (xs : list (binary_float prec emax)),
  ((finite rx /\ 0 <= val rx /\ Forall (fun x => ball_finite_1 x rx) xs) \/
  (rx = infinity prec emax false /\ Forall (fun x => ball_whole_1 x rx) xs)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_scale_1_seq prec emax nan_abs nan_fma nan_const rx a xs in
  Forall2 (fun x w_ =>
    let z := w_ in
    forall x_ : R, in_ball_1 x rx x_ -> in_ball_1 z r_ (x_ * val a))
    xs ws_.
Proof.
intros prec emax Hp He nan_abs nan_fma nan_const Hp1 rx a xs HX.
pose proof (canonical_radius_1 prec emax rx _ _ HX) as Nrx.
generalize (bv_scale_1_true prec emax Hp He nan_abs nan_fma Hp1 rx a xs Nrx).
unfold IeeeFoldModel.bv_scale_1_seq. cbv zeta.
change (IeeeFoldModel.bv_scale_1_record prec emax nan_abs)
  with (IeeeFoldModel.norm_upper_1_step prec emax nan_abs).
set (s := fold_seq (IeeeFoldModel.norm_upper_1_step prec emax nan_abs)
            (IeeeOperations.pzero prec emax, true)
            (map (IeeeFoldModel.bv_scale_1_step prec emax nan_fma a) xs)).
generalize (norm_finish_1_correct prec emax Hp He nan_abs nan_const
              (IeeeModel.bv_scale_radius_1 prec emax nan_abs nan_fma (fst s) rx a) (snd s)).
destruct (IeeeModel.norm_finish_1 prec emax nan_abs nan_const
            (IeeeModel.bv_scale_radius_1 prec emax nan_abs nan_fma (fst s) rx a) (snd s))
  as [r flag].
cbn [fst snd]. intros [H1 [H2 _]] T.
destruct flag; cbv beta iota.
- destruct (proj1 H1 eq_refl) as [Eok Frad]. rewrite (H2 eq_refl).
  destruct (T Eok Frad) as [Frx [Fa [Pr [Hz Vr]]]].
  assert (Bx : 0 <= val rx /\ Forall (fun x => ball_finite_1 x rx) xs).
  { destruct HX as [[_ [P B]]|[E _]]. split; assumption. rewrite E in Frx. discriminate Frx. }
  destruct Bx as [Px Bx].
  assert (Fv : Forall (fun x => fmt (ieee_emin prec emax) prec x) (map (fun x => val x) xs)).
  { apply Forall_map. apply Forall_forall. intros x _. apply val_format. }
  destruct (bv_scale_1_correct (ieee_emin prec emax) prec Hp1 (val rx) (val a)
              (map (fun x => val x) xs) (val_format prec emax rx) Px (val_format prec emax a) Fv)
    as [_ R].
  unfold FoldModel.bv_scale_1_map in R. apply Forall2_map_r_inv in R. apply Forall_map_inv in R.
  apply Forall2_map_r. apply Forall_forall. intros x Hin.
  destruct (proj1 (Forall_forall _ xs) Hz x Hin) as [Fz Vz].
  pose proof (proj1 (Forall_forall _ xs) R x Hin) as Rx.
  cbv beta iota zeta. intros x_ Ix.
  destruct Ix as [[_ E]|[_ Dx]]. { rewrite E in Frx. discriminate Frx. }
  right. split.
  + split. exact Fz. split. exact Frad. exact Pr.
  + rewrite Vz, Vr. exact (proj2 Rx x_ Dx).
- rewrite map_map. apply Forall2_map_r. apply Forall_forall. intros x _.
  cbv beta iota zeta. intros x_ _. left. split. exists false. reflexivity. reflexivity.
Qed.

Lemma bv_scale_1_lanes_ieee_v1 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (1 <= prec)%Z ->
  forall (W : nat) (rx a : binary_float prec emax) (xs : list (binary_float prec emax)),
  ((finite rx /\ 0 <= val rx /\ Forall (fun x => ball_finite_1 x rx) xs) \/
  (rx = infinity prec emax false /\ Forall (fun x => ball_whole_1 x rx) xs)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_scale_1_lanes prec emax nan_abs nan_fma nan_const W rx a xs in
  ((finite r_ /\ 0 <= val r_ /\ Forall (fun w_ => ball_finite_1 w_ r_) ws_) \/
   (r_ = infinity prec emax false /\ Forall (fun w_ => ball_whole_1 w_ r_) ws_)) /\
  (flag_ = true <-> finite r_).
Proof.
intros prec emax Hp He nan_abs nan_fma nan_const Hp1 W rx a xs HX.
rewrite bv_scale_1_lanes_seq_ieee.
exact (bv_scale_1_seq_ieee_v1 prec emax Hp He nan_abs nan_fma nan_const Hp1 rx a xs HX).
Qed.

Lemma bv_scale_1_lanes_ieee_v2 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (1 <= prec)%Z ->
  forall (W : nat) (rx a : binary_float prec emax) (xs : list (binary_float prec emax)),
  ((finite rx /\ 0 <= val rx /\ Forall (fun x => ball_finite_1 x rx) xs) \/
  (rx = infinity prec emax false /\ Forall (fun x => ball_whole_1 x rx) xs)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_scale_1_lanes prec emax nan_abs nan_fma nan_const W rx a xs in
  Forall2 (fun x w_ =>
    let z := w_ in
    forall x_ : R, in_ball_1 x rx x_ -> in_ball_1 z r_ (x_ * val a))
    xs ws_.
Proof.
intros prec emax Hp He nan_abs nan_fma nan_const Hp1 W rx a xs HX.
rewrite bv_scale_1_lanes_seq_ieee.
exact (bv_scale_1_seq_ieee_v2 prec emax Hp He nan_abs nan_fma nan_const Hp1 rx a xs HX).
Qed.

Lemma bv_scale_1_lanes_ieee_v3 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (1 <= prec)%Z ->
  forall (W : nat) (rx a : binary_float prec emax) (xs : list (binary_float prec emax)),
  ((finite rx /\ 0 <= val rx /\ Forall (fun x => ball_finite_1 x rx) xs) \/
  (rx = infinity prec emax false /\ Forall (fun x => ball_whole_1 x rx) xs)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_scale_1_lanes prec emax nan_abs nan_fma nan_const W rx a xs in
  (finite r_ ->
   finite rx /\ finite a /\
   Forall2 (fun x w_ =>
     let z := w_ in
     val z = scale_step_1 (ieee_emin prec emax) prec tie_even (val x) (val a)) xs ws_ /\
   val r_ = FoldModel.bv_scale_1_radius (ieee_emin prec emax) prec tie_even (val rx) (val a)
              (map (fun x => val x) xs)).
Proof.
intros prec emax Hp He nan_abs nan_fma nan_const Hp1 W rx a xs HX.
rewrite bv_scale_1_lanes_seq_ieee.
exact (bv_scale_1_seq_ieee_v3 prec emax Hp He nan_abs nan_fma nan_const Hp1 rx a xs HX).
Qed.

(** * Centers of two limbs *)

(* An operand of a canonical ball vector of two limbs has canonical centers: finite and
   normalized, or zeros. *)
Lemma ball_canonical_2 :
  forall (prec emax : Z) (c0 c1 r : binary_float prec emax),
  ball_finite_2 c0 c1 r \/ ball_whole_2 c0 c1 r -> canonical_2 c0 c1.
Proof.
intros prec emax c0 c1 r [[F0 [F1 [N _]]]|[[s0 E0] [[s1 E1] _]]].
- left. split. exact F0. split. exact F1. exact N.
- left. subst c0 c1. split. reflexivity. split. reflexivity.
  change (val (B754_zero prec emax s0)) with 0. change (val (B754_zero prec emax s1)) with 0.
  split. apply generic_format_0. split. apply generic_format_0.
  unfold RN. rewrite Rplus_0_l. symmetry. apply round_0; auto with typeclass_instances.
Qed.

Lemma canonical_operands_2 :
  forall (prec emax : Z) (r : binary_float prec emax) (A : Type)
    (sel : A -> binary_float prec emax * binary_float prec emax)
         (xys : list A),
  ((finite r /\ 0 <= val r /\ Forall (fun xy => ball_finite_2 (fst (sel xy)) (snd (sel xy)) r) xys)
    \/
   (r = infinity prec emax false /\ Forall (fun xy => ball_whole_2 (fst (sel xy)) (snd (sel xy)) r)
     xys)) ->
  Forall (fun xy => canonical_2 (fst (sel xy)) (snd (sel xy))) xys.
Proof.
intros prec emax r A sel xys [[_ [_ B]]|[_ B]]; revert B; apply Forall_impl; intros xy H;
  apply (ball_canonical_2 prec emax _ _ r); [left|right]; exact H.
Qed.

(* The record of two limbs in the real model reads the leading limb. *)
Lemma real_record_2 :
  forall (s : R * bool) (x : R * R),
  FoldModel.norm_upper_2_step s x = FoldModel.norm_upper_1_step s (fst x).
Proof.
intros s x. unfold FoldModel.norm_upper_2_step, FoldModel.norm_upper_1_step, norm_step_2.
destruct (norm_step_1 (fst s) (snd s) (fst x)). reflexivity.
Qed.

Lemma real_record_2_seq :
  forall l : list (R * R),
  fold_seq FoldModel.norm_upper_2_step (0, true) l =
  fold_seq FoldModel.norm_upper_1_step (0, true) (map fst l).
Proof.
intros l. rewrite <- (fold_seq_map _ _ _ FoldModel.norm_upper_1_step fst (0, true) l).
apply fold_seq_ext. intros s x. apply real_record_2.
Qed.

(** * bv_add_2 *)

Lemma bv_add_2_lanes_seq_ieee :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true})
         (W : nat) (rx ry : binary_float prec emax)
         (xys : list ((binary_float prec emax * binary_float prec emax) *
                      (binary_float prec emax * binary_float prec emax))),
  IeeeFoldModel.bv_add_2_lanes prec emax nan_plus nan_minus nan_abs nan_fma nan_const W rx ry xys =
  IeeeFoldModel.bv_add_2_seq prec emax nan_plus nan_minus nan_abs nan_fma nan_const rx ry xys.
Proof.
intros. unfold IeeeFoldModel.bv_add_2_lanes, IeeeFoldModel.bv_add_2_seq. cbv zeta.
change (IeeeFoldModel.bv_add_2_record prec emax nan_abs)
  with (IeeeFoldModel.norm_upper_2_step prec emax nan_abs).
change (IeeeFoldModel.bv_add_2_combine prec emax)
  with (IeeeFoldModel.norm_upper_2_combine prec emax).
now rewrite norm_upper_2_lanes_seq_state.
Qed.

(* The centers written, entry by entry: a finite leading limb means a finite normalized
   center, the real model's. *)
Lemma bv_add_2_centers :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax),
  (3 <= prec)%Z ->
  forall xys : list ((binary_float prec emax * binary_float prec emax) *
                     (binary_float prec emax * binary_float prec emax)),
  Forall (fun xy => canonical_2 (fst (fst xy)) (snd (fst xy)) /\
                    canonical_2 (fst (snd xy)) (snd (snd xy))) xys ->
  Forall (fun xy =>
    let w := IeeeFoldModel.bv_add_2_step prec emax nan_plus nan_minus xy in
    finite (fst w) ->
    finite (snd w) /\ normalized_2 (ieee_emin prec emax) prec (val (fst w)) (val (snd w)) /\
    (val (fst w), val (snd w)) =
      add_2_2 (ieee_emin prec emax) prec tie_even (val (fst (fst xy))) (val (snd (fst xy)))
        (val (fst (snd xy))) (val (snd (snd xy)))) xys.
Proof.
intros prec emax Hp He nan_plus nan_minus Hp3 xys HQ. revert HQ. apply Forall_impl.
intros [[x0 x1] [y0 y1]] [Cx Cy]. cbn [fst snd] in Cx, Cy |- *.
unfold IeeeFoldModel.bv_add_2_step. cbn [fst snd].
destruct (IeeeModel.add_2_2 prec emax nan_plus nan_minus x0 x1 y0 y1) as [z0 z1] eqn:Ez.
cbn [fst snd]. intros Fz.
destruct (add_2_2_entry prec emax nan_plus nan_minus Hp3 x0 x1 y0 y1 Cx Cy z0 z1 Ez Fz)
  as [_ [_ [_ [_ [Fz1 [V [N _]]]]]]].
split. exact Fz1. split. exact N. exact V.
Qed.

Lemma bv_add_2_seq_ieee_v1 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (3 <= prec)%Z ->
  forall (rx ry : binary_float prec emax)
         (xys : list ((binary_float prec emax * binary_float prec emax) *
                      (binary_float prec emax * binary_float prec emax))),
  ((finite rx /\ 0 <= val rx /\ Forall (fun xy => ball_finite_2 (fst (fst xy)) (snd (fst xy)) rx)
    xys) \/
  (rx = infinity prec emax false /\ Forall (fun xy => ball_whole_2 (fst (fst xy)) (snd (fst xy)) rx)
    xys)) ->
  ((finite ry /\ 0 <= val ry /\ Forall (fun xy => ball_finite_2 (fst (snd xy)) (snd (snd xy)) ry)
    xys) \/
  (ry = infinity prec emax false /\ Forall (fun xy => ball_whole_2 (fst (snd xy)) (snd (snd xy)) ry)
    xys)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_add_2_seq prec emax nan_plus nan_minus nan_abs nan_fma nan_const rx ry xys in
  ((finite r_ /\ 0 <= val r_ /\ Forall (fun w_ => ball_finite_2 (fst w_) (snd w_) r_) ws_) \/
   (r_ = infinity prec emax false /\ Forall (fun w_ => ball_whole_2 (fst w_) (snd w_) r_) ws_)) /\
  (flag_ = true <-> finite r_).
Proof.
intros prec emax Hp He nan_plus nan_minus nan_abs nan_fma nan_const Hp3 rx ry xys HX HY.
pose proof (canonical_radius_1 prec emax rx _ _ HX) as Nrx.
pose proof (canonical_radius_1 prec emax ry _ _ HY) as Nry.
assert (HQ : Forall (fun xy => canonical_2 (fst (fst xy)) (snd (fst xy)) /\
                               canonical_2 (fst (snd xy)) (snd (snd xy))) xys).
{ apply Forall_and.
  - exact (canonical_operands_2 prec emax rx _ fst xys HX).
  - exact (canonical_operands_2 prec emax ry _ snd xys HY). }
pose proof (bv_add_2_centers prec emax Hp He nan_plus nan_minus Hp3 xys HQ) as Hc.
unfold IeeeFoldModel.bv_add_2_seq. cbv zeta.
apply (bv2_v1 prec emax nan_abs nan_const _
         (fun m => IeeeModel.bv_add_radius_2 prec emax nan_plus nan_fma m rx ry)).
- intros m M.
  destruct (add_radius_2_ieee prec emax nan_plus nan_fma Hp3 m rx ry
              (mag_nonneg_ext prec emax m M) Nrx Nry) as [N E].
  split. exact N. intros F. exact (proj1 (E F)).
- apply Forall_map. revert Hc. apply Forall_impl. intros xy H F.
  destruct (H F) as [F1 [N _]]. split; assumption.
Qed.

Lemma bv_add_2_true :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_abs : nan1 prec emax)
           (nan_fma : nan3 prec emax),
  (3 <= prec)%Z ->
  forall (rx ry : binary_float prec emax)
         (xys : list ((binary_float prec emax * binary_float prec emax) *
                      (binary_float prec emax * binary_float prec emax))),
  nonneg_ext rx -> nonneg_ext ry ->
  Forall (fun xy => canonical_2 (fst (fst xy)) (snd (fst xy)) /\
                    canonical_2 (fst (snd xy)) (snd (snd xy))) xys ->
  let ws := map (IeeeFoldModel.bv_add_2_step prec emax nan_plus nan_minus) xys in
  let s := fold_seq (IeeeFoldModel.norm_upper_2_step prec emax nan_abs)
             (IeeeOperations.pzero prec emax, true) ws in
  let rz := IeeeModel.bv_add_radius_2 prec emax nan_plus nan_fma (fst s) rx ry in
  snd s = true -> finite rz ->
  finite rx /\ finite ry /\ 0 <= val rz /\
  Forall (fun xy =>
    let w := IeeeFoldModel.bv_add_2_step prec emax nan_plus nan_minus xy in
    finite (fst w) /\ finite (snd w) /\
    normalized_2 (ieee_emin prec emax) prec (val (fst w)) (val (snd w)) /\
    (val (fst w), val (snd w)) =
      add_2_2 (ieee_emin prec emax) prec tie_even (val (fst (fst xy))) (val (snd (fst xy)))
        (val (fst (snd xy))) (val (snd (snd xy)))) xys /\
  val rz = FoldModel.bv_add_2_radius (ieee_emin prec emax) prec tie_even (val rx) (val ry)
             (map (fun xy => ((val (fst (fst xy)), val (snd (fst xy))),
                              (val (fst (snd xy)), val (snd (snd xy))))) xys).
Proof.
intros prec emax Hp He nan_plus nan_minus nan_abs nan_fma Hp3 rx ry xys Nrx Nry HQ.
cbv zeta. intros Eok Frz.
pose proof (bv_add_2_centers prec emax Hp He nan_plus nan_minus Hp3 xys HQ) as Hc.
set (ws := map (IeeeFoldModel.bv_add_2_step prec emax nan_plus nan_minus) xys) in *.
assert (E2 : fold_seq (IeeeFoldModel.norm_upper_2_step prec emax nan_abs)
               (IeeeOperations.pzero prec emax, true) ws =
             fold_seq (IeeeFoldModel.norm_upper_1_step prec emax nan_abs)
               (IeeeOperations.pzero prec emax, true) (map fst ws)).
{ rewrite <- (fold_seq_map _ _ _ (IeeeFoldModel.norm_upper_1_step prec emax nan_abs) fst
                (IeeeOperations.pzero prec emax, true) ws).
  apply fold_seq_ext. intros t x. apply step_2_eq. }
rewrite E2 in Eok, Frz |- *.
destruct (seq_1_state prec emax nan_abs (map fst ws)) as [M HS].
set (s := fold_seq (IeeeFoldModel.norm_upper_1_step prec emax nan_abs)
            (IeeeOperations.pzero prec emax, true) (map fst ws)) in *.
destruct (add_radius_2_ieee prec emax nan_plus nan_fma Hp3 (fst s) rx ry
            (mag_nonneg_ext prec emax _ M) Nrx Nry) as [Nr Er].
destruct (Er Frz) as [Fm [Frx [Fry Vr]]].
destruct (HS Fm Eok) as [Fws Vs].
assert (Hz : Forall (fun xy =>
    let w := IeeeFoldModel.bv_add_2_step prec emax nan_plus nan_minus xy in
    finite (fst w) /\ finite (snd w) /\
    normalized_2 (ieee_emin prec emax) prec (val (fst w)) (val (snd w)) /\
    (val (fst w), val (snd w)) =
      add_2_2 (ieee_emin prec emax) prec tie_even (val (fst (fst xy))) (val (snd (fst xy)))
        (val (fst (snd xy))) (val (snd (snd xy)))) xys).
{ unfold ws in Fws. apply Forall_map_inv in Fws. apply Forall_map_inv in Fws.
  apply Forall_forall. intros xy Hin.
  pose proof (proj1 (Forall_forall _ xys) Fws xy Hin) as F0.
  pose proof (proj1 (Forall_forall _ xys) Hc xy Hin) as H. cbv zeta in H |- *.
  destruct (H F0) as [F1 [N V]]. split. exact F0. split. exact F1. split. exact N. exact V. }
split. exact Frx. split. exact Fry. split. exact (nonneg_ext_fin prec emax _ Nr Frz).
split. exact Hz.
change (val (IeeeModel.bv_add_radius_2 prec emax nan_plus nan_fma (fst s) rx ry)) with
  (B2R prec emax (IeeeModel.bv_add_radius_2 prec emax nan_plus nan_fma (fst s) rx ry)).
rewrite Vr. unfold FoldModel.bv_add_2_radius.
change (B2R prec emax (fst s)) with (fst (IeeeFoldNorm.vals prec emax s)). rewrite Vs.
unfold FoldModel.norm_upper_1_seq.
change FoldModel.bv_add_2_record with FoldModel.norm_upper_2_step. rewrite real_record_2_seq.
f_equal. f_equal. f_equal.
unfold ws, FoldModel.bv_add_2_map. rewrite !map_map. apply map_ext_in. intros xy Hin.
pose proof (proj1 (Forall_forall _ xys) Hz xy Hin) as H. cbv zeta in H.
destruct H as [_ [_ [_ V]]]. exact (f_equal fst V).
Qed.

Lemma bv_add_2_seq_ieee_v3 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (3 <= prec)%Z ->
  forall (rx ry : binary_float prec emax)
         (xys : list ((binary_float prec emax * binary_float prec emax) *
                      (binary_float prec emax * binary_float prec emax))),
  ((finite rx /\ 0 <= val rx /\ Forall (fun xy => ball_finite_2 (fst (fst xy)) (snd (fst xy)) rx)
    xys) \/
  (rx = infinity prec emax false /\ Forall (fun xy => ball_whole_2 (fst (fst xy)) (snd (fst xy)) rx)
    xys)) ->
  ((finite ry /\ 0 <= val ry /\ Forall (fun xy => ball_finite_2 (fst (snd xy)) (snd (snd xy)) ry)
    xys) \/
  (ry = infinity prec emax false /\ Forall (fun xy => ball_whole_2 (fst (snd xy)) (snd (snd xy)) ry)
    xys)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_add_2_seq prec emax nan_plus nan_minus nan_abs nan_fma nan_const rx ry xys in
  (finite r_ ->
   finite rx /\ finite ry /\
   Forall2 (fun xy w_ =>
     let '((x0, x1), (y0, y1)) := xy in
     let '(z0, z1) := w_ in
     (val z0, val z1) = add_2_2 (ieee_emin prec emax) prec tie_even (val x0) (val x1) (val y0)
       (val y1)) xys ws_ /\
   val r_ = FoldModel.bv_add_2_radius (ieee_emin prec emax) prec tie_even (val rx) (val ry)
     (map (fun xy =>
     ((val (fst (fst xy)), val (snd (fst xy))), (val (fst (snd xy)), val (snd (snd xy))))) xys)).
Proof.
intros prec emax Hp He nan_plus nan_minus nan_abs nan_fma nan_const Hp3 rx ry xys HX HY.
pose proof (canonical_radius_1 prec emax rx _ _ HX) as Nrx.
pose proof (canonical_radius_1 prec emax ry _ _ HY) as Nry.
assert (HQ : Forall (fun xy => canonical_2 (fst (fst xy)) (snd (fst xy)) /\
                               canonical_2 (fst (snd xy)) (snd (snd xy))) xys).
{ apply Forall_forall. intros xy Hin. split.
  - exact (proj1 (Forall_forall _ xys) (canonical_operands_2 prec emax rx _ fst xys HX) xy Hin).
  - exact (proj1 (Forall_forall _ xys) (canonical_operands_2 prec emax ry _ snd xys HY) xy Hin). }
generalize (bv_add_2_true prec emax Hp He nan_plus nan_minus nan_abs nan_fma Hp3 rx ry xys
              Nrx Nry HQ).
unfold IeeeFoldModel.bv_add_2_seq. cbv zeta.
change (IeeeFoldModel.bv_add_2_record prec emax nan_abs)
  with (IeeeFoldModel.norm_upper_2_step prec emax nan_abs).
set (s := fold_seq (IeeeFoldModel.norm_upper_2_step prec emax nan_abs)
            (IeeeOperations.pzero prec emax, true)
            (map (IeeeFoldModel.bv_add_2_step prec emax nan_plus nan_minus) xys)).
generalize (norm_finish_1_correct prec emax Hp He nan_abs nan_const
              (IeeeModel.bv_add_radius_2 prec emax nan_plus nan_fma (fst s) rx ry) (snd s)).
destruct (IeeeModel.norm_finish_1 prec emax nan_abs nan_const
            (IeeeModel.bv_add_radius_2 prec emax nan_plus nan_fma (fst s) rx ry) (snd s))
  as [r flag].
cbn [fst snd]. intros [H1 [H2 _]] T.
destruct flag; cbv beta iota.
- intros _. destruct (proj1 H1 eq_refl) as [Eok Frad]. rewrite (H2 eq_refl).
  destruct (T Eok Frad) as [Frx [Fry [_ [Hz Vr]]]].
  split. exact Frx. split. exact Fry. split.
  + apply Forall2_map_r. revert Hz. apply Forall_impl. intros [[x0 x1] [y0 y1]] H.
    cbv zeta in H. destruct H as [_ [_ [_ V]]]. cbn [fst snd] in V.
    revert V. destruct
      (IeeeFoldModel.bv_add_2_step prec emax nan_plus nan_minus ((x0, x1), (y0, y1)))
      as [z0 z1].
    cbn [fst snd]. intros V. exact V.
  + exact Vr.
- intros F. discriminate F.
Qed.

Lemma bv_add_2_seq_ieee_v2 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (3 <= prec)%Z ->
  forall (rx ry : binary_float prec emax)
         (xys : list ((binary_float prec emax * binary_float prec emax) *
                      (binary_float prec emax * binary_float prec emax))),
  ((finite rx /\ 0 <= val rx /\ Forall (fun xy => ball_finite_2 (fst (fst xy)) (snd (fst xy)) rx)
    xys) \/
  (rx = infinity prec emax false /\ Forall (fun xy => ball_whole_2 (fst (fst xy)) (snd (fst xy)) rx)
    xys)) ->
  ((finite ry /\ 0 <= val ry /\ Forall (fun xy => ball_finite_2 (fst (snd xy)) (snd (snd xy)) ry)
    xys) \/
  (ry = infinity prec emax false /\ Forall (fun xy => ball_whole_2 (fst (snd xy)) (snd (snd xy)) ry)
    xys)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_add_2_seq prec emax nan_plus nan_minus nan_abs nan_fma nan_const rx ry xys in
  Forall2 (fun xy w_ =>
    let '((x0, x1), (y0, y1)) := xy in
    let '(z0, z1) := w_ in
    forall x_ y_ : R, in_ball_2 x0 x1 rx x_ -> in_ball_2 y0 y1 ry y_ -> in_ball_2 z0 z1 r_
      (x_ + y_))
    xys ws_.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_abs nan_fma nan_const Hp3 rx ry xys HX HY.
pose proof (canonical_radius_1 prec emax rx _ _ HX) as Nrx.
pose proof (canonical_radius_1 prec emax ry _ _ HY) as Nry.
assert (HQ : Forall (fun xy => canonical_2 (fst (fst xy)) (snd (fst xy)) /\
                               canonical_2 (fst (snd xy)) (snd (snd xy))) xys).
{ apply Forall_forall. intros xy Hin. split.
  - exact (proj1 (Forall_forall _ xys) (canonical_operands_2 prec emax rx _ fst xys HX) xy Hin).
  - exact (proj1 (Forall_forall _ xys) (canonical_operands_2 prec emax ry _ snd xys HY) xy Hin). }
generalize (bv_add_2_true prec emax Hp He nan_plus nan_minus nan_abs nan_fma Hp3 rx ry xys
              Nrx Nry HQ).
unfold IeeeFoldModel.bv_add_2_seq. cbv zeta.
change (IeeeFoldModel.bv_add_2_record prec emax nan_abs)
  with (IeeeFoldModel.norm_upper_2_step prec emax nan_abs).
set (s := fold_seq (IeeeFoldModel.norm_upper_2_step prec emax nan_abs)
            (IeeeOperations.pzero prec emax, true)
            (map (IeeeFoldModel.bv_add_2_step prec emax nan_plus nan_minus) xys)).
generalize (norm_finish_1_correct prec emax Hp He nan_abs nan_const
              (IeeeModel.bv_add_radius_2 prec emax nan_plus nan_fma (fst s) rx ry) (snd s)).
destruct (IeeeModel.norm_finish_1 prec emax nan_abs nan_const
            (IeeeModel.bv_add_radius_2 prec emax nan_plus nan_fma (fst s) rx ry) (snd s))
  as [r flag].
cbn [fst snd]. intros [H1 [H2 _]] T.
destruct flag; cbv beta iota.
- destruct (proj1 H1 eq_refl) as [Eok Frad]. rewrite (H2 eq_refl).
  destruct (T Eok Frad) as [Frx [Fry [Pr [Hz Vr]]]].
  assert (Bx : 0 <= val rx /\
               Forall (fun xy => ball_finite_2 (fst (fst xy)) (snd (fst xy)) rx) xys).
  { destruct HX as [[_ [P B]]|[E _]]. split; assumption. rewrite E in Frx. discriminate Frx. }
  assert (By : 0 <= val ry /\
               Forall (fun xy => ball_finite_2 (fst (snd xy)) (snd (snd xy)) ry) xys).
  { destruct HY as [[_ [P B]]|[E _]]. split; assumption. rewrite E in Fry. discriminate Fry. }
  destruct Bx as [Px Bx]. destruct By as [Py By].
  assert (Fv : Forall
    (fun xy => normalized_2 (ieee_emin prec emax) prec (fst (fst xy)) (snd (fst xy)) /\
                                 normalized_2 (ieee_emin prec emax) prec (fst (snd xy))
                                   (snd (snd xy)))
                      (map (fun xy => ((val (fst (fst xy)), val (snd (fst xy))),
                                       (val (fst (snd xy)), val (snd (snd xy))))) xys)).
  { apply Forall_map. apply Forall_forall. intros xy Hin.
    destruct (proj1 (Forall_forall _ xys) Bx xy Hin) as [_ [_ [Nx _]]].
    destruct (proj1 (Forall_forall _ xys) By xy Hin) as [_ [_ [Ny _]]].
    split; assumption. }
  destruct (bv_add_2_correct (ieee_emin prec emax) prec Hp3 (val rx) (val ry) _
              (val_format prec emax rx) Px (val_format prec emax ry) Py Fv) as [_ R].
  unfold FoldModel.bv_add_2_map in R. apply Forall2_map_r_inv in R. apply Forall_map_inv in R.
  apply Forall2_map_r. apply Forall_forall. intros [[x0 x1] [y0 y1]] Hin.
  pose proof (proj1 (Forall_forall _ xys) Hz _ Hin) as H. cbv zeta in H.
  pose proof (proj1 (Forall_forall _ xys) R _ Hin) as Rab.
  unfold FoldModel.bv_add_2_step in Rab. cbn [fst snd] in H, Rab.
  destruct H as [F0 [F1 [N V]]].
  revert F0 F1 N V Rab.
  destruct (IeeeFoldModel.bv_add_2_step prec emax nan_plus nan_minus ((x0, x1), (y0, y1)))
    as [z0 z1].
  cbn [fst snd]. intros F0 F1 N V Rab.
  rewrite <- V in Rab. cbv beta iota in Rab.
  cbv beta iota zeta. intros x_ y_ Ix Iy.
  destruct Ix as [[_ [_ E]]|[_ Dx]]. { rewrite E in Frx. discriminate Frx. }
  destruct Iy as [[_ [_ E]]|[_ Dy]]. { rewrite E in Fry. discriminate Fry. }
  right. split.
  + split. exact F0. split. exact F1. split. exact N. split. exact Frad. exact Pr.
  + rewrite Vr. exact (proj2 Rab x_ y_ Dx Dy).
- rewrite map_map. apply Forall2_map_r. apply Forall_forall. intros [[x0 x1] [y0 y1]] _.
  cbv beta iota zeta. intros x_ y_ _ _. left. split. exists false. reflexivity.
  split. exists false. reflexivity. reflexivity.
Qed.

Lemma bv_add_2_lanes_ieee_v1 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (3 <= prec)%Z ->
  forall (W : nat) (rx ry : binary_float prec emax)
         (xys : list ((binary_float prec emax * binary_float prec emax) *
                      (binary_float prec emax * binary_float prec emax))),
  ((finite rx /\ 0 <= val rx /\ Forall (fun xy => ball_finite_2 (fst (fst xy)) (snd (fst xy)) rx)
    xys) \/
  (rx = infinity prec emax false /\ Forall (fun xy => ball_whole_2 (fst (fst xy)) (snd (fst xy)) rx)
    xys)) ->
  ((finite ry /\ 0 <= val ry /\ Forall (fun xy => ball_finite_2 (fst (snd xy)) (snd (snd xy)) ry)
    xys) \/
  (ry = infinity prec emax false /\ Forall (fun xy => ball_whole_2 (fst (snd xy)) (snd (snd xy)) ry)
    xys)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_add_2_lanes prec emax nan_plus nan_minus nan_abs nan_fma nan_const W rx ry xys
      in
  ((finite r_ /\ 0 <= val r_ /\ Forall (fun w_ => ball_finite_2 (fst w_) (snd w_) r_) ws_) \/
   (r_ = infinity prec emax false /\ Forall (fun w_ => ball_whole_2 (fst w_) (snd w_) r_) ws_)) /\
  (flag_ = true <-> finite r_).
Proof.
intros prec emax Hp He nan_plus nan_minus nan_abs nan_fma nan_const Hp3 W rx ry xys HX HY.
rewrite bv_add_2_lanes_seq_ieee.
exact (bv_add_2_seq_ieee_v1 prec emax Hp He nan_plus nan_minus nan_abs nan_fma nan_const Hp3
         rx ry xys HX HY).
Qed.

Lemma bv_add_2_lanes_ieee_v2 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (3 <= prec)%Z ->
  forall (W : nat) (rx ry : binary_float prec emax)
         (xys : list ((binary_float prec emax * binary_float prec emax) *
                      (binary_float prec emax * binary_float prec emax))),
  ((finite rx /\ 0 <= val rx /\ Forall (fun xy => ball_finite_2 (fst (fst xy)) (snd (fst xy)) rx)
    xys) \/
  (rx = infinity prec emax false /\ Forall (fun xy => ball_whole_2 (fst (fst xy)) (snd (fst xy)) rx)
    xys)) ->
  ((finite ry /\ 0 <= val ry /\ Forall (fun xy => ball_finite_2 (fst (snd xy)) (snd (snd xy)) ry)
    xys) \/
  (ry = infinity prec emax false /\ Forall (fun xy => ball_whole_2 (fst (snd xy)) (snd (snd xy)) ry)
    xys)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_add_2_lanes prec emax nan_plus nan_minus nan_abs nan_fma nan_const W rx ry xys
      in
  Forall2 (fun xy w_ =>
    let '((x0, x1), (y0, y1)) := xy in
    let '(z0, z1) := w_ in
    forall x_ y_ : R, in_ball_2 x0 x1 rx x_ -> in_ball_2 y0 y1 ry y_ -> in_ball_2 z0 z1 r_
      (x_ + y_))
    xys ws_.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_abs nan_fma nan_const Hp3 W rx ry xys HX HY.
rewrite bv_add_2_lanes_seq_ieee.
exact (bv_add_2_seq_ieee_v2 prec emax Hp He nan_plus nan_minus nan_abs nan_fma nan_const Hp3
         rx ry xys HX HY).
Qed.

Lemma bv_add_2_lanes_ieee_v3 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (3 <= prec)%Z ->
  forall (W : nat) (rx ry : binary_float prec emax)
         (xys : list ((binary_float prec emax * binary_float prec emax) *
                      (binary_float prec emax * binary_float prec emax))),
  ((finite rx /\ 0 <= val rx /\ Forall (fun xy => ball_finite_2 (fst (fst xy)) (snd (fst xy)) rx)
    xys) \/
  (rx = infinity prec emax false /\ Forall (fun xy => ball_whole_2 (fst (fst xy)) (snd (fst xy)) rx)
    xys)) ->
  ((finite ry /\ 0 <= val ry /\ Forall (fun xy => ball_finite_2 (fst (snd xy)) (snd (snd xy)) ry)
    xys) \/
  (ry = infinity prec emax false /\ Forall (fun xy => ball_whole_2 (fst (snd xy)) (snd (snd xy)) ry)
    xys)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_add_2_lanes prec emax nan_plus nan_minus nan_abs nan_fma nan_const W rx ry xys
      in
  (finite r_ ->
   finite rx /\ finite ry /\
   Forall2 (fun xy w_ =>
     let '((x0, x1), (y0, y1)) := xy in
     let '(z0, z1) := w_ in
     (val z0, val z1) = add_2_2 (ieee_emin prec emax) prec tie_even (val x0) (val x1) (val y0)
       (val y1)) xys ws_ /\
   val r_ = FoldModel.bv_add_2_radius (ieee_emin prec emax) prec tie_even (val rx) (val ry)
     (map (fun xy =>
     ((val (fst (fst xy)), val (snd (fst xy))), (val (fst (snd xy)), val (snd (snd xy))))) xys)).
Proof.
intros prec emax Hp He nan_plus nan_minus nan_abs nan_fma nan_const Hp3 W rx ry xys HX HY.
rewrite bv_add_2_lanes_seq_ieee.
exact (bv_add_2_seq_ieee_v3 prec emax Hp He nan_plus nan_minus nan_abs nan_fma nan_const Hp3
         rx ry xys HX HY).
Qed.

(** * bv_sub_2: the same, with sub_2_2 *)

Lemma bv_sub_2_lanes_seq_ieee :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_opp nan_abs : nan1 prec emax)
           (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true})
         (W : nat) (rx ry : binary_float prec emax)
         (xys : list ((binary_float prec emax * binary_float prec emax) *
                      (binary_float prec emax * binary_float prec emax))),
  IeeeFoldModel.bv_sub_2_lanes prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const W rx
    ry xys =
  IeeeFoldModel.bv_sub_2_seq prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const rx ry
    xys.
Proof.
intros. unfold IeeeFoldModel.bv_sub_2_lanes, IeeeFoldModel.bv_sub_2_seq. cbv zeta.
change (IeeeFoldModel.bv_sub_2_record prec emax nan_abs)
  with (IeeeFoldModel.norm_upper_2_step prec emax nan_abs).
change (IeeeFoldModel.bv_sub_2_combine prec emax)
  with (IeeeFoldModel.norm_upper_2_combine prec emax).
now rewrite norm_upper_2_lanes_seq_state.
Qed.

(* The centers written, entry by entry: a finite leading limb means a finite normalized
   center, the real model's. *)
Lemma bv_sub_2_centers :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_opp : nan1 prec emax),
  (3 <= prec)%Z ->
  forall xys : list ((binary_float prec emax * binary_float prec emax) *
                     (binary_float prec emax * binary_float prec emax)),
  Forall (fun xy => canonical_2 (fst (fst xy)) (snd (fst xy)) /\
                    canonical_2 (fst (snd xy)) (snd (snd xy))) xys ->
  Forall (fun xy =>
    let w := IeeeFoldModel.bv_sub_2_step prec emax nan_plus nan_minus nan_opp xy in
    finite (fst w) ->
    finite (snd w) /\ normalized_2 (ieee_emin prec emax) prec (val (fst w)) (val (snd w)) /\
    (val (fst w), val (snd w)) =
      sub_2_2 (ieee_emin prec emax) prec tie_even (val (fst (fst xy))) (val (snd (fst xy)))
        (val (fst (snd xy))) (val (snd (snd xy)))) xys.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp Hp3 xys HQ. revert HQ. apply Forall_impl.
intros [[x0 x1] [y0 y1]] [Cx Cy]. cbn [fst snd] in Cx, Cy |- *.
unfold IeeeFoldModel.bv_sub_2_step. cbn [fst snd].
destruct (IeeeModel.sub_2_2 prec emax nan_plus nan_minus nan_opp x0 x1 y0 y1) as [z0 z1] eqn:Ez.
cbn [fst snd]. intros Fz.
destruct (sub_2_2_entry prec emax nan_plus nan_minus nan_opp Hp3 x0 x1 y0 y1 Cx Cy z0 z1 Ez Fz)
  as [_ [_ [_ [_ [Fz1 [V [N _]]]]]]].
split. exact Fz1. split. exact N. exact V.
Qed.

Lemma bv_sub_2_seq_ieee_v1 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_opp nan_abs : nan1 prec emax)
           (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (3 <= prec)%Z ->
  forall (rx ry : binary_float prec emax)
         (xys : list ((binary_float prec emax * binary_float prec emax) *
                      (binary_float prec emax * binary_float prec emax))),
  ((finite rx /\ 0 <= val rx /\ Forall (fun xy => ball_finite_2 (fst (fst xy)) (snd (fst xy)) rx)
    xys) \/
  (rx = infinity prec emax false /\ Forall (fun xy => ball_whole_2 (fst (fst xy)) (snd (fst xy)) rx)
    xys)) ->
  ((finite ry /\ 0 <= val ry /\ Forall (fun xy => ball_finite_2 (fst (snd xy)) (snd (snd xy)) ry)
    xys) \/
  (ry = infinity prec emax false /\ Forall (fun xy => ball_whole_2 (fst (snd xy)) (snd (snd xy)) ry)
    xys)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_sub_2_seq prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const rx ry
      xys in
  ((finite r_ /\ 0 <= val r_ /\ Forall (fun w_ => ball_finite_2 (fst w_) (snd w_) r_) ws_) \/
   (r_ = infinity prec emax false /\ Forall (fun w_ => ball_whole_2 (fst w_) (snd w_) r_) ws_)) /\
  (flag_ = true <-> finite r_).
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const Hp3 rx ry xys HX HY.
pose proof (canonical_radius_1 prec emax rx _ _ HX) as Nrx.
pose proof (canonical_radius_1 prec emax ry _ _ HY) as Nry.
assert (HQ : Forall (fun xy => canonical_2 (fst (fst xy)) (snd (fst xy)) /\
                               canonical_2 (fst (snd xy)) (snd (snd xy))) xys).
{ apply Forall_and.
  - exact (canonical_operands_2 prec emax rx _ fst xys HX).
  - exact (canonical_operands_2 prec emax ry _ snd xys HY). }
pose proof (bv_sub_2_centers prec emax Hp He nan_plus nan_minus nan_opp Hp3 xys HQ) as Hc.
unfold IeeeFoldModel.bv_sub_2_seq. cbv zeta.
apply (bv2_v1 prec emax nan_abs nan_const _
         (fun m => IeeeModel.bv_add_radius_2 prec emax nan_plus nan_fma m rx ry)).
- intros m M.
  destruct (add_radius_2_ieee prec emax nan_plus nan_fma Hp3 m rx ry
              (mag_nonneg_ext prec emax m M) Nrx Nry) as [N E].
  split. exact N. intros F. exact (proj1 (E F)).
- apply Forall_map. revert Hc. apply Forall_impl. intros xy H F.
  destruct (H F) as [F1 [N _]]. split; assumption.
Qed.

Lemma bv_sub_2_true :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_opp nan_abs : nan1 prec emax)
           (nan_fma : nan3 prec emax),
  (3 <= prec)%Z ->
  forall (rx ry : binary_float prec emax)
         (xys : list ((binary_float prec emax * binary_float prec emax) *
                      (binary_float prec emax * binary_float prec emax))),
  nonneg_ext rx -> nonneg_ext ry ->
  Forall (fun xy => canonical_2 (fst (fst xy)) (snd (fst xy)) /\
                    canonical_2 (fst (snd xy)) (snd (snd xy))) xys ->
  let ws := map (IeeeFoldModel.bv_sub_2_step prec emax nan_plus nan_minus nan_opp) xys in
  let s := fold_seq (IeeeFoldModel.norm_upper_2_step prec emax nan_abs)
             (IeeeOperations.pzero prec emax, true) ws in
  let rz := IeeeModel.bv_add_radius_2 prec emax nan_plus nan_fma (fst s) rx ry in
  snd s = true -> finite rz ->
  finite rx /\ finite ry /\ 0 <= val rz /\
  Forall (fun xy =>
    let w := IeeeFoldModel.bv_sub_2_step prec emax nan_plus nan_minus nan_opp xy in
    finite (fst w) /\ finite (snd w) /\
    normalized_2 (ieee_emin prec emax) prec (val (fst w)) (val (snd w)) /\
    (val (fst w), val (snd w)) =
      sub_2_2 (ieee_emin prec emax) prec tie_even (val (fst (fst xy))) (val (snd (fst xy)))
        (val (fst (snd xy))) (val (snd (snd xy)))) xys /\
  val rz = FoldModel.bv_sub_2_radius (ieee_emin prec emax) prec tie_even (val rx) (val ry)
             (map (fun xy => ((val (fst (fst xy)), val (snd (fst xy))),
                              (val (fst (snd xy)), val (snd (snd xy))))) xys).
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma Hp3 rx ry xys Nrx Nry HQ.
cbv zeta. intros Eok Frz.
pose proof (bv_sub_2_centers prec emax Hp He nan_plus nan_minus nan_opp Hp3 xys HQ) as Hc.
set (ws := map (IeeeFoldModel.bv_sub_2_step prec emax nan_plus nan_minus nan_opp) xys) in *.
assert (E2 : fold_seq (IeeeFoldModel.norm_upper_2_step prec emax nan_abs)
               (IeeeOperations.pzero prec emax, true) ws =
             fold_seq (IeeeFoldModel.norm_upper_1_step prec emax nan_abs)
               (IeeeOperations.pzero prec emax, true) (map fst ws)).
{ rewrite <- (fold_seq_map _ _ _ (IeeeFoldModel.norm_upper_1_step prec emax nan_abs) fst
                (IeeeOperations.pzero prec emax, true) ws).
  apply fold_seq_ext. intros t x. apply step_2_eq. }
rewrite E2 in Eok, Frz |- *.
destruct (seq_1_state prec emax nan_abs (map fst ws)) as [M HS].
set (s := fold_seq (IeeeFoldModel.norm_upper_1_step prec emax nan_abs)
            (IeeeOperations.pzero prec emax, true) (map fst ws)) in *.
destruct (add_radius_2_ieee prec emax nan_plus nan_fma Hp3 (fst s) rx ry
            (mag_nonneg_ext prec emax _ M) Nrx Nry) as [Nr Er].
destruct (Er Frz) as [Fm [Frx [Fry Vr]]].
destruct (HS Fm Eok) as [Fws Vs].
assert (Hz : Forall (fun xy =>
    let w := IeeeFoldModel.bv_sub_2_step prec emax nan_plus nan_minus nan_opp xy in
    finite (fst w) /\ finite (snd w) /\
    normalized_2 (ieee_emin prec emax) prec (val (fst w)) (val (snd w)) /\
    (val (fst w), val (snd w)) =
      sub_2_2 (ieee_emin prec emax) prec tie_even (val (fst (fst xy))) (val (snd (fst xy)))
        (val (fst (snd xy))) (val (snd (snd xy)))) xys).
{ unfold ws in Fws. apply Forall_map_inv in Fws. apply Forall_map_inv in Fws.
  apply Forall_forall. intros xy Hin.
  pose proof (proj1 (Forall_forall _ xys) Fws xy Hin) as F0.
  pose proof (proj1 (Forall_forall _ xys) Hc xy Hin) as H. cbv zeta in H |- *.
  destruct (H F0) as [F1 [N V]]. split. exact F0. split. exact F1. split. exact N. exact V. }
split. exact Frx. split. exact Fry. split. exact (nonneg_ext_fin prec emax _ Nr Frz).
split. exact Hz.
change (val (IeeeModel.bv_add_radius_2 prec emax nan_plus nan_fma (fst s) rx ry)) with
  (B2R prec emax (IeeeModel.bv_add_radius_2 prec emax nan_plus nan_fma (fst s) rx ry)).
rewrite Vr. unfold FoldModel.bv_sub_2_radius.
change (B2R prec emax (fst s)) with (fst (IeeeFoldNorm.vals prec emax s)). rewrite Vs.
unfold FoldModel.norm_upper_1_seq.
change FoldModel.bv_sub_2_record with FoldModel.norm_upper_2_step. rewrite real_record_2_seq.
f_equal. f_equal. f_equal.
unfold ws, FoldModel.bv_sub_2_map. rewrite !map_map. apply map_ext_in. intros xy Hin.
pose proof (proj1 (Forall_forall _ xys) Hz xy Hin) as H. cbv zeta in H.
destruct H as [_ [_ [_ V]]]. exact (f_equal fst V).
Qed.

Lemma bv_sub_2_seq_ieee_v3 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_opp nan_abs : nan1 prec emax)
           (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (3 <= prec)%Z ->
  forall (rx ry : binary_float prec emax)
         (xys : list ((binary_float prec emax * binary_float prec emax) *
                      (binary_float prec emax * binary_float prec emax))),
  ((finite rx /\ 0 <= val rx /\ Forall (fun xy => ball_finite_2 (fst (fst xy)) (snd (fst xy)) rx)
    xys) \/
  (rx = infinity prec emax false /\ Forall (fun xy => ball_whole_2 (fst (fst xy)) (snd (fst xy)) rx)
    xys)) ->
  ((finite ry /\ 0 <= val ry /\ Forall (fun xy => ball_finite_2 (fst (snd xy)) (snd (snd xy)) ry)
    xys) \/
  (ry = infinity prec emax false /\ Forall (fun xy => ball_whole_2 (fst (snd xy)) (snd (snd xy)) ry)
    xys)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_sub_2_seq prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const rx ry
      xys in
  (finite r_ ->
   finite rx /\ finite ry /\
   Forall2 (fun xy w_ =>
     let '((x0, x1), (y0, y1)) := xy in
     let '(z0, z1) := w_ in
     (val z0, val z1) = sub_2_2 (ieee_emin prec emax) prec tie_even (val x0) (val x1) (val y0)
       (val y1)) xys ws_ /\
   val r_ = FoldModel.bv_sub_2_radius (ieee_emin prec emax) prec tie_even (val rx) (val ry)
     (map (fun xy =>
     ((val (fst (fst xy)), val (snd (fst xy))), (val (fst (snd xy)), val (snd (snd xy))))) xys)).
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const Hp3 rx ry xys HX HY.
pose proof (canonical_radius_1 prec emax rx _ _ HX) as Nrx.
pose proof (canonical_radius_1 prec emax ry _ _ HY) as Nry.
assert (HQ : Forall (fun xy => canonical_2 (fst (fst xy)) (snd (fst xy)) /\
                               canonical_2 (fst (snd xy)) (snd (snd xy))) xys).
{ apply Forall_forall. intros xy Hin. split.
  - exact (proj1 (Forall_forall _ xys) (canonical_operands_2 prec emax rx _ fst xys HX) xy Hin).
  - exact (proj1 (Forall_forall _ xys) (canonical_operands_2 prec emax ry _ snd xys HY) xy Hin). }
generalize (bv_sub_2_true prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma Hp3 rx ry xys
              Nrx Nry HQ).
unfold IeeeFoldModel.bv_sub_2_seq. cbv zeta.
change (IeeeFoldModel.bv_sub_2_record prec emax nan_abs)
  with (IeeeFoldModel.norm_upper_2_step prec emax nan_abs).
set (s := fold_seq (IeeeFoldModel.norm_upper_2_step prec emax nan_abs)
            (IeeeOperations.pzero prec emax, true)
            (map (IeeeFoldModel.bv_sub_2_step prec emax nan_plus nan_minus nan_opp) xys)).
generalize (norm_finish_1_correct prec emax Hp He nan_abs nan_const
              (IeeeModel.bv_add_radius_2 prec emax nan_plus nan_fma (fst s) rx ry) (snd s)).
destruct (IeeeModel.norm_finish_1 prec emax nan_abs nan_const
            (IeeeModel.bv_add_radius_2 prec emax nan_plus nan_fma (fst s) rx ry) (snd s))
  as [r flag].
cbn [fst snd]. intros [H1 [H2 _]] T.
destruct flag; cbv beta iota.
- intros _. destruct (proj1 H1 eq_refl) as [Eok Frad]. rewrite (H2 eq_refl).
  destruct (T Eok Frad) as [Frx [Fry [_ [Hz Vr]]]].
  split. exact Frx. split. exact Fry. split.
  + apply Forall2_map_r. revert Hz. apply Forall_impl. intros [[x0 x1] [y0 y1]] H.
    cbv zeta in H. destruct H as [_ [_ [_ V]]]. cbn [fst snd] in V.
    revert V. destruct
      (IeeeFoldModel.bv_sub_2_step prec emax nan_plus nan_minus nan_opp ((x0, x1), (y0, y1)))
      as [z0 z1].
    cbn [fst snd]. intros V. exact V.
  + exact Vr.
- intros F. discriminate F.
Qed.

Lemma bv_sub_2_seq_ieee_v2 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_opp nan_abs : nan1 prec emax)
           (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (3 <= prec)%Z ->
  forall (rx ry : binary_float prec emax)
         (xys : list ((binary_float prec emax * binary_float prec emax) *
                      (binary_float prec emax * binary_float prec emax))),
  ((finite rx /\ 0 <= val rx /\ Forall (fun xy => ball_finite_2 (fst (fst xy)) (snd (fst xy)) rx)
    xys) \/
  (rx = infinity prec emax false /\ Forall (fun xy => ball_whole_2 (fst (fst xy)) (snd (fst xy)) rx)
    xys)) ->
  ((finite ry /\ 0 <= val ry /\ Forall (fun xy => ball_finite_2 (fst (snd xy)) (snd (snd xy)) ry)
    xys) \/
  (ry = infinity prec emax false /\ Forall (fun xy => ball_whole_2 (fst (snd xy)) (snd (snd xy)) ry)
    xys)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_sub_2_seq prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const rx ry
      xys in
  Forall2 (fun xy w_ =>
    let '((x0, x1), (y0, y1)) := xy in
    let '(z0, z1) := w_ in
    forall x_ y_ : R, in_ball_2 x0 x1 rx x_ -> in_ball_2 y0 y1 ry y_ -> in_ball_2 z0 z1 r_
      (x_ - y_))
    xys ws_.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const Hp3 rx ry xys HX HY.
pose proof (canonical_radius_1 prec emax rx _ _ HX) as Nrx.
pose proof (canonical_radius_1 prec emax ry _ _ HY) as Nry.
assert (HQ : Forall (fun xy => canonical_2 (fst (fst xy)) (snd (fst xy)) /\
                               canonical_2 (fst (snd xy)) (snd (snd xy))) xys).
{ apply Forall_forall. intros xy Hin. split.
  - exact (proj1 (Forall_forall _ xys) (canonical_operands_2 prec emax rx _ fst xys HX) xy Hin).
  - exact (proj1 (Forall_forall _ xys) (canonical_operands_2 prec emax ry _ snd xys HY) xy Hin). }
generalize (bv_sub_2_true prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma Hp3 rx ry xys
              Nrx Nry HQ).
unfold IeeeFoldModel.bv_sub_2_seq. cbv zeta.
change (IeeeFoldModel.bv_sub_2_record prec emax nan_abs)
  with (IeeeFoldModel.norm_upper_2_step prec emax nan_abs).
set (s := fold_seq (IeeeFoldModel.norm_upper_2_step prec emax nan_abs)
            (IeeeOperations.pzero prec emax, true)
            (map (IeeeFoldModel.bv_sub_2_step prec emax nan_plus nan_minus nan_opp) xys)).
generalize (norm_finish_1_correct prec emax Hp He nan_abs nan_const
              (IeeeModel.bv_add_radius_2 prec emax nan_plus nan_fma (fst s) rx ry) (snd s)).
destruct (IeeeModel.norm_finish_1 prec emax nan_abs nan_const
            (IeeeModel.bv_add_radius_2 prec emax nan_plus nan_fma (fst s) rx ry) (snd s))
  as [r flag].
cbn [fst snd]. intros [H1 [H2 _]] T.
destruct flag; cbv beta iota.
- destruct (proj1 H1 eq_refl) as [Eok Frad]. rewrite (H2 eq_refl).
  destruct (T Eok Frad) as [Frx [Fry [Pr [Hz Vr]]]].
  assert (Bx : 0 <= val rx /\
               Forall (fun xy => ball_finite_2 (fst (fst xy)) (snd (fst xy)) rx) xys).
  { destruct HX as [[_ [P B]]|[E _]]. split; assumption. rewrite E in Frx. discriminate Frx. }
  assert (By : 0 <= val ry /\
               Forall (fun xy => ball_finite_2 (fst (snd xy)) (snd (snd xy)) ry) xys).
  { destruct HY as [[_ [P B]]|[E _]]. split; assumption. rewrite E in Fry. discriminate Fry. }
  destruct Bx as [Px Bx]. destruct By as [Py By].
  assert (Fv : Forall
    (fun xy => normalized_2 (ieee_emin prec emax) prec (fst (fst xy)) (snd (fst xy)) /\
                                 normalized_2 (ieee_emin prec emax) prec (fst (snd xy))
                                   (snd (snd xy)))
                      (map (fun xy => ((val (fst (fst xy)), val (snd (fst xy))),
                                       (val (fst (snd xy)), val (snd (snd xy))))) xys)).
  { apply Forall_map. apply Forall_forall. intros xy Hin.
    destruct (proj1 (Forall_forall _ xys) Bx xy Hin) as [_ [_ [Nx _]]].
    destruct (proj1 (Forall_forall _ xys) By xy Hin) as [_ [_ [Ny _]]].
    split; assumption. }
  destruct (bv_sub_2_correct (ieee_emin prec emax) prec Hp3 (val rx) (val ry) _
              (val_format prec emax rx) Px (val_format prec emax ry) Py Fv) as [_ R].
  unfold FoldModel.bv_sub_2_map in R. apply Forall2_map_r_inv in R. apply Forall_map_inv in R.
  apply Forall2_map_r. apply Forall_forall. intros [[x0 x1] [y0 y1]] Hin.
  pose proof (proj1 (Forall_forall _ xys) Hz _ Hin) as H. cbv zeta in H.
  pose proof (proj1 (Forall_forall _ xys) R _ Hin) as Rab.
  unfold FoldModel.bv_sub_2_step in Rab. cbn [fst snd] in H, Rab.
  destruct H as [F0 [F1 [N V]]].
  revert F0 F1 N V Rab.
  destruct (IeeeFoldModel.bv_sub_2_step prec emax nan_plus nan_minus nan_opp ((x0, x1), (y0, y1)))
    as [z0 z1].
  cbn [fst snd]. intros F0 F1 N V Rab.
  rewrite <- V in Rab. cbv beta iota in Rab.
  cbv beta iota zeta. intros x_ y_ Ix Iy.
  destruct Ix as [[_ [_ E]]|[_ Dx]]. { rewrite E in Frx. discriminate Frx. }
  destruct Iy as [[_ [_ E]]|[_ Dy]]. { rewrite E in Fry. discriminate Fry. }
  right. split.
  + split. exact F0. split. exact F1. split. exact N. split. exact Frad. exact Pr.
  + rewrite Vr. exact (proj2 Rab x_ y_ Dx Dy).
- rewrite map_map. apply Forall2_map_r. apply Forall_forall. intros [[x0 x1] [y0 y1]] _.
  cbv beta iota zeta. intros x_ y_ _ _. left. split. exists false. reflexivity.
  split. exists false. reflexivity. reflexivity.
Qed.

Lemma bv_sub_2_lanes_ieee_v1 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_opp nan_abs : nan1 prec emax)
           (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (3 <= prec)%Z ->
  forall (W : nat) (rx ry : binary_float prec emax)
         (xys : list ((binary_float prec emax * binary_float prec emax) *
                      (binary_float prec emax * binary_float prec emax))),
  ((finite rx /\ 0 <= val rx /\ Forall (fun xy => ball_finite_2 (fst (fst xy)) (snd (fst xy)) rx)
    xys) \/
  (rx = infinity prec emax false /\ Forall (fun xy => ball_whole_2 (fst (fst xy)) (snd (fst xy)) rx)
    xys)) ->
  ((finite ry /\ 0 <= val ry /\ Forall (fun xy => ball_finite_2 (fst (snd xy)) (snd (snd xy)) ry)
    xys) \/
  (ry = infinity prec emax false /\ Forall (fun xy => ball_whole_2 (fst (snd xy)) (snd (snd xy)) ry)
    xys)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_sub_2_lanes prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const W rx
      ry xys in
  ((finite r_ /\ 0 <= val r_ /\ Forall (fun w_ => ball_finite_2 (fst w_) (snd w_) r_) ws_) \/
   (r_ = infinity prec emax false /\ Forall (fun w_ => ball_whole_2 (fst w_) (snd w_) r_) ws_)) /\
  (flag_ = true <-> finite r_).
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const Hp3 W rx ry xys HX HY.
rewrite bv_sub_2_lanes_seq_ieee.
exact (bv_sub_2_seq_ieee_v1 prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const Hp3
         rx ry xys HX HY).
Qed.

Lemma bv_sub_2_lanes_ieee_v2 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_opp nan_abs : nan1 prec emax)
           (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (3 <= prec)%Z ->
  forall (W : nat) (rx ry : binary_float prec emax)
         (xys : list ((binary_float prec emax * binary_float prec emax) *
                      (binary_float prec emax * binary_float prec emax))),
  ((finite rx /\ 0 <= val rx /\ Forall (fun xy => ball_finite_2 (fst (fst xy)) (snd (fst xy)) rx)
    xys) \/
  (rx = infinity prec emax false /\ Forall (fun xy => ball_whole_2 (fst (fst xy)) (snd (fst xy)) rx)
    xys)) ->
  ((finite ry /\ 0 <= val ry /\ Forall (fun xy => ball_finite_2 (fst (snd xy)) (snd (snd xy)) ry)
    xys) \/
  (ry = infinity prec emax false /\ Forall (fun xy => ball_whole_2 (fst (snd xy)) (snd (snd xy)) ry)
    xys)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_sub_2_lanes prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const W rx
      ry xys in
  Forall2 (fun xy w_ =>
    let '((x0, x1), (y0, y1)) := xy in
    let '(z0, z1) := w_ in
    forall x_ y_ : R, in_ball_2 x0 x1 rx x_ -> in_ball_2 y0 y1 ry y_ -> in_ball_2 z0 z1 r_
      (x_ - y_))
    xys ws_.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const Hp3 W rx ry xys HX HY.
rewrite bv_sub_2_lanes_seq_ieee.
exact (bv_sub_2_seq_ieee_v2 prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const Hp3
         rx ry xys HX HY).
Qed.

Lemma bv_sub_2_lanes_ieee_v3 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_opp nan_abs : nan1 prec emax)
           (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (3 <= prec)%Z ->
  forall (W : nat) (rx ry : binary_float prec emax)
         (xys : list ((binary_float prec emax * binary_float prec emax) *
                      (binary_float prec emax * binary_float prec emax))),
  ((finite rx /\ 0 <= val rx /\ Forall (fun xy => ball_finite_2 (fst (fst xy)) (snd (fst xy)) rx)
    xys) \/
  (rx = infinity prec emax false /\ Forall (fun xy => ball_whole_2 (fst (fst xy)) (snd (fst xy)) rx)
    xys)) ->
  ((finite ry /\ 0 <= val ry /\ Forall (fun xy => ball_finite_2 (fst (snd xy)) (snd (snd xy)) ry)
    xys) \/
  (ry = infinity prec emax false /\ Forall (fun xy => ball_whole_2 (fst (snd xy)) (snd (snd xy)) ry)
    xys)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_sub_2_lanes prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const W rx
      ry xys in
  (finite r_ ->
   finite rx /\ finite ry /\
   Forall2 (fun xy w_ =>
     let '((x0, x1), (y0, y1)) := xy in
     let '(z0, z1) := w_ in
     (val z0, val z1) = sub_2_2 (ieee_emin prec emax) prec tie_even (val x0) (val x1) (val y0)
       (val y1)) xys ws_ /\
   val r_ = FoldModel.bv_sub_2_radius (ieee_emin prec emax) prec tie_even (val rx) (val ry)
     (map (fun xy =>
     ((val (fst (fst xy)), val (snd (fst xy))), (val (fst (snd xy)), val (snd (snd xy))))) xys)).
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const Hp3 W rx ry xys HX HY.
rewrite bv_sub_2_lanes_seq_ieee.
exact (bv_sub_2_seq_ieee_v3 prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const Hp3
         rx ry xys HX HY).
Qed.

(** * bv_scale_2 *)

Lemma bv_scale_2_lanes_seq_ieee :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_opp nan_abs : nan1 prec emax)
         (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true})
         (W : nat) (rx a : binary_float prec emax)
         (xs : list (binary_float prec emax * binary_float prec emax)),
  IeeeFoldModel.bv_scale_2_lanes prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const W rx
    a xs =
  IeeeFoldModel.bv_scale_2_seq prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const rx a
    xs.
Proof.
intros. unfold IeeeFoldModel.bv_scale_2_lanes, IeeeFoldModel.bv_scale_2_seq. cbv zeta.
change (IeeeFoldModel.bv_scale_2_record prec emax nan_abs)
  with (IeeeFoldModel.norm_upper_2_step prec emax nan_abs).
change (IeeeFoldModel.bv_scale_2_combine prec emax)
  with (IeeeFoldModel.norm_upper_2_combine prec emax).
now rewrite norm_upper_2_lanes_seq_state.
Qed.

Lemma bv_scale_2_centers :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_opp : nan1 prec emax)
           (nan_fma : nan3 prec emax),
  (2 <= prec)%Z ->
  forall (a : binary_float prec emax) (xs : list (binary_float prec emax * binary_float prec emax)),
  Forall (fun x => canonical_2 (fst x) (snd x)) xs ->
  Forall (fun x =>
    let w := IeeeFoldModel.bv_scale_2_step prec emax nan_plus nan_minus nan_opp nan_fma a x in
    finite (fst w) ->
    finite a /\ finite (snd w) /\
    normalized_2 (ieee_emin prec emax) prec (val (fst w)) (val (snd w)) /\
    (val (fst w), val (snd w)) =
      scale_step_2 (ieee_emin prec emax) prec tie_even (val (fst x)) (val (snd x)) (val a)) xs.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp2 a xs HQ. revert HQ.
apply Forall_impl. intros [x0 x1] Cx. cbn [fst snd] in Cx |- *.
unfold IeeeFoldModel.bv_scale_2_step. cbn [fst snd].
destruct (IeeeModel.scale_step_2 prec emax nan_plus nan_minus nan_opp nan_fma x0 x1 a)
  as [z0 z1] eqn:Ez.
cbn [fst snd]. intros Fz.
destruct (scale_step_2_entry prec emax nan_plus nan_minus nan_opp nan_fma Hp2 x0 x1 a Cx z0 z1 Ez
    Fz)
  as [_ [_ [Fa [Fz1 [V [N _]]]]]].
split. exact Fa. split. exact Fz1. split. exact N. exact V.
Qed.

Lemma bv_scale_2_seq_ieee_v1 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_opp nan_abs : nan1 prec emax)
         (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (2 <= prec)%Z ->
  forall (rx a : binary_float prec emax)
    (xs : list (binary_float prec emax * binary_float prec emax)),
  ((finite rx /\ 0 <= val rx /\ Forall (fun x => ball_finite_2 (fst x) (snd x) rx) xs) \/
  (rx = infinity prec emax false /\ Forall (fun x => ball_whole_2 (fst x) (snd x) rx) xs)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_scale_2_seq prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const rx a
      xs in
  ((finite r_ /\ 0 <= val r_ /\ Forall (fun w_ => ball_finite_2 (fst w_) (snd w_) r_) ws_) \/
   (r_ = infinity prec emax false /\ Forall (fun w_ => ball_whole_2 (fst w_) (snd w_) r_) ws_)) /\
  (flag_ = true <-> finite r_).
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const Hp2 rx a xs HX.
pose proof (canonical_radius_1 prec emax rx _ _ HX) as Nrx.
pose proof (canonical_operands_2 prec emax rx _ (fun x => x) xs HX) as HQ.
pose proof (bv_scale_2_centers prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp2 a xs HQ) as
    Hc.
unfold IeeeFoldModel.bv_scale_2_seq. cbv zeta.
apply (bv2_v1 prec emax nan_abs nan_const _
         (fun m => IeeeModel.bv_scale_radius_2 prec emax nan_abs nan_fma m rx a)).
- intros m M.
  destruct (scale_radius_2_ieee prec emax nan_abs nan_fma Hp2 m rx a
              (mag_nonneg_ext prec emax m M) Nrx) as [N E].
  split. exact N. intros F. exact (proj1 (E F)).
- apply Forall_map. revert Hc. apply Forall_impl. intros x H F.
  destruct (H F) as [_ [F1 [N _]]]. split; assumption.
Qed.

Lemma bv_scale_2_true :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_opp nan_abs : nan1 prec emax)
         (nan_fma : nan3 prec emax),
  (2 <= prec)%Z ->
  forall (rx a : binary_float prec emax)
    (xs : list (binary_float prec emax * binary_float prec emax)),
  nonneg_ext rx ->
  Forall (fun x => canonical_2 (fst x) (snd x)) xs ->
  let ws := map (IeeeFoldModel.bv_scale_2_step prec emax nan_plus nan_minus nan_opp nan_fma a) xs in
  let s := fold_seq (IeeeFoldModel.norm_upper_2_step prec emax nan_abs)
             (IeeeOperations.pzero prec emax, true) ws in
  let rz := IeeeModel.bv_scale_radius_2 prec emax nan_abs nan_fma (fst s) rx a in
  snd s = true -> finite rz ->
  finite rx /\ finite a /\ 0 <= val rz /\
  Forall (fun x =>
    let w := IeeeFoldModel.bv_scale_2_step prec emax nan_plus nan_minus nan_opp nan_fma a x in
    finite (fst w) /\ finite (snd w) /\
    normalized_2 (ieee_emin prec emax) prec (val (fst w)) (val (snd w)) /\
    (val (fst w), val (snd w)) =
      scale_step_2 (ieee_emin prec emax) prec tie_even (val (fst x)) (val (snd x)) (val a)) xs /\
  val rz = FoldModel.bv_scale_2_radius (ieee_emin prec emax) prec tie_even (val rx) (val a)
             (map (fun x => (val (fst x), val (snd x))) xs).
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma Hp2 rx a xs Nrx HQ.
cbv zeta. intros Eok Frz.
pose proof (bv_scale_2_centers prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp2 a xs HQ)
  as Hc.
set (ws := map (IeeeFoldModel.bv_scale_2_step prec emax nan_plus nan_minus nan_opp nan_fma a) xs)
  in *.
assert (E2 : fold_seq (IeeeFoldModel.norm_upper_2_step prec emax nan_abs)
               (IeeeOperations.pzero prec emax, true) ws =
             fold_seq (IeeeFoldModel.norm_upper_1_step prec emax nan_abs)
               (IeeeOperations.pzero prec emax, true) (map fst ws)).
{ rewrite <- (fold_seq_map _ _ _ (IeeeFoldModel.norm_upper_1_step prec emax nan_abs) fst
                (IeeeOperations.pzero prec emax, true) ws).
  apply fold_seq_ext. intros t x. apply step_2_eq. }
rewrite E2 in Eok, Frz |- *.
destruct (seq_1_state prec emax nan_abs (map fst ws)) as [M HS].
set (s := fold_seq (IeeeFoldModel.norm_upper_1_step prec emax nan_abs)
            (IeeeOperations.pzero prec emax, true) (map fst ws)) in *.
destruct (scale_radius_2_ieee prec emax nan_abs nan_fma Hp2 (fst s) rx a
            (mag_nonneg_ext prec emax _ M) Nrx) as [Nr Er].
destruct (Er Frz) as [Fm [Frx [Fa Vr]]].
destruct (HS Fm Eok) as [Fws Vs].
assert (Hz : Forall (fun x =>
    let w := IeeeFoldModel.bv_scale_2_step prec emax nan_plus nan_minus nan_opp nan_fma a x in
    finite (fst w) /\ finite (snd w) /\
    normalized_2 (ieee_emin prec emax) prec (val (fst w)) (val (snd w)) /\
    (val (fst w), val (snd w)) =
      scale_step_2 (ieee_emin prec emax) prec tie_even (val (fst x)) (val (snd x)) (val a)) xs).
{ unfold ws in Fws. apply Forall_map_inv in Fws. apply Forall_map_inv in Fws.
  apply Forall_forall. intros x Hin.
  pose proof (proj1 (Forall_forall _ xs) Fws x Hin) as F0.
  pose proof (proj1 (Forall_forall _ xs) Hc x Hin) as H. cbv zeta in H |- *.
  destruct (H F0) as [_ [F1 [N V]]]. split. exact F0. split. exact F1. split. exact N. exact V. }
split. exact Frx. split. exact Fa. split. exact (nonneg_ext_fin prec emax _ Nr Frz).
split. exact Hz.
change (val (IeeeModel.bv_scale_radius_2 prec emax nan_abs nan_fma (fst s) rx a)) with
  (B2R prec emax (IeeeModel.bv_scale_radius_2 prec emax nan_abs nan_fma (fst s) rx a)).
rewrite Vr. unfold FoldModel.bv_scale_2_radius.
change (B2R prec emax (fst s)) with (fst (IeeeFoldNorm.vals prec emax s)). rewrite Vs.
unfold FoldModel.norm_upper_1_seq.
change FoldModel.bv_scale_2_record with FoldModel.norm_upper_2_step. rewrite real_record_2_seq.
f_equal. f_equal. f_equal.
unfold ws, FoldModel.bv_scale_2_map. rewrite !map_map. apply map_ext_in. intros x Hin.
pose proof (proj1 (Forall_forall _ xs) Hz x Hin) as H. cbv zeta in H.
destruct H as [_ [_ [_ V]]]. exact (f_equal fst V).
Qed.

Lemma bv_scale_2_seq_ieee_v3 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_opp nan_abs : nan1 prec emax)
         (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (2 <= prec)%Z ->
  forall (rx a : binary_float prec emax)
    (xs : list (binary_float prec emax * binary_float prec emax)),
  ((finite rx /\ 0 <= val rx /\ Forall (fun x => ball_finite_2 (fst x) (snd x) rx) xs) \/
  (rx = infinity prec emax false /\ Forall (fun x => ball_whole_2 (fst x) (snd x) rx) xs)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_scale_2_seq prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const rx a
      xs in
  (finite r_ ->
   finite rx /\ finite a /\
   Forall2 (fun x w_ =>
     let '(x0, x1) := x in
     let '(z0, z1) := w_ in
     (val z0, val z1) = scale_step_2 (ieee_emin prec emax) prec tie_even (val x0) (val x1) (val a))
       xs ws_ /\
   val r_ = FoldModel.bv_scale_2_radius (ieee_emin prec emax) prec tie_even (val rx) (val a)
              (map (fun x => (val (fst x), val (snd x))) xs)).
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const Hp2 rx a xs HX.
pose proof (canonical_radius_1 prec emax rx _ _ HX) as Nrx.
pose proof (canonical_operands_2 prec emax rx _ (fun x => x) xs HX) as HQ.
generalize (bv_scale_2_true prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma Hp2 rx a xs
              Nrx HQ).
unfold IeeeFoldModel.bv_scale_2_seq. cbv zeta.
change (IeeeFoldModel.bv_scale_2_record prec emax nan_abs)
  with (IeeeFoldModel.norm_upper_2_step prec emax nan_abs).
set (s := fold_seq (IeeeFoldModel.norm_upper_2_step prec emax nan_abs)
            (IeeeOperations.pzero prec emax, true)
            (map (IeeeFoldModel.bv_scale_2_step prec emax nan_plus nan_minus nan_opp nan_fma a)
              xs)).
generalize (norm_finish_1_correct prec emax Hp He nan_abs nan_const
              (IeeeModel.bv_scale_radius_2 prec emax nan_abs nan_fma (fst s) rx a) (snd s)).
destruct (IeeeModel.norm_finish_1 prec emax nan_abs nan_const
            (IeeeModel.bv_scale_radius_2 prec emax nan_abs nan_fma (fst s) rx a) (snd s))
  as [r flag].
cbn [fst snd]. intros [H1 [H2 _]] T.
destruct flag; cbv beta iota.
- intros _. destruct (proj1 H1 eq_refl) as [Eok Frad]. rewrite (H2 eq_refl).
  destruct (T Eok Frad) as [Frx [Fa [_ [Hz Vr]]]].
  split. exact Frx. split. exact Fa. split.
  + apply Forall2_map_r. revert Hz. apply Forall_impl. intros [x0 x1] H.
    cbv zeta in H. destruct H as [_ [_ [_ V]]]. cbn [fst snd] in V.
    revert V.
    destruct (IeeeFoldModel.bv_scale_2_step prec emax nan_plus nan_minus nan_opp nan_fma a (x0, x1))
      as [z0 z1].
    cbn [fst snd]. intros V. exact V.
  + exact Vr.
- intros F. discriminate F.
Qed.

Lemma bv_scale_2_seq_ieee_v2 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_opp nan_abs : nan1 prec emax)
         (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (2 <= prec)%Z ->
  forall (rx a : binary_float prec emax)
    (xs : list (binary_float prec emax * binary_float prec emax)),
  ((finite rx /\ 0 <= val rx /\ Forall (fun x => ball_finite_2 (fst x) (snd x) rx) xs) \/
  (rx = infinity prec emax false /\ Forall (fun x => ball_whole_2 (fst x) (snd x) rx) xs)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_scale_2_seq prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const rx a
      xs in
  Forall2 (fun x w_ =>
    let '(x0, x1) := x in
    let '(z0, z1) := w_ in
    forall x_ : R, in_ball_2 x0 x1 rx x_ -> in_ball_2 z0 z1 r_ (x_ * val a))
    xs ws_.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const Hp2 rx a xs HX.
pose proof (canonical_radius_1 prec emax rx _ _ HX) as Nrx.
pose proof (canonical_operands_2 prec emax rx _ (fun x => x) xs HX) as HQ.
generalize (bv_scale_2_true prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma Hp2 rx a xs
              Nrx HQ).
unfold IeeeFoldModel.bv_scale_2_seq. cbv zeta.
change (IeeeFoldModel.bv_scale_2_record prec emax nan_abs)
  with (IeeeFoldModel.norm_upper_2_step prec emax nan_abs).
set (s := fold_seq (IeeeFoldModel.norm_upper_2_step prec emax nan_abs)
            (IeeeOperations.pzero prec emax, true)
            (map (IeeeFoldModel.bv_scale_2_step prec emax nan_plus nan_minus nan_opp nan_fma a)
              xs)).
generalize (norm_finish_1_correct prec emax Hp He nan_abs nan_const
              (IeeeModel.bv_scale_radius_2 prec emax nan_abs nan_fma (fst s) rx a) (snd s)).
destruct (IeeeModel.norm_finish_1 prec emax nan_abs nan_const
            (IeeeModel.bv_scale_radius_2 prec emax nan_abs nan_fma (fst s) rx a) (snd s))
  as [r flag].
cbn [fst snd]. intros [H1 [H2 _]] T.
destruct flag; cbv beta iota.
- destruct (proj1 H1 eq_refl) as [Eok Frad]. rewrite (H2 eq_refl).
  destruct (T Eok Frad) as [Frx [Fa [Pr [Hz Vr]]]].
  assert (Bx : 0 <= val rx /\ Forall (fun x => ball_finite_2 (fst x) (snd x) rx) xs).
  { destruct HX as [[_ [P B]]|[E _]]. split; assumption. rewrite E in Frx. discriminate Frx. }
  destruct Bx as [Px Bx].
  assert (Fv : Forall (fun x => normalized_2 (ieee_emin prec emax) prec (fst x) (snd x))
                      (map (fun x => (val (fst x), val (snd x))) xs)).
  { apply Forall_map. apply Forall_forall. intros x Hin.
    destruct (proj1 (Forall_forall _ xs) Bx x Hin) as [_ [_ [Nx _]]]. exact Nx. }
  destruct (bv_scale_2_correct (ieee_emin prec emax) prec Hp2 (val rx) (val a) _
              (val_format prec emax rx) Px (val_format prec emax a) Fv) as [_ R].
  unfold FoldModel.bv_scale_2_map in R. apply Forall2_map_r_inv in R. apply Forall_map_inv in R.
  apply Forall2_map_r. apply Forall_forall. intros [x0 x1] Hin.
  pose proof (proj1 (Forall_forall _ xs) Hz _ Hin) as H. cbv zeta in H.
  pose proof (proj1 (Forall_forall _ xs) R _ Hin) as Rx.
  unfold FoldModel.bv_scale_2_step in Rx. cbn [fst snd] in H, Rx.
  destruct H as [F0 [F1 [N V]]].
  revert F0 F1 N V Rx.
  destruct (IeeeFoldModel.bv_scale_2_step prec emax nan_plus nan_minus nan_opp nan_fma a (x0, x1))
    as [z0 z1].
  cbn [fst snd]. intros F0 F1 N V Rx.
  rewrite <- V in Rx. cbv beta iota in Rx.
  cbv beta iota zeta. intros x_ Ix.
  destruct Ix as [[_ [_ E]]|[_ Dx]]. { rewrite E in Frx. discriminate Frx. }
  right. split.
  + split. exact F0. split. exact F1. split. exact N. split. exact Frad. exact Pr.
  + rewrite Vr. exact (proj2 Rx x_ Dx).
- rewrite map_map. apply Forall2_map_r. apply Forall_forall. intros [x0 x1] _.
  cbv beta iota zeta. intros x_ _. left. split. exists false. reflexivity.
  split. exists false. reflexivity. reflexivity.
Qed.

Lemma bv_scale_2_lanes_ieee_v1 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_opp nan_abs : nan1 prec emax)
         (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (2 <= prec)%Z ->
  forall (W : nat) (rx a : binary_float prec emax)
         (xs : list (binary_float prec emax * binary_float prec emax)),
  ((finite rx /\ 0 <= val rx /\ Forall (fun x => ball_finite_2 (fst x) (snd x) rx) xs) \/
  (rx = infinity prec emax false /\ Forall (fun x => ball_whole_2 (fst x) (snd x) rx) xs)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_scale_2_lanes prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const W
      rx a xs in
  ((finite r_ /\ 0 <= val r_ /\ Forall (fun w_ => ball_finite_2 (fst w_) (snd w_) r_) ws_) \/
   (r_ = infinity prec emax false /\ Forall (fun w_ => ball_whole_2 (fst w_) (snd w_) r_) ws_)) /\
  (flag_ = true <-> finite r_).
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const Hp2 W rx a xs HX.
rewrite bv_scale_2_lanes_seq_ieee.
exact (bv_scale_2_seq_ieee_v1 prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const
         Hp2 rx a xs HX).
Qed.

Lemma bv_scale_2_lanes_ieee_v2 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_opp nan_abs : nan1 prec emax)
         (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (2 <= prec)%Z ->
  forall (W : nat) (rx a : binary_float prec emax)
         (xs : list (binary_float prec emax * binary_float prec emax)),
  ((finite rx /\ 0 <= val rx /\ Forall (fun x => ball_finite_2 (fst x) (snd x) rx) xs) \/
  (rx = infinity prec emax false /\ Forall (fun x => ball_whole_2 (fst x) (snd x) rx) xs)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_scale_2_lanes prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const W
      rx a xs in
  Forall2 (fun x w_ =>
    let '(x0, x1) := x in
    let '(z0, z1) := w_ in
    forall x_ : R, in_ball_2 x0 x1 rx x_ -> in_ball_2 z0 z1 r_ (x_ * val a))
    xs ws_.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const Hp2 W rx a xs HX.
rewrite bv_scale_2_lanes_seq_ieee.
exact (bv_scale_2_seq_ieee_v2 prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const
         Hp2 rx a xs HX).
Qed.

Lemma bv_scale_2_lanes_ieee_v3 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_opp nan_abs : nan1 prec emax)
         (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (2 <= prec)%Z ->
  forall (W : nat) (rx a : binary_float prec emax)
         (xs : list (binary_float prec emax * binary_float prec emax)),
  ((finite rx /\ 0 <= val rx /\ Forall (fun x => ball_finite_2 (fst x) (snd x) rx) xs) \/
  (rx = infinity prec emax false /\ Forall (fun x => ball_whole_2 (fst x) (snd x) rx) xs)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_scale_2_lanes prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const W
      rx a xs in
  (finite r_ ->
   finite rx /\ finite a /\
   Forall2 (fun x w_ =>
     let '(x0, x1) := x in
     let '(z0, z1) := w_ in
     (val z0, val z1) = scale_step_2 (ieee_emin prec emax) prec tie_even (val x0) (val x1) (val a))
       xs ws_ /\
   val r_ = FoldModel.bv_scale_2_radius (ieee_emin prec emax) prec tie_even (val rx) (val a)
              (map (fun x => (val (fst x), val (snd x))) xs)).
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const Hp2 W rx a xs HX.
rewrite bv_scale_2_lanes_seq_ieee.
exact (bv_scale_2_seq_ieee_v3 prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const
         Hp2 rx a xs HX).
Qed.

(** * V4 for the other ball vectors, and for the lane order *)

(* V4 for bv_sub_1: that of bv_add_1, with sub_1_1. *)
Lemma bv_sub_1_seq_ieee_v4 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (2 <= prec)%Z ->
  forall (rx ry : binary_float prec emax)
    (xys : list (binary_float prec emax * binary_float prec emax)),
  ((finite rx /\ 0 <= val rx /\ Forall (fun xy => ball_finite_1 (fst xy) rx) xys) \/
  (rx = infinity prec emax false /\ Forall (fun xy => ball_whole_1 (fst xy) rx) xys)) ->
  ((finite ry /\ 0 <= val ry /\ Forall (fun xy => ball_finite_1 (snd xy) ry) xys) \/
  (ry = infinity prec emax false /\ Forall (fun xy => ball_whole_1 (snd xy) ry) xys)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_sub_1_seq prec emax nan_plus nan_minus nan_abs nan_fma nan_const rx ry xys in
  (finite rx -> finite ry ->
   Rabs (val rx + val ry) <= bpow radix2 (emax - 2) ->
   Forall (fun xy =>
     let '(x, y) := xy in
     Rabs (((Rabs (val x - val y)) + val rx) + val ry) <= bpow radix2 (emax - 2)) xys ->
   finite r_).
Proof.
intros prec emax Hp He nan_plus nan_minus nan_abs nan_fma nan_const Hp2 rx ry xys HX HY.
unfold IeeeFoldModel.bv_sub_1_seq. cbv zeta.
change (IeeeFoldModel.bv_sub_1_record prec emax nan_abs)
  with (IeeeFoldModel.norm_upper_1_step prec emax nan_abs).
set (ws := map (IeeeFoldModel.bv_sub_1_step prec emax nan_minus) xys).
set (s := fold_seq (IeeeFoldModel.norm_upper_1_step prec emax nan_abs)
            (IeeeOperations.pzero prec emax, true) ws).
set (rz := IeeeModel.bv_add_radius_1 prec emax nan_plus nan_fma (fst s) rx ry).
assert (Main : finite rx -> finite ry -> Rabs (val rx + val ry) <= bpow radix2 (emax - 2) ->
               Forall (fun xy => let '(x, y) := xy in
                         Rabs (((Rabs (val x - val y)) + val rx) + val ry) <= bpow radix2
                           (emax - 2))
                      xys ->
               snd s = true /\ finite rz).
2: { generalize (norm_finish_1_correct prec emax Hp He nan_abs nan_const rz (snd s)).
     destruct (IeeeModel.norm_finish_1 prec emax nan_abs nan_const rz (snd s)) as [r flag].
     cbn [fst snd]. intros [K1 [K2 _]].
     destruct flag; cbv beta iota; intros Frx Fry Hr Hent.
     - rewrite (K2 eq_refl). exact (proj2 (Main Frx Fry Hr Hent)).
     - exfalso. destruct (Main Frx Fry Hr Hent) as [E F].
       assert (K : false = true) by (apply K1; split; assumption). discriminate K. }
intros Frx Fry Hr Hent.
assert (Bx : 0 <= val rx /\ Forall (fun xy => ball_finite_1 (fst xy) rx) xys).
{ destruct HX as [[_ [P B]]|[E _]]. split; assumption. rewrite E in Frx. discriminate Frx. }
assert (By : 0 <= val ry /\ Forall (fun xy => ball_finite_1 (snd xy) ry) xys).
{ destruct HY as [[_ [P B]]|[E _]]. split; assumption. rewrite E in Fry. discriminate Fry. }
destruct Bx as [Px Bx]. destruct By as [Py By].
set (d := bpow radix2 (emax - 2 - prec - 1)).
assert (D0 : 0 < d) by apply bpow_gt_0.
assert (Hel : (3 - emax - prec + prec <= emax - 2)%Z).
{ generalize He. unfold BinarySingleNaN.Prec_lt_emax. lia. }
(* Every center written is finite and within d of the exact sum, which is within the limit. *)
assert (Hz : Forall (fun xy =>
          finite (IeeeFoldModel.bv_sub_1_step prec emax nan_minus xy) /\
          Rabs (val (IeeeFoldModel.bv_sub_1_step prec emax nan_minus xy)) <=
            Rabs (val (fst xy) - val (snd xy)) + d) xys).
{ apply Forall_forall. intros [a b] Hin.
  destruct (proj1 (Forall_forall _ xys) Bx (a, b) Hin) as [Fa _].
  destruct (proj1 (Forall_forall _ xys) By (a, b) Hin) as [Fb _].
  pose proof (proj1 (Forall_forall _ xys) Hent (a, b) Hin) as Hab. cbv beta iota in Hab.
  cbn [fst snd] in Fa, Fb |- *.
  assert (Lab : Rabs (val a - val b) <= bpow radix2 (emax - 2)).
  { generalize (Rabs_pos (val a - val b)). intros A0.
    rewrite Rabs_pos_eq in Hab by lra. lra. }
  assert (Ic : IeeeBridge.inrange emax (round radix2 (FLT_exp (3 - emax - prec) prec)
                                         (Znearest tie_even) (val a - val b))).
  { apply (le_bpow_inrange emax) with (emax - 2)%Z. lia. apply
    (RN_abs_le_bpow (3 - emax - prec) prec).
    exact Lab. }
  destruct (sub_spec prec emax nan_minus a b Fa Fb) as [S1 S2].
  assert (Fz : is_finite prec emax (IeeeOperations.sub prec emax nan_minus a b) = true)
    by now apply S1.
  split. exact Fz.
  unfold IeeeFoldModel.bv_sub_1_step, IeeeModel.sub_1_1. cbn [fst snd]. cbv zeta.
  unfold val. rewrite (S2 Fz).
  exact (abs_rnd_le_half prec emax _ (emax - 2) Hel Lab). }
assert (Fws : Forall (fun w => finite w) ws).
{ unfold ws. apply Forall_map. revert Hz. apply Forall_impl. intros xy [F _]. exact F. }
destruct (seq_1_good prec emax nan_abs ws Fws) as [M [Fm Eok]]. fold s in M, Fm, Eok.
destruct (seq_1_state prec emax nan_abs ws) as [_ HS]. fold s in HS.
destruct (HS Fm Eok) as [_ Vs].
rewrite norm_upper_1_seq_value in Vs.
assert (Vm : val (fst s) = fold_right Rmax 0 (map (fun x => Rabs x) (map (@val prec emax) ws))).
{ change (val (fst s)) with (fst (IeeeFoldNorm.vals prec emax s)). now rewrite Vs. }
(* The largest magnitude, against the limit. *)
set (b := 4 * (bpow radix2 (emax - 2) + d / 4 - (val rx + val ry))).
assert (Hrxy : val rx + val ry <= bpow radix2 (emax - 2)).
{ rewrite Rabs_pos_eq in Hr by lra. exact Hr. }
assert (Mb : val (fst s) <= b).
{ rewrite Vm. apply maxl_le. unfold b. lra.
  rewrite map_map. unfold ws. rewrite map_map. apply Forall_map.
  apply Forall_forall. intros [a c] Hin.
  destruct (proj1 (Forall_forall _ xys) Hz (a, c) Hin) as [_ Za].
  pose proof (proj1 (Forall_forall _ xys) Hent (a, c) Hin) as Hac. cbv beta iota in Hac.
  cbn [fst snd] in Za |- *.
  generalize (Rabs_pos (val a - val c)). intros A0.
  rewrite Rabs_pos_eq in Hac by lra. unfold b. lra. }
assert (M0 : 0 <= val (fst s)) by exact (mag_nonneg prec emax _ M Fm).
(* The radius: the chain of radius2_range, the constants of ball_add_1. *)
destruct (consts_ball_add_1 prec emax Hp2) as [[FE [EE _]] [[FG [EG _]] [FH [EH _]]]].
destruct (E_add_1_le prec emax Hp2) as [E0 E1].
destruct (G_3_le prec emax Hp2) as [Gl Gu].
destruct (H_add_le prec emax Hp2) as [H0 H1].
assert (HX' : 0 <= val rx + val ry <= bpow radix2 (emax - 2)) by lra.
assert (Y0 : 0 <= val (fst s) * Model.up_ball_add_1_0 (3 - emax - prec) prec)
  by (apply Rmult_le_pos; lra).
assert (Y1 : val (fst s) * Model.up_ball_add_1_0 (3 - emax - prec) prec <= b * / 4).
{ apply Rmult_le_compat; lra. }
assert (HS' : val rx + val ry + val (fst s) * Model.up_ball_add_1_0 (3 - emax - prec) prec
              < bpow radix2 (emax - 2) + bpow radix2 (emax - 2 - prec - 1)).
{ fold d. unfold b in Y1. lra. }
destruct (radius2_range prec emax Hp2 _ _ _ _ HX' Y0 HS' (conj Gl Gu) (conj H0 H1))
  as [Is [It Ir]].
assert (Frz : finite rz).
{ unfold rz, IeeeModel.bv_add_radius_1. cbv zeta.
  apply (radius2_add_fin prec emax nan_plus nan_fma); trivial.
  - unfold val in It. rewrite EE. exact It.
  - unfold val in Ir. rewrite EE, EG, EH. exact Ir. }
split. exact Eok. exact Frz.
Qed.

(* V4 for bv_scale_1, in the form it will take: a finite radius and scalar, |a| rx within the
   limit, and every entry within it, give a finite radius, for every length; from precision 2.
   The proof is that of ball_scale_1_finite (IeeeBallFinite.v) at the largest magnitude. *)
Lemma bv_scale_1_seq_ieee_v4 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (2 <= prec)%Z ->
  forall (rx a : binary_float prec emax) (xs : list (binary_float prec emax)),
  ((finite rx /\ 0 <= val rx /\ Forall (fun x => ball_finite_1 x rx) xs) \/
  (rx = infinity prec emax false /\ Forall (fun x => ball_whole_1 x rx) xs)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_scale_1_seq prec emax nan_abs nan_fma nan_const rx a xs in
  (finite rx -> finite a ->
   Rabs (val rx * val a) <= bpow radix2 (emax - 2) ->
   Forall (fun x =>
     Rabs (((Rabs (val x)) + val rx) * val a) <= bpow radix2 (emax - 2)) xs ->
   finite r_).
Proof.
intros prec emax Hp He nan_abs nan_fma nan_const Hp2 rx a xs HX.
unfold IeeeFoldModel.bv_scale_1_seq. cbv zeta.
change (IeeeFoldModel.bv_scale_1_record prec emax nan_abs)
  with (IeeeFoldModel.norm_upper_1_step prec emax nan_abs).
set (ws := map (IeeeFoldModel.bv_scale_1_step prec emax nan_fma a) xs).
set (s := fold_seq (IeeeFoldModel.norm_upper_1_step prec emax nan_abs)
            (IeeeOperations.pzero prec emax, true) ws).
set (rz := IeeeModel.bv_scale_radius_1 prec emax nan_abs nan_fma (fst s) rx a).
assert (Main : finite rx -> finite a -> Rabs (val rx * val a) <= bpow radix2 (emax - 2) ->
               Forall (fun x => Rabs (((Rabs (val x)) + val rx) * val a) <= bpow radix2 (emax - 2))
                      xs ->
               snd s = true /\ finite rz).
2: { generalize (norm_finish_1_correct prec emax Hp He nan_abs nan_const rz (snd s)).
     destruct (IeeeModel.norm_finish_1 prec emax nan_abs nan_const rz (snd s)) as [r flag].
     cbn [fst snd]. intros [K1 [K2 _]].
     destruct flag; cbv beta iota; intros Frx Fa Hr Hent.
     - rewrite (K2 eq_refl). exact (proj2 (Main Frx Fa Hr Hent)).
     - exfalso. destruct (Main Frx Fa Hr Hent) as [E F].
       assert (K : false = true) by (apply K1; split; assumption). discriminate K. }
intros Frx Fa Hr Hent.
assert (Bx : 0 <= val rx /\ Forall (fun x => ball_finite_1 x rx) xs).
{ destruct HX as [[_ [P B]]|[E _]]. split; assumption. rewrite E in Frx. discriminate Frx. }
destruct Bx as [Px Bx].
set (d := bpow radix2 (emax - 2 - prec - 1)).
assert (D0 : 0 < d) by apply bpow_gt_0.
assert (Hel : (3 - emax - prec + prec <= emax - 2)%Z).
{ generalize He. unfold BinarySingleNaN.Prec_lt_emax. lia. }
generalize (Rabs_pos (val a)). intros A0.
assert (X0 : 0 <= Rabs (val a) * val rx) by (apply Rmult_le_pos; lra).
assert (Hra : Rabs (val a) * val rx <= bpow radix2 (emax - 2)).
{ rewrite Rabs_mult, (Rabs_pos_eq (val rx)) in Hr by lra. lra. }
(* Every center written is finite and within d of the exact product, which is within the
   limit. *)
assert (Hz : Forall (fun x =>
          finite (IeeeFoldModel.bv_scale_1_step prec emax nan_fma a x) /\
          Rabs (val (IeeeFoldModel.bv_scale_1_step prec emax nan_fma a x)) <=
            Rabs (val x) * Rabs (val a) + d) xs).
{ apply Forall_forall. intros x Hin.
  destruct (proj1 (Forall_forall _ xs) Bx x Hin) as [Fx _].
  pose proof (proj1 (Forall_forall _ xs) Hent x Hin) as Hx. cbv beta in Hx.
  generalize (Rabs_pos (val x)). intros C0.
  rewrite Rabs_mult, (Rabs_pos_eq (Rabs (val x) + val rx)) in Hx by lra.
  assert (Ec : Rabs (val x * val a + 0) = Rabs (val x) * Rabs (val a))
    by now rewrite Rplus_0_r, Rabs_mult.
  assert (Lx : Rabs (val x * val a + 0) <= bpow radix2 (emax - 2)).
  { rewrite Ec. assert (0 <= val rx * Rabs (val a)) by (apply Rmult_le_pos; lra). lra. }
  assert (Ic : IeeeBridge.inrange emax (round radix2 (FLT_exp (3 - emax - prec) prec)
                                         (Znearest tie_even) (val x * val a + 0))).
  { apply (le_bpow_inrange emax) with (emax - 2)%Z. lia.
    apply (RN_abs_le_bpow (3 - emax - prec) prec). exact Lx. }
  destruct (prod_fin prec emax nan_fma x a Fx Fa Ic) as [Fz Ez].
  unfold IeeeFoldModel.bv_scale_1_step, IeeeModel.scale_step_1, IeeeModel.mul_1_1. cbv zeta.
  split. exact Fz.
  rewrite <- Ec. unfold val. rewrite Ez.
  exact (abs_rnd_le_half prec emax _ (emax - 2) Hel Lx). }
assert (Fws : Forall (fun w => finite w) ws).
{ unfold ws. apply Forall_map. revert Hz. apply Forall_impl. intros x [F _]. exact F. }
destruct (seq_1_good prec emax nan_abs ws Fws) as [M [Fm Eok]]. fold s in M, Fm, Eok.
destruct (seq_1_state prec emax nan_abs ws) as [_ HS]. fold s in HS.
destruct (HS Fm Eok) as [_ Vs].
rewrite norm_upper_1_seq_value in Vs.
assert (Vm : val (fst s) = fold_right Rmax 0 (map (fun x => Rabs x) (map (@val prec emax) ws))).
{ change (val (fst s)) with (fst (IeeeFoldNorm.vals prec emax s)). now rewrite Vs. }
(* The largest magnitude, against the limit. *)
set (b := 4 * (bpow radix2 (emax - 2) + d / 4 - Rabs (val a) * val rx)).
assert (Mb : val (fst s) <= b).
{ rewrite Vm. apply maxl_le. unfold b. lra.
  rewrite map_map. unfold ws. rewrite map_map. apply Forall_map.
  apply Forall_forall. intros x Hin.
  destruct (proj1 (Forall_forall _ xs) Hz x Hin) as [_ Zx].
  pose proof (proj1 (Forall_forall _ xs) Hent x Hin) as Hx. cbv beta in Hx |- *.
  generalize (Rabs_pos (val x)). intros C0.
  rewrite Rabs_mult, (Rabs_pos_eq (Rabs (val x) + val rx)) in Hx by lra.
  unfold b. lra. }
assert (M0 : 0 <= val (fst s)) by exact (mag_nonneg prec emax _ M Fm).
(* The radius: the chain of radius2_range, the constants of ball_scale_1. *)
destruct (consts_ball_scale_1 prec emax Hp2) as [[FE [EE _]] [[FG [EG _]] [FH [EH _]]]].
destruct (E_mul_1_le prec emax Hp2) as [E0 E1].
destruct (G_3_le prec emax Hp2) as [Gl Gu].
destruct (H_scale_1_le prec emax Hp2) as [H0 H1].
assert (HX' : 0 <= Rabs (val a) * val rx + 0 <= bpow radix2 (emax - 2)) by lra.
assert (Y0 : 0 <= val (fst s) * Model.up_ball_mul_1_0 (3 - emax - prec) prec)
  by (apply Rmult_le_pos; lra).
assert (Y1 : val (fst s) * Model.up_ball_mul_1_0 (3 - emax - prec) prec <= b * / 4).
{ apply Rmult_le_compat; lra. }
assert (HS' : Rabs (val a) * val rx + 0 + val (fst s) * Model.up_ball_mul_1_0 (3 - emax - prec) prec
              < bpow radix2 (emax - 2) + bpow radix2 (emax - 2 - prec - 1)).
{ fold d. unfold b in Y1. lra. }
destruct (radius2_range prec emax Hp2 _ _ _ _ HX' Y0 HS' (conj Gl Gu) (conj H0 H1))
  as [Is [It Ir]].
assert (Frz : finite rz).
{ unfold rz, IeeeModel.bv_scale_radius_1. cbv zeta.
  assert (Faa : finite (IeeeOperations.abs prec emax nan_abs a))
    by (unfold finite; now rewrite (abs_finite prec emax nan_abs)).
  apply (radius2_scale_fin prec emax nan_fma); trivial.
  - rewrite (abs_val prec emax nan_abs). exact Is.
  - rewrite (abs_val prec emax nan_abs). unfold val in It. rewrite EE. exact It.
  - rewrite (abs_val prec emax nan_abs). unfold val in Ir. rewrite EE, EG, EH. exact Ir. }
split. exact Eok. exact Frz.
Qed.

(* V4 for bv_add_2, in the form it will take; from precision 3, the precision of the
   statements of two limbs. The proof is that of ball_add_2_finite (IeeeBallFinite.v) at the
   largest magnitude of a leading limb: every center is finite with a leading limb at most 5/3
   of its exact sum (add_2_2_center), and E <= 1/2. *)
Lemma bv_add_2_seq_ieee_v4 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (3 <= prec)%Z ->
  forall (rx ry : binary_float prec emax)
         (xys : list ((binary_float prec emax * binary_float prec emax) *
                      (binary_float prec emax * binary_float prec emax))),
  ((finite rx /\ 0 <= val rx /\ Forall (fun xy => ball_finite_2 (fst (fst xy)) (snd (fst xy)) rx)
    xys) \/
  (rx = infinity prec emax false /\ Forall (fun xy => ball_whole_2 (fst (fst xy)) (snd (fst xy)) rx)
    xys)) ->
  ((finite ry /\ 0 <= val ry /\ Forall (fun xy => ball_finite_2 (fst (snd xy)) (snd (snd xy)) ry)
    xys) \/
  (ry = infinity prec emax false /\ Forall (fun xy => ball_whole_2 (fst (snd xy)) (snd (snd xy)) ry)
    xys)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_add_2_seq prec emax nan_plus nan_minus nan_abs nan_fma nan_const rx ry xys in
  (finite rx -> finite ry ->
   Rabs (val rx + val ry) <= bpow radix2 (emax - 2) ->
   Forall (fun xy =>
     let '((x0, x1), (y0, y1)) := xy in
     Rabs (((Rabs ((val x0 + val x1) + (val y0 + val y1))) + val rx) + val ry) <= bpow radix2
       (emax - 2)) xys ->
   finite r_).
Proof.
intros prec emax Hp He nan_plus nan_minus nan_abs nan_fma nan_const Hp3 rx ry xys HX HY.
assert (Hp2 : (2 <= prec)%Z) by lia.
unfold IeeeFoldModel.bv_add_2_seq. cbv zeta.
change (IeeeFoldModel.bv_add_2_record prec emax nan_abs)
  with (IeeeFoldModel.norm_upper_2_step prec emax nan_abs).
set (ws := map (IeeeFoldModel.bv_add_2_step prec emax nan_plus nan_minus) xys).
assert (E2 : fold_seq (IeeeFoldModel.norm_upper_2_step prec emax nan_abs)
               (IeeeOperations.pzero prec emax, true) ws =
             fold_seq (IeeeFoldModel.norm_upper_1_step prec emax nan_abs)
               (IeeeOperations.pzero prec emax, true) (map fst ws)).
{ rewrite <- (fold_seq_map _ _ _ (IeeeFoldModel.norm_upper_1_step prec emax nan_abs) fst
                (IeeeOperations.pzero prec emax, true) ws).
  apply fold_seq_ext. intros t x. apply step_2_eq. }
rewrite E2.
set (s := fold_seq (IeeeFoldModel.norm_upper_1_step prec emax nan_abs)
            (IeeeOperations.pzero prec emax, true) (map fst ws)).
set (rz := IeeeModel.bv_add_radius_2 prec emax nan_plus nan_fma (fst s) rx ry).
assert (Main : finite rx -> finite ry -> Rabs (val rx + val ry) <= bpow radix2 (emax - 2) ->
               Forall (fun xy => let '((x0, x1), (y0, y1)) := xy in
                         Rabs (((Rabs ((val x0 + val x1) + (val y0 + val y1))) + val rx) + val ry)
                           <= bpow radix2 (emax - 2)) xys ->
               snd s = true /\ finite rz).
2: { generalize (norm_finish_1_correct prec emax Hp He nan_abs nan_const rz (snd s)).
     destruct (IeeeModel.norm_finish_1 prec emax nan_abs nan_const rz (snd s)) as [r flag].
     cbn [fst snd]. intros [K1 [K2 _]].
     destruct flag; cbv beta iota; intros Frx Fry Hr Hent.
     - rewrite (K2 eq_refl). exact (proj2 (Main Frx Fry Hr Hent)).
     - exfalso. destruct (Main Frx Fry Hr Hent) as [E F].
       assert (K : false = true) by (apply K1; split; assumption). discriminate K. }
intros Frx Fry Hr Hent.
assert (Bx : 0 <= val rx /\
             Forall (fun xy => ball_finite_2 (fst (fst xy)) (snd (fst xy)) rx) xys).
{ destruct HX as [[_ [P B]]|[E _]]. split; assumption. rewrite E in Frx. discriminate Frx. }
assert (By : 0 <= val ry /\
             Forall (fun xy => ball_finite_2 (fst (snd xy)) (snd (snd xy)) ry) xys).
{ destruct HY as [[_ [P B]]|[E _]]. split; assumption. rewrite E in Fry. discriminate Fry. }
destruct Bx as [Px Bx]. destruct By as [Py By].
assert (Hrxy : val rx + val ry <= bpow radix2 (emax - 2)).
{ rewrite Rabs_pos_eq in Hr by lra. exact Hr. }
(* Every center written has a finite leading limb, at most 5/3 of what the limit leaves. *)
assert (Hz : Forall (fun xy =>
          finite (fst (IeeeFoldModel.bv_add_2_step prec emax nan_plus nan_minus xy)) /\
          3 * Rabs (val (fst (IeeeFoldModel.bv_add_2_step prec emax nan_plus nan_minus xy))) <=
            5 * (bpow radix2 (emax - 2) - (val rx + val ry))) xys).
{ apply Forall_forall. intros [[x0 x1] [y0 y1]] Hin.
  destruct (proj1 (Forall_forall _ xys) Bx _ Hin) as [F0 [F1 [Nx _]]].
  destruct (proj1 (Forall_forall _ xys) By _ Hin) as [G0 [G1 [Ny _]]].
  pose proof (proj1 (Forall_forall _ xys) Hent _ Hin) as Hab. cbv beta iota in Hab.
  cbn [fst snd] in F0, F1, Nx, G0, G1, Ny.
  generalize (Rabs_pos ((val x0 + val x1) + (val y0 + val y1))). intros T0.
  rewrite Rabs_pos_eq in Hab by lra.
  assert (Hs : Rabs ((val x0 + val x1) + (val y0 + val y1)) <= bpow radix2 (emax - 2)) by lra.
  destruct (add_2_2_center prec emax nan_plus nan_minus (fun _ => nan_const) nan_fma Hp3
              x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny Hs) as [Fz Lz].
  unfold IeeeFoldModel.bv_add_2_step. cbn [fst snd].
  split. exact Fz. lra. }
assert (Fws : Forall (fun w => finite w) (map fst ws)).
{ unfold ws. rewrite map_map. apply Forall_map. revert Hz. apply Forall_impl.
  intros xy [F _]. exact F. }
destruct (seq_1_good prec emax nan_abs (map fst ws) Fws) as [M [Fm Eok]]. fold s in M, Fm, Eok.
destruct (seq_1_state prec emax nan_abs (map fst ws)) as [_ HS]. fold s in HS.
destruct (HS Fm Eok) as [_ Vs].
rewrite norm_upper_1_seq_value in Vs.
assert (Vm : val (fst s) =
             fold_right Rmax 0 (map (fun x => Rabs x) (map (@val prec emax) (map fst ws)))).
{ change (val (fst s)) with (fst (IeeeFoldNorm.vals prec emax s)). now rewrite Vs. }
(* The largest magnitude, against the limit. *)
set (b := 5 / 3 * (bpow radix2 (emax - 2) - (val rx + val ry))).
assert (Mb : val (fst s) <= b).
{ rewrite Vm. apply maxl_le. unfold b. lra.
  rewrite !map_map. unfold ws. rewrite map_map. apply Forall_map.
  apply Forall_forall. intros xy Hin.
  destruct (proj1 (Forall_forall _ xys) Hz xy Hin) as [_ Z]. cbv beta.
  unfold b. lra. }
assert (M0 : 0 <= val (fst s)) by exact (mag_nonneg prec emax _ M Fm).
(* The radius: the chain of radius2_range, the constants of ball_add_2. *)
destruct (consts_ball_add_2 prec emax Hp3) as [[FE [EE _]] [[FG [EG _]] [FH [EH _]]]].
destruct (E_add_2_le prec emax Hp3) as [E0 E1].
destruct (G_3_le prec emax Hp2) as [Gl Gu].
destruct (H_add_le prec emax Hp2) as [H0 H1].
assert (HX' : 0 <= val rx + val ry <= bpow radix2 (emax - 2)) by lra.
assert (Y0 : 0 <= val (fst s) * Model.up_ball_add_2_0 (3 - emax - prec) prec)
  by (apply Rmult_le_pos; lra).
assert (Y1 : val (fst s) * Model.up_ball_add_2_0 (3 - emax - prec) prec <= b * / 2).
{ apply Rmult_le_compat; lra. }
assert (D0 : 0 < bpow radix2 (emax - 2 - prec - 1)) by apply bpow_gt_0.
assert (HS' : val rx + val ry + val (fst s) * Model.up_ball_add_2_0 (3 - emax - prec) prec
              < bpow radix2 (emax - 2) + bpow radix2 (emax - 2 - prec - 1)).
{ unfold b in Y1. lra. }
destruct (radius2_range prec emax Hp2 _ _ _ _ HX' Y0 HS' (conj Gl Gu) (conj H0 H1))
  as [Is [It Ir]].
assert (Frz : finite rz).
{ unfold rz, IeeeModel.bv_add_radius_2. cbv zeta.
  apply (radius2_add_fin prec emax nan_plus nan_fma); trivial.
  - unfold val in It. rewrite EE. exact It.
  - unfold val in Ir. rewrite EE, EG, EH. exact Ir. }
split. exact Eok. exact Frz.
Qed.

(* V4 for bv_sub_2: that of bv_add_2, with sub_2_2 (sub_2_2_center). *)
Lemma bv_sub_2_seq_ieee_v4 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_opp nan_abs : nan1 prec emax)
           (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (3 <= prec)%Z ->
  forall (rx ry : binary_float prec emax)
         (xys : list ((binary_float prec emax * binary_float prec emax) *
                      (binary_float prec emax * binary_float prec emax))),
  ((finite rx /\ 0 <= val rx /\ Forall (fun xy => ball_finite_2 (fst (fst xy)) (snd (fst xy)) rx)
    xys) \/
  (rx = infinity prec emax false /\ Forall (fun xy => ball_whole_2 (fst (fst xy)) (snd (fst xy)) rx)
    xys)) ->
  ((finite ry /\ 0 <= val ry /\ Forall (fun xy => ball_finite_2 (fst (snd xy)) (snd (snd xy)) ry)
    xys) \/
  (ry = infinity prec emax false /\ Forall (fun xy => ball_whole_2 (fst (snd xy)) (snd (snd xy)) ry)
    xys)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_sub_2_seq prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const rx ry
      xys in
  (finite rx -> finite ry ->
   Rabs (val rx + val ry) <= bpow radix2 (emax - 2) ->
   Forall (fun xy =>
     let '((x0, x1), (y0, y1)) := xy in
     Rabs (((Rabs ((val x0 + val x1) - (val y0 + val y1))) + val rx) + val ry) <= bpow radix2
       (emax - 2)) xys ->
   finite r_).
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const Hp3 rx ry xys HX HY.
assert (Hp2 : (2 <= prec)%Z) by lia.
unfold IeeeFoldModel.bv_sub_2_seq. cbv zeta.
change (IeeeFoldModel.bv_sub_2_record prec emax nan_abs)
  with (IeeeFoldModel.norm_upper_2_step prec emax nan_abs).
set (ws := map (IeeeFoldModel.bv_sub_2_step prec emax nan_plus nan_minus nan_opp) xys).
assert (E2 : fold_seq (IeeeFoldModel.norm_upper_2_step prec emax nan_abs)
               (IeeeOperations.pzero prec emax, true) ws =
             fold_seq (IeeeFoldModel.norm_upper_1_step prec emax nan_abs)
               (IeeeOperations.pzero prec emax, true) (map fst ws)).
{ rewrite <- (fold_seq_map _ _ _ (IeeeFoldModel.norm_upper_1_step prec emax nan_abs) fst
                (IeeeOperations.pzero prec emax, true) ws).
  apply fold_seq_ext. intros t x. apply step_2_eq. }
rewrite E2.
set (s := fold_seq (IeeeFoldModel.norm_upper_1_step prec emax nan_abs)
            (IeeeOperations.pzero prec emax, true) (map fst ws)).
set (rz := IeeeModel.bv_add_radius_2 prec emax nan_plus nan_fma (fst s) rx ry).
assert (Main : finite rx -> finite ry -> Rabs (val rx + val ry) <= bpow radix2 (emax - 2) ->
               Forall (fun xy => let '((x0, x1), (y0, y1)) := xy in
                         Rabs (((Rabs ((val x0 + val x1) - (val y0 + val y1))) + val rx) + val ry)
                           <= bpow radix2 (emax - 2)) xys ->
               snd s = true /\ finite rz).
2: { generalize (norm_finish_1_correct prec emax Hp He nan_abs nan_const rz (snd s)).
     destruct (IeeeModel.norm_finish_1 prec emax nan_abs nan_const rz (snd s)) as [r flag].
     cbn [fst snd]. intros [K1 [K2 _]].
     destruct flag; cbv beta iota; intros Frx Fry Hr Hent.
     - rewrite (K2 eq_refl). exact (proj2 (Main Frx Fry Hr Hent)).
     - exfalso. destruct (Main Frx Fry Hr Hent) as [E F].
       assert (K : false = true) by (apply K1; split; assumption). discriminate K. }
intros Frx Fry Hr Hent.
assert (Bx : 0 <= val rx /\
             Forall (fun xy => ball_finite_2 (fst (fst xy)) (snd (fst xy)) rx) xys).
{ destruct HX as [[_ [P B]]|[E _]]. split; assumption. rewrite E in Frx. discriminate Frx. }
assert (By : 0 <= val ry /\
             Forall (fun xy => ball_finite_2 (fst (snd xy)) (snd (snd xy)) ry) xys).
{ destruct HY as [[_ [P B]]|[E _]]. split; assumption. rewrite E in Fry. discriminate Fry. }
destruct Bx as [Px Bx]. destruct By as [Py By].
assert (Hrxy : val rx + val ry <= bpow radix2 (emax - 2)).
{ rewrite Rabs_pos_eq in Hr by lra. exact Hr. }
(* Every center written has a finite leading limb, at most 5/3 of what the limit leaves. *)
assert (Hz : Forall (fun xy =>
          finite (fst (IeeeFoldModel.bv_sub_2_step prec emax nan_plus nan_minus nan_opp xy)) /\
          3 * Rabs (val (fst (IeeeFoldModel.bv_sub_2_step prec emax nan_plus nan_minus nan_opp xy)))
            <=
            5 * (bpow radix2 (emax - 2) - (val rx + val ry))) xys).
{ apply Forall_forall. intros [[x0 x1] [y0 y1]] Hin.
  destruct (proj1 (Forall_forall _ xys) Bx _ Hin) as [F0 [F1 [Nx _]]].
  destruct (proj1 (Forall_forall _ xys) By _ Hin) as [G0 [G1 [Ny _]]].
  pose proof (proj1 (Forall_forall _ xys) Hent _ Hin) as Hab. cbv beta iota in Hab.
  cbn [fst snd] in F0, F1, Nx, G0, G1, Ny.
  generalize (Rabs_pos ((val x0 + val x1) - (val y0 + val y1))). intros T0.
  rewrite Rabs_pos_eq in Hab by lra.
  assert (Hs : Rabs ((val x0 + val x1) - (val y0 + val y1)) <= bpow radix2 (emax - 2)) by lra.
  destruct (sub_2_2_center prec emax nan_plus nan_minus nan_opp nan_fma Hp3
              x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny Hs) as [Fz Lz].
  unfold IeeeFoldModel.bv_sub_2_step. cbn [fst snd].
  split. exact Fz. lra. }
assert (Fws : Forall (fun w => finite w) (map fst ws)).
{ unfold ws. rewrite map_map. apply Forall_map. revert Hz. apply Forall_impl.
  intros xy [F _]. exact F. }
destruct (seq_1_good prec emax nan_abs (map fst ws) Fws) as [M [Fm Eok]]. fold s in M, Fm, Eok.
destruct (seq_1_state prec emax nan_abs (map fst ws)) as [_ HS]. fold s in HS.
destruct (HS Fm Eok) as [_ Vs].
rewrite norm_upper_1_seq_value in Vs.
assert (Vm : val (fst s) =
             fold_right Rmax 0 (map (fun x => Rabs x) (map (@val prec emax) (map fst ws)))).
{ change (val (fst s)) with (fst (IeeeFoldNorm.vals prec emax s)). now rewrite Vs. }
(* The largest magnitude, against the limit. *)
set (b := 5 / 3 * (bpow radix2 (emax - 2) - (val rx + val ry))).
assert (Mb : val (fst s) <= b).
{ rewrite Vm. apply maxl_le. unfold b. lra.
  rewrite !map_map. unfold ws. rewrite map_map. apply Forall_map.
  apply Forall_forall. intros xy Hin.
  destruct (proj1 (Forall_forall _ xys) Hz xy Hin) as [_ Z]. cbv beta.
  unfold b. lra. }
assert (M0 : 0 <= val (fst s)) by exact (mag_nonneg prec emax _ M Fm).
(* The radius: the chain of radius2_range, the constants of ball_add_2. *)
destruct (consts_ball_add_2 prec emax Hp3) as [[FE [EE _]] [[FG [EG _]] [FH [EH _]]]].
destruct (E_add_2_le prec emax Hp3) as [E0 E1].
destruct (G_3_le prec emax Hp2) as [Gl Gu].
destruct (H_add_le prec emax Hp2) as [H0 H1].
assert (HX' : 0 <= val rx + val ry <= bpow radix2 (emax - 2)) by lra.
assert (Y0 : 0 <= val (fst s) * Model.up_ball_add_2_0 (3 - emax - prec) prec)
  by (apply Rmult_le_pos; lra).
assert (Y1 : val (fst s) * Model.up_ball_add_2_0 (3 - emax - prec) prec <= b * / 2).
{ apply Rmult_le_compat; lra. }
assert (D0 : 0 < bpow radix2 (emax - 2 - prec - 1)) by apply bpow_gt_0.
assert (HS' : val rx + val ry + val (fst s) * Model.up_ball_add_2_0 (3 - emax - prec) prec
              < bpow radix2 (emax - 2) + bpow radix2 (emax - 2 - prec - 1)).
{ unfold b in Y1. lra. }
destruct (radius2_range prec emax Hp2 _ _ _ _ HX' Y0 HS' (conj Gl Gu) (conj H0 H1))
  as [Is [It Ir]].
assert (Frz : finite rz).
{ unfold rz, IeeeModel.bv_add_radius_2. cbv zeta.
  apply (radius2_add_fin prec emax nan_plus nan_fma); trivial.
  - unfold val in It. rewrite EE. exact It.
  - unfold val in Ir. rewrite EE, EG, EH. exact Ir. }
split. exact Eok. exact Frz.
Qed.

(* V4 for bv_scale_2, in the form it will take; from precision 2. The proof is that of
   ball_scale_2_finite (IeeeBallFinite.v) at the largest magnitude of a leading limb. *)
Lemma bv_scale_2_seq_ieee_v4 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_opp nan_abs : nan1 prec emax)
         (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (2 <= prec)%Z ->
  forall (rx a : binary_float prec emax)
    (xs : list (binary_float prec emax * binary_float prec emax)),
  ((finite rx /\ 0 <= val rx /\ Forall (fun x => ball_finite_2 (fst x) (snd x) rx) xs) \/
  (rx = infinity prec emax false /\ Forall (fun x => ball_whole_2 (fst x) (snd x) rx) xs)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_scale_2_seq prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const rx a
      xs in
  (finite rx -> finite a ->
   Rabs (val rx * val a) <= bpow radix2 (emax - 2) ->
   Forall (fun x =>
     let '(x0, x1) := x in
     Rabs (((Rabs (val x0 + val x1)) + val rx) * val a) <= bpow radix2 (emax - 2)) xs ->
   finite r_).
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const Hp2 rx a xs HX.
unfold IeeeFoldModel.bv_scale_2_seq. cbv zeta.
change (IeeeFoldModel.bv_scale_2_record prec emax nan_abs)
  with (IeeeFoldModel.norm_upper_2_step prec emax nan_abs).
set (ws := map (IeeeFoldModel.bv_scale_2_step prec emax nan_plus nan_minus nan_opp nan_fma a) xs).
assert (E2 : fold_seq (IeeeFoldModel.norm_upper_2_step prec emax nan_abs)
               (IeeeOperations.pzero prec emax, true) ws =
             fold_seq (IeeeFoldModel.norm_upper_1_step prec emax nan_abs)
               (IeeeOperations.pzero prec emax, true) (map fst ws)).
{ rewrite <- (fold_seq_map _ _ _ (IeeeFoldModel.norm_upper_1_step prec emax nan_abs) fst
                (IeeeOperations.pzero prec emax, true) ws).
  apply fold_seq_ext. intros t x. apply step_2_eq. }
rewrite E2.
set (s := fold_seq (IeeeFoldModel.norm_upper_1_step prec emax nan_abs)
            (IeeeOperations.pzero prec emax, true) (map fst ws)).
set (rz := IeeeModel.bv_scale_radius_2 prec emax nan_abs nan_fma (fst s) rx a).
assert (Main : finite rx -> finite a -> Rabs (val rx * val a) <= bpow radix2 (emax - 2) ->
               Forall (fun x => let '(x0, x1) := x in
                         Rabs (((Rabs (val x0 + val x1)) + val rx) * val a) <= bpow radix2
                           (emax - 2))
                      xs ->
               snd s = true /\ finite rz).
2: { generalize (norm_finish_1_correct prec emax Hp He nan_abs nan_const rz (snd s)).
     destruct (IeeeModel.norm_finish_1 prec emax nan_abs nan_const rz (snd s)) as [r flag].
     cbn [fst snd]. intros [K1 [K2 _]].
     destruct flag; cbv beta iota; intros Frx Fa Hr Hent.
     - rewrite (K2 eq_refl). exact (proj2 (Main Frx Fa Hr Hent)).
     - exfalso. destruct (Main Frx Fa Hr Hent) as [E F].
       assert (K : false = true) by (apply K1; split; assumption). discriminate K. }
intros Frx Fa Hr Hent.
assert (Bx : 0 <= val rx /\ Forall (fun x => ball_finite_2 (fst x) (snd x) rx) xs).
{ destruct HX as [[_ [P B]]|[E _]]. split; assumption. rewrite E in Frx. discriminate Frx. }
destruct Bx as [Px Bx].
generalize (Rabs_pos (val a)) (bpow_gt_0 radix2 (3 - emax - prec)). intros A0 Eta0.
assert (X0 : 0 <= Rabs (val a) * val rx) by (apply Rmult_le_pos; lra).
assert (Hra : Rabs (val a) * val rx <= bpow radix2 (emax - 2)).
{ rewrite Rabs_mult, (Rabs_pos_eq (val rx)) in Hr by lra. lra. }
assert (EtaD : bpow radix2 (3 - emax - prec) <= bpow radix2 (emax - 2 - prec - 1)).
{ apply bpow_le. generalize He. unfold BinarySingleNaN.Prec_lt_emax. lia. }
(* Every center written has a finite leading limb, at most 5/3 of what the limit leaves, and
   4/3 eta. *)
assert (Hz : Forall (fun x =>
          finite (fst
            (IeeeFoldModel.bv_scale_2_step prec emax nan_plus nan_minus nan_opp nan_fma a x)) /\
          3 * Rabs (val (fst (IeeeFoldModel.bv_scale_2_step prec emax nan_plus nan_minus nan_opp
                                nan_fma a x))) <=
            5 * (bpow radix2 (emax - 2) - Rabs (val a) * val rx) + 4 * bpow radix2
              (3 - emax - prec))
         xs).
{ apply Forall_forall. intros [x0 x1] Hin.
  destruct (proj1 (Forall_forall _ xs) Bx _ Hin) as [F0 [F1 [Nx _]]].
  pose proof (proj1 (Forall_forall _ xs) Hent _ Hin) as Hx. cbv beta iota in Hx.
  cbn [fst snd] in F0, F1, Nx.
  generalize (Rabs_pos (val x0 + val x1)). intros C0.
  rewrite Rabs_mult, (Rabs_pos_eq (Rabs (val x0 + val x1) + val rx)) in Hx by lra.
  assert (Hc : Rabs (val x0 + val x1) * Rabs (val a) <= bpow radix2 (emax - 2)) by lra.
  destruct (scale_step_2_center prec emax nan_plus nan_minus nan_opp nan_fma Hp2 x0 x1 a
              F0 F1 Fa Nx Hc) as [Fz Lz].
  unfold eta in Lz.
  unfold IeeeFoldModel.bv_scale_2_step. cbn [fst snd].
  split. exact Fz. lra. }
assert (Fws : Forall (fun w => finite w) (map fst ws)).
{ unfold ws. rewrite map_map. apply Forall_map. revert Hz. apply Forall_impl.
  intros x [F _]. exact F. }
destruct (seq_1_good prec emax nan_abs (map fst ws) Fws) as [M [Fm Eok]]. fold s in M, Fm, Eok.
destruct (seq_1_state prec emax nan_abs (map fst ws)) as [_ HS]. fold s in HS.
destruct (HS Fm Eok) as [_ Vs].
rewrite norm_upper_1_seq_value in Vs.
assert (Vm : val (fst s) =
             fold_right Rmax 0 (map (fun x => Rabs x) (map (@val prec emax) (map fst ws)))).
{ change (val (fst s)) with (fst (IeeeFoldNorm.vals prec emax s)). now rewrite Vs. }
(* The largest magnitude, against the limit. *)
set (b := (5 * (bpow radix2 (emax - 2) - Rabs (val a) * val rx) +
           4 * bpow radix2 (3 - emax - prec)) / 3).
assert (Mb : val (fst s) <= b).
{ rewrite Vm. apply maxl_le. unfold b. lra.
  rewrite !map_map. unfold ws. rewrite map_map. apply Forall_map.
  apply Forall_forall. intros x Hin.
  destruct (proj1 (Forall_forall _ xs) Hz x Hin) as [_ Z]. cbv beta.
  unfold b. lra. }
assert (M0 : 0 <= val (fst s)) by exact (mag_nonneg prec emax _ M Fm).
(* The radius: the chain of radius2_range, the constants of ball_scale_2. *)
destruct (consts_ball_scale_2 prec emax Hp2) as [[FE [EE _]] [[FG [EG _]] [FH [EH _]]]].
destruct (E_scale_2_le prec emax Hp2) as [E0 E1].
destruct (G_3_le prec emax Hp2) as [Gl Gu].
destruct (H_scale_2_le prec emax Hp2) as [H0 H1].
assert (HX' : 0 <= Rabs (val a) * val rx + 0 <= bpow radix2 (emax - 2)) by lra.
assert (Y0 : 0 <= val (fst s) * Model.up_ball_scale_2_0 (3 - emax - prec) prec)
  by (apply Rmult_le_pos; lra).
assert (Y1 : val (fst s) * Model.up_ball_scale_2_0 (3 - emax - prec) prec <= b * / 2).
{ apply Rmult_le_compat; lra. }
assert (HS' : Rabs (val a) * val rx + 0 +
              val (fst s) * Model.up_ball_scale_2_0 (3 - emax - prec) prec
              < bpow radix2 (emax - 2) + bpow radix2 (emax - 2 - prec - 1)).
{ unfold b in Y1. lra. }
destruct (radius2_range prec emax Hp2 _ _ _ _ HX' Y0 HS' (conj Gl Gu) (conj H0 H1))
  as [Is [It Ir]].
assert (Frz : finite rz).
{ unfold rz, IeeeModel.bv_scale_radius_2. cbv zeta.
  assert (Faa : finite (IeeeOperations.abs prec emax nan_abs a))
    by (unfold finite; now rewrite (abs_finite prec emax nan_abs)).
  apply (radius2_scale_fin prec emax nan_fma); trivial.
  - rewrite (abs_val prec emax nan_abs). exact Is.
  - rewrite (abs_val prec emax nan_abs). unfold val in It. rewrite EE. exact It.
  - rewrite (abs_val prec emax nan_abs). unfold val in Ir. rewrite EE, EG, EH. exact Ir. }
split. exact Eok. exact Frz.
Qed.

(* The lane order returns what the sequential order returns (F_lanes_seq_ieee). *)

Lemma bv_add_1_lanes_ieee_v4 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus : nan2 prec emax) (nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (2 <= prec)%Z ->
  forall (W : nat) (rx ry : binary_float prec emax)
    (xys : list (binary_float prec emax * binary_float prec emax)),
  ((finite rx /\ 0 <= val rx /\ Forall (fun xy => ball_finite_1 (fst xy) rx) xys) \/
  (rx = infinity prec emax false /\ Forall (fun xy => ball_whole_1 (fst xy) rx) xys)) ->
  ((finite ry /\ 0 <= val ry /\ Forall (fun xy => ball_finite_1 (snd xy) ry) xys) \/
  (ry = infinity prec emax false /\ Forall (fun xy => ball_whole_1 (snd xy) ry) xys)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_add_1_lanes prec emax nan_plus nan_abs nan_fma nan_const W rx ry xys in
  (finite rx -> finite ry ->
   Rabs (val rx + val ry) <= bpow radix2 (emax - 2) ->
   Forall (fun xy =>
     let '(x, y) := xy in
     Rabs (((Rabs (val x + val y)) + val rx) + val ry) <= bpow radix2 (emax - 2)) xys ->
   finite r_).
Proof.
intros prec emax Hp He nan_plus nan_abs nan_fma nan_const Hp2 W rx ry xys HX HY.
rewrite bv_add_1_lanes_seq_ieee.
exact (bv_add_1_seq_ieee_v4 prec emax Hp He nan_plus nan_abs nan_fma nan_const Hp2 rx ry xys HX HY).
Qed.

Lemma bv_sub_1_lanes_ieee_v4 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (2 <= prec)%Z ->
  forall (W : nat) (rx ry : binary_float prec emax)
    (xys : list (binary_float prec emax * binary_float prec emax)),
  ((finite rx /\ 0 <= val rx /\ Forall (fun xy => ball_finite_1 (fst xy) rx) xys) \/
  (rx = infinity prec emax false /\ Forall (fun xy => ball_whole_1 (fst xy) rx) xys)) ->
  ((finite ry /\ 0 <= val ry /\ Forall (fun xy => ball_finite_1 (snd xy) ry) xys) \/
  (ry = infinity prec emax false /\ Forall (fun xy => ball_whole_1 (snd xy) ry) xys)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_sub_1_lanes prec emax nan_plus nan_minus nan_abs nan_fma nan_const W rx ry xys
      in
  (finite rx -> finite ry ->
   Rabs (val rx + val ry) <= bpow radix2 (emax - 2) ->
   Forall (fun xy =>
     let '(x, y) := xy in
     Rabs (((Rabs (val x - val y)) + val rx) + val ry) <= bpow radix2 (emax - 2)) xys ->
   finite r_).
Proof.
intros prec emax Hp He nan_plus nan_minus nan_abs nan_fma nan_const Hp2 W rx ry xys HX HY.
rewrite bv_sub_1_lanes_seq_ieee.
exact (bv_sub_1_seq_ieee_v4 prec emax Hp He nan_plus nan_minus nan_abs nan_fma nan_const Hp2 rx ry
    xys HX HY).
Qed.

Lemma bv_scale_1_lanes_ieee_v4 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (2 <= prec)%Z ->
  forall (W : nat) (rx a : binary_float prec emax) (xs : list (binary_float prec emax)),
  ((finite rx /\ 0 <= val rx /\ Forall (fun x => ball_finite_1 x rx) xs) \/
  (rx = infinity prec emax false /\ Forall (fun x => ball_whole_1 x rx) xs)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_scale_1_lanes prec emax nan_abs nan_fma nan_const W rx a xs in
  (finite rx -> finite a ->
   Rabs (val rx * val a) <= bpow radix2 (emax - 2) ->
   Forall (fun x =>
     Rabs (((Rabs (val x)) + val rx) * val a) <= bpow radix2 (emax - 2)) xs ->
   finite r_).
Proof.
intros prec emax Hp He nan_abs nan_fma nan_const Hp2 W rx a xs HX.
rewrite bv_scale_1_lanes_seq_ieee.
exact (bv_scale_1_seq_ieee_v4 prec emax Hp He nan_abs nan_fma nan_const Hp2 rx a xs HX).
Qed.

Lemma bv_add_2_lanes_ieee_v4 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (3 <= prec)%Z ->
  forall (W : nat) (rx ry : binary_float prec emax)
         (xys : list ((binary_float prec emax * binary_float prec emax) *
                      (binary_float prec emax * binary_float prec emax))),
  ((finite rx /\ 0 <= val rx /\ Forall (fun xy => ball_finite_2 (fst (fst xy)) (snd (fst xy)) rx)
    xys) \/
  (rx = infinity prec emax false /\ Forall (fun xy => ball_whole_2 (fst (fst xy)) (snd (fst xy)) rx)
    xys)) ->
  ((finite ry /\ 0 <= val ry /\ Forall (fun xy => ball_finite_2 (fst (snd xy)) (snd (snd xy)) ry)
    xys) \/
  (ry = infinity prec emax false /\ Forall (fun xy => ball_whole_2 (fst (snd xy)) (snd (snd xy)) ry)
    xys)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_add_2_lanes prec emax nan_plus nan_minus nan_abs nan_fma nan_const W rx ry xys
      in
  (finite rx -> finite ry ->
   Rabs (val rx + val ry) <= bpow radix2 (emax - 2) ->
   Forall (fun xy =>
     let '((x0, x1), (y0, y1)) := xy in
     Rabs (((Rabs ((val x0 + val x1) + (val y0 + val y1))) + val rx) + val ry) <= bpow radix2
       (emax - 2)) xys ->
   finite r_).
Proof.
intros prec emax Hp He nan_plus nan_minus nan_abs nan_fma nan_const Hp3 W rx ry xys HX HY.
rewrite bv_add_2_lanes_seq_ieee.
exact (bv_add_2_seq_ieee_v4 prec emax Hp He nan_plus nan_minus nan_abs nan_fma nan_const Hp3 rx ry
    xys HX HY).
Qed.

Lemma bv_sub_2_lanes_ieee_v4 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_opp nan_abs : nan1 prec emax)
           (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (3 <= prec)%Z ->
  forall (W : nat) (rx ry : binary_float prec emax)
         (xys : list ((binary_float prec emax * binary_float prec emax) *
                      (binary_float prec emax * binary_float prec emax))),
  ((finite rx /\ 0 <= val rx /\ Forall (fun xy => ball_finite_2 (fst (fst xy)) (snd (fst xy)) rx)
    xys) \/
  (rx = infinity prec emax false /\ Forall (fun xy => ball_whole_2 (fst (fst xy)) (snd (fst xy)) rx)
    xys)) ->
  ((finite ry /\ 0 <= val ry /\ Forall (fun xy => ball_finite_2 (fst (snd xy)) (snd (snd xy)) ry)
    xys) \/
  (ry = infinity prec emax false /\ Forall (fun xy => ball_whole_2 (fst (snd xy)) (snd (snd xy)) ry)
    xys)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_sub_2_lanes prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const W rx
      ry xys in
  (finite rx -> finite ry ->
   Rabs (val rx + val ry) <= bpow radix2 (emax - 2) ->
   Forall (fun xy =>
     let '((x0, x1), (y0, y1)) := xy in
     Rabs (((Rabs ((val x0 + val x1) - (val y0 + val y1))) + val rx) + val ry) <= bpow radix2
       (emax - 2)) xys ->
   finite r_).
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const Hp3 W rx ry xys HX HY.
rewrite bv_sub_2_lanes_seq_ieee.
exact (bv_sub_2_seq_ieee_v4 prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const Hp3
    rx ry xys HX HY).
Qed.

Lemma bv_scale_2_lanes_ieee_v4 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_opp nan_abs : nan1 prec emax)
         (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (2 <= prec)%Z ->
  forall (W : nat) (rx a : binary_float prec emax)
    (xs : list (binary_float prec emax * binary_float prec emax)),
  ((finite rx /\ 0 <= val rx /\ Forall (fun x => ball_finite_2 (fst x) (snd x) rx) xs) \/
  (rx = infinity prec emax false /\ Forall (fun x => ball_whole_2 (fst x) (snd x) rx) xs)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_scale_2_lanes prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const W
      rx a xs in
  (finite rx -> finite a ->
   Rabs (val rx * val a) <= bpow radix2 (emax - 2) ->
   Forall (fun x =>
     let '(x0, x1) := x in
     Rabs (((Rabs (val x0 + val x1)) + val rx) * val a) <= bpow radix2 (emax - 2)) xs ->
   finite r_).
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const Hp2 W rx a xs HX.
rewrite bv_scale_2_lanes_seq_ieee.
exact (bv_scale_2_seq_ieee_v4 prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const
    Hp2 rx a xs HX).
Qed.
