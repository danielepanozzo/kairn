(* The Ball kernels of the second radius design in the IEEE model: the finite cores, and
   B1 to B3 of milestone1.md ("Ball kernels") for the full kernels, with containment in
   every case.

   The cores (proofs/gen/IeeeModel.v, from proofs/gen/Model.v) compute a center, by the
   kernel of the same name or by one operation of T, and a radius by additions, opaque
   products, fused operations and absolute values. For operands whose centers are finite (and
   normalized) and whose radii are nonnegative, +infinity or NaN (K_core):

   - every value of the radius computation is nonnegative, +infinity or NaN: an
     absolute value is, the constants are, and add, prod and fma keep the property
     (IeeeOps.v). So the radius is never -infinity;
   - a finite radius means that every value it was computed from is finite: each of
     these operations returns a value that is not finite when an operand is not. In
     particular the radii of the operands and the leading limb of the center, whose
     absolute value enters the radius, are finite;
   - the center is then that of the real model, by the bridge of its kernel, and so is
     the radius, operation by operation.

   So a finite center and a finite radius are those of the real model, whose theorem
   (Ball2.v) gives containment. With the fix-up (IeeeBall.v) this gives B1 to B3. The
   corners: an operand that is the whole line has radius +infinity, which reaches the
   radius of the result as +infinity or, through 0 times infinity, as a NaN; in both
   cases the test lt (rz, inf) fails and the result is the whole line. It is the empty
   set only when an operand is.

   The constants E, G, H of each kernel are finite numbers of the IEEE format from
   precision 2 on (E <= 1, G <= 4, H <= 16 eta), whence the minimum precision 2 of the
   statements for a center of one limb, where the real model has 1.

   The statements, in the form of proofs/gen/IeeeStatements.v, are at the end of the file. *)
From Stdlib Require Import Reals ZArith List Arith Bool Lia Lra Psatz.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements IeeeStatements.
From Kairn Require Import Format Normalized Sign Program IeeeBridge IeeeEFT
  IeeeAdd22 IeeeMul22 IeeeMore IeeeVocabulary IeeeOps IeeeBall.
From Kairn Require Ball2 IeeeOperations.
From Kairn.Gen Require IeeeModel.
Import ListNotations.
Open Scope R_scope.

(** * Bounds of the expressions the constants round *)

Lemma rel_1_quarter : forall prec : Z, (2 <= prec)%Z -> 0 <= 1 / (1 + u prec) * u prec ^ 1 <= / 4.
Proof.
intros prec Hp. assert (Ht : 0 < u prec <= / 4) by exact (Ball2.u_bounds prec 2 Hp).
destruct Ht as [T0 T1]. set (t := u prec) in *.
replace (1 / (1 + t) * t ^ 1) with (t / (1 + t)) by (field; lra).
assert (I : 0 < / (1 + t)) by (apply Rinv_0_lt_compat; lra).
split.
- unfold Rdiv. apply Rmult_le_pos; lra.
- apply Rmult_le_reg_r with (1 + t). lra.
  unfold Rdiv. rewrite Rmult_assoc, Rinv_l by lra. lra.
Qed.

Lemma rel_add_2_quarter :
  forall prec : Z, (3 <= prec)%Z -> 0 <= 3 / (1 - 4 * u prec) * u prec ^ 2 <= / 4.
Proof.
intros prec Hp. assert (Ht : 0 < u prec <= / 8) by exact (Ball2.u_bounds prec 3 Hp).
destruct Ht as [T0 T8]. set (t := u prec) in *.
replace (3 / (1 - 4 * t) * t ^ 2) with (3 * (t * t) / (1 - 4 * t)) by (field; lra).
assert (I : 0 < / (1 - 4 * t)) by (apply Rinv_0_lt_compat; lra).
assert (Hq : 0 <= t * t) by (apply Rmult_le_pos; lra).
assert (Hq2 : t * t <= / 8 * / 8) by (apply Rmult_le_compat; lra).
split.
- unfold Rdiv. apply Rmult_le_pos; lra.
- apply Rmult_le_reg_r with (1 - 4 * t). lra.
  unfold Rdiv. rewrite Rmult_assoc, Rinv_l by lra. lra.
Qed.

Lemma rel_square_quarter :
  forall (c : R) (prec : Z), (2 <= prec)%Z -> 0 <= c <= 4 -> 0 <= c * u prec ^ 2 <= / 4.
Proof.
intros c prec Hp [C0 C4]. assert (Ht : 0 < u prec <= / 4) by exact (Ball2.u_bounds prec 2 Hp).
destruct Ht as [T0 T1]. set (t := u prec) in *.
replace (t ^ 2) with (t * t) by ring.
assert (Hq : 0 <= t * t) by (apply Rmult_le_pos; lra).
assert (Hq2 : t * t <= / 4 * / 4) by (apply Rmult_le_compat; lra).
split. now apply Rmult_le_pos. nra.
Qed.

(* Uq, times a factor up to 5/4, is at most 1. *)
Lemma uq_le_1 : forall rel k : R, 0 <= rel <= / 4 -> 1 <= k <= 5 / 4 -> 0 <= Ball2.uq rel * k <= 1.
Proof.
intros rel k [R0 R1] [K0 K1]. unfold Ball2.uq.
assert (I : 0 < / (1 - rel)) by (apply Rinv_0_lt_compat; lra).
assert (Q0 : 0 <= rel / (1 - rel)) by (unfold Rdiv; apply Rmult_le_pos; lra).
assert (Q1 : rel / (1 - rel) <= / 3).
{ apply Rmult_le_reg_r with (1 - rel). lra.
  unfold Rdiv. rewrite Rmult_assoc, Rinv_l by lra. lra. }
nra.
Qed.

Lemma vq_le :
  forall rel tiny e : R, 0 <= rel <= / 4 -> 0 <= tiny <= 3 / 2 * e ->
  0 <= Ball2.vq rel tiny <= 3 * e.
Proof.
intros rel tiny e [R0 R1] [T0 T1]. unfold Ball2.vq.
assert (I : 0 < / (1 - rel)) by (apply Rinv_0_lt_compat; lra).
split.
- unfold Rdiv. apply Rmult_le_pos; lra.
- apply Rmult_le_reg_r with (1 - rel). lra.
  unfold Rdiv. rewrite Rmult_assoc, Rinv_l by lra. nra.
Qed.

Lemma pow_le_4 :
  forall (t : R) (n : nat), 0 < t <= / 4 -> (n <= 6)%nat -> 0 <= (1 + t) ^ n <= 4.
Proof.
intros t n [T0 T1] Hn. split. apply pow_le; lra.
apply Rle_trans with ((5 / 4) ^ n). apply pow_incr; lra.
apply Rle_trans with ((5 / 4) ^ 6). apply Rle_pow; [lra|exact Hn].
simpl. lra.
Qed.

Lemma h2_le :
  forall (emin prec : Z) (V : R), (2 <= prec)%Z -> 0 <= V <= 3 * eta emin ->
  0 <= Ball2.h2 emin prec V <= bpow radix2 (emin + 4).
Proof.
intros emin prec V Hp [V0 V1].
assert (Ht : 0 < u prec <= / 4) by exact (Ball2.u_bounds prec 2 Hp).
destruct (pow_le_4 (u prec) 2 Ht ltac:(lia)) as [P0 P4].
assert (B : bpow radix2 (emin + 4) = 16 * eta emin).
{ rewrite bpow_plus. unfold eta. change (bpow radix2 4) with 16. ring. }
rewrite B. unfold Ball2.h2. destruct Ht as [T0 T1].
generalize (bpow_gt_0 radix2 emin). fold (eta emin). intros E0.
set (t := u prec) in *. set (e := eta emin) in *. set (q := (1 + t) ^ 2) in *.
assert (Q : q * e <= 4 * e) by (apply Rmult_le_compat_r; lra).
assert (Q0 : 0 <= q * e) by (apply Rmult_le_pos; lra).
assert (A : 0 <= q * e + V + e / 2 <= 15 / 2 * e) by lra.
split. apply Rmult_le_pos; lra. nra.
Qed.

Lemma h4_le :
  forall (emin prec : Z) (n : nat) (V : R), (2 <= prec)%Z -> (n <= 5)%nat ->
  0 <= V <= 3 * eta emin ->
  0 <= Ball2.h4 emin prec n V <= bpow radix2 (emin + 4).
Proof.
intros emin prec n V Hp Hn [V0 V1].
assert (Ht : 0 < u prec <= / 4) by exact (Ball2.u_bounds prec 2 Hp).
destruct (pow_le_4 (u prec) n Ht ltac:(lia)) as [P0 P4].
assert (B : bpow radix2 (emin + 4) = 16 * eta emin).
{ rewrite bpow_plus. unfold eta. change (bpow radix2 4) with 16. ring. }
rewrite B. unfold Ball2.h4. destruct Ht as [T0 T1].
generalize (bpow_gt_0 radix2 emin). fold (eta emin). intros E0.
set (t := u prec) in *. set (e := eta emin) in *. set (q := (1 + t) ^ n) in *.
assert (Q : q * e <= 4 * e) by (apply Rmult_le_compat_r; lra).
assert (Q0 : 0 <= q * e) by (apply Rmult_le_pos; lra).
assert (A : 0 <= 2 * q * e + V + e / 2 <= 23 / 2 * e) by lra.
split. apply Rmult_le_pos; lra. nra.
Qed.

Section IeeeBallCores.
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

Notation emin := (3 - emax - prec)%Z.
Notation fexp := (FLT_exp emin prec).
Notation format := (generic_format radix2 fexp).
Notation rnd := (round radix2 fexp (Znearest tie_even)).
Notation fin x := (is_finite prec emax x = true).
Notation b2r := (B2R prec emax).
Notation add := (IeeeOperations.add prec emax nan_plus).
Notation neg := (IeeeOperations.neg prec emax nan_opp).
Notation fabs := (IeeeOperations.abs prec emax nan_abs).
Notation fma := (IeeeOperations.fma prec emax nan_fma).
Notation prod := (IeeeOperations.prod prec emax nan_fma).
Notation const_of := (IeeeOperations.const_of prec emax).
Notation fixup_1 := (IeeeBall.ball_fixup_1 prec emax nan_abs).
Notation fixup_2 := (IeeeBall.ball_fixup_2 prec emax nan_abs).

Let Hprec : (0 < prec)%Z.
Proof. exact prec_gt_0_. Qed.
Let Hemax : (prec < emax)%Z.
Proof. exact prec_lt_emax_. Qed.

(** * The constants *)

(* A constant c of the IEEE model whose value is the constant r of the real model: a
   finite nonnegative number. *)
Definition good_const (c : float) (r : R) : Prop := fin c /\ b2r c = r /\ nonneg_ext c.

Lemma good_le_1 :
  forall t : R, 0 <= t <= 1 -> good_const (const_of (RU emin prec t)) (RU emin prec t).
Proof.
intros t [T0 T1]. apply (const_of_RU prec emax t 1 T0 T1).
- change 1 with (bpow radix2 0). apply generic_format_bpow. unfold FLT_exp. lia.
- change 1 with (bpow radix2 0). apply bpow_lt. lia.
Qed.

Lemma good_le_4 :
  (2 <= prec)%Z ->
  forall t : R, 0 <= t <= 4 -> good_const (const_of (RU emin prec t)) (RU emin prec t).
Proof.
intros Hp t [T0 T1]. change 4 with (bpow radix2 2) in T1.
apply (const_of_RU prec emax t (bpow radix2 2) T0 T1).
- apply generic_format_bpow. unfold FLT_exp. lia.
- apply bpow_lt. lia.
Qed.

Lemma good_le_16eta :
  (2 <= prec)%Z ->
  forall t : R, 0 <= t <= bpow radix2 (emin + 4) ->
  good_const (const_of (RU emin prec t)) (RU emin prec t).
Proof.
intros Hp t [T0 T1].
apply (const_of_RU prec emax t (bpow radix2 (emin + 4)) T0 T1).
- apply generic_format_bpow. unfold FLT_exp. lia.
- apply bpow_lt. lia.
Qed.

Lemma kappa_bounds : (2 <= prec)%Z -> 1 <= 1 + u prec <= 5 / 4.
Proof. intros Hp. assert (Ht : 0 < u prec <= / 4) by exact (Ball2.u_bounds prec 2 Hp). lra. Qed.

Lemma eta_tiny : forall t : R, 0 <= t <= 3 / 2 -> 0 <= t * eta emin <= 3 / 2 * eta emin.
Proof.
intros t [T0 T1]. generalize (bpow_gt_0 radix2 emin). fold (eta emin). intros E0. nra.
Qed.

Lemma consts_ball_add_1 :
  (2 <= prec)%Z ->
  good_const (IeeeModel.up_ball_add_1_0 prec emax) (Model.up_ball_add_1_0 emin prec) /\
  good_const (IeeeModel.up_ball_add_1_1 prec emax) (Model.up_ball_add_1_1 emin prec) /\
  good_const (IeeeModel.up_ball_add_1_2 prec emax) (Model.up_ball_add_1_2 emin prec).
Proof.
intros Hp. unfold IeeeModel.up_ball_add_1_0, IeeeModel.up_ball_add_1_1,
                  IeeeModel.up_ball_add_1_2.
rewrite Ball2.e_add_1_eq, Ball2.g_add_1_eq, Ball2.h_add_1_eq.
split; [|split].
- apply good_le_1. generalize (uq_le_1 _ 1 (rel_1_quarter prec Hp) ltac:(lra)). lra.
- apply good_le_4; trivial. apply pow_le_4. exact (Ball2.u_bounds prec 2 Hp). lia.
- apply good_le_16eta; trivial.
  replace ((1 + u prec) * ((1 + u prec) ^ 2 * eta emin + eta emin / 2))
    with (Ball2.h2 emin prec 0) by (unfold Ball2.h2; ring).
  apply h2_le; trivial. generalize (bpow_gt_0 radix2 emin). unfold eta. lra.
Qed.

Lemma consts_ball_add_2 :
  (3 <= prec)%Z ->
  good_const (IeeeModel.up_ball_add_2_0 prec emax) (Model.up_ball_add_2_0 emin prec) /\
  good_const (IeeeModel.up_ball_add_1_1 prec emax) (Model.up_ball_add_1_1 emin prec) /\
  good_const (IeeeModel.up_ball_add_1_2 prec emax) (Model.up_ball_add_1_2 emin prec).
Proof.
intros Hp. assert (Hp2 : (2 <= prec)%Z) by lia.
unfold IeeeModel.up_ball_add_2_0, IeeeModel.up_ball_add_1_1,
       IeeeModel.up_ball_add_1_2.
rewrite Ball2.e_add_2_eq, Ball2.g_add_2_eq, Ball2.h_add_2_eq.
split; [|split].
- apply good_le_1. exact (uq_le_1 _ _ (rel_add_2_quarter prec Hp) (kappa_bounds Hp2)).
- apply good_le_4; trivial. apply pow_le_4. exact (Ball2.u_bounds prec 2 Hp2). lia.
- apply good_le_16eta; trivial.
  replace ((1 + u prec) * ((1 + u prec) ^ 2 * eta emin + eta emin / 2))
    with (Ball2.h2 emin prec 0) by (unfold Ball2.h2; ring).
  apply h2_le; trivial. generalize (bpow_gt_0 radix2 emin). unfold eta. lra.
Qed.

Lemma consts_ball_scale_1 :
  (2 <= prec)%Z ->
  good_const (IeeeModel.up_ball_mul_1_0 prec emax) (Model.up_ball_mul_1_0 emin prec) /\
  good_const (IeeeModel.up_ball_add_1_1 prec emax) (Model.up_ball_add_1_1 emin prec) /\
  good_const (IeeeModel.up_ball_scale_1_2 prec emax) (Model.up_ball_scale_1_2 emin prec).
Proof.
intros Hp. unfold IeeeModel.up_ball_mul_1_0, IeeeModel.up_ball_add_1_1,
                  IeeeModel.up_ball_scale_1_2.
rewrite Ball2.e_scale_1_eq, Ball2.g_scale_1_eq, Ball2.h_scale_1_eq.
split; [|split].
- apply good_le_1. generalize (uq_le_1 _ 1 (rel_1_quarter prec Hp) ltac:(lra)). lra.
- apply good_le_4; trivial. apply pow_le_4. exact (Ball2.u_bounds prec 2 Hp). lia.
- apply good_le_16eta; trivial. apply h2_le; trivial.
  apply vq_le. exact (rel_1_quarter prec Hp). apply eta_tiny. lra.
Qed.

Lemma consts_ball_scale_2 :
  (2 <= prec)%Z ->
  good_const (IeeeModel.up_ball_scale_2_0 prec emax) (Model.up_ball_scale_2_0 emin prec) /\
  good_const (IeeeModel.up_ball_add_1_1 prec emax) (Model.up_ball_add_1_1 emin prec) /\
  good_const (IeeeModel.up_ball_scale_2_2 prec emax) (Model.up_ball_scale_2_2 emin prec).
Proof.
intros Hp. unfold IeeeModel.up_ball_scale_2_0, IeeeModel.up_ball_add_1_1,
                  IeeeModel.up_ball_scale_2_2.
rewrite Ball2.e_scale_2_eq, Ball2.g_scale_2_eq, Ball2.h_scale_2_eq.
assert (Hrel := rel_square_quarter 2 prec Hp ltac:(lra)).
split; [|split].
- apply good_le_1. exact (uq_le_1 _ _ Hrel (kappa_bounds Hp)).
- apply good_le_4; trivial. apply pow_le_4. exact (Ball2.u_bounds prec 2 Hp). lia.
- apply good_le_16eta; trivial. apply h2_le; trivial.
  apply vq_le. exact Hrel. apply eta_tiny. lra.
Qed.

Lemma consts_ball_mul_1 :
  (2 <= prec)%Z ->
  good_const (IeeeModel.up_ball_mul_1_0 prec emax) (Model.up_ball_mul_1_0 emin prec) /\
  good_const (IeeeModel.up_ball_mul_1_1 prec emax) (Model.up_ball_mul_1_1 emin prec) /\
  good_const (IeeeModel.up_ball_mul_1_2 prec emax) (Model.up_ball_mul_1_2 emin prec).
Proof.
intros Hp. unfold IeeeModel.up_ball_mul_1_0, IeeeModel.up_ball_mul_1_1,
                  IeeeModel.up_ball_mul_1_2.
rewrite Ball2.e_mul_1_eq, Ball2.g_mul_1_eq, Ball2.h_mul_1_eq.
split; [|split].
- apply good_le_1. generalize (uq_le_1 _ 1 (rel_1_quarter prec Hp) ltac:(lra)). lra.
- apply good_le_4; trivial. apply pow_le_4. exact (Ball2.u_bounds prec 2 Hp). lia.
- apply good_le_16eta; trivial. apply h4_le; [exact Hp|lia|].
  apply vq_le. exact (rel_1_quarter prec Hp). apply eta_tiny. lra.
Qed.

Lemma consts_ball_mul_2 :
  (4 <= prec)%Z ->
  good_const (IeeeModel.up_ball_mul_2_0 prec emax) (Model.up_ball_mul_2_0 emin prec) /\
  good_const (IeeeModel.up_ball_mul_2_1 prec emax) (Model.up_ball_mul_2_1 emin prec) /\
  good_const (IeeeModel.up_ball_mul_2_2 prec emax) (Model.up_ball_mul_2_2 emin prec).
Proof.
intros Hp. assert (Hp2 : (2 <= prec)%Z) by lia.
unfold IeeeModel.up_ball_mul_2_0, IeeeModel.up_ball_mul_2_1,
       IeeeModel.up_ball_mul_2_2.
rewrite Ball2.e_mul_2_eq, Ball2.g_mul_2_eq, Ball2.h_mul_2_eq.
assert (Hrel := rel_square_quarter 4 prec Hp2 ltac:(lra)).
split; [|split].
- apply good_le_1. generalize (uq_le_1 _ 1 Hrel ltac:(lra)). lra.
- apply good_le_4; trivial. apply pow_le_4. exact (Ball2.u_bounds prec 2 Hp2). lia.
- apply good_le_16eta; trivial. apply h4_le; [exact Hp2|lia|].
  apply vq_le. exact Hrel. apply eta_tiny. lra.
Qed.

(** * The cores: centers of one limb *)

Notation ball_add_1 := (IeeeModel.ball_add_1 prec emax nan_plus nan_abs nan_fma).
Notation ball_sub_1 := (IeeeModel.ball_sub_1 prec emax nan_plus nan_opp nan_abs nan_fma).
Notation ball_mul_1 := (IeeeModel.ball_mul_1 prec emax nan_abs nan_fma).
Notation ball_scale_1 := (IeeeModel.ball_scale_1 prec emax nan_abs nan_fma).

Lemma ball_add_1_core :
  (2 <= prec)%Z ->
  forall cx rx cy ry : float, fin cx -> fin cy -> nonneg_ext rx -> nonneg_ext ry ->
  let '(cz, rz) := ball_add_1 cx rx cy ry in
  nonneg_ext rz /\
  (fin cz -> fin rz ->
   fin rx /\ fin ry /\
   (b2r cz, b2r rz)
   = Model.ball_add_1 emin prec tie_even (b2r cx) (b2r rx) (b2r cy) (b2r ry)).
Proof.
intros Hp cx rx cy ry Fx Fy Hrx Hry.
unfold IeeeModel.ball_add_1, Model.ball_add_1. cbv beta iota zeta.
destruct (consts_ball_add_1 Hp) as [[FE [EE HE]] [[FG [EG HG]] [FH [EH HH]]]].
destruct (add_nonneg prec emax nan_plus rx ry Hrx Hry) as [Hs [Es _]].
destruct (fma_nonneg prec emax nan_fma _ _ _ (abs_nonneg prec emax nan_abs (add cx cy)) HE Hs)
  as [Ht Et].
destruct (fma_nonneg prec emax nan_fma _ _ _ Ht HG HH) as [Hrz Erz].
split. exact Hrz.
intros Fz Frz. destruct (Erz Frz) as [Ft [_ [_ E1]]]. destruct (Et Ft) as [_ [_ [Fs E2]]].
destruct (Es Fs) as [Frx [Fry E3]].
split. exact Frx. split. exact Fry.
rewrite E1, E2, E3, (abs_val prec emax nan_abs), EE, EG, EH.
rewrite (proj2 (add_spec prec emax nan_plus cx cy Fx Fy) Fz). reflexivity.
Qed.

Lemma ball_sub_1_core :
  (2 <= prec)%Z ->
  forall cx rx cy ry : float, fin cx -> fin cy -> nonneg_ext rx -> nonneg_ext ry ->
  let '(cz, rz) := ball_sub_1 cx rx cy ry in
  nonneg_ext rz /\
  (fin cz -> fin rz ->
   fin rx /\ fin ry /\
   (b2r cz, b2r rz)
   = Model.ball_sub_1 emin prec tie_even (b2r cx) (b2r rx) (b2r cy) (b2r ry)).
Proof.
intros Hp cx rx cy ry Fx Fy Hrx Hry.
unfold IeeeModel.ball_sub_1, Model.ball_sub_1. cbv zeta.
assert (Fn : fin (neg cy)) by (unfold IeeeOperations.neg; now rewrite is_finite_Bopp).
generalize (ball_add_1_core Hp cx rx (neg cy) ry Fx Fn Hrx Hry).
replace (b2r (neg cy)) with (- b2r cy) by (symmetry; apply B2R_Bopp).
destruct (ball_add_1 cx rx (neg cy) ry) as [cz rz].
destruct (Model.ball_add_1 emin prec tie_even (b2r cx) (b2r rx) (- b2r cy) (b2r ry)) as [c r].
cbv beta iota. intros K. exact K.
Qed.

Lemma ball_mul_1_core :
  (2 <= prec)%Z ->
  forall cx rx cy ry : float, fin cx -> fin cy -> nonneg_ext rx -> nonneg_ext ry ->
  let '(cz, rz) := ball_mul_1 cx rx cy ry in
  nonneg_ext rz /\
  (fin cz -> fin rz ->
   fin rx /\ fin ry /\
   (b2r cz, b2r rz)
   = Model.ball_mul_1 emin prec tie_even (b2r cx) (b2r rx) (b2r cy) (b2r ry)).
Proof.
intros Hp cx rx cy ry Fx Fy Hrx Hry.
unfold IeeeModel.ball_mul_1, Model.ball_mul_1. cbv beta iota zeta.
destruct (consts_ball_mul_1 Hp) as [[FE [EE HE]] [[FG [EG HG]] [FH [EH HH]]]].
destruct (prod_nonneg prec emax nan_fma rx ry Hrx Hry) as [Hp1 Ep].
destruct (fma_nonneg prec emax nan_fma _ _ _ (abs_nonneg prec emax nan_abs cy) Hrx Hp1) as [Hq Eq].
destruct (fma_nonneg prec emax nan_fma _ _ _ (abs_nonneg prec emax nan_abs cx) Hry Hq) as [Hw Ew].
destruct (fma_nonneg prec emax nan_fma _ _ _ (abs_nonneg prec emax nan_abs (prod cx cy)) HE Hw)
  as [Ht Et].
destruct (fma_nonneg prec emax nan_fma _ _ _ Ht HG HH) as [Hrz Erz].
split. exact Hrz.
intros Fz Frz. destruct (Erz Frz) as [Ft [_ [_ E1]]]. destruct (Et Ft) as [_ [_ [Fw E2]]].
destruct (Ew Fw) as [_ [Fry [Fq E3]]]. destruct (Eq Fq) as [_ [Frx [Fp E4]]].
destruct (Ep Fp) as [_ [_ E5]].
split. exact Frx. split. exact Fry.
rewrite E1, E2, E3, E4, E5, !(abs_val prec emax nan_abs), EE, EG, EH.
assert (Ec : b2r (prod cx cy) = rnd (b2r cx * b2r cy + 0)).
{ unfold IeeeOperations.prod. change 0 with (b2r (IeeeOperations.pzero prec emax)).
  now apply (fma_spec prec emax nan_fma cx cy (IeeeOperations.pzero prec emax) Fx Fy eq_refl). }
rewrite Ec. reflexivity.
Qed.

Lemma ball_scale_1_core :
  (2 <= prec)%Z ->
  forall cx rx a : float, fin cx -> nonneg_ext rx ->
  let '(cz, rz) := ball_scale_1 cx rx a in
  nonneg_ext rz /\
  (fin cz -> fin rz ->
   fin rx /\ fin a /\
   (b2r cz, b2r rz) = Model.ball_scale_1 emin prec tie_even (b2r cx) (b2r rx) (b2r a)).
Proof.
intros Hp cx rx a Fx Hrx.
unfold IeeeModel.ball_scale_1, Model.ball_scale_1. cbv beta iota zeta.
destruct (consts_ball_scale_1 Hp) as [[FE [EE HE]] [[FG [EG HG]] [FH [EH HH]]]].
destruct (prod_nonneg prec emax nan_fma _ _ (abs_nonneg prec emax nan_abs a) Hrx) as [Hp1 Ep].
destruct (fma_nonneg prec emax nan_fma _ _ _ (abs_nonneg prec emax nan_abs (prod cx a)) HE Hp1)
  as [Ht Et].
destruct (fma_nonneg prec emax nan_fma _ _ _ Ht HG HH) as [Hrz Erz].
split. exact Hrz.
intros Fz Frz. destruct (Erz Frz) as [Ft [_ [_ E1]]]. destruct (Et Ft) as [_ [_ [Fp E2]]].
destruct (Ep Fp) as [Faa [Frx E3]].
assert (Fa : fin a) by now rewrite <- (abs_finite prec emax nan_abs).
split. exact Frx. split. exact Fa.
rewrite E1, E2, E3, !(abs_val prec emax nan_abs), EE, EG, EH.
assert (Ec : b2r (prod cx a) = rnd (b2r cx * b2r a + 0)).
{ unfold IeeeOperations.prod. change 0 with (b2r (IeeeOperations.pzero prec emax)).
  now apply (fma_spec prec emax nan_fma cx a (IeeeOperations.pzero prec emax) Fx Fa eq_refl). }
rewrite Ec. reflexivity.
Qed.

(** * The cores: centers of two limbs *)

Notation ball_add_2 := (IeeeModel.ball_add_2 prec emax nan_plus nan_minus nan_abs nan_fma).
Notation ball_sub_2 := (IeeeModel.ball_sub_2 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma).
Notation ball_mul_2 := (IeeeModel.ball_mul_2 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma).
Notation ball_scale_2 :=
  (IeeeModel.ball_scale_2 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma).

Lemma ball_add_2_core :
  (3 <= prec)%Z ->
  forall cx0 cx1 rx cy0 cy1 ry : float,
  fin cx0 -> fin cx1 -> fin cy0 -> fin cy1 ->
  normalized_2 emin prec (b2r cx0) (b2r cx1) -> normalized_2 emin prec (b2r cy0) (b2r cy1) ->
  nonneg_ext rx -> nonneg_ext ry ->
  let '(cz0, cz1, rz) := ball_add_2 cx0 cx1 rx cy0 cy1 ry in
  nonneg_ext rz /\
  (fin cz0 -> fin rz ->
   fin rx /\ fin ry /\ fin cz1 /\
   (b2r cz0, b2r cz1, b2r rz)
   = Model.ball_add_2 emin prec tie_even (b2r cx0) (b2r cx1) (b2r rx)
       (b2r cy0) (b2r cy1) (b2r ry)).
Proof.
intros Hp cx0 cx1 rx cy0 cy1 ry F0 F1 G0 G1 Nx Ny Hrx Hry.
unfold IeeeModel.ball_add_2, Model.ball_add_2.
generalize (add_2_2_values prec emax nan_plus nan_minus nan_opp nan_fma Hp cx0 cx1 cy0 cy1
              F0 F1 G0 G1 Nx Ny).
destruct (IeeeModel.add_2_2 prec emax nan_plus nan_minus cx0 cx1 cy0 cy1) as [cz0 cz1].
cbv beta iota zeta. intros V.
destruct (consts_ball_add_2 Hp) as [[FE [EE HE]] [[FG [EG HG]] [FH [EH HH]]]].
destruct (add_nonneg prec emax nan_plus rx ry Hrx Hry) as [Hs [Es _]].
destruct (fma_nonneg prec emax nan_fma _ _ _ (abs_nonneg prec emax nan_abs cz0) HE Hs) as [Ht Et].
destruct (fma_nonneg prec emax nan_fma _ _ _ Ht HG HH) as [Hrz Erz].
split. exact Hrz.
intros Fz0 Frz. destruct (Erz Frz) as [Ft [_ [_ E1]]]. destruct (Et Ft) as [_ [_ [Fs E2]]].
destruct (Es Fs) as [Frx [Fry E3]]. destruct (V Fz0) as [Fz1 Ec].
split. exact Frx. split. exact Fry. split. exact Fz1.
rewrite <- Ec. cbv beta iota zeta.
rewrite E1, E2, E3, (abs_val prec emax nan_abs), EE, EG, EH. reflexivity.
Qed.

Lemma ball_sub_2_core :
  (3 <= prec)%Z ->
  forall cx0 cx1 rx cy0 cy1 ry : float,
  fin cx0 -> fin cx1 -> fin cy0 -> fin cy1 ->
  normalized_2 emin prec (b2r cx0) (b2r cx1) -> normalized_2 emin prec (b2r cy0) (b2r cy1) ->
  nonneg_ext rx -> nonneg_ext ry ->
  let '(cz0, cz1, rz) := ball_sub_2 cx0 cx1 rx cy0 cy1 ry in
  nonneg_ext rz /\
  (fin cz0 -> fin rz ->
   fin rx /\ fin ry /\ fin cz1 /\
   (b2r cz0, b2r cz1, b2r rz)
   = Model.ball_sub_2 emin prec tie_even (b2r cx0) (b2r cx1) (b2r rx)
       (b2r cy0) (b2r cy1) (b2r ry)).
Proof.
intros Hp cx0 cx1 rx cy0 cy1 ry F0 F1 G0 G1 Nx Ny Hrx Hry.
unfold IeeeModel.ball_sub_2, Model.ball_sub_2, IeeeModel.neg_2, neg_2. cbv beta iota zeta.
assert (Fn0 : fin (neg cy0)) by (unfold IeeeOperations.neg; now rewrite is_finite_Bopp).
assert (Fn1 : fin (neg cy1)) by (unfold IeeeOperations.neg; now rewrite is_finite_Bopp).
assert (E0 : b2r (neg cy0) = - b2r cy0) by apply B2R_Bopp.
assert (E1 : b2r (neg cy1) = - b2r cy1) by apply B2R_Bopp.
assert (Nn : normalized_2 emin prec (b2r (neg cy0)) (b2r (neg cy1))).
{ rewrite E0, E1. now apply normalized_2_opp. }
generalize (ball_add_2_core Hp cx0 cx1 rx (neg cy0) (neg cy1) ry F0 F1 Fn0 Fn1 Nx Nn Hrx Hry).
rewrite E0, E1.
destruct (ball_add_2 cx0 cx1 rx (neg cy0) (neg cy1) ry) as [[cz0 cz1] rz].
destruct (Model.ball_add_2 emin prec tie_even (b2r cx0) (b2r cx1) (b2r rx)
            (- b2r cy0) (- b2r cy1) (b2r ry)) as [[c0 c1] r].
cbv beta iota. intros K. exact K.
Qed.

Lemma ball_mul_2_core :
  (4 <= prec)%Z ->
  forall cx0 cx1 rx cy0 cy1 ry : float,
  fin cx0 -> fin cx1 -> fin cy0 -> fin cy1 ->
  normalized_2 emin prec (b2r cx0) (b2r cx1) -> normalized_2 emin prec (b2r cy0) (b2r cy1) ->
  nonneg_ext rx -> nonneg_ext ry ->
  let '(cz0, cz1, rz) := ball_mul_2 cx0 cx1 rx cy0 cy1 ry in
  nonneg_ext rz /\
  (fin cz0 -> fin rz ->
   fin rx /\ fin ry /\ fin cz1 /\
   (b2r cz0, b2r cz1, b2r rz)
   = Model.ball_mul_2 emin prec tie_even (b2r cx0) (b2r cx1) (b2r rx)
       (b2r cy0) (b2r cy1) (b2r ry)).
Proof.
intros Hp cx0 cx1 rx cy0 cy1 ry F0 F1 G0 G1 Nx Ny Hrx Hry.
unfold IeeeModel.ball_mul_2, Model.ball_mul_2.
generalize (mul_2_2_values prec emax nan_plus nan_minus nan_opp nan_fma Hp cx0 cx1 cy0 cy1
              F0 F1 G0 G1 Nx Ny).
destruct (IeeeModel.mul_2_2 prec emax nan_plus nan_minus nan_opp nan_fma cx0 cx1 cy0 cy1)
  as [cz0 cz1].
cbv beta iota zeta. intros V.
destruct (consts_ball_mul_2 Hp) as [[FE [EE HE]] [[FG [EG HG]] [FH [EH HH]]]].
destruct (prod_nonneg prec emax nan_fma rx ry Hrx Hry) as [Hp1 Ep].
destruct (fma_nonneg prec emax nan_fma _ _ _ (abs_nonneg prec emax nan_abs cy0) Hrx Hp1) as [Hq Eq].
destruct (fma_nonneg prec emax nan_fma _ _ _ (abs_nonneg prec emax nan_abs cx0) Hry Hq) as [Hw Ew].
destruct (fma_nonneg prec emax nan_fma _ _ _ (abs_nonneg prec emax nan_abs cz0) HE Hw) as [Ht Et].
destruct (fma_nonneg prec emax nan_fma _ _ _ Ht HG HH) as [Hrz Erz].
split. exact Hrz.
intros Fz0 Frz. destruct (Erz Frz) as [Ft [_ [_ E1]]]. destruct (Et Ft) as [_ [_ [Fw E2]]].
destruct (Ew Fw) as [_ [Fry [Fq E3]]]. destruct (Eq Fq) as [_ [Frx [Fp E4]]].
destruct (Ep Fp) as [_ [_ E5]]. destruct (V Fz0) as [Fz1 Ec].
split. exact Frx. split. exact Fry. split. exact Fz1.
rewrite <- Ec. cbv beta iota zeta.
rewrite E1, E2, E3, E4, E5, !(abs_val prec emax nan_abs), EE, EG, EH. reflexivity.
Qed.

Lemma ball_scale_2_core :
  (2 <= prec)%Z ->
  forall cx0 cx1 rx a : float,
  fin cx0 -> fin cx1 -> normalized_2 emin prec (b2r cx0) (b2r cx1) -> nonneg_ext rx ->
  let '(cz0, cz1, rz) := ball_scale_2 cx0 cx1 rx a in
  nonneg_ext rz /\
  (fin cz0 -> fin rz ->
   fin rx /\ fin a /\ fin cz1 /\
   (b2r cz0, b2r cz1, b2r rz)
   = Model.ball_scale_2 emin prec tie_even (b2r cx0) (b2r cx1) (b2r rx) (b2r a)).
Proof.
intros Hp cx0 cx1 rx a F0 F1 Nx Hrx.
unfold IeeeModel.ball_scale_2, Model.ball_scale_2.
generalize (fun Fa => mul_2_1_values prec emax nan_plus nan_minus nan_opp nan_fma Hp cx0 cx1 a
                        F0 F1 Fa Nx).
destruct (IeeeModel.mul_2_1 prec emax nan_plus nan_minus nan_opp nan_fma cx0 cx1 a) as [cz0 cz1].
cbv beta iota zeta. intros V.
destruct (consts_ball_scale_2 Hp) as [[FE [EE HE]] [[FG [EG HG]] [FH [EH HH]]]].
destruct (prod_nonneg prec emax nan_fma _ _ (abs_nonneg prec emax nan_abs a) Hrx) as [Hp1 Ep].
destruct (fma_nonneg prec emax nan_fma _ _ _ (abs_nonneg prec emax nan_abs cz0) HE Hp1) as [Ht Et].
destruct (fma_nonneg prec emax nan_fma _ _ _ Ht HG HH) as [Hrz Erz].
split. exact Hrz.
intros Fz0 Frz. destruct (Erz Frz) as [Ft [_ [_ E1]]]. destruct (Et Ft) as [_ [_ [Fp E2]]].
destruct (Ep Fp) as [Faa [Frx E3]].
assert (Fa : fin a) by now rewrite <- (abs_finite prec emax nan_abs).
destruct (V Fa Fz0) as [Fz1 Ec].
split. exact Frx. split. exact Fa. split. exact Fz1.
rewrite <- Ec. cbv beta iota zeta.
rewrite E1, E2, E3, !(abs_val prec emax nan_abs), EE, EG, EH. reflexivity.
Qed.

(** * From a core to its full kernel *)

(* Two ball operands, centers of two limbs. core is the result of the core in the IEEE
   model, real that of the real model on the values of the operands, g the operation. *)
Lemma full_2_two :
  forall (g : R -> R -> R) (core : float * float * float) (real : R * R * R)
         (cx0 cx1 rx cy0 cy1 ry : float),
  ball_2 cx0 cx1 rx -> ball_2 cy0 cy1 ry ->
  (fin cx0 -> fin cx1 -> fin cy0 -> fin cy1 ->
   normalized_2 emin prec (b2r cx0) (b2r cx1) -> normalized_2 emin prec (b2r cy0) (b2r cy1) ->
   let '(cz0, cz1, rz) := core in
   nonneg_ext rz /\
   (fin cz0 -> fin rz -> fin rx /\ fin ry /\ fin cz1 /\ (b2r cz0, b2r cz1, b2r rz) = real)) ->
  (normalized_2 emin prec (b2r cx0) (b2r cx1) -> normalized_2 emin prec (b2r cy0) (b2r cy1) ->
   0 <= b2r rx -> 0 <= b2r ry ->
   let '(z0, z1, r) := real in
   fmt emin prec r /\ normalized_2 emin prec z0 z1 /\
   (forall x y : R, Rabs (x - (b2r cx0 + b2r cx1)) <= b2r rx ->
    Rabs (y - (b2r cy0 + b2r cy1)) <= b2r ry -> Rabs (g x y - (z0 + z1)) <= r)) ->
  let '(cw0, cw1, rw) := (let '(cz0, cz1, rz) := core in fixup_2 cz0 cz1 rz (add rx ry)) in
  ball_2 cw0 cw1 rw /\
  (ball_empty_2 cw0 cw1 rw <-> ball_empty_2 cx0 cx1 rx \/ ball_empty_2 cy0 cy1 ry) /\
  (ball_finite_2 cw0 cw1 rw ->
   (ball_finite_2 cx0 cx1 rx /\ ball_finite_2 cy0 cy1 ry) /\
   (forall x y : R, Rabs (x - (b2r cx0 + b2r cx1)) <= b2r rx ->
    Rabs (y - (b2r cy0 + b2r cy1)) <= b2r ry -> Rabs (g x y - (b2r cw0 + b2r cw1)) <= b2r rw)).
Proof.
intros g core real cx0 cx1 rx cy0 cy1 ry Bx By Hcore Hreal.
generalize (ball_2_radius prec emax _ _ _ Bx) (ball_2_radius prec emax _ _ _ By). intros Hrx Hry.
assert (K : ~ (ball_empty_2 cx0 cx1 rx \/ ball_empty_2 cy0 cy1 ry) ->
  let '(cz0, cz1, rz) := core in
  fin cz0 ->
  nonneg_ext rz /\
  (fin rz ->
   (ball_finite_2 cx0 cx1 rx /\ ball_finite_2 cy0 cy1 ry) /\ fin cz1 /\
   normalized_2 emin prec (b2r cz0) (b2r cz1) /\
   (forall x y : R, Rabs (x - (b2r cx0 + b2r cx1)) <= b2r rx ->
    Rabs (y - (b2r cy0 + b2r cy1)) <= b2r ry -> Rabs (g x y - (b2r cz0 + b2r cz1)) <= b2r rz))).
{ intros NE.
  assert (Nrx : is_nan prec emax rx = false).
  { destruct (is_nan prec emax rx) eqn:N; trivial. elim NE. left. now apply (ball_2_empty prec emax). }
  assert (Nry : is_nan prec emax ry = false).
  { destruct (is_nan prec emax ry) eqn:N; trivial. elim NE. right. now apply (ball_2_empty prec emax). }
  destruct (ball_2_center prec emax _ _ _ Bx Nrx) as [F0 [F1 Nx]].
  destruct (ball_2_center prec emax _ _ _ By Nry) as [G0 [G1 Ny]].
  specialize (Hcore F0 F1 G0 G1 Nx Ny). specialize (Hreal Nx Ny).
  destruct core as [[cz0 cz1] rz]. destruct Hcore as [Hrz Kc]. intros Fz0. split. exact Hrz.
  intros Frz. destruct (Kc Fz0 Frz) as [Frx [Fry [Fz1 E]]].
  specialize (Hreal (nonneg_ext_fin prec emax rx Hrx Frx) (nonneg_ext_fin prec emax ry Hry Fry)).
  rewrite <- E in Hreal. cbv beta iota in Hreal. destruct Hreal as [_ [Nz C]].
  split; [split; now apply (ball_2_finite prec emax)|split; [exact Fz1|split; [exact Nz|exact C]]]. }
revert K. destruct core as [[cz0 cz1] rz]. intros K.
exact (ball_template_2 prec emax nan_abs cz0 cz1 rz (add rx ry) _ _
         (fun cw0 cw1 rw => forall x y : R, Rabs (x - (b2r cx0 + b2r cx1)) <= b2r rx ->
            Rabs (y - (b2r cy0 + b2r cy1)) <= b2r ry ->
            Rabs (g x y - (b2r cw0 + b2r cw1)) <= b2r rw)
         (q_empty_2 prec emax nan_plus _ _ _ _ _ _ Bx By) K).
Qed.

(* Two ball operands, centers of one limb. *)
Lemma full_1_two :
  forall (g : R -> R -> R) (core : float * float) (real : R * R) (cx rx cy ry : float),
  ball_1 cx rx -> ball_1 cy ry ->
  (fin cx -> fin cy ->
   let '(cz, rz) := core in
   nonneg_ext rz /\ (fin cz -> fin rz -> fin rx /\ fin ry /\ (b2r cz, b2r rz) = real)) ->
  (0 <= b2r rx -> 0 <= b2r ry ->
   let '(z, r) := real in
   fmt emin prec z /\ fmt emin prec r /\
   (forall x y : R, Rabs (x - b2r cx) <= b2r rx -> Rabs (y - b2r cy) <= b2r ry ->
    Rabs (g x y - z) <= r)) ->
  let '(cw, rw) := (let '(cz, rz) := core in fixup_1 cz rz (add rx ry)) in
  ball_1 cw rw /\
  (ball_empty_1 cw rw <-> ball_empty_1 cx rx \/ ball_empty_1 cy ry) /\
  (ball_finite_1 cw rw ->
   (ball_finite_1 cx rx /\ ball_finite_1 cy ry) /\
   (forall x y : R, Rabs (x - b2r cx) <= b2r rx -> Rabs (y - b2r cy) <= b2r ry ->
    Rabs (g x y - b2r cw) <= b2r rw)).
Proof.
intros g core real cx rx cy ry Bx By Hcore Hreal.
generalize (ball_1_radius prec emax _ _ Bx) (ball_1_radius prec emax _ _ By). intros Hrx Hry.
assert (K : ~ (ball_empty_1 cx rx \/ ball_empty_1 cy ry) ->
  let '(cz, rz) := core in
  fin cz ->
  nonneg_ext rz /\
  (fin rz ->
   (ball_finite_1 cx rx /\ ball_finite_1 cy ry) /\
   (forall x y : R, Rabs (x - b2r cx) <= b2r rx -> Rabs (y - b2r cy) <= b2r ry ->
    Rabs (g x y - b2r cz) <= b2r rz))).
{ intros NE.
  assert (Nrx : is_nan prec emax rx = false).
  { destruct (is_nan prec emax rx) eqn:N; trivial. elim NE. left. now apply (ball_1_empty prec emax). }
  assert (Nry : is_nan prec emax ry = false).
  { destruct (is_nan prec emax ry) eqn:N; trivial. elim NE. right. now apply (ball_1_empty prec emax). }
  specialize (Hcore (ball_1_center prec emax _ _ Bx Nrx) (ball_1_center prec emax _ _ By Nry)).
  destruct core as [cz rz]. destruct Hcore as [Hrz Kc]. intros Fz. split. exact Hrz.
  intros Frz. destruct (Kc Fz Frz) as [Frx [Fry E]].
  specialize (Hreal (nonneg_ext_fin prec emax rx Hrx Frx) (nonneg_ext_fin prec emax ry Hry Fry)).
  rewrite <- E in Hreal. cbv beta iota in Hreal. destruct Hreal as [_ [_ C]].
  split; [split; now apply (ball_1_finite prec emax)|exact C]. }
revert K. destruct core as [cz rz]. intros K.
exact (ball_template_1 prec emax nan_abs cz rz (add rx ry) _ _
         (fun cw rw => forall x y : R, Rabs (x - b2r cx) <= b2r rx ->
            Rabs (y - b2r cy) <= b2r ry -> Rabs (g x y - b2r cw) <= b2r rw)
         (q_empty_1 prec emax nan_plus _ _ _ _ Bx By) K).
Qed.

(* One ball operand and a scalar a, center of two limbs. *)
Lemma full_2_scale :
  forall (core : float * float * float) (real : R * R * R) (cx0 cx1 rx a : float),
  ball_2 cx0 cx1 rx ->
  (fin cx0 -> fin cx1 -> normalized_2 emin prec (b2r cx0) (b2r cx1) ->
   let '(cz0, cz1, rz) := core in
   nonneg_ext rz /\
   (fin cz0 -> fin rz -> fin rx /\ fin a /\ fin cz1 /\ (b2r cz0, b2r cz1, b2r rz) = real)) ->
  (normalized_2 emin prec (b2r cx0) (b2r cx1) -> 0 <= b2r rx ->
   let '(z0, z1, r) := real in
   fmt emin prec r /\ normalized_2 emin prec z0 z1 /\
   (forall x : R, Rabs (x - (b2r cx0 + b2r cx1)) <= b2r rx ->
    Rabs (x * b2r a - (z0 + z1)) <= r)) ->
  let '(cw0, cw1, rw) := (let '(cz0, cz1, rz) := core in fixup_2 cz0 cz1 rz rx) in
  ball_2 cw0 cw1 rw /\
  (ball_empty_2 cw0 cw1 rw <-> ball_empty_2 cx0 cx1 rx) /\
  (ball_finite_2 cw0 cw1 rw ->
   (ball_finite_2 cx0 cx1 rx /\ fin a) /\
   (forall x : R, Rabs (x - (b2r cx0 + b2r cx1)) <= b2r rx ->
    Rabs (x * b2r a - (b2r cw0 + b2r cw1)) <= b2r rw)).
Proof.
intros core real cx0 cx1 rx a Bx Hcore Hreal.
generalize (ball_2_radius prec emax _ _ _ Bx). intros Hrx.
assert (K : ~ ball_empty_2 cx0 cx1 rx ->
  let '(cz0, cz1, rz) := core in
  fin cz0 ->
  nonneg_ext rz /\
  (fin rz ->
   (ball_finite_2 cx0 cx1 rx /\ fin a) /\ fin cz1 /\
   normalized_2 emin prec (b2r cz0) (b2r cz1) /\
   (forall x : R, Rabs (x - (b2r cx0 + b2r cx1)) <= b2r rx ->
    Rabs (x * b2r a - (b2r cz0 + b2r cz1)) <= b2r rz))).
{ intros NE.
  assert (Nrx : is_nan prec emax rx = false).
  { destruct (is_nan prec emax rx) eqn:N; trivial. elim NE. now apply (ball_2_empty prec emax). }
  destruct (ball_2_center prec emax _ _ _ Bx Nrx) as [F0 [F1 Nx]].
  specialize (Hcore F0 F1 Nx). specialize (Hreal Nx).
  destruct core as [[cz0 cz1] rz]. destruct Hcore as [Hrz Kc]. intros Fz0. split. exact Hrz.
  intros Frz. destruct (Kc Fz0 Frz) as [Frx [Fa [Fz1 E]]].
  specialize (Hreal (nonneg_ext_fin prec emax rx Hrx Frx)).
  rewrite <- E in Hreal. cbv beta iota in Hreal. destruct Hreal as [_ [Nz C]].
  split; [split; [now apply (ball_2_finite prec emax)|exact Fa]
         |split; [exact Fz1|split; [exact Nz|exact C]]]. }
revert K. destruct core as [[cz0 cz1] rz]. intros K.
exact (ball_template_2 prec emax nan_abs cz0 cz1 rz rx _ _
         (fun cw0 cw1 rw => forall x : R, Rabs (x - (b2r cx0 + b2r cx1)) <= b2r rx ->
            Rabs (x * b2r a - (b2r cw0 + b2r cw1)) <= b2r rw)
         (q_empty_scale_2 prec emax _ _ _ Bx) K).
Qed.

(* One ball operand and a scalar a, center of one limb. *)
Lemma full_1_scale :
  forall (core : float * float) (real : R * R) (cx rx a : float),
  ball_1 cx rx ->
  (fin cx ->
   let '(cz, rz) := core in
   nonneg_ext rz /\ (fin cz -> fin rz -> fin rx /\ fin a /\ (b2r cz, b2r rz) = real)) ->
  (0 <= b2r rx ->
   let '(z, r) := real in
   fmt emin prec z /\ fmt emin prec r /\
   (forall x : R, Rabs (x - b2r cx) <= b2r rx -> Rabs (x * b2r a - z) <= r)) ->
  let '(cw, rw) := (let '(cz, rz) := core in fixup_1 cz rz rx) in
  ball_1 cw rw /\
  (ball_empty_1 cw rw <-> ball_empty_1 cx rx) /\
  (ball_finite_1 cw rw ->
   (ball_finite_1 cx rx /\ fin a) /\
   (forall x : R, Rabs (x - b2r cx) <= b2r rx -> Rabs (x * b2r a - b2r cw) <= b2r rw)).
Proof.
intros core real cx rx a Bx Hcore Hreal.
generalize (ball_1_radius prec emax _ _ Bx). intros Hrx.
assert (K : ~ ball_empty_1 cx rx ->
  let '(cz, rz) := core in
  fin cz ->
  nonneg_ext rz /\
  (fin rz ->
   (ball_finite_1 cx rx /\ fin a) /\
   (forall x : R, Rabs (x - b2r cx) <= b2r rx -> Rabs (x * b2r a - b2r cz) <= b2r rz))).
{ intros NE.
  assert (Nrx : is_nan prec emax rx = false).
  { destruct (is_nan prec emax rx) eqn:N; trivial. elim NE. now apply (ball_1_empty prec emax). }
  specialize (Hcore (ball_1_center prec emax _ _ Bx Nrx)).
  destruct core as [cz rz]. destruct Hcore as [Hrz Kc]. intros Fz. split. exact Hrz.
  intros Frz. destruct (Kc Fz Frz) as [Frx [Fa E]].
  specialize (Hreal (nonneg_ext_fin prec emax rx Hrx Frx)).
  rewrite <- E in Hreal. cbv beta iota in Hreal. destruct Hreal as [_ [_ C]].
  split; [split; [now apply (ball_1_finite prec emax)|exact Fa]|exact C]. }
revert K. destruct core as [cz rz]. intros K.
exact (ball_template_1 prec emax nan_abs cz rz rx _ _
         (fun cw rw => forall x : R, Rabs (x - b2r cx) <= b2r rx ->
            Rabs (x * b2r a - b2r cw) <= b2r rw)
         (q_empty_scale_1 prec emax _ _ Bx) K).
Qed.

(** * The full kernels *)

Notation ball_add_1_full := (IeeeModel.ball_add_1_full prec emax nan_plus nan_abs nan_fma).
Notation ball_sub_1_full := (IeeeModel.ball_sub_1_full prec emax nan_plus nan_opp nan_abs nan_fma).
Notation ball_mul_1_full := (IeeeModel.ball_mul_1_full prec emax nan_plus nan_abs nan_fma).
Notation ball_scale_1_full := (IeeeModel.ball_scale_1_full prec emax nan_abs nan_fma).
Notation ball_add_2_full :=
  (IeeeModel.ball_add_2_full prec emax nan_plus nan_minus nan_abs nan_fma).
Notation ball_sub_2_full :=
  (IeeeModel.ball_sub_2_full prec emax nan_plus nan_minus nan_opp nan_abs nan_fma).
Notation ball_mul_2_full :=
  (IeeeModel.ball_mul_2_full prec emax nan_plus nan_minus nan_opp nan_abs nan_fma).
Notation ball_scale_2_full :=
  (IeeeModel.ball_scale_2_full prec emax nan_plus nan_minus nan_opp nan_abs nan_fma).

Lemma ball_add_1_full_facts :
  (2 <= prec)%Z ->
  forall cx rx cy ry : float, ball_1 cx rx -> ball_1 cy ry ->
  let '(cw, rw) := ball_add_1_full cx rx cy ry in
  ball_1 cw rw /\
  (ball_empty_1 cw rw <-> ball_empty_1 cx rx \/ ball_empty_1 cy ry) /\
  (ball_finite_1 cw rw ->
   (ball_finite_1 cx rx /\ ball_finite_1 cy ry) /\
   (forall x y : R, Rabs (x - b2r cx) <= b2r rx -> Rabs (y - b2r cy) <= b2r ry ->
    Rabs ((x + y) - b2r cw) <= b2r rw)).
Proof.
intros Hp cx rx cy ry Bx By.
exact (full_1_two Rplus (ball_add_1 cx rx cy ry) _ cx rx cy ry Bx By
         (fun Fx Fy => ball_add_1_core Hp cx rx cy ry Fx Fy
            (ball_1_radius prec emax _ _ Bx) (ball_1_radius prec emax _ _ By))
         (fun Px Py => Ball2.ball_add_1_correct emin prec ltac:(lia) _ _ _ _
            (b2r_format prec emax cx) (b2r_format prec emax rx)
            (b2r_format prec emax cy) (b2r_format prec emax ry) Px Py)).
Qed.

Lemma ball_sub_1_full_facts :
  (2 <= prec)%Z ->
  forall cx rx cy ry : float, ball_1 cx rx -> ball_1 cy ry ->
  let '(cw, rw) := ball_sub_1_full cx rx cy ry in
  ball_1 cw rw /\
  (ball_empty_1 cw rw <-> ball_empty_1 cx rx \/ ball_empty_1 cy ry) /\
  (ball_finite_1 cw rw ->
   (ball_finite_1 cx rx /\ ball_finite_1 cy ry) /\
   (forall x y : R, Rabs (x - b2r cx) <= b2r rx -> Rabs (y - b2r cy) <= b2r ry ->
    Rabs ((x - y) - b2r cw) <= b2r rw)).
Proof.
intros Hp cx rx cy ry Bx By.
exact (full_1_two Rminus (ball_sub_1 cx rx cy ry) _ cx rx cy ry Bx By
         (fun Fx Fy => ball_sub_1_core Hp cx rx cy ry Fx Fy
            (ball_1_radius prec emax _ _ Bx) (ball_1_radius prec emax _ _ By))
         (fun Px Py => Ball2.ball_sub_1_correct emin prec ltac:(lia) _ _ _ _
            (b2r_format prec emax cx) (b2r_format prec emax rx)
            (b2r_format prec emax cy) (b2r_format prec emax ry) Px Py)).
Qed.

Lemma ball_mul_1_full_facts :
  (2 <= prec)%Z ->
  forall cx rx cy ry : float, ball_1 cx rx -> ball_1 cy ry ->
  let '(cw, rw) := ball_mul_1_full cx rx cy ry in
  ball_1 cw rw /\
  (ball_empty_1 cw rw <-> ball_empty_1 cx rx \/ ball_empty_1 cy ry) /\
  (ball_finite_1 cw rw ->
   (ball_finite_1 cx rx /\ ball_finite_1 cy ry) /\
   (forall x y : R, Rabs (x - b2r cx) <= b2r rx -> Rabs (y - b2r cy) <= b2r ry ->
    Rabs ((x * y) - b2r cw) <= b2r rw)).
Proof.
intros Hp cx rx cy ry Bx By.
exact (full_1_two Rmult (ball_mul_1 cx rx cy ry) _ cx rx cy ry Bx By
         (fun Fx Fy => ball_mul_1_core Hp cx rx cy ry Fx Fy
            (ball_1_radius prec emax _ _ Bx) (ball_1_radius prec emax _ _ By))
         (fun Px Py => Ball2.ball_mul_1_correct emin prec ltac:(lia) _ _ _ _
            (b2r_format prec emax cx) (b2r_format prec emax rx)
            (b2r_format prec emax cy) (b2r_format prec emax ry) Px Py)).
Qed.

Lemma ball_scale_1_full_facts :
  (2 <= prec)%Z ->
  forall cx rx a : float, ball_1 cx rx ->
  let '(cw, rw) := ball_scale_1_full cx rx a in
  ball_1 cw rw /\
  (ball_empty_1 cw rw <-> ball_empty_1 cx rx) /\
  (ball_finite_1 cw rw ->
   (ball_finite_1 cx rx /\ fin a) /\
   (forall x : R, Rabs (x - b2r cx) <= b2r rx -> Rabs (x * b2r a - b2r cw) <= b2r rw)).
Proof.
intros Hp cx rx a Bx.
exact (full_1_scale (ball_scale_1 cx rx a) _ cx rx a Bx
         (fun Fx => ball_scale_1_core Hp cx rx a Fx (ball_1_radius prec emax _ _ Bx))
         (fun Px => Ball2.ball_scale_1_correct emin prec ltac:(lia) _ _ _
            (b2r_format prec emax cx) (b2r_format prec emax rx) (b2r_format prec emax a) Px)).
Qed.

Lemma ball_add_2_full_facts :
  (3 <= prec)%Z ->
  forall cx0 cx1 rx cy0 cy1 ry : float, ball_2 cx0 cx1 rx -> ball_2 cy0 cy1 ry ->
  let '(cw0, cw1, rw) := ball_add_2_full cx0 cx1 rx cy0 cy1 ry in
  ball_2 cw0 cw1 rw /\
  (ball_empty_2 cw0 cw1 rw <-> ball_empty_2 cx0 cx1 rx \/ ball_empty_2 cy0 cy1 ry) /\
  (ball_finite_2 cw0 cw1 rw ->
   (ball_finite_2 cx0 cx1 rx /\ ball_finite_2 cy0 cy1 ry) /\
   (forall x y : R, Rabs (x - (b2r cx0 + b2r cx1)) <= b2r rx ->
    Rabs (y - (b2r cy0 + b2r cy1)) <= b2r ry -> Rabs ((x + y) - (b2r cw0 + b2r cw1)) <= b2r rw)).
Proof.
intros Hp cx0 cx1 rx cy0 cy1 ry Bx By.
exact (full_2_two Rplus (ball_add_2 cx0 cx1 rx cy0 cy1 ry) _ cx0 cx1 rx cy0 cy1 ry Bx By
         (fun F0 F1 G0 G1 Nx Ny => ball_add_2_core Hp cx0 cx1 rx cy0 cy1 ry F0 F1 G0 G1 Nx Ny
            (ball_2_radius prec emax _ _ _ Bx) (ball_2_radius prec emax _ _ _ By))
         (fun Nx Ny Px Py => Ball2.ball_add_2_correct emin prec Hp _ _ _ _ _ _ Nx
            (b2r_format prec emax rx) Ny (b2r_format prec emax ry) Px Py)).
Qed.

Lemma ball_sub_2_full_facts :
  (3 <= prec)%Z ->
  forall cx0 cx1 rx cy0 cy1 ry : float, ball_2 cx0 cx1 rx -> ball_2 cy0 cy1 ry ->
  let '(cw0, cw1, rw) := ball_sub_2_full cx0 cx1 rx cy0 cy1 ry in
  ball_2 cw0 cw1 rw /\
  (ball_empty_2 cw0 cw1 rw <-> ball_empty_2 cx0 cx1 rx \/ ball_empty_2 cy0 cy1 ry) /\
  (ball_finite_2 cw0 cw1 rw ->
   (ball_finite_2 cx0 cx1 rx /\ ball_finite_2 cy0 cy1 ry) /\
   (forall x y : R, Rabs (x - (b2r cx0 + b2r cx1)) <= b2r rx ->
    Rabs (y - (b2r cy0 + b2r cy1)) <= b2r ry -> Rabs ((x - y) - (b2r cw0 + b2r cw1)) <= b2r rw)).
Proof.
intros Hp cx0 cx1 rx cy0 cy1 ry Bx By.
exact (full_2_two Rminus (ball_sub_2 cx0 cx1 rx cy0 cy1 ry) _ cx0 cx1 rx cy0 cy1 ry Bx By
         (fun F0 F1 G0 G1 Nx Ny => ball_sub_2_core Hp cx0 cx1 rx cy0 cy1 ry F0 F1 G0 G1 Nx Ny
            (ball_2_radius prec emax _ _ _ Bx) (ball_2_radius prec emax _ _ _ By))
         (fun Nx Ny Px Py => Ball2.ball_sub_2_correct emin prec Hp _ _ _ _ _ _ Nx
            (b2r_format prec emax rx) Ny (b2r_format prec emax ry) Px Py)).
Qed.

Lemma ball_mul_2_full_facts :
  (4 <= prec)%Z ->
  forall cx0 cx1 rx cy0 cy1 ry : float, ball_2 cx0 cx1 rx -> ball_2 cy0 cy1 ry ->
  let '(cw0, cw1, rw) := ball_mul_2_full cx0 cx1 rx cy0 cy1 ry in
  ball_2 cw0 cw1 rw /\
  (ball_empty_2 cw0 cw1 rw <-> ball_empty_2 cx0 cx1 rx \/ ball_empty_2 cy0 cy1 ry) /\
  (ball_finite_2 cw0 cw1 rw ->
   (ball_finite_2 cx0 cx1 rx /\ ball_finite_2 cy0 cy1 ry) /\
   (forall x y : R, Rabs (x - (b2r cx0 + b2r cx1)) <= b2r rx ->
    Rabs (y - (b2r cy0 + b2r cy1)) <= b2r ry -> Rabs ((x * y) - (b2r cw0 + b2r cw1)) <= b2r rw)).
Proof.
intros Hp cx0 cx1 rx cy0 cy1 ry Bx By.
exact (full_2_two Rmult (ball_mul_2 cx0 cx1 rx cy0 cy1 ry) _ cx0 cx1 rx cy0 cy1 ry Bx By
         (fun F0 F1 G0 G1 Nx Ny => ball_mul_2_core Hp cx0 cx1 rx cy0 cy1 ry F0 F1 G0 G1 Nx Ny
            (ball_2_radius prec emax _ _ _ Bx) (ball_2_radius prec emax _ _ _ By))
         (fun Nx Ny Px Py => Ball2.ball_mul_2_correct emin prec Hp _ _ _ _ _ _ Nx
            (b2r_format prec emax rx) Ny (b2r_format prec emax ry) Px Py)).
Qed.

Lemma ball_scale_2_full_facts :
  (2 <= prec)%Z ->
  forall cx0 cx1 rx a : float, ball_2 cx0 cx1 rx ->
  let '(cw0, cw1, rw) := ball_scale_2_full cx0 cx1 rx a in
  ball_2 cw0 cw1 rw /\
  (ball_empty_2 cw0 cw1 rw <-> ball_empty_2 cx0 cx1 rx) /\
  (ball_finite_2 cw0 cw1 rw ->
   (ball_finite_2 cx0 cx1 rx /\ fin a) /\
   (forall x : R, Rabs (x - (b2r cx0 + b2r cx1)) <= b2r rx ->
    Rabs (x * b2r a - (b2r cw0 + b2r cw1)) <= b2r rw)).
Proof.
intros Hp cx0 cx1 rx a Bx.
exact (full_2_scale (ball_scale_2 cx0 cx1 rx a) _ cx0 cx1 rx a Bx
         (fun F0 F1 Nx => ball_scale_2_core Hp cx0 cx1 rx a F0 F1 Nx
            (ball_2_radius prec emax _ _ _ Bx))
         (fun Nx Px => Ball2.ball_scale_2_correct emin prec Hp _ _ _ _ Nx
            (b2r_format prec emax rx) (b2r_format prec emax a) Px)).
Qed.

(** * ball_neg_k: no fix-up *)

Lemma ball_neg_1_facts :
  forall cx rx : float, ball_1 cx rx ->
  ball_1 (neg cx) rx /\
  (ball_empty_1 (neg cx) rx <-> ball_empty_1 cx rx) /\
  (ball_finite_1 (neg cx) rx ->
   ball_finite_1 cx rx /\
   (forall x : R, Rabs (x - b2r cx) <= b2r rx -> Rabs (- x - b2r (neg cx)) <= b2r rx)).
Proof.
intros cx rx Bx.
assert (En : b2r (neg cx) = - b2r cx) by apply B2R_Bopp.
assert (Fn : is_finite prec emax (neg cx) = is_finite prec emax cx) by apply is_finite_Bopp.
split; [|split].
- destruct Bx as [[F [Fr P]]|[[[s E] Er]|[N Nr]]].
  + left. unfold ball_finite_1, finite. rewrite Fn. split; [exact F|split; assumption].
  + right. left. split; [|exact Er]. rewrite E. now exists (negb s).
  + right. right. split; [|exact Nr]. unfold nan in *.
    destruct cx; try discriminate N. reflexivity.
- split.
  + intros [_ Nr]. now apply (ball_1_empty prec emax).
  + intros [N Nr]. split; [|exact Nr]. unfold nan in *.
    destruct cx; try discriminate N. reflexivity.
- intros [_ [Fr _]]. split. now apply (ball_1_finite prec emax).
  intros x Hx. rewrite En. replace (- x - - b2r cx) with (- (x - b2r cx)) by ring.
  now rewrite Rabs_Ropp.
Qed.

Lemma ball_neg_2_facts :
  forall cx0 cx1 rx : float, ball_2 cx0 cx1 rx ->
  ball_2 (neg cx0) (neg cx1) rx /\
  (ball_empty_2 (neg cx0) (neg cx1) rx <-> ball_empty_2 cx0 cx1 rx) /\
  (ball_finite_2 (neg cx0) (neg cx1) rx ->
   ball_finite_2 cx0 cx1 rx /\
   (forall x : R, Rabs (x - (b2r cx0 + b2r cx1)) <= b2r rx ->
    Rabs (- x - (b2r (neg cx0) + b2r (neg cx1))) <= b2r rx)).
Proof.
intros cx0 cx1 rx Bx.
assert (E0 : b2r (neg cx0) = - b2r cx0) by apply B2R_Bopp.
assert (E1 : b2r (neg cx1) = - b2r cx1) by apply B2R_Bopp.
assert (F0 : is_finite prec emax (neg cx0) = is_finite prec emax cx0) by apply is_finite_Bopp.
assert (F1 : is_finite prec emax (neg cx1) = is_finite prec emax cx1) by apply is_finite_Bopp.
split; [|split].
- destruct Bx as [[G0 [G1 [N [Fr P]]]]|[[[s0 Z0] [[s1 Z1] Er]]|[N0 [N1 Nr]]]].
  + left. unfold ball_finite_2, finite, val. rewrite F0, F1, E0, E1.
    split; [exact G0|split; [exact G1|split; [now apply normalized_2_opp|split; assumption]]].
  + right. left. rewrite Z0, Z1.
    split; [now exists (negb s0)|split; [now exists (negb s1)|exact Er]].
  + right. right. unfold nan in *. split; [|split; [|exact Nr]].
    * destruct cx0; try discriminate N0. reflexivity.
    * destruct cx1; try discriminate N1. reflexivity.
- split.
  + intros [_ [_ Nr]]. now apply (ball_2_empty prec emax).
  + intros [N0 [N1 Nr]]. unfold nan in *. split; [|split; [|exact Nr]].
    * destruct cx0; try discriminate N0. reflexivity.
    * destruct cx1; try discriminate N1. reflexivity.
- intros [_ [_ [_ [Fr _]]]]. split. now apply (ball_2_finite prec emax).
  intros x Hx. rewrite E0, E1.
  replace (- x - (- b2r cx0 + - b2r cx1)) with (- (x - (b2r cx0 + b2r cx1))) by ring.
  now rewrite Rabs_Ropp.
Qed.

End IeeeBallCores.

(** * The statements of proofs/gen/IeeeStatements.v *)

Theorem ball_add_1_full_correct : ball_add_1_full_spec.
Proof.
intros prec emax Hp He nan_plus nan_abs nan_fma Hp2 cx rx cy ry Bx By.
generalize (ball_add_1_full_facts prec emax nan_plus nan_abs nan_fma Hp2 cx rx cy ry Bx By).
destruct (IeeeModel.ball_add_1_full prec emax nan_plus nan_abs nan_fma cx rx cy ry) as [cw rw].
intros [B1 [B2 B3]].
split; [exact B1|split; [exact B2|split]].
- intros Fw. destruct (B3 Fw) as [[Fx Fy] C]. split; [exact Fx|split; [exact Fy|exact C]].
- exact (every_case_1 prec emax Rplus _ _ _ _ _ _ B1 B2 B3).
Qed.

Theorem ball_sub_1_full_correct : ball_sub_1_full_spec.
Proof.
intros prec emax Hp He nan_plus nan_opp nan_abs nan_fma Hp2 cx rx cy ry Bx By.
generalize (ball_sub_1_full_facts prec emax nan_plus nan_opp nan_abs nan_fma Hp2 cx rx cy ry Bx By).
destruct (IeeeModel.ball_sub_1_full prec emax nan_plus nan_opp nan_abs nan_fma cx rx cy ry) as [cw rw].
intros [B1 [B2 B3]].
split; [exact B1|split; [exact B2|split]].
- intros Fw. destruct (B3 Fw) as [[Fx Fy] C]. split; [exact Fx|split; [exact Fy|exact C]].
- exact (every_case_1 prec emax Rminus _ _ _ _ _ _ B1 B2 B3).
Qed.

Theorem ball_mul_1_full_correct : ball_mul_1_full_spec.
Proof.
intros prec emax Hp He nan_plus nan_abs nan_fma Hp2 cx rx cy ry Bx By.
generalize (ball_mul_1_full_facts prec emax nan_plus nan_abs nan_fma Hp2 cx rx cy ry Bx By).
destruct (IeeeModel.ball_mul_1_full prec emax nan_plus nan_abs nan_fma cx rx cy ry) as [cw rw].
intros [B1 [B2 B3]].
split; [exact B1|split; [exact B2|split]].
- intros Fw. destruct (B3 Fw) as [[Fx Fy] C]. split; [exact Fx|split; [exact Fy|exact C]].
- exact (every_case_1 prec emax Rmult _ _ _ _ _ _ B1 B2 B3).
Qed.

Theorem ball_scale_1_full_correct : ball_scale_1_full_spec.
Proof.
intros prec emax Hp He nan_abs nan_fma Hp2 cx rx a Bx.
generalize (ball_scale_1_full_facts prec emax nan_abs nan_fma Hp2 cx rx a Bx).
destruct (IeeeModel.ball_scale_1_full prec emax nan_abs nan_fma cx rx a) as [cw rw].
intros [B1 [B2 B3]].
split; [exact B1|split; [exact B2|split]].
- intros Fw. destruct (B3 Fw) as [[Fx Fa] C]. split; [exact Fx|split; [exact Fa|exact C]].
- intros Fa. apply (every_case_scale_1 prec emax (fun x : R => x * val a) _ _ _ _ B1 B2).
  intros Fw. destruct (B3 Fw) as [[Fx _] C]. split; [exact Fx|exact C].
Qed.

Theorem ball_add_2_full_correct : ball_add_2_full_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_abs nan_fma Hpm cx0 cx1 rx cy0 cy1 ry Bx By.
generalize (ball_add_2_full_facts prec emax nan_plus nan_minus (fun x => nan_plus x x) nan_abs nan_fma Hpm cx0 cx1 rx cy0 cy1 ry Bx By).
destruct (IeeeModel.ball_add_2_full prec emax nan_plus nan_minus nan_abs nan_fma cx0 cx1 rx cy0 cy1 ry) as [[cw0 cw1] rw].
intros [B1 [B2 B3]].
split; [exact B1|split; [exact B2|split]].
- intros Fw. destruct (B3 Fw) as [[Fx Fy] C]. split; [exact Fx|split; [exact Fy|exact C]].
- exact (every_case_2 prec emax Rplus _ _ _ _ _ _ _ _ _ B1 B2 B3).
Qed.

Theorem ball_sub_2_full_correct : ball_sub_2_full_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma Hpm cx0 cx1 rx cy0 cy1 ry Bx By.
generalize (ball_sub_2_full_facts prec emax nan_plus nan_minus nan_opp nan_abs nan_fma Hpm cx0 cx1 rx cy0 cy1 ry Bx By).
destruct (IeeeModel.ball_sub_2_full prec emax nan_plus nan_minus nan_opp nan_abs nan_fma cx0 cx1 rx cy0 cy1 ry) as [[cw0 cw1] rw].
intros [B1 [B2 B3]].
split; [exact B1|split; [exact B2|split]].
- intros Fw. destruct (B3 Fw) as [[Fx Fy] C]. split; [exact Fx|split; [exact Fy|exact C]].
- exact (every_case_2 prec emax Rminus _ _ _ _ _ _ _ _ _ B1 B2 B3).
Qed.

Theorem ball_mul_2_full_correct : ball_mul_2_full_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma Hpm cx0 cx1 rx cy0 cy1 ry Bx By.
generalize (ball_mul_2_full_facts prec emax nan_plus nan_minus nan_opp nan_abs nan_fma Hpm cx0 cx1 rx cy0 cy1 ry Bx By).
destruct (IeeeModel.ball_mul_2_full prec emax nan_plus nan_minus nan_opp nan_abs nan_fma cx0 cx1 rx cy0 cy1 ry) as [[cw0 cw1] rw].
intros [B1 [B2 B3]].
split; [exact B1|split; [exact B2|split]].
- intros Fw. destruct (B3 Fw) as [[Fx Fy] C]. split; [exact Fx|split; [exact Fy|exact C]].
- exact (every_case_2 prec emax Rmult _ _ _ _ _ _ _ _ _ B1 B2 B3).
Qed.

Theorem ball_scale_2_full_correct : ball_scale_2_full_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma Hp2 cx0 cx1 rx a Bx.
generalize (ball_scale_2_full_facts prec emax nan_plus nan_minus nan_opp nan_abs nan_fma Hp2
              cx0 cx1 rx a Bx).
destruct (IeeeModel.ball_scale_2_full prec emax nan_plus nan_minus nan_opp nan_abs nan_fma
            cx0 cx1 rx a) as [[cw0 cw1] rw].
intros [B1 [B2 B3]].
split; [exact B1|split; [exact B2|split]].
- intros Fw. destruct (B3 Fw) as [[Fx Fa] C]. split; [exact Fx|split; [exact Fa|exact C]].
- intros Fa. apply (every_case_scale_2 prec emax (fun x : R => x * val a) _ _ _ _ _ _ B1 B2).
  intros Fw. destruct (B3 Fw) as [[Fx _] C]. split; [exact Fx|exact C].
Qed.

Theorem ball_neg_1_ieee_correct : ball_neg_1_ieee_spec.
Proof.
intros prec emax Hp He nan_opp _ cx rx Bx.
unfold IeeeModel.ball_neg_1. cbv zeta.
destruct (ball_neg_1_facts prec emax nan_opp cx rx Bx) as [B1 [B2 B3]].
split; [exact B1|split; [exact B2|split; [exact B3|]]].
exact (every_case_scale_1 prec emax Ropp _ _ _ _ B1 B2 B3).
Qed.

Theorem ball_neg_2_ieee_correct : ball_neg_2_ieee_spec.
Proof.
intros prec emax Hp He nan_opp _ cx0 cx1 rx Bx.
unfold IeeeModel.ball_neg_2, IeeeModel.neg_2. cbv beta iota zeta.
destruct (ball_neg_2_facts prec emax nan_opp cx0 cx1 rx Bx) as [B1 [B2 B3]].
split; [exact B1|split; [exact B2|split; [exact B3|]]].
exact (every_case_scale_2 prec emax Ropp _ _ _ _ _ _ B1 B2 B3).
Qed.
