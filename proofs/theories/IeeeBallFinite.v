(* The full Ball kernels in the IEEE model: when the result is a finite ball (statement
   B4 of milestone1.md, "Ball kernels"), and the statements of the eight full kernels.

   B1 to B3 (IeeeBallCores.v) say what a full Ball kernel returns, but not that it ever
   returns a finite ball: the whole line contains everything, so a kernel that always
   returned it would satisfy them. B4 is the missing guarantee. For finite operands,

     ball_add_k, ball_sub_k   |cx o cy| + rx + ry           <= 2^(emax - 2)
     ball_scale_k             (|cx| + rx) |a|               <= 2^(emax - 2)
     ball_mul_2               (|cx| + rx) (|cy| + ry)       <= 2^(emax - 2)
     ball_mul_1               (|cx| + rx) (|cy| + ry)       <= 2^(emax - 4)

   give a finite ball. The left sides are the largest magnitude of x o y over the
   operands, so each condition reads: no member of the exact result exceeds a quarter
   (for ball_mul_1, a sixteenth) of the overflow threshold 2^emax.

   Why it holds. A core computes a center and then a radius by a chain of operations
   on nonnegative numbers, each rounded to nearest (Ball2.v):

     sum, scaling   s = RN (X)                  X = rx + ry, or |a| rx
                    t = RN (az E + s)           az the magnitude of the leading limb
                    rz = RN (t G + H)           of the center
     product        p = RN (rx ry), q = RN (ay rx + p), w = RN (ax ry + q)
                    t = RN (az E + w), rz = RN (t G + H)

   An operation of the IEEE model returns a finite number exactly when its rounded
   real result is below 2^emax (IeeeBridge.v), so "finite" is a bound on real numbers.
   - The center is finite by the threshold of its own kernel (IeeeFinite.v,
     IeeeMul22.v), or because it is one rounding of a number below the bound.
   - With B = 2^e the bound of the condition, the exact value that t evaluates is at
     most B, and each rounding adds at most half a unit in the last place. A value
     below B + half the gap above B rounds to at most B (rnd_le_bpow_mid): this is
     what keeps t at B for sums and scalings (chain2_le), and at the next number
     above B for ball_mul_1 (chain3_le and rnd_le_succ_bpow_mid). For ball_mul_2 the
     leading limbs of the centers stand for the centers, which costs a factor up to
     4/3, and t is at most 2 B (radius4_range_2).
   - The last operation multiplies by G and adds H. From the definitions of the
     constants: G <= 2 for sums and scalings, 4 for ball_mul_1 and 3/2 for ball_mul_2;
     H is at most 4 N, and 6 N for ball_mul_1, with N = 2^(2 - emax) the smallest normal
     number. So t G + H is at most 3/4 of 2^emax (7/8 for ball_mul_2), a number of the
     format below 2^emax.
   The bounds on G and H are those of the smallest formats (two bits of precision,
   emax = 3), which the statements include: there G = 4 and H = 3/8 of 2^emax for
   ball_mul_1, and that is why its condition is a sixteenth and not a quarter. The
   conditions are sufficient, not necessary: the smallest operands for which a result
   is the whole line, found by enumerating small formats, are in milestone1.md.

   Contents: rounding to nearest near a power of two; the chains; the constants; the
   radius of each core in range; each core finite under its condition; B4 for the full
   kernels; and the statements, in the form of proofs/gen/IeeeStatements.v, at the
   end. *)
From Stdlib Require Import Reals ZArith List Arith Bool Lia Lra Psatz.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements IeeeStatements.
From Kairn Require Import Format Normalized Sign Program IeeeBridge IeeeEFT
  IeeeAdd22 IeeeMul22 IeeeMore IeeeVocabulary IeeeOps IeeeFinite IeeeBall IeeeBallCores.
From Kairn Require Ball2 IeeeOperations.
From Kairn.Gen Require IeeeModel.
Import ListNotations.
Open Scope R_scope.

(** * Real-number facts *)

Lemma half_bpow : forall e : Z, bpow radix2 (e - 1) = / 2 * bpow radix2 e.
Proof.
intros e. replace (e - 1)%Z with (-1 + e)%Z by ring. rewrite bpow_plus, pow2_m1. reflexivity.
Qed.

Lemma two_bpow : forall e : Z, bpow radix2 (e + 1) = 2 * bpow radix2 e.
Proof.
intros e. replace (e + 1)%Z with (1 + e)%Z by ring. rewrite bpow_plus, pow2_1. reflexivity.
Qed.

(* |z| <= |v| + |z - v|. *)
Lemma Rabs_le_plus_err : forall z v : R, Rabs z <= Rabs v + Rabs (z - v).
Proof.
intros z v. unfold Rabs. destruct (Rcase_abs z), (Rcase_abs v), (Rcase_abs (z - v)); lra.
Qed.

(* Uq, times a factor up to 5/4, is at most 1/2; and at most 1/4 for the one-limb
   kernels, whose relative error is at most 1/5. *)
Lemma uq_le_half :
  forall rel k : R, 0 <= rel <= / 4 -> 1 <= k <= 5 / 4 -> 0 <= Ball2.uq rel * k <= / 2.
Proof.
intros rel k [R0 R1] [K0 K1]. unfold Ball2.uq.
assert (I : 0 < / (1 - rel)) by (apply Rinv_0_lt_compat; lra).
assert (Q0 : 0 <= rel / (1 - rel)) by (unfold Rdiv; apply Rmult_le_pos; lra).
assert (Q1 : rel / (1 - rel) <= / 3).
{ apply Rmult_le_reg_r with (1 - rel). lra.
  unfold Rdiv. rewrite Rmult_assoc, Rinv_l by lra. lra. }
nra.
Qed.

Lemma uq_le_quarter : forall rel : R, 0 <= rel <= / 5 -> 0 <= Ball2.uq rel <= / 4.
Proof.
intros rel [R0 R1]. unfold Ball2.uq.
assert (I : 0 < / (1 - rel)) by (apply Rinv_0_lt_compat; lra).
split.
- unfold Rdiv. apply Rmult_le_pos; lra.
- apply Rmult_le_reg_r with (1 - rel). lra.
  unfold Rdiv. rewrite Rmult_assoc, Rinv_l by lra. lra.
Qed.

Lemma rel_1_fifth : forall prec : Z, (2 <= prec)%Z -> 0 <= 1 / (1 + u prec) * u prec ^ 1 <= / 5.
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

Section IeeeBallFinite.
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
Notation inrange := (inrange emax).
Notation add := (IeeeOperations.add prec emax nan_plus).
Notation neg := (IeeeOperations.neg prec emax nan_opp).
Notation fabs := (IeeeOperations.abs prec emax nan_abs).
Notation fma := (IeeeOperations.fma prec emax nan_fma).
Notation prod := (IeeeOperations.prod prec emax nan_fma).
Notation fixup_1 := (IeeeBall.ball_fixup_1 prec emax nan_abs).
Notation fixup_2 := (IeeeBall.ball_fixup_2 prec emax nan_abs).

Let Hprec : (0 < prec)%Z.
Proof. exact prec_gt_0_. Qed.
Let Hemax : (prec < emax)%Z.
Proof. exact prec_lt_emax_. Qed.

(** * Rounding to nearest near a power of two *)

Lemma format_bpow : forall e : Z, (emin <= e)%Z -> format (bpow radix2 e).
Proof. intros e He. apply generic_format_bpow. unfold FLT_exp. lia. Qed.

Lemma rnd_pos : forall x : R, 0 <= x -> 0 <= rnd x.
Proof.
intros x Hx. apply round_ge_generic; auto with typeclass_instances. apply generic_format_0.
Qed.

(* Rounding does not cross a number of the format. *)
Lemma rnd_le_format : forall x y : R, format y -> x <= y -> rnd x <= y.
Proof. intros x y Fy H. apply round_le_generic; auto with typeclass_instances. Qed.

(* Up to 2^e, in the normal range, a rounding moves a number by at most 2^(e - prec - 1):
   half a unit in the last place of the numbers just below 2^e. *)
Lemma abs_rnd_le_half :
  forall (x : R) (e : Z), (emin + prec <= e)%Z -> Rabs x <= bpow radix2 e ->
  Rabs (rnd x) <= Rabs x + bpow radix2 (e - prec - 1).
Proof.
intros x e He Hx.
generalize (round_error_bpow emin prec tie_even x e Hx).
rewrite Z.max_l by lia. rewrite <- (half_bpow (e - prec)). intros K.
generalize (Rabs_le_plus_err (rnd x) x). lra.
Qed.

Lemma rnd_le_half :
  forall (x : R) (e : Z), (emin + prec <= e)%Z -> 0 <= x <= bpow radix2 e ->
  rnd x <= x + bpow radix2 (e - prec - 1).
Proof.
intros x e He [H0 H1].
assert (K : Rabs (rnd x) <= Rabs x + bpow radix2 (e - prec - 1)).
{ apply abs_rnd_le_half; trivial. now rewrite Rabs_pos_eq. }
rewrite (Rabs_pos_eq x H0) in K. apply Rle_trans with (2 := K). apply Rle_abs.
Qed.

(* The number of the format just above 2^e is 2^e + 2 * 2^(e - prec). *)
Lemma succ_bpow_eq :
  forall e : Z, (emin + prec <= e + 1)%Z ->
  succ radix2 fexp (bpow radix2 e) = bpow radix2 e + 2 * bpow radix2 (e - prec).
Proof.
intros e He. rewrite succ_eq_pos by apply bpow_ge_0. rewrite ulp_bpow.
replace (fexp (e + 1)) with (e - prec + 1)%Z by (unfold FLT_exp; lia).
now rewrite two_bpow.
Qed.

Lemma format_succ_bpow :
  forall e : Z, (emin + prec <= e + 1)%Z -> format (bpow radix2 e + 2 * bpow radix2 (e - prec)).
Proof.
intros e He. rewrite <- succ_bpow_eq by exact He.
apply generic_format_succ; auto with typeclass_instances. apply format_bpow. lia.
Qed.

(* Below the midpoint of 2^e and the next number, a number rounds to at most 2^e. *)
Lemma rnd_le_bpow_mid :
  forall (x : R) (e : Z), (emin + prec <= e + 1)%Z ->
  x < bpow radix2 e + bpow radix2 (e - prec) -> rnd x <= bpow radix2 e.
Proof.
intros x e He Hx.
assert (FB : format (bpow radix2 e)) by (apply format_bpow; lia).
apply round_N_le_midp; auto with typeclass_instances.
rewrite succ_bpow_eq by exact He. lra.
Qed.

(* The same one number higher: below the midpoint of the two numbers that follow 2^e. *)
Lemma rnd_le_succ_bpow_mid :
  (2 <= prec)%Z -> forall (x : R) (e : Z), (emin + prec <= e + 1)%Z ->
  x < bpow radix2 e + 3 * bpow radix2 (e - prec) ->
  rnd x <= bpow radix2 e + 2 * bpow radix2 (e - prec).
Proof.
intros Hp x e He Hx.
assert (D0 : 0 < bpow radix2 (e - prec)) by apply bpow_gt_0.
assert (B0 : 0 < bpow radix2 e) by apply bpow_gt_0.
assert (DB : 4 * bpow radix2 (e - prec) <= bpow radix2 e).
{ change 4 with (bpow radix2 2). rewrite <- bpow_plus. apply bpow_le. lia. }
assert (FS : format (bpow radix2 e + 2 * bpow radix2 (e - prec))) by now apply format_succ_bpow.
assert (EU : ulp radix2 fexp (bpow radix2 e + 2 * bpow radix2 (e - prec))
             = 2 * bpow radix2 (e - prec)).
{ rewrite ulp_neq_0 by lra. unfold cexp.
  replace (mag radix2 (bpow radix2 e + 2 * bpow radix2 (e - prec)) : Z) with (e + 1)%Z.
  - replace (fexp (e + 1)) with (e - prec + 1)%Z by (unfold FLT_exp; lia). apply two_bpow.
  - symmetry. apply mag_unique_pos. replace (e + 1 - 1)%Z with e by ring.
    rewrite (two_bpow e). lra. }
apply round_N_le_midp; auto with typeclass_instances.
rewrite succ_eq_pos by lra. rewrite EU. lra.
Qed.

(** * The chains *)

(* Two roundings, for a sum X + Y that exceeds B = 2^e by less than half a unit in the
   last place below B: both values stay at most B. *)
Lemma chain2_le :
  forall (X Y : R) (e : Z), (emin + prec <= e)%Z ->
  0 <= X <= bpow radix2 e -> 0 <= Y ->
  X + Y < bpow radix2 e + bpow radix2 (e - prec - 1) ->
  0 <= rnd X <= bpow radix2 e /\ 0 <= rnd (Y + rnd X) <= bpow radix2 e.
Proof.
intros X Y e He [X0 X1] Y0 HS.
assert (FB : format (bpow radix2 e)) by (apply format_bpow; lia).
assert (S0 : 0 <= rnd X) by now apply rnd_pos.
assert (S1 : rnd X <= bpow radix2 e) by now apply rnd_le_format.
assert (S2 : rnd X <= X + bpow radix2 (e - prec - 1))
  by (apply rnd_le_half; [exact He|split; assumption]).
split. split; assumption.
split. apply rnd_pos. lra.
apply rnd_le_bpow_mid. lia.
generalize (half_bpow (e - prec)) (bpow_gt_0 radix2 (e - prec)). lra.
Qed.

(* Three roundings, for a sum X1 + X2 + X3 of at most B = 2^e. With D = 2^(e - prec), half
   a unit in the last place of the numbers between B and 2 B: each rounding adds at most
   D, and the last value is at most the number of the format that follows B. *)
Lemma chain3_le :
  forall (X1 X2 X3 : R) (e : Z), (emin + prec <= e + 1)%Z ->
  0 <= X1 -> 0 <= X2 -> 0 <= X3 -> X1 + X2 + X3 <= bpow radix2 e ->
  0 <= rnd X1 <= X1 + bpow radix2 (e - prec) /\
  0 <= rnd (X2 + rnd X1) <= X1 + X2 + 2 * bpow radix2 (e - prec) /\
  0 <= rnd (X3 + rnd (X2 + rnd X1)) <= X1 + X2 + X3 + 3 * bpow radix2 (e - prec) /\
  rnd (X3 + rnd (X2 + rnd X1)) <= bpow radix2 e + 2 * bpow radix2 (e - prec).
Proof.
intros X1 X2 X3 e He P1 P2 P3 HS.
assert (D0 : 0 < bpow radix2 (e - prec)) by apply bpow_gt_0.
assert (DB : 2 * bpow radix2 (e - prec) <= bpow radix2 e).
{ rewrite <- two_bpow. apply bpow_le. lia. }
assert (E2 : bpow radix2 (e + 1) = 2 * bpow radix2 e) by apply two_bpow.
assert (Half : forall x : R, 0 <= x <= 2 * bpow radix2 e -> rnd x <= x + bpow radix2 (e - prec)).
{ intros x Hx. replace (e - prec)%Z with (e + 1 - prec - 1)%Z by ring.
  apply rnd_le_half. lia. now rewrite E2. }
assert (A0 : 0 <= rnd X1) by now apply rnd_pos.
assert (A1 : rnd X1 <= X1 + bpow radix2 (e - prec)) by (apply Half; lra).
assert (B0 : 0 <= rnd (X2 + rnd X1)) by (apply rnd_pos; lra).
assert (B1 : rnd (X2 + rnd X1) <= X2 + rnd X1 + bpow radix2 (e - prec)) by (apply Half; lra).
assert (C0 : 0 <= rnd (X3 + rnd (X2 + rnd X1))) by (apply rnd_pos; lra).
assert (C1 : rnd (X3 + rnd (X2 + rnd X1)) <= X3 + rnd (X2 + rnd X1) + bpow radix2 (e - prec))
  by (apply Half; lra).
assert (C2 : rnd (X3 + rnd (X2 + rnd X1)) <= bpow radix2 e + 2 * bpow radix2 (e - prec)).
{ apply rnd_le_format. now apply format_succ_bpow. lra. }
repeat split; lra.
Qed.

(** * The constants *)

Lemma RU_le : forall t M : R, format M -> t <= M -> RU emin prec t <= M.
Proof. intros t M FM H. unfold RU. apply round_le_generic; auto with typeclass_instances. Qed.

Lemma kappa_le : (2 <= prec)%Z -> 1 <= 1 + u prec <= 5 / 4.
Proof. intros Hp. assert (Ht : 0 < u prec <= / 4) by exact (Ball2.u_bounds prec 2 Hp). lra. Qed.

Lemma format_half : (2 <= prec)%Z -> format (/ 2).
Proof. intros Hp. change (/ 2) with (bpow radix2 (-1)). apply format_bpow. lia. Qed.

Lemma format_quarter : (2 <= prec)%Z -> format (/ 4).
Proof. intros Hp. change (/ 4) with (bpow radix2 (-2)). apply format_bpow. lia. Qed.

(* E: at most 1/4 for one limb, 1/2 for two. *)
Lemma E_add_1_le : (2 <= prec)%Z -> 0 <= Model.up_ball_add_1_0 emin prec <= / 4.
Proof.
intros Hp. rewrite Ball2.e_add_1_eq.
destruct (uq_le_quarter _ (rel_1_fifth prec Hp)) as [Q0 Q1].
split. exact (proj1 (Ball2.RU_ge emin prec _ Q0)).
apply RU_le; trivial. now apply format_quarter.
Qed.

Lemma E_mul_1_le : (2 <= prec)%Z -> 0 <= Model.up_ball_mul_1_0 emin prec <= / 4.
Proof.
intros Hp. rewrite Ball2.e_mul_1_eq.
destruct (uq_le_quarter _ (rel_1_fifth prec Hp)) as [Q0 Q1].
split. exact (proj1 (Ball2.RU_ge emin prec _ Q0)).
apply RU_le; trivial. now apply format_quarter.
Qed.

Lemma E_add_2_le : (3 <= prec)%Z -> 0 <= Model.up_ball_add_2_0 emin prec <= / 2.
Proof.
intros Hp. assert (Hp2 : (2 <= prec)%Z) by lia. rewrite Ball2.e_add_2_eq.
destruct (uq_le_half _ _ (rel_add_2_quarter prec Hp) (kappa_le Hp2)) as [Q0 Q1].
split. exact (proj1 (Ball2.RU_ge emin prec _ Q0)).
apply RU_le; trivial. now apply format_half.
Qed.

Lemma E_scale_2_le : (2 <= prec)%Z -> 0 <= Model.up_ball_scale_2_0 emin prec <= / 2.
Proof.
intros Hp. rewrite Ball2.e_scale_2_eq.
destruct (uq_le_half _ _ (rel_square_quarter 2 prec Hp ltac:(lra)) (kappa_le Hp)) as [Q0 Q1].
split. exact (proj1 (Ball2.RU_ge emin prec _ Q0)).
apply RU_le; trivial. now apply format_half.
Qed.

Lemma E_mul_2_le : (4 <= prec)%Z -> 0 <= Model.up_ball_mul_2_0 emin prec <= / 2.
Proof.
intros Hp. assert (Hp2 : (2 <= prec)%Z) by lia. rewrite Ball2.e_mul_2_eq.
generalize (uq_le_half _ 1 (rel_square_quarter 4 prec Hp2 ltac:(lra)) ltac:(lra)).
rewrite Rmult_1_r. intros [Q0 Q1].
split. exact (proj1 (Ball2.RU_ge emin prec _ Q0)).
apply RU_le; trivial. now apply format_half.
Qed.

(* G: at most 2 for sums and scalings, 4 for ball_mul_1, 3/2 for ball_mul_2. *)
Lemma G_3_le : (2 <= prec)%Z -> 0 <= Model.up_ball_add_1_1 emin prec <= 2.
Proof.
intros Hp. rewrite Ball2.g_add_1_eq.
assert (Ht : 0 < u prec <= / 4) by exact (Ball2.u_bounds prec 2 Hp).
assert (P : 0 <= (1 + u prec) ^ 3 <= 2).
{ split. apply pow_le; lra.
  apply Rle_trans with ((5 / 4) ^ 3). apply pow_incr; lra. simpl. lra. }
split. exact (proj1 (Ball2.RU_ge emin prec _ (proj1 P))).
apply RU_le; [|exact (proj2 P)]. change 2 with (bpow radix2 1). apply format_bpow. lia.
Qed.

Lemma G_5_le : (2 <= prec)%Z -> 0 <= Model.up_ball_mul_1_1 emin prec <= 4.
Proof.
intros Hp. rewrite Ball2.g_mul_1_eq.
assert (Ht : 0 < u prec <= / 4) by exact (Ball2.u_bounds prec 2 Hp).
destruct (pow_le_4 (u prec) 5 Ht ltac:(lia)) as [P0 P1].
split. exact (proj1 (Ball2.RU_ge emin prec _ P0)).
apply RU_le; [|exact P1]. change 4 with (bpow radix2 2). apply format_bpow. lia.
Qed.

Lemma G_6_le : (4 <= prec)%Z -> 0 <= Model.up_ball_mul_2_1 emin prec <= 3 / 2.
Proof.
intros Hp. assert (Hp2 : (2 <= prec)%Z) by lia. rewrite Ball2.g_mul_2_eq.
assert (Ht : 0 < u prec <= / 16) by exact (Ball2.u_bounds prec 4 Hp).
assert (P : 0 <= (1 + u prec) ^ 6 <= 3 / 2).
{ split. apply pow_le; lra.
  apply Rle_trans with ((17 / 16) ^ 6). apply pow_incr; lra. simpl. lra. }
split. exact (proj1 (Ball2.RU_ge emin prec _ (proj1 P))).
apply RU_le; [|exact (proj2 P)].
change (3 / 2) with (3 * bpow radix2 (-1)).
apply generic_format_FLT. exists (Float radix2 3 (-1)).
- reflexivity.
- apply Z.lt_le_trans with (2 := Zpower_le radix2 2 prec Hp2). reflexivity.
- change (emin <= -1)%Z. lia.
Qed.

(* H is an expression h plus the smallest normal number N = 2^(2 - emax), rounded up. *)
Lemma eta_le_nrm : (2 <= prec)%Z -> 2 * eta emin <= Ball2.nrm emin prec.
Proof.
intros Hp. rewrite Ball2.nrm_eq. unfold eta. rewrite <- two_bpow. apply bpow_le. lia.
Qed.

Lemma RU_nrm_le_4 :
  forall h : R, 0 <= h <= 3 * Ball2.nrm emin prec ->
  0 <= RU emin prec (h + Ball2.nrm emin prec) <= bpow radix2 (4 - emax).
Proof.
intros h [h0 h1].
generalize (Ball2.nrm_ge_0 emin prec). intros N0.
assert (S0 : 0 <= h + Ball2.nrm emin prec) by lra.
split. exact (proj1 (Ball2.RU_ge emin prec _ S0)).
apply RU_le. apply format_bpow. lia.
replace (bpow radix2 (4 - emax)) with (4 * Ball2.nrm emin prec). lra.
rewrite Ball2.nrm_eq. change 4 with (bpow radix2 2). rewrite <- bpow_plus. f_equal. lia.
Qed.

Lemma RU_nrm_le_6 :
  (2 <= prec)%Z -> forall h : R, 0 <= h <= 5 * Ball2.nrm emin prec ->
  0 <= RU emin prec (h + Ball2.nrm emin prec) <= 3 * bpow radix2 (3 - emax).
Proof.
intros Hp h [h0 h1].
generalize (Ball2.nrm_ge_0 emin prec). intros N0.
assert (S0 : 0 <= h + Ball2.nrm emin prec) by lra.
assert (EN : bpow radix2 (3 - emax) = 2 * Ball2.nrm emin prec).
{ rewrite Ball2.nrm_eq, <- two_bpow. f_equal. lia. }
split. exact (proj1 (Ball2.RU_ge emin prec _ S0)).
apply RU_le.
- apply generic_format_FLT. exists (Float radix2 3 (3 - emax)).
  + reflexivity.
  + apply Z.lt_le_trans with (2 := Zpower_le radix2 2 prec Hp). reflexivity.
  + change (emin <= 3 - emax)%Z. lia.
- rewrite EN. lra.
Qed.

Lemma h2_le_6 :
  (2 <= prec)%Z -> forall V : R, 0 <= V <= 2 * eta emin ->
  0 <= Ball2.h2 emin prec V <= 6 * eta emin.
Proof.
intros Hp V [V0 V1].
assert (Ht : 0 < u prec <= / 4) by exact (Ball2.u_bounds prec 2 Hp).
assert (P0 : 0 <= (1 + u prec) ^ 2) by (apply pow_le; lra).
assert (P2 : (1 + u prec) ^ 2 <= 25 / 16).
{ apply Rle_trans with ((5 / 4) ^ 2). apply pow_incr; lra. simpl. lra. }
unfold Ball2.h2. destruct Ht as [T0 T1].
generalize (bpow_gt_0 radix2 emin). fold (eta emin). intros E0.
set (t := u prec) in *. set (e := eta emin) in *. set (q := (1 + t) ^ 2) in *.
assert (Q : q * e <= 25 / 16 * e) by (apply Rmult_le_compat_r; lra).
assert (Q0 : 0 <= q * e) by (apply Rmult_le_pos; lra).
assert (A : 0 <= q * e + V + e / 2 <= 65 / 16 * e) by lra.
split. apply Rmult_le_pos; lra. nra.
Qed.

Lemma h4_le_10 :
  (2 <= prec)%Z -> forall V : R, 0 <= V <= 2 * eta emin ->
  0 <= Ball2.h4 emin prec 4 V <= 10 * eta emin.
Proof.
intros Hp V [V0 V1].
assert (Ht : 0 < u prec <= / 4) by exact (Ball2.u_bounds prec 2 Hp).
assert (P0 : 0 <= (1 + u prec) ^ 4) by (apply pow_le; lra).
assert (P2 : (1 + u prec) ^ 4 <= 625 / 256).
{ apply Rle_trans with ((5 / 4) ^ 4). apply pow_incr; lra. simpl. lra. }
unfold Ball2.h4. destruct Ht as [T0 T1].
generalize (bpow_gt_0 radix2 emin). fold (eta emin). intros E0.
set (t := u prec) in *. set (e := eta emin) in *. set (q := (1 + t) ^ 4) in *.
assert (Q : q * e <= 625 / 256 * e) by (apply Rmult_le_compat_r; lra).
assert (Q0 : 0 <= q * e) by (apply Rmult_le_pos; lra).
assert (A : 0 <= 2 * q * e + V + e / 2 <= 1890 / 256 * e) by lra.
split. apply Rmult_le_pos; lra. nra.
Qed.

(* H of the sums and the scalings: at most 4 N, which is at most a quarter of 2^emax. *)
Lemma H_small :
  (2 <= prec)%Z -> forall V : R, 0 <= V <= 2 * eta emin ->
  0 <= RU emin prec (Ball2.h2 emin prec V + Ball2.nrm emin prec) <= bpow radix2 (emax - 2).
Proof.
intros Hp V HV. destruct (h2_le_6 Hp V HV) as [h0 h1].
generalize (eta_le_nrm Hp). intros EN.
assert (HH : 0 <= Ball2.h2 emin prec V <= 3 * Ball2.nrm emin prec) by lra.
destruct (RU_nrm_le_4 _ HH) as [R0 R1].
split. exact R0. apply Rle_trans with (1 := R1). apply bpow_le. lia.
Qed.

Lemma H_add_le : (2 <= prec)%Z -> 0 <= Model.up_ball_add_1_2 emin prec <= bpow radix2 (emax - 2).
Proof.
intros Hp. rewrite Ball2.h_add_1_eq.
replace ((1 + u prec) * ((1 + u prec) ^ 2 * eta emin + eta emin / 2))
  with (Ball2.h2 emin prec 0) by (unfold Ball2.h2; ring).
apply H_small; trivial. generalize (bpow_gt_0 radix2 emin). unfold eta. lra.
Qed.

Lemma H_scale_1_le :
  (2 <= prec)%Z -> 0 <= Model.up_ball_scale_1_2 emin prec <= bpow radix2 (emax - 2).
Proof.
intros Hp. rewrite Ball2.h_scale_1_eq. apply H_small; trivial.
generalize (bpow_gt_0 radix2 emin). fold (eta emin). intros E0.
generalize (vq_le _ (1 / 2 * eta emin) (2 / 3 * eta emin) (rel_1_quarter prec Hp) ltac:(lra)).
lra.
Qed.

Lemma H_scale_2_le :
  (2 <= prec)%Z -> 0 <= Model.up_ball_scale_2_2 emin prec <= bpow radix2 (emax - 2).
Proof.
intros Hp. rewrite Ball2.h_scale_2_eq. apply H_small; trivial.
generalize (bpow_gt_0 radix2 emin). fold (eta emin). intros E0.
generalize (vq_le _ (1 * eta emin) (2 / 3 * eta emin)
              (rel_square_quarter 2 prec Hp ltac:(lra)) ltac:(lra)).
lra.
Qed.

(* H of ball_mul_1: at most 6 N, which is at most 3/8 of 2^emax. *)
Lemma H_mul_1_le :
  (2 <= prec)%Z -> 0 <= Model.up_ball_mul_1_2 emin prec <= 3 * bpow radix2 (emax - 3).
Proof.
intros Hp. rewrite Ball2.h_mul_1_eq.
generalize (bpow_gt_0 radix2 emin). fold (eta emin). intros E0.
assert (V : 0 <= Ball2.vq (1 / (1 + u prec) * u prec ^ 1) (1 / 2 * eta emin) <= 2 * eta emin).
{ generalize (vq_le _ (1 / 2 * eta emin) (2 / 3 * eta emin) (rel_1_quarter prec Hp) ltac:(lra)).
  lra. }
destruct (h4_le_10 Hp _ V) as [h0 h1].
generalize (eta_le_nrm Hp). intros EN.
assert (HH : 0 <= Ball2.h4 emin prec 4 (Ball2.vq (1 / (1 + u prec) * u prec ^ 1) (1 / 2 * eta emin))
             <= 5 * Ball2.nrm emin prec) by lra.
destruct (RU_nrm_le_6 Hp _ HH) as [R0 R1].
assert (L : bpow radix2 (3 - emax) <= bpow radix2 (emax - 3)) by (apply bpow_le; lia).
split. exact R0. lra.
Qed.

(* H of ball_mul_2: at most 4 N, which is at most an eighth of 2^emax. *)
Lemma H_mul_2_le :
  (4 <= prec)%Z -> 0 <= Model.up_ball_mul_2_2 emin prec <= bpow radix2 (emax - 3).
Proof.
intros Hp. assert (Hp2 : (2 <= prec)%Z) by lia. rewrite Ball2.h_mul_2_eq.
generalize (bpow_gt_0 radix2 emin). fold (eta emin). intros E0.
assert (V : 0 <= Ball2.vq (4 * u prec ^ 2) (3 / 2 * eta emin) <= 3 * eta emin).
{ apply vq_le. exact (rel_square_quarter 4 prec Hp2 ltac:(lra)). lra. }
destruct (h4_le emin prec 5 _ Hp2 ltac:(lia) V) as [h0 h1].
assert (L : bpow radix2 (emin + 4) <= 2 * Ball2.nrm emin prec).
{ rewrite Ball2.nrm_eq, <- two_bpow. apply bpow_le. lia. }
generalize (Ball2.nrm_ge_0 emin prec). intros N0.
assert (HH : 0 <= Ball2.h4 emin prec 5 (Ball2.vq (4 * u prec ^ 2) (3 / 2 * eta emin))
             <= 3 * Ball2.nrm emin prec) by lra.
destruct (RU_nrm_le_4 _ HH) as [R0 R1].
split. exact R0. apply Rle_trans with (1 := R1). apply bpow_le. lia.
Qed.

(** * The radius of each core, in range *)

Lemma inrange_of_bounds :
  forall v M : R, 0 <= v <= M -> M < bpow radix2 emax -> inrange v.
Proof.
intros v M [V0 V1] LM. unfold IeeeBridge.inrange. rewrite Rabs_pos_eq by exact V0. lra.
Qed.

Lemma inrange_le :
  forall x M : R, format M -> M < bpow radix2 emax -> 0 <= x <= M -> inrange (rnd x).
Proof.
intros x M FM LM [X0 X1]. unfold IeeeBridge.inrange.
apply Rle_lt_trans with (2 := LM).
apply (round_abs_le emin prec tie_even); trivial. now rewrite Rabs_pos_eq.
Qed.

(* 3/4 and 7/8 of 2^emax are numbers of the format below 2^emax. *)
Lemma format_3_quarters : (2 <= prec)%Z -> format (3 * bpow radix2 (emax - 2)).
Proof.
intros Hp. apply generic_format_FLT. exists (Float radix2 3 (emax - 2)).
- reflexivity.
- apply Z.lt_le_trans with (2 := Zpower_le radix2 2 prec Hp). reflexivity.
- change (emin <= emax - 2)%Z. lia.
Qed.

Lemma format_7_eighths : (3 <= prec)%Z -> format (7 * bpow radix2 (emax - 3)).
Proof.
intros Hp. apply generic_format_FLT. exists (Float radix2 7 (emax - 3)).
- reflexivity.
- apply Z.lt_le_trans with (2 := Zpower_le radix2 3 prec Hp). reflexivity.
- change (emin <= emax - 3)%Z. lia.
Qed.

Lemma top_4 : bpow radix2 emax = 4 * bpow radix2 (emax - 2).
Proof. change 4 with (bpow radix2 2). rewrite <- bpow_plus. f_equal. lia. Qed.

Lemma top_8 : bpow radix2 emax = 8 * bpow radix2 (emax - 3).
Proof. change 8 with (bpow radix2 3). rewrite <- bpow_plus. f_equal. lia. Qed.

Lemma top_16 : bpow radix2 emax = 16 * bpow radix2 (emax - 4).
Proof. change 16 with (bpow radix2 4). rewrite <- bpow_plus. f_equal. lia. Qed.

(* Sums and scalings: X is rx + ry or |a| rx, Y is az E, and B = 2^(emax - 2). *)
Lemma radius2_range :
  (2 <= prec)%Z ->
  forall X Y G H : R,
  0 <= X <= bpow radix2 (emax - 2) -> 0 <= Y ->
  X + Y < bpow radix2 (emax - 2) + bpow radix2 (emax - 2 - prec - 1) ->
  0 <= G <= 2 -> 0 <= H <= bpow radix2 (emax - 2) ->
  inrange (rnd X) /\ inrange (rnd (Y + rnd X)) /\
  inrange (rnd (rnd (Y + rnd X) * G + H)).
Proof.
intros Hp X Y G H HX HY HS [G0 G1] [H0 H1].
assert (He : (emin + prec <= emax - 2)%Z) by lia.
destruct (chain2_le X Y (emax - 2) He HX HY HS) as [[S0 S1] [T0 T1]].
assert (B0 : 0 < bpow radix2 (emax - 2)) by apply bpow_gt_0.
generalize top_4. intros T4.
assert (LT : bpow radix2 (emax - 2) < bpow radix2 emax) by lra.
split. exact (inrange_of_bounds _ _ (conj S0 S1) LT).
split. exact (inrange_of_bounds _ _ (conj T0 T1) LT).
apply inrange_le with (3 * bpow radix2 (emax - 2)).
- now apply format_3_quarters.
- lra.
- assert (K : rnd (Y + rnd X) * G <= bpow radix2 (emax - 2) * 2) by (apply Rmult_le_compat; lra).
  assert (K0 : 0 <= rnd (Y + rnd X) * G) by (apply Rmult_le_pos; lra).
  lra.
Qed.

(* ball_mul_1: X1 + X2 + X3 is rx ry + |cy| rx + |cx| ry, m is |cx cy|, az the magnitude
   of the rounded product, and B = 2^(emax - 4). The exact value of t is at most B and
   three roundings came before it; t is nevertheless at most the number that follows
   B, because either m is small, and then az E is, or the three other terms are at
   most B - m. *)
Lemma radius4_range_1 :
  (2 <= prec)%Z ->
  forall X1 X2 X3 az m E G H : R,
  0 <= X1 -> 0 <= X2 -> 0 <= X3 -> 0 <= m ->
  X1 + X2 + X3 + m <= bpow radix2 (emax - 4) ->
  0 <= az <= m + bpow radix2 (emax - 4 - prec) ->
  0 <= E <= / 4 -> 0 <= G <= 4 -> 0 <= H <= 3 * bpow radix2 (emax - 3) ->
  inrange (rnd X1) /\ inrange (rnd (X2 + rnd X1)) /\
  inrange (rnd (X3 + rnd (X2 + rnd X1))) /\
  inrange (rnd (az * E + rnd (X3 + rnd (X2 + rnd X1)))) /\
  inrange (rnd (rnd (az * E + rnd (X3 + rnd (X2 + rnd X1))) * G + H)).
Proof.
intros Hp X1 X2 X3 az m E G H P1 P2 P3 Pm HS [A0 A1] [E0 E1] [G0 G1] [H0 H1].
assert (He : (emin + prec <= emax - 4 + 1)%Z) by lia.
assert (HS3 : X1 + X2 + X3 <= bpow radix2 (emax - 4)) by lra.
destruct (chain3_le X1 X2 X3 (emax - 4) He P1 P2 P3 HS3) as [[p0 p1] [[q0 q1] [[w0 w1] w2]]].
assert (D0 : 0 < bpow radix2 (emax - 4 - prec)) by apply bpow_gt_0.
assert (B0 : 0 < bpow radix2 (emax - 4)) by apply bpow_gt_0.
assert (DB : 4 * bpow radix2 (emax - 4 - prec) <= bpow radix2 (emax - 4)).
{ change 4 with (bpow radix2 2). rewrite <- bpow_plus. apply bpow_le. lia. }
generalize top_16. intros T16.
assert (E3 : bpow radix2 (emax - 3) = 2 * bpow radix2 (emax - 4)).
{ rewrite <- two_bpow. f_equal. lia. }
assert (E2 : bpow radix2 (emax - 2) = 4 * bpow radix2 (emax - 4)).
{ change 4 with (bpow radix2 2). rewrite <- bpow_plus. f_equal. lia. }
assert (LT : 2 * bpow radix2 (emax - 4) < bpow radix2 emax) by lra.
set (w := rnd (X3 + rnd (X2 + rnd X1))) in *.
assert (AE0 : 0 <= az * E) by (apply Rmult_le_pos; lra).
assert (AE : az * E <= (m + bpow radix2 (emax - 4 - prec)) * / 4)
  by (apply Rmult_le_compat; lra).
assert (X4 : az * E + w < bpow radix2 (emax - 4) + 3 * bpow radix2 (emax - 4 - prec)).
{ destruct (Rle_or_lt m (bpow radix2 (emax - 4 - prec))) as [L|L]; lra. }
assert (T1 : rnd (az * E + w) <= bpow radix2 (emax - 4) + 2 * bpow radix2 (emax - 4 - prec))
  by (apply (rnd_le_succ_bpow_mid Hp); [exact He|exact X4]).
assert (T0 : 0 <= rnd (az * E + w)) by (apply rnd_pos; lra).
split. apply inrange_of_bounds with (2 * bpow radix2 (emax - 4)); [lra|exact LT].
split. apply inrange_of_bounds with (2 * bpow radix2 (emax - 4)); [lra|exact LT].
split. apply inrange_of_bounds with (2 * bpow radix2 (emax - 4)); [lra|exact LT].
split. apply inrange_of_bounds with (2 * bpow radix2 (emax - 4)); [lra|exact LT].
apply inrange_le with (3 * bpow radix2 (emax - 2)).
- now apply format_3_quarters.
- lra.
- assert (K : rnd (az * E + w) * G
              <= (bpow radix2 (emax - 4) + 2 * bpow radix2 (emax - 4 - prec)) * 4)
    by (apply Rmult_le_compat; lra).
  assert (K0 : 0 <= rnd (az * E + w) * G) by (apply Rmult_le_pos; lra).
  lra.
Qed.

(* ball_mul_2: the sum of the four terms, with what three roundings can add, is at most
   2^(emax - 1), so every value is. *)
Lemma radius4_range_2 :
  (4 <= prec)%Z ->
  forall X1 X2 X3 Y G H : R,
  0 <= X1 -> 0 <= X2 -> 0 <= X3 -> 0 <= Y ->
  X1 + X2 + X3 + Y + 3 * bpow radix2 (emax - 1 - prec) <= bpow radix2 (emax - 1) ->
  0 <= G <= 3 / 2 -> 0 <= H <= bpow radix2 (emax - 3) ->
  inrange (rnd X1) /\ inrange (rnd (X2 + rnd X1)) /\
  inrange (rnd (X3 + rnd (X2 + rnd X1))) /\
  inrange (rnd (Y + rnd (X3 + rnd (X2 + rnd X1)))) /\
  inrange (rnd (rnd (Y + rnd (X3 + rnd (X2 + rnd X1))) * G + H)).
Proof.
intros Hp X1 X2 X3 Y G H P1 P2 P3 PY HS [G0 G1] [H0 H1].
assert (He : (emin + prec <= emax - 1 + 1)%Z) by lia.
assert (D0 : 0 < bpow radix2 (emax - 1 - prec)) by apply bpow_gt_0.
assert (HS3 : X1 + X2 + X3 <= bpow radix2 (emax - 1)) by lra.
destruct (chain3_le X1 X2 X3 (emax - 1) He P1 P2 P3 HS3) as [[p0 p1] [[q0 q1] [[w0 w1] w2]]].
assert (B0 : 0 < bpow radix2 (emax - 3)) by apply bpow_gt_0.
generalize top_8. intros T8.
assert (E1 : bpow radix2 (emax - 1) = 4 * bpow radix2 (emax - 3)).
{ change 4 with (bpow radix2 2). rewrite <- bpow_plus. f_equal. lia. }
assert (LT : bpow radix2 (emax - 1) < bpow radix2 emax) by lra.
set (w := rnd (X3 + rnd (X2 + rnd X1))) in *.
assert (FB : format (bpow radix2 (emax - 1))) by (apply format_bpow; lia).
assert (T1 : rnd (Y + w) <= bpow radix2 (emax - 1)) by (apply rnd_le_format; [exact FB|lra]).
assert (T0 : 0 <= rnd (Y + w)) by (apply rnd_pos; lra).
split. apply inrange_of_bounds with (bpow radix2 (emax - 1)); [lra|exact LT].
split. apply inrange_of_bounds with (bpow radix2 (emax - 1)); [lra|exact LT].
split. apply inrange_of_bounds with (bpow radix2 (emax - 1)); [lra|exact LT].
split. apply inrange_of_bounds with (bpow radix2 (emax - 1)); [lra|exact LT].
apply inrange_le with (7 * bpow radix2 (emax - 3)).
- apply format_7_eighths. lia.
- lra.
- assert (K : rnd (Y + w) * G <= bpow radix2 (emax - 1) * (3 / 2))
    by (apply Rmult_le_compat; lra).
  assert (K0 : 0 <= rnd (Y + w) * G) by (apply Rmult_le_pos; lra).
  lra.
Qed.

(* The leading limb of a normalized pair is at most 4/3 of the value, in magnitude. *)
Lemma lead_le :
  (2 <= prec)%Z -> forall x0 x1 : R, normalized_2 emin prec x0 x1 ->
  3 * Rabs x0 <= 4 * Rabs (x0 + x1).
Proof.
intros Hp x0 x1 N.
generalize (normalized_2_tail_rel emin prec x0 x1 N) (Rabs_pos x0). intros T P.
assert (Ht : 0 < u prec <= / 4) by exact (Ball2.u_bounds prec 2 Hp).
assert (T' : u prec * Rabs x0 <= / 4 * Rabs x0) by (apply Rmult_le_compat_r; lra).
generalize (Rabs_le_plus_err x0 (x0 + x1)).
replace (x0 - (x0 + x1)) with (- x1) by ring. rewrite Rabs_Ropp. lra.
Qed.

(** * One operation, and the radius, in the IEEE model *)

Lemma add_fin :
  forall x y : float, fin x -> fin y -> inrange (rnd (b2r x + b2r y)) ->
  fin (add x y) /\ b2r (add x y) = rnd (b2r x + b2r y).
Proof.
intros x y Fx Fy H. destruct (add_spec prec emax nan_plus x y Fx Fy) as [S1 S2].
assert (F : fin (add x y)) by now apply S1.
split. exact F. now apply S2.
Qed.

Lemma fma_fin :
  forall x y z : float, fin x -> fin y -> fin z -> inrange (rnd (b2r x * b2r y + b2r z)) ->
  fin (fma x y z) /\ b2r (fma x y z) = rnd (b2r x * b2r y + b2r z).
Proof.
intros x y z Fx Fy Fz H. destruct (fma_spec prec emax nan_fma x y z Fx Fy Fz) as [S1 S2].
assert (F : fin (fma x y z)) by now apply S1.
split. exact F. now apply S2.
Qed.

Lemma prod_fin :
  forall x y : float, fin x -> fin y -> inrange (rnd (b2r x * b2r y + 0)) ->
  fin (prod x y) /\ b2r (prod x y) = rnd (b2r x * b2r y + 0).
Proof.
intros x y Fx Fy H.
exact (fma_fin x y (IeeeOperations.pzero prec emax) Fx Fy eq_refl H).
Qed.

(* The radius of a sum, of a scaling and of a product: finite when the values of the real
   model are in range. *)
Lemma radius2_add_fin :
  forall az rx ry E G H : float,
  fin az -> fin rx -> fin ry -> fin E -> fin G -> fin H ->
  inrange (rnd (b2r rx + b2r ry)) ->
  inrange (rnd (b2r az * b2r E + rnd (b2r rx + b2r ry))) ->
  inrange (rnd (rnd (b2r az * b2r E + rnd (b2r rx + b2r ry)) * b2r G + b2r H)) ->
  fin (fma (fma az E (add rx ry)) G H).
Proof.
intros az rx ry E G H Faz Frx Fry FE FG FH Is It Ir.
destruct (add_fin rx ry Frx Fry Is) as [Fs Es].
rewrite <- Es in It, Ir.
destruct (fma_fin az E (add rx ry) Faz FE Fs It) as [Ft Et].
rewrite <- Et in Ir.
exact (proj1 (fma_fin _ G H Ft FG FH Ir)).
Qed.

Lemma radius2_scale_fin :
  forall az aa rx E G H : float,
  fin az -> fin aa -> fin rx -> fin E -> fin G -> fin H ->
  inrange (rnd (b2r aa * b2r rx + 0)) ->
  inrange (rnd (b2r az * b2r E + rnd (b2r aa * b2r rx + 0))) ->
  inrange (rnd (rnd (b2r az * b2r E + rnd (b2r aa * b2r rx + 0)) * b2r G + b2r H)) ->
  fin (fma (fma az E (prod aa rx)) G H).
Proof.
intros az aa rx E G H Faz Faa Frx FE FG FH Ip It Ir.
destruct (prod_fin aa rx Faa Frx Ip) as [Fp Ep].
rewrite <- Ep in It, Ir.
destruct (fma_fin az E (prod aa rx) Faz FE Fp It) as [Ft Et].
rewrite <- Et in Ir.
exact (proj1 (fma_fin _ G H Ft FG FH Ir)).
Qed.

Lemma radius4_fin :
  forall ax ay az rx ry E G H : float,
  fin ax -> fin ay -> fin az -> fin rx -> fin ry -> fin E -> fin G -> fin H ->
  inrange (rnd (b2r rx * b2r ry + 0)) ->
  inrange (rnd (b2r ay * b2r rx + rnd (b2r rx * b2r ry + 0))) ->
  inrange (rnd (b2r ax * b2r ry + rnd (b2r ay * b2r rx + rnd (b2r rx * b2r ry + 0)))) ->
  inrange (rnd (b2r az * b2r E
                + rnd (b2r ax * b2r ry + rnd (b2r ay * b2r rx + rnd (b2r rx * b2r ry + 0))))) ->
  inrange (rnd (rnd (b2r az * b2r E
                     + rnd (b2r ax * b2r ry + rnd (b2r ay * b2r rx + rnd (b2r rx * b2r ry + 0))))
                * b2r G + b2r H)) ->
  fin (fma (fma az E (fma ax ry (fma ay rx (prod rx ry)))) G H).
Proof.
intros ax ay az rx ry E G H Fax Fay Faz Frx Fry FE FG FH Ip Iq Iw It Ir.
destruct (prod_fin rx ry Frx Fry Ip) as [Fp Ep].
rewrite <- Ep in Iq, Iw, It, Ir.
destruct (fma_fin ay rx (prod rx ry) Fay Frx Fp Iq) as [Fq Eq].
rewrite <- Eq in Iw, It, Ir.
destruct (fma_fin ax ry _ Fax Fry Fq Iw) as [Fw Ew].
rewrite <- Ew in It, Ir.
destruct (fma_fin az E _ Faz FE Fw It) as [Ft Et].
rewrite <- Et in Ir.
exact (proj1 (fma_fin _ G H Ft FG FH Ir)).
Qed.

(** * The cores: finite under the condition *)

Notation ball_add_1 := (IeeeModel.ball_add_1 prec emax nan_plus nan_abs nan_fma).
Notation ball_sub_1 := (IeeeModel.ball_sub_1 prec emax nan_plus nan_opp nan_abs nan_fma).
Notation ball_mul_1 := (IeeeModel.ball_mul_1 prec emax nan_abs nan_fma).
Notation ball_scale_1 := (IeeeModel.ball_scale_1 prec emax nan_abs nan_fma).
Notation ball_add_2 := (IeeeModel.ball_add_2 prec emax nan_plus nan_minus nan_abs nan_fma).
Notation ball_sub_2 := (IeeeModel.ball_sub_2 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma).
Notation ball_mul_2 := (IeeeModel.ball_mul_2 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma).
Notation ball_scale_2 :=
  (IeeeModel.ball_scale_2 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma).

Lemma ball_add_1_finite :
  (2 <= prec)%Z ->
  forall cx rx cy ry : float, fin cx -> fin rx -> fin cy -> fin ry ->
  0 <= b2r rx -> 0 <= b2r ry ->
  Rabs (b2r cx + b2r cy) + b2r rx + b2r ry <= bpow radix2 (emax - 2) ->
  let '(cz, rz) := ball_add_1 cx rx cy ry in fin cz /\ fin rz.
Proof.
intros Hp cx rx cy ry Fx Frx Fy Fry Prx Pry Hc.
unfold IeeeModel.ball_add_1. cbv beta iota zeta.
destruct (consts_ball_add_1 prec emax Hp) as [[FE [EE _]] [[FG [EG _]] [FH [EH _]]]].
destruct (E_add_1_le Hp) as [E0 E1].
destruct (G_3_le Hp) as [Gl Gu].
destruct (H_add_le Hp) as [H0 H1].
assert (He : (emin + prec <= emax - 2)%Z) by lia.
generalize (Rabs_pos (b2r cx + b2r cy)) (bpow_gt_0 radix2 (emax - 2 - prec - 1)). intros C0 D0.
assert (Ic : inrange (rnd (b2r cx + b2r cy))).
{ apply (le_bpow_inrange emax) with (emax - 2)%Z. lia. apply (RN_abs_le_bpow emin prec). lra. }
destruct (add_fin cx cy Fx Fy Ic) as [Fz Ez].
split. exact Fz.
assert (Haz : Rabs (rnd (b2r cx + b2r cy))
              <= Rabs (b2r cx + b2r cy) + bpow radix2 (emax - 2 - prec - 1)).
{ apply abs_rnd_le_half. exact He. lra. }
assert (HY : Rabs (rnd (b2r cx + b2r cy)) * Model.up_ball_add_1_0 emin prec
             <= (Rabs (b2r cx + b2r cy) + bpow radix2 (emax - 2 - prec - 1)) * / 4).
{ apply Rmult_le_compat; try lra. apply Rabs_pos. }
assert (HX : 0 <= b2r rx + b2r ry <= bpow radix2 (emax - 2)) by lra.
assert (Y0 : 0 <= Rabs (rnd (b2r cx + b2r cy)) * Model.up_ball_add_1_0 emin prec)
  by (apply Rmult_le_pos; [apply Rabs_pos|exact E0]).
assert (HS : b2r rx + b2r ry + Rabs (rnd (b2r cx + b2r cy)) * Model.up_ball_add_1_0 emin prec
             < bpow radix2 (emax - 2) + bpow radix2 (emax - 2 - prec - 1)) by lra.
destruct (radius2_range Hp _ _ _ _ HX Y0 HS (conj Gl Gu) (conj H0 H1)) as [Is [It Ir]].
assert (Faz : fin (fabs (add cx cy))) by now rewrite (abs_finite prec emax nan_abs).
apply radius2_add_fin; trivial.
- rewrite (abs_val prec emax nan_abs), Ez, EE. exact It.
- rewrite (abs_val prec emax nan_abs), Ez, EE, EG, EH. exact Ir.
Qed.

Lemma ball_sub_1_finite :
  (2 <= prec)%Z ->
  forall cx rx cy ry : float, fin cx -> fin rx -> fin cy -> fin ry ->
  0 <= b2r rx -> 0 <= b2r ry ->
  Rabs (b2r cx - b2r cy) + b2r rx + b2r ry <= bpow radix2 (emax - 2) ->
  let '(cz, rz) := ball_sub_1 cx rx cy ry in fin cz /\ fin rz.
Proof.
intros Hp cx rx cy ry Fx Frx Fy Fry Prx Pry Hc.
unfold IeeeModel.ball_sub_1. cbv zeta.
assert (Fn : fin (neg cy)) by (unfold IeeeOperations.neg; now rewrite is_finite_Bopp).
generalize (ball_add_1_finite Hp cx rx (neg cy) ry Fx Frx Fn Fry Prx Pry).
replace (b2r (neg cy)) with (- b2r cy) by (symmetry; apply B2R_Bopp).
destruct (ball_add_1 cx rx (neg cy) ry) as [cz rz].
cbv beta iota. intros K. apply K. exact Hc.
Qed.

Lemma ball_scale_1_finite :
  (2 <= prec)%Z ->
  forall cx rx a : float, fin cx -> fin rx -> fin a -> 0 <= b2r rx ->
  (Rabs (b2r cx) + b2r rx) * Rabs (b2r a) <= bpow radix2 (emax - 2) ->
  let '(cz, rz) := ball_scale_1 cx rx a in fin cz /\ fin rz.
Proof.
intros Hp cx rx a Fx Frx Fa Prx Hc.
unfold IeeeModel.ball_scale_1. cbv beta iota zeta.
destruct (consts_ball_scale_1 prec emax Hp) as [[FE [EE _]] [[FG [EG _]] [FH [EH _]]]].
destruct (E_mul_1_le Hp) as [E0 E1].
destruct (G_3_le Hp) as [Gl Gu].
destruct (H_scale_1_le Hp) as [H0 H1].
assert (He : (emin + prec <= emax - 2)%Z) by lia.
generalize (Rabs_pos (b2r cx)) (Rabs_pos (b2r a)) (bpow_gt_0 radix2 (emax - 2 - prec - 1)).
intros C0 A0 D0.
assert (M0 : 0 <= Rabs (b2r cx) * Rabs (b2r a)) by now apply Rmult_le_pos.
assert (M1 : 0 <= Rabs (b2r a) * b2r rx) by now apply Rmult_le_pos.
assert (Ec : Rabs (b2r cx * b2r a + 0) = Rabs (b2r cx) * Rabs (b2r a))
  by now rewrite Rplus_0_r, Rabs_mult.
assert (Ic : inrange (rnd (b2r cx * b2r a + 0))).
{ apply (le_bpow_inrange emax) with (emax - 2)%Z. lia.
  apply (RN_abs_le_bpow emin prec). rewrite Ec. lra. }
destruct (prod_fin cx a Fx Fa Ic) as [Fz Ez].
split. exact Fz.
assert (Haz : Rabs (rnd (b2r cx * b2r a + 0))
              <= Rabs (b2r cx) * Rabs (b2r a) + bpow radix2 (emax - 2 - prec - 1)).
{ rewrite <- Ec. apply abs_rnd_le_half. exact He. rewrite Ec. lra. }
assert (HY : Rabs (rnd (b2r cx * b2r a + 0)) * Model.up_ball_mul_1_0 emin prec
             <= (Rabs (b2r cx) * Rabs (b2r a) + bpow radix2 (emax - 2 - prec - 1)) * / 4).
{ apply Rmult_le_compat; try lra. apply Rabs_pos. }
assert (HX : 0 <= Rabs (b2r a) * b2r rx + 0 <= bpow radix2 (emax - 2)) by lra.
assert (Y0 : 0 <= Rabs (rnd (b2r cx * b2r a + 0)) * Model.up_ball_mul_1_0 emin prec)
  by (apply Rmult_le_pos; [apply Rabs_pos|exact E0]).
assert (HS : Rabs (b2r a) * b2r rx + 0
             + Rabs (rnd (b2r cx * b2r a + 0)) * Model.up_ball_mul_1_0 emin prec
             < bpow radix2 (emax - 2) + bpow radix2 (emax - 2 - prec - 1)) by lra.
destruct (radius2_range Hp _ _ _ _ HX Y0 HS (conj Gl Gu) (conj H0 H1)) as [Is [It Ir]].
assert (Faa : fin (fabs a)) by now rewrite (abs_finite prec emax nan_abs).
assert (Faz : fin (fabs (prod cx a))) by now rewrite (abs_finite prec emax nan_abs).
apply radius2_scale_fin; trivial.
- rewrite (abs_val prec emax nan_abs). exact Is.
- rewrite !(abs_val prec emax nan_abs), Ez, EE. exact It.
- rewrite !(abs_val prec emax nan_abs), Ez, EE, EG, EH. exact Ir.
Qed.

Lemma ball_mul_1_finite :
  (2 <= prec)%Z ->
  forall cx rx cy ry : float, fin cx -> fin rx -> fin cy -> fin ry ->
  0 <= b2r rx -> 0 <= b2r ry ->
  (Rabs (b2r cx) + b2r rx) * (Rabs (b2r cy) + b2r ry) <= bpow radix2 (emax - 4) ->
  let '(cz, rz) := ball_mul_1 cx rx cy ry in fin cz /\ fin rz.
Proof.
intros Hp cx rx cy ry Fx Frx Fy Fry Prx Pry Hc.
unfold IeeeModel.ball_mul_1. cbv beta iota zeta.
destruct (consts_ball_mul_1 prec emax Hp) as [[FE [EE _]] [[FG [EG _]] [FH [EH _]]]].
destruct (E_mul_1_le Hp) as [E0 E1].
destruct (G_5_le Hp) as [Gl Gu].
destruct (H_mul_1_le Hp) as [H0 H1].
generalize (Rabs_pos (b2r cx)) (Rabs_pos (b2r cy)). intros A0 B0.
assert (M0 : 0 <= Rabs (b2r cx) * Rabs (b2r cy)) by now apply Rmult_le_pos.
assert (M1 : 0 <= b2r rx * b2r ry) by now apply Rmult_le_pos.
assert (M2 : 0 <= Rabs (b2r cy) * b2r rx) by now apply Rmult_le_pos.
assert (M3 : 0 <= Rabs (b2r cx) * b2r ry) by now apply Rmult_le_pos.
assert (Ec : Rabs (b2r cx * b2r cy + 0) = Rabs (b2r cx) * Rabs (b2r cy))
  by now rewrite Rplus_0_r, Rabs_mult.
assert (Ic : inrange (rnd (b2r cx * b2r cy + 0))).
{ apply (le_bpow_inrange emax) with (emax - 4)%Z. lia.
  apply (RN_abs_le_bpow emin prec). rewrite Ec. lra. }
destruct (prod_fin cx cy Fx Fy Ic) as [Fz Ez].
split. exact Fz.
assert (Haz : Rabs (rnd (b2r cx * b2r cy + 0))
              <= Rabs (b2r cx) * Rabs (b2r cy) + bpow radix2 (emax - 4 - prec)).
{ rewrite <- Ec. replace (emax - 4 - prec)%Z with (emax - 3 - prec - 1)%Z by ring.
  apply abs_rnd_le_half. lia. rewrite Ec.
  apply Rle_trans with (bpow radix2 (emax - 4)). lra. apply bpow_le. lia. }
assert (P1 : 0 <= b2r rx * b2r ry + 0) by lra.
assert (HS : b2r rx * b2r ry + 0 + Rabs (b2r cy) * b2r rx + Rabs (b2r cx) * b2r ry
             + Rabs (b2r cx) * Rabs (b2r cy) <= bpow radix2 (emax - 4)) by lra.
assert (Az : 0 <= Rabs (rnd (b2r cx * b2r cy + 0))
             <= Rabs (b2r cx) * Rabs (b2r cy) + bpow radix2 (emax - 4 - prec))
  by (split; [apply Rabs_pos|exact Haz]).
destruct (radius4_range_1 Hp _ _ _ _ _ _ _ _ P1 M2 M3 M0 HS Az (conj E0 E1) (conj Gl Gu)
            (conj H0 H1)) as [Ip [Iq [Iw [It Ir]]]].
assert (Fax : fin (fabs cx)) by now rewrite (abs_finite prec emax nan_abs).
assert (Fay : fin (fabs cy)) by now rewrite (abs_finite prec emax nan_abs).
assert (Faz : fin (fabs (prod cx cy))) by now rewrite (abs_finite prec emax nan_abs).
apply radius4_fin; trivial.
- rewrite !(abs_val prec emax nan_abs). exact Iq.
- rewrite !(abs_val prec emax nan_abs). exact Iw.
- rewrite !(abs_val prec emax nan_abs), Ez, EE. exact It.
- rewrite !(abs_val prec emax nan_abs), Ez, EE, EG, EH. exact Ir.
Qed.

Lemma ball_add_2_finite :
  (3 <= prec)%Z ->
  forall cx0 cx1 rx cy0 cy1 ry : float,
  fin cx0 -> fin cx1 -> fin cy0 -> fin cy1 ->
  normalized_2 emin prec (b2r cx0) (b2r cx1) -> normalized_2 emin prec (b2r cy0) (b2r cy1) ->
  fin rx -> fin ry -> 0 <= b2r rx -> 0 <= b2r ry ->
  Rabs ((b2r cx0 + b2r cx1) + (b2r cy0 + b2r cy1)) + b2r rx + b2r ry <= bpow radix2 (emax - 2) ->
  let '(cz0, cz1, rz) := ball_add_2 cx0 cx1 rx cy0 cy1 ry in fin cz0 /\ fin rz.
Proof.
intros Hp cx0 cx1 rx cy0 cy1 ry F0 F1 G0 G1 Nx Ny Frx Fry Prx Pry Hc.
assert (Hp2 : (2 <= prec)%Z) by lia.
generalize (Rabs_pos ((b2r cx0 + b2r cx1) + (b2r cy0 + b2r cy1))). intros C0.
assert (Hs : Rabs ((b2r cx0 + b2r cx1) + (b2r cy0 + b2r cy1)) <= bpow radix2 (emax - 2)) by lra.
unfold IeeeModel.ball_add_2.
generalize (add_2_2_ieee_finite_result prec emax prec_gt_0_ prec_lt_emax_ nan_plus nan_minus
              nan_opp nan_fma Hp cx0 cx1 cy0 cy1 F0 F1 G0 G1 Nx Ny Hs)
           (add_2_2_values_correct prec emax nan_plus nan_minus nan_opp nan_fma Hp
              cx0 cx1 cy0 cy1 F0 F1 G0 G1 Nx Ny).
destruct (IeeeModel.add_2_2 prec emax nan_plus nan_minus cx0 cx1 cy0 cy1) as [cz0 cz1].
cbv beta iota zeta. intros [_ [Fz0 Fz1]] V. destruct (V Fz0) as [_ [Nz Ez]].
split. exact Fz0.
destruct (rel_add_2_quarter prec Hp) as [R0 R1].
assert (RC : 3 / (1 - 4 * u prec) * u prec ^ 2
               * Rabs ((b2r cx0 + b2r cx1) + (b2r cy0 + b2r cy1))
             <= / 4 * Rabs ((b2r cx0 + b2r cx1) + (b2r cy0 + b2r cy1)))
  by (apply Rmult_le_compat_r; lra).
generalize (Rabs_le_plus_err (b2r cz0 + b2r cz1) ((b2r cx0 + b2r cx1) + (b2r cy0 + b2r cy1)))
           (lead_le Hp2 _ _ Nz) (Rabs_pos (b2r cz0))
           (bpow_gt_0 radix2 (emax - 2 - prec - 1)).
intros Hz Hl Z0 D0.
destruct (consts_ball_add_2 prec emax Hp) as [[FE [EE _]] [[FG [EG _]] [FH [EH _]]]].
destruct (E_add_2_le Hp) as [E0 E1].
destruct (G_3_le Hp2) as [Gl Gu].
destruct (H_add_le Hp2) as [H0 H1].
assert (HY : Rabs (b2r cz0) * Model.up_ball_add_2_0 emin prec
             <= (5 / 3 * Rabs ((b2r cx0 + b2r cx1) + (b2r cy0 + b2r cy1))) * / 2).
{ apply Rmult_le_compat; lra. }
assert (HX : 0 <= b2r rx + b2r ry <= bpow radix2 (emax - 2)) by lra.
assert (Y0 : 0 <= Rabs (b2r cz0) * Model.up_ball_add_2_0 emin prec)
  by (apply Rmult_le_pos; lra).
assert (HS : b2r rx + b2r ry + Rabs (b2r cz0) * Model.up_ball_add_2_0 emin prec
             < bpow radix2 (emax - 2) + bpow radix2 (emax - 2 - prec - 1)) by lra.
destruct (radius2_range Hp2 _ _ _ _ HX Y0 HS (conj Gl Gu) (conj H0 H1)) as [Is [It Ir]].
assert (Faz : fin (fabs cz0)) by now rewrite (abs_finite prec emax nan_abs).
apply radius2_add_fin; trivial.
- rewrite (abs_val prec emax nan_abs), EE. exact It.
- rewrite (abs_val prec emax nan_abs), EE, EG, EH. exact Ir.
Qed.

Lemma ball_sub_2_finite :
  (3 <= prec)%Z ->
  forall cx0 cx1 rx cy0 cy1 ry : float,
  fin cx0 -> fin cx1 -> fin cy0 -> fin cy1 ->
  normalized_2 emin prec (b2r cx0) (b2r cx1) -> normalized_2 emin prec (b2r cy0) (b2r cy1) ->
  fin rx -> fin ry -> 0 <= b2r rx -> 0 <= b2r ry ->
  Rabs ((b2r cx0 + b2r cx1) - (b2r cy0 + b2r cy1)) + b2r rx + b2r ry <= bpow radix2 (emax - 2) ->
  let '(cz0, cz1, rz) := ball_sub_2 cx0 cx1 rx cy0 cy1 ry in fin cz0 /\ fin rz.
Proof.
intros Hp cx0 cx1 rx cy0 cy1 ry F0 F1 G0 G1 Nx Ny Frx Fry Prx Pry Hc.
unfold IeeeModel.ball_sub_2, IeeeModel.neg_2. cbv beta iota zeta.
assert (Fn0 : fin (neg cy0)) by (unfold IeeeOperations.neg; now rewrite is_finite_Bopp).
assert (Fn1 : fin (neg cy1)) by (unfold IeeeOperations.neg; now rewrite is_finite_Bopp).
assert (E0 : b2r (neg cy0) = - b2r cy0) by apply B2R_Bopp.
assert (E1 : b2r (neg cy1) = - b2r cy1) by apply B2R_Bopp.
assert (Nn : normalized_2 emin prec (b2r (neg cy0)) (b2r (neg cy1))).
{ rewrite E0, E1. now apply normalized_2_opp. }
generalize (ball_add_2_finite Hp cx0 cx1 rx (neg cy0) (neg cy1) ry F0 F1 Fn0 Fn1 Nx Nn
              Frx Fry Prx Pry).
rewrite E0, E1.
destruct (ball_add_2 cx0 cx1 rx (neg cy0) (neg cy1) ry) as [[cz0 cz1] rz].
cbv beta iota. intros K. apply K.
replace (b2r cx0 + b2r cx1 + (- b2r cy0 + - b2r cy1))
  with (b2r cx0 + b2r cx1 - (b2r cy0 + b2r cy1)) by ring.
exact Hc.
Qed.

Lemma ball_scale_2_finite :
  (2 <= prec)%Z ->
  forall cx0 cx1 rx a : float,
  fin cx0 -> fin cx1 -> normalized_2 emin prec (b2r cx0) (b2r cx1) ->
  fin rx -> fin a -> 0 <= b2r rx ->
  (Rabs (b2r cx0 + b2r cx1) + b2r rx) * Rabs (b2r a) <= bpow radix2 (emax - 2) ->
  let '(cz0, cz1, rz) := ball_scale_2 cx0 cx1 rx a in fin cz0 /\ fin rz.
Proof.
intros Hp cx0 cx1 rx a F0 F1 Nx Frx Fa Prx Hc.
generalize (Rabs_pos (b2r cx0 + b2r cx1)) (Rabs_pos (b2r a)). intros C0 A0.
assert (M0 : 0 <= Rabs (b2r cx0 + b2r cx1) * Rabs (b2r a)) by now apply Rmult_le_pos.
assert (M1 : 0 <= Rabs (b2r a) * b2r rx) by now apply Rmult_le_pos.
assert (Hs : Rabs ((b2r cx0 + b2r cx1) * b2r a) <= bpow radix2 (emax - 1)).
{ rewrite Rabs_mult. apply Rle_trans with (bpow radix2 (emax - 2)). lra. apply bpow_le. lia. }
unfold IeeeModel.ball_scale_2.
generalize (mul_2_1_ieee_finite prec emax prec_gt_0_ prec_lt_emax_ nan_plus nan_minus
              nan_opp nan_fma Hp cx0 cx1 a F0 F1 Fa Nx Hs)
           (mul_2_1_values_correct prec emax nan_plus nan_minus nan_opp nan_fma Hp
              cx0 cx1 a F0 F1 Fa Nx).
destruct (IeeeModel.mul_2_1 prec emax nan_plus nan_minus nan_opp nan_fma cx0 cx1 a) as [cz0 cz1].
cbv beta iota zeta. intros [_ [Fz0 Fz1]] V. destruct (V Fz0) as [_ [Nz Ez]].
split. exact Fz0.
rewrite Rabs_mult in Ez.
destruct (rel_square_quarter 2 prec Hp ltac:(lra)) as [R0 R1].
generalize (bpow_gt_0 radix2 emin). fold (eta emin). intros Eta0.
assert (RC : 2 * u prec ^ 2 * (Rabs (b2r cx0 + b2r cx1) * Rabs (b2r a))
             <= / 4 * (Rabs (b2r cx0 + b2r cx1) * Rabs (b2r a)))
  by (apply Rmult_le_compat_r; lra).
assert (Hz : Rabs (b2r cz0 + b2r cz1)
             <= 5 / 4 * (Rabs (b2r cx0 + b2r cx1) * Rabs (b2r a)) + eta emin).
{ generalize (Rabs_le_plus_err (b2r cz0 + b2r cz1) ((b2r cx0 + b2r cx1) * b2r a)).
  rewrite (Rabs_mult (b2r cx0 + b2r cx1)). lra. }
generalize (lead_le Hp _ _ Nz) (Rabs_pos (b2r cz0)) (bpow_gt_0 radix2 (emax - 2 - prec - 1)).
intros Hl Z0 D0.
destruct (consts_ball_scale_2 prec emax Hp) as [[FE [EE _]] [[FG [EG _]] [FH [EH _]]]].
destruct (E_scale_2_le Hp) as [E0 E1].
destruct (G_3_le Hp) as [Gl Gu].
destruct (H_scale_2_le Hp) as [H0 H1].
assert (HY : Rabs (b2r cz0) * Model.up_ball_scale_2_0 emin prec
             <= (5 / 3 * (Rabs (b2r cx0 + b2r cx1) * Rabs (b2r a)) + 4 / 3 * eta emin) * / 2).
{ apply Rmult_le_compat; lra. }
assert (EtaD : eta emin <= bpow radix2 (emax - 2 - prec - 1)).
{ unfold eta. apply bpow_le. lia. }
assert (HX : 0 <= Rabs (b2r a) * b2r rx + 0 <= bpow radix2 (emax - 2)) by lra.
assert (Y0 : 0 <= Rabs (b2r cz0) * Model.up_ball_scale_2_0 emin prec)
  by (apply Rmult_le_pos; lra).
assert (HS : Rabs (b2r a) * b2r rx + 0 + Rabs (b2r cz0) * Model.up_ball_scale_2_0 emin prec
             < bpow radix2 (emax - 2) + bpow radix2 (emax - 2 - prec - 1)) by lra.
destruct (radius2_range Hp _ _ _ _ HX Y0 HS (conj Gl Gu) (conj H0 H1)) as [Is [It Ir]].
assert (Faa : fin (fabs a)) by now rewrite (abs_finite prec emax nan_abs).
assert (Faz : fin (fabs cz0)) by now rewrite (abs_finite prec emax nan_abs).
apply radius2_scale_fin; trivial.
- rewrite (abs_val prec emax nan_abs). exact Is.
- rewrite !(abs_val prec emax nan_abs), EE. exact It.
- rewrite !(abs_val prec emax nan_abs), EE, EG, EH. exact Ir.
Qed.

Lemma ball_mul_2_finite :
  (4 <= prec)%Z ->
  forall cx0 cx1 rx cy0 cy1 ry : float,
  fin cx0 -> fin cx1 -> fin cy0 -> fin cy1 ->
  normalized_2 emin prec (b2r cx0) (b2r cx1) -> normalized_2 emin prec (b2r cy0) (b2r cy1) ->
  fin rx -> fin ry -> 0 <= b2r rx -> 0 <= b2r ry ->
  (Rabs (b2r cx0 + b2r cx1) + b2r rx) * (Rabs (b2r cy0 + b2r cy1) + b2r ry)
  <= bpow radix2 (emax - 2) ->
  let '(cz0, cz1, rz) := ball_mul_2 cx0 cx1 rx cy0 cy1 ry in fin cz0 /\ fin rz.
Proof.
intros Hp cx0 cx1 rx cy0 cy1 ry F0 F1 G0 G1 Nx Ny Frx Fry Prx Pry Hc.
assert (Hp2 : (2 <= prec)%Z) by lia.
generalize (Rabs_pos (b2r cx0 + b2r cx1)) (Rabs_pos (b2r cy0 + b2r cy1)). intros A0 B0.
assert (M0 : 0 <= Rabs (b2r cx0 + b2r cx1) * Rabs (b2r cy0 + b2r cy1)) by now apply Rmult_le_pos.
assert (M1 : 0 <= b2r rx * b2r ry) by now apply Rmult_le_pos.
assert (M2 : 0 <= Rabs (b2r cy0 + b2r cy1) * b2r rx) by now apply Rmult_le_pos.
assert (M3 : 0 <= Rabs (b2r cx0 + b2r cx1) * b2r ry) by now apply Rmult_le_pos.
assert (Hs : Rabs ((b2r cx0 + b2r cx1) * (b2r cy0 + b2r cy1)) <= bpow radix2 (emax - 1)).
{ rewrite Rabs_mult. apply Rle_trans with (bpow radix2 (emax - 2)). lra. apply bpow_le. lia. }
unfold IeeeModel.ball_mul_2.
generalize (mul_2_2_ieee_finite prec emax prec_gt_0_ prec_lt_emax_ nan_plus nan_minus
              nan_opp nan_fma Hp cx0 cx1 cy0 cy1 F0 F1 G0 G1 Nx Ny Hs)
           (mul_2_2_values_correct prec emax nan_plus nan_minus nan_opp nan_fma Hp
              cx0 cx1 cy0 cy1 F0 F1 G0 G1 Nx Ny).
destruct (IeeeModel.mul_2_2 prec emax nan_plus nan_minus nan_opp nan_fma cx0 cx1 cy0 cy1)
  as [cz0 cz1].
cbv beta iota zeta. intros [_ [Fz0 Fz1]] V. destruct (V Fz0) as [_ [Nz Ez]].
split. exact Fz0.
rewrite Rabs_mult in Ez.
destruct (rel_square_quarter 4 prec Hp2 ltac:(lra)) as [R0 R1].
generalize (bpow_gt_0 radix2 emin). fold (eta emin). intros Eta0.
assert (RC : 4 * u prec ^ 2 * (Rabs (b2r cx0 + b2r cx1) * Rabs (b2r cy0 + b2r cy1))
             <= / 4 * (Rabs (b2r cx0 + b2r cx1) * Rabs (b2r cy0 + b2r cy1)))
  by (apply Rmult_le_compat_r; lra).
assert (Hz : Rabs (b2r cz0 + b2r cz1)
             <= 5 / 4 * (Rabs (b2r cx0 + b2r cx1) * Rabs (b2r cy0 + b2r cy1))
                + 3 / 2 * eta emin).
{ generalize (Rabs_le_plus_err (b2r cz0 + b2r cz1)
                ((b2r cx0 + b2r cx1) * (b2r cy0 + b2r cy1))).
  rewrite (Rabs_mult (b2r cx0 + b2r cx1)). lra. }
generalize (lead_le Hp2 _ _ Nz) (lead_le Hp2 _ _ Nx) (lead_le Hp2 _ _ Ny)
           (Rabs_pos (b2r cz0)) (Rabs_pos (b2r cx0)) (Rabs_pos (b2r cy0)).
intros Lz Lx Ly Z0 X0 Y0.
destruct (consts_ball_mul_2 prec emax Hp) as [[FE [EE _]] [[FG [EG _]] [FH [EH _]]]].
destruct (E_mul_2_le Hp) as [E0 E1].
destruct (G_6_le Hp) as [Gl Gu].
destruct (H_mul_2_le Hp) as [H0 H1].
assert (K2 : Rabs (b2r cy0) * b2r rx <= 4 / 3 * Rabs (b2r cy0 + b2r cy1) * b2r rx)
  by (apply Rmult_le_compat_r; lra).
assert (K3 : Rabs (b2r cx0) * b2r ry <= 4 / 3 * Rabs (b2r cx0 + b2r cx1) * b2r ry)
  by (apply Rmult_le_compat_r; lra).
assert (KY : Rabs (b2r cz0) * Model.up_ball_mul_2_0 emin prec
             <= (5 / 3 * (Rabs (b2r cx0 + b2r cx1) * Rabs (b2r cy0 + b2r cy1))
                 + 2 * eta emin) * / 2).
{ apply Rmult_le_compat; lra. }
assert (Q2 : 0 <= Rabs (b2r cy0) * b2r rx) by (apply Rmult_le_pos; lra).
assert (Q3 : 0 <= Rabs (b2r cx0) * b2r ry) by (apply Rmult_le_pos; lra).
assert (QY : 0 <= Rabs (b2r cz0) * Model.up_ball_mul_2_0 emin prec)
  by (apply Rmult_le_pos; lra).
assert (P1 : 0 <= b2r rx * b2r ry + 0) by lra.
assert (D1 : 8 * bpow radix2 (emax - 1 - prec) <= bpow radix2 (emax - 2)).
{ change 8 with (bpow radix2 3). rewrite <- bpow_plus. apply bpow_le. lia. }
assert (D2 : 8 * eta emin <= bpow radix2 (emax - 2)).
{ unfold eta. change 8 with (bpow radix2 3). rewrite <- bpow_plus. apply bpow_le. lia. }
assert (E21 : bpow radix2 (emax - 1) = 2 * bpow radix2 (emax - 2)).
{ rewrite <- two_bpow. f_equal. lia. }
assert (HS : b2r rx * b2r ry + 0 + Rabs (b2r cy0) * b2r rx + Rabs (b2r cx0) * b2r ry
             + Rabs (b2r cz0) * Model.up_ball_mul_2_0 emin prec
             + 3 * bpow radix2 (emax - 1 - prec) <= bpow radix2 (emax - 1)) by lra.
destruct (radius4_range_2 Hp _ _ _ _ _ _ P1 Q2 Q3 QY HS (conj Gl Gu) (conj H0 H1))
  as [Ip [Iq [Iw [It Ir]]]].
assert (Fax : fin (fabs cx0)) by now rewrite (abs_finite prec emax nan_abs).
assert (Fay : fin (fabs cy0)) by now rewrite (abs_finite prec emax nan_abs).
assert (Faz : fin (fabs cz0)) by now rewrite (abs_finite prec emax nan_abs).
apply radius4_fin; trivial.
- rewrite !(abs_val prec emax nan_abs). exact Iq.
- rewrite !(abs_val prec emax nan_abs). exact Iw.
- rewrite !(abs_val prec emax nan_abs), EE. exact It.
- rewrite !(abs_val prec emax nan_abs), EE, EG, EH. exact Ir.
Qed.

(** * From a core to its full kernel *)

(* The sum of two finite nonnegative radii is not a NaN. *)
Lemma add_radii_not_nan :
  forall rx ry : float, fin rx -> fin ry -> 0 <= b2r rx -> 0 <= b2r ry ->
  is_nan prec emax (add rx ry) = false.
Proof.
intros rx ry Frx Fry Prx Pry.
destruct (is_nan prec emax (add rx ry)) eqn:N; trivial.
destruct (add_nonneg prec emax nan_plus rx ry (nonneg_ext_finite prec emax rx Frx Prx)
            (nonneg_ext_finite prec emax ry Fry Pry)) as [_ [_ K]].
destruct (proj1 K N) as [M|M].
- rewrite (finite_not_nan prec emax rx Frx) in M. discriminate M.
- rewrite (finite_not_nan prec emax ry Fry) in M. discriminate M.
Qed.

(* With no empty operand, a finite center and a finite radius, the fix-up returns what
   the core returned. *)
Lemma fixup_2_finite :
  forall cz0 cz1 rz q : float, fin cz0 -> fin rz -> is_nan prec emax q = false ->
  fixup_2 cz0 cz1 rz q = (cz0, cz1, rz).
Proof.
intros cz0 cz1 rz q F0 Fr Nq. unfold IeeeBall.ball_fixup_2. cbv zeta.
rewrite eq_self, lt_abs_pinf, Nq, F0. rewrite lt_pinf_finite by exact Fr. reflexivity.
Qed.

Lemma fixup_1_finite :
  forall cz rz q : float, fin cz -> fin rz -> is_nan prec emax q = false ->
  fixup_1 cz rz q = (cz, rz).
Proof.
intros cz rz q F0 Fr Nq. unfold IeeeBall.ball_fixup_1. cbv zeta.
rewrite eq_self, lt_abs_pinf, Nq, F0. rewrite lt_pinf_finite by exact Fr. reflexivity.
Qed.

(* So the result, which is a canonical ball (B1), is a finite one. *)
Lemma finite_ball_2 :
  forall (core : float * float * float) (q : float),
  is_nan prec emax q = false ->
  (let '(cz0, cz1, rz) := core in fin cz0 /\ fin rz) ->
  let '(cw0, cw1, rw) := (let '(cz0, cz1, rz) := core in fixup_2 cz0 cz1 rz q) in
  ball_2 cw0 cw1 rw -> ball_finite_2 cw0 cw1 rw.
Proof.
intros [[cz0 cz1] rz] q Nq. cbv beta iota. intros [F0 Fr].
rewrite (fixup_2_finite cz0 cz1 rz q F0 Fr Nq). cbv beta iota.
intros B. now apply (ball_2_finite prec emax).
Qed.

Lemma finite_ball_1 :
  forall (core : float * float) (q : float),
  is_nan prec emax q = false ->
  (let '(cz, rz) := core in fin cz /\ fin rz) ->
  let '(cw, rw) := (let '(cz, rz) := core in fixup_1 cz rz q) in
  ball_1 cw rw -> ball_finite_1 cw rw.
Proof.
intros [cz rz] q Nq. cbv beta iota. intros [F0 Fr].
rewrite (fixup_1_finite cz rz q F0 Fr Nq). cbv beta iota.
intros B. now apply (ball_1_finite prec emax).
Qed.

(** * The full kernels: B4 *)

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

Lemma ball_add_1_full_finite :
  (2 <= prec)%Z ->
  forall cx rx cy ry : float, ball_finite_1 cx rx -> ball_finite_1 cy ry ->
  Rabs (Rabs (b2r cx + b2r cy) + b2r rx + b2r ry) <= bpow radix2 (emax - 2) ->
  let '(cw, rw) := ball_add_1_full cx rx cy ry in ball_1 cw rw -> ball_finite_1 cw rw.
Proof.
intros Hp cx rx cy ry [Fx [Frx Prx]] [Fy [Fry Pry]] Hc. unfold val in Prx, Pry.
generalize (Rabs_pos (b2r cx + b2r cy)). intros C0.
rewrite (Rabs_pos_eq (Rabs (b2r cx + b2r cy) + b2r rx + b2r ry)) in Hc by lra.
exact (finite_ball_1 (ball_add_1 cx rx cy ry) (add rx ry)
         (add_radii_not_nan rx ry Frx Fry Prx Pry)
         (ball_add_1_finite Hp cx rx cy ry Fx Frx Fy Fry Prx Pry Hc)).
Qed.

Lemma ball_sub_1_full_finite :
  (2 <= prec)%Z ->
  forall cx rx cy ry : float, ball_finite_1 cx rx -> ball_finite_1 cy ry ->
  Rabs (Rabs (b2r cx - b2r cy) + b2r rx + b2r ry) <= bpow radix2 (emax - 2) ->
  let '(cw, rw) := ball_sub_1_full cx rx cy ry in ball_1 cw rw -> ball_finite_1 cw rw.
Proof.
intros Hp cx rx cy ry [Fx [Frx Prx]] [Fy [Fry Pry]] Hc. unfold val in Prx, Pry.
generalize (Rabs_pos (b2r cx - b2r cy)). intros C0.
rewrite (Rabs_pos_eq (Rabs (b2r cx - b2r cy) + b2r rx + b2r ry)) in Hc by lra.
exact (finite_ball_1 (ball_sub_1 cx rx cy ry) (add rx ry)
         (add_radii_not_nan rx ry Frx Fry Prx Pry)
         (ball_sub_1_finite Hp cx rx cy ry Fx Frx Fy Fry Prx Pry Hc)).
Qed.

Lemma ball_mul_1_full_finite :
  (2 <= prec)%Z ->
  forall cx rx cy ry : float, ball_finite_1 cx rx -> ball_finite_1 cy ry ->
  Rabs ((Rabs (b2r cx) + b2r rx) * (Rabs (b2r cy) + b2r ry)) <= bpow radix2 (emax - 4) ->
  let '(cw, rw) := ball_mul_1_full cx rx cy ry in ball_1 cw rw -> ball_finite_1 cw rw.
Proof.
intros Hp cx rx cy ry [Fx [Frx Prx]] [Fy [Fry Pry]] Hc. unfold val in Prx, Pry.
generalize (Rabs_pos (b2r cx)) (Rabs_pos (b2r cy)). intros A0 B0.
rewrite (Rabs_pos_eq ((Rabs (b2r cx) + b2r rx) * (Rabs (b2r cy) + b2r ry))) in Hc
  by (apply Rmult_le_pos; lra).
exact (finite_ball_1 (ball_mul_1 cx rx cy ry) (add rx ry)
         (add_radii_not_nan rx ry Frx Fry Prx Pry)
         (ball_mul_1_finite Hp cx rx cy ry Fx Frx Fy Fry Prx Pry Hc)).
Qed.

Lemma ball_scale_1_full_finite :
  (2 <= prec)%Z ->
  forall cx rx a : float, ball_finite_1 cx rx -> fin a ->
  Rabs ((Rabs (b2r cx) + b2r rx) * b2r a) <= bpow radix2 (emax - 2) ->
  let '(cw, rw) := ball_scale_1_full cx rx a in ball_1 cw rw -> ball_finite_1 cw rw.
Proof.
intros Hp cx rx a [Fx [Frx Prx]] Fa Hc. unfold val in Prx.
generalize (Rabs_pos (b2r cx)). intros C0.
rewrite Rabs_mult, (Rabs_pos_eq (Rabs (b2r cx) + b2r rx)) in Hc by lra.
exact (finite_ball_1 (ball_scale_1 cx rx a) rx (finite_not_nan prec emax rx Frx)
         (ball_scale_1_finite Hp cx rx a Fx Frx Fa Prx Hc)).
Qed.

Lemma ball_add_2_full_finite :
  (3 <= prec)%Z ->
  forall cx0 cx1 rx cy0 cy1 ry : float, ball_finite_2 cx0 cx1 rx -> ball_finite_2 cy0 cy1 ry ->
  Rabs (Rabs ((b2r cx0 + b2r cx1) + (b2r cy0 + b2r cy1)) + b2r rx + b2r ry)
  <= bpow radix2 (emax - 2) ->
  let '(cw0, cw1, rw) := ball_add_2_full cx0 cx1 rx cy0 cy1 ry in
  ball_2 cw0 cw1 rw -> ball_finite_2 cw0 cw1 rw.
Proof.
intros Hp cx0 cx1 rx cy0 cy1 ry [F0 [F1 [Nx [Frx Prx]]]] [G0 [G1 [Ny [Fry Pry]]]] Hc.
unfold val in Prx, Pry.
generalize (Rabs_pos ((b2r cx0 + b2r cx1) + (b2r cy0 + b2r cy1))). intros C0.
rewrite (Rabs_pos_eq (Rabs ((b2r cx0 + b2r cx1) + (b2r cy0 + b2r cy1)) + b2r rx + b2r ry))
  in Hc by lra.
exact (finite_ball_2 (ball_add_2 cx0 cx1 rx cy0 cy1 ry) (add rx ry)
         (add_radii_not_nan rx ry Frx Fry Prx Pry)
         (ball_add_2_finite Hp cx0 cx1 rx cy0 cy1 ry F0 F1 G0 G1 Nx Ny Frx Fry Prx Pry Hc)).
Qed.

Lemma ball_sub_2_full_finite :
  (3 <= prec)%Z ->
  forall cx0 cx1 rx cy0 cy1 ry : float, ball_finite_2 cx0 cx1 rx -> ball_finite_2 cy0 cy1 ry ->
  Rabs (Rabs ((b2r cx0 + b2r cx1) - (b2r cy0 + b2r cy1)) + b2r rx + b2r ry)
  <= bpow radix2 (emax - 2) ->
  let '(cw0, cw1, rw) := ball_sub_2_full cx0 cx1 rx cy0 cy1 ry in
  ball_2 cw0 cw1 rw -> ball_finite_2 cw0 cw1 rw.
Proof.
intros Hp cx0 cx1 rx cy0 cy1 ry [F0 [F1 [Nx [Frx Prx]]]] [G0 [G1 [Ny [Fry Pry]]]] Hc.
unfold val in Prx, Pry.
generalize (Rabs_pos ((b2r cx0 + b2r cx1) - (b2r cy0 + b2r cy1))). intros C0.
rewrite (Rabs_pos_eq (Rabs ((b2r cx0 + b2r cx1) - (b2r cy0 + b2r cy1)) + b2r rx + b2r ry))
  in Hc by lra.
exact (finite_ball_2 (ball_sub_2 cx0 cx1 rx cy0 cy1 ry) (add rx ry)
         (add_radii_not_nan rx ry Frx Fry Prx Pry)
         (ball_sub_2_finite Hp cx0 cx1 rx cy0 cy1 ry F0 F1 G0 G1 Nx Ny Frx Fry Prx Pry Hc)).
Qed.

Lemma ball_mul_2_full_finite :
  (4 <= prec)%Z ->
  forall cx0 cx1 rx cy0 cy1 ry : float, ball_finite_2 cx0 cx1 rx -> ball_finite_2 cy0 cy1 ry ->
  Rabs ((Rabs (b2r cx0 + b2r cx1) + b2r rx) * (Rabs (b2r cy0 + b2r cy1) + b2r ry))
  <= bpow radix2 (emax - 2) ->
  let '(cw0, cw1, rw) := ball_mul_2_full cx0 cx1 rx cy0 cy1 ry in
  ball_2 cw0 cw1 rw -> ball_finite_2 cw0 cw1 rw.
Proof.
intros Hp cx0 cx1 rx cy0 cy1 ry [F0 [F1 [Nx [Frx Prx]]]] [G0 [G1 [Ny [Fry Pry]]]] Hc.
unfold val in Prx, Pry.
generalize (Rabs_pos (b2r cx0 + b2r cx1)) (Rabs_pos (b2r cy0 + b2r cy1)). intros A0 B0.
rewrite (Rabs_pos_eq ((Rabs (b2r cx0 + b2r cx1) + b2r rx) * (Rabs (b2r cy0 + b2r cy1) + b2r ry)))
  in Hc by (apply Rmult_le_pos; lra).
exact (finite_ball_2 (ball_mul_2 cx0 cx1 rx cy0 cy1 ry) (add rx ry)
         (add_radii_not_nan rx ry Frx Fry Prx Pry)
         (ball_mul_2_finite Hp cx0 cx1 rx cy0 cy1 ry F0 F1 G0 G1 Nx Ny Frx Fry Prx Pry Hc)).
Qed.

Lemma ball_scale_2_full_finite :
  (2 <= prec)%Z ->
  forall cx0 cx1 rx a : float, ball_finite_2 cx0 cx1 rx -> fin a ->
  Rabs ((Rabs (b2r cx0 + b2r cx1) + b2r rx) * b2r a) <= bpow radix2 (emax - 2) ->
  let '(cw0, cw1, rw) := ball_scale_2_full cx0 cx1 rx a in
  ball_2 cw0 cw1 rw -> ball_finite_2 cw0 cw1 rw.
Proof.
intros Hp cx0 cx1 rx a [F0 [F1 [Nx [Frx Prx]]]] Fa Hc. unfold val in Prx.
generalize (Rabs_pos (b2r cx0 + b2r cx1)). intros C0.
rewrite Rabs_mult, (Rabs_pos_eq (Rabs (b2r cx0 + b2r cx1) + b2r rx)) in Hc by lra.
exact (finite_ball_2 (ball_scale_2 cx0 cx1 rx a) rx (finite_not_nan prec emax rx Frx)
         (ball_scale_2_finite Hp cx0 cx1 rx a F0 F1 Nx Frx Fa Prx Hc)).
Qed.

End IeeeBallFinite.

(** * The statements of proofs/gen/IeeeStatements.v *)

Theorem ball_add_1_full_correct : ball_add_1_full_spec.
Proof.
intros prec emax Hp He nan_plus nan_abs nan_fma Hp2 cx rx cy ry Bx By.
generalize (ball_add_1_full_facts prec emax nan_plus nan_abs nan_fma Hp2 cx rx cy ry Bx By)
           (ball_add_1_full_finite prec emax nan_plus nan_abs nan_fma Hp2 cx rx cy ry).
destruct (IeeeModel.ball_add_1_full prec emax nan_plus nan_abs nan_fma cx rx cy ry) as [cw rw].
intros [B1 [B2 B3]] B4.
split; [exact B1|split; [exact B2|split; [|split]]].
- intros Fw. destruct (B3 Fw) as [[Fx Fy] C]. split; [exact Fx|split; [exact Fy|exact C]].
- intros Fx Fy Hc. exact (B4 Fx Fy Hc B1).
- exact (every_case_1 prec emax Rplus _ _ _ _ _ _ B1 B2 B3).
Qed.

Theorem ball_sub_1_full_correct : ball_sub_1_full_spec.
Proof.
intros prec emax Hp He nan_plus nan_opp nan_abs nan_fma Hp2 cx rx cy ry Bx By.
generalize (ball_sub_1_full_facts prec emax nan_plus nan_opp nan_abs nan_fma Hp2 cx rx cy ry Bx By)
           (ball_sub_1_full_finite prec emax nan_plus nan_opp nan_abs nan_fma Hp2 cx rx cy ry).
destruct (IeeeModel.ball_sub_1_full prec emax nan_plus nan_opp nan_abs nan_fma cx rx cy ry) as [cw rw].
intros [B1 [B2 B3]] B4.
split; [exact B1|split; [exact B2|split; [|split]]].
- intros Fw. destruct (B3 Fw) as [[Fx Fy] C]. split; [exact Fx|split; [exact Fy|exact C]].
- intros Fx Fy Hc. exact (B4 Fx Fy Hc B1).
- exact (every_case_1 prec emax Rminus _ _ _ _ _ _ B1 B2 B3).
Qed.

Theorem ball_mul_1_full_correct : ball_mul_1_full_spec.
Proof.
intros prec emax Hp He nan_plus nan_abs nan_fma Hp2 cx rx cy ry Bx By.
generalize (ball_mul_1_full_facts prec emax nan_plus nan_abs nan_fma Hp2 cx rx cy ry Bx By)
           (ball_mul_1_full_finite prec emax nan_plus nan_abs nan_fma Hp2 cx rx cy ry).
destruct (IeeeModel.ball_mul_1_full prec emax nan_plus nan_abs nan_fma cx rx cy ry) as [cw rw].
intros [B1 [B2 B3]] B4.
split; [exact B1|split; [exact B2|split; [|split]]].
- intros Fw. destruct (B3 Fw) as [[Fx Fy] C]. split; [exact Fx|split; [exact Fy|exact C]].
- intros Fx Fy Hc. exact (B4 Fx Fy Hc B1).
- exact (every_case_1 prec emax Rmult _ _ _ _ _ _ B1 B2 B3).
Qed.

Theorem ball_scale_1_full_correct : ball_scale_1_full_spec.
Proof.
intros prec emax Hp He nan_abs nan_fma Hp2 cx rx a Bx.
generalize (ball_scale_1_full_facts prec emax nan_abs nan_fma Hp2 cx rx a Bx)
           (ball_scale_1_full_finite prec emax nan_abs nan_fma Hp2 cx rx a).
destruct (IeeeModel.ball_scale_1_full prec emax nan_abs nan_fma cx rx a) as [cw rw].
intros [B1 [B2 B3]] B4.
split; [exact B1|split; [exact B2|split; [|split]]].
- intros Fw. destruct (B3 Fw) as [[Fx Fa] C]. split; [exact Fx|split; [exact Fa|exact C]].
- intros Fx Fa Hc. exact (B4 Fx Fa Hc B1).
- intros Fa. apply (every_case_scale_1 prec emax (fun x : R => x * val a) _ _ _ _ B1 B2).
  intros Fw. destruct (B3 Fw) as [[Fx _] C]. split; [exact Fx|exact C].
Qed.

Theorem ball_add_2_full_correct : ball_add_2_full_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_abs nan_fma Hpm cx0 cx1 rx cy0 cy1 ry Bx By.
generalize (ball_add_2_full_facts prec emax nan_plus nan_minus (fun x => nan_plus x x) nan_abs nan_fma Hpm cx0 cx1 rx cy0 cy1 ry Bx By)
           (ball_add_2_full_finite prec emax nan_plus nan_minus (fun x => nan_plus x x) nan_abs nan_fma Hpm cx0 cx1 rx cy0 cy1 ry).
destruct (IeeeModel.ball_add_2_full prec emax nan_plus nan_minus nan_abs nan_fma cx0 cx1 rx cy0 cy1 ry) as [[cw0 cw1] rw].
intros [B1 [B2 B3]] B4.
split; [exact B1|split; [exact B2|split; [|split]]].
- intros Fw. destruct (B3 Fw) as [[Fx Fy] C]. split; [exact Fx|split; [exact Fy|exact C]].
- intros Fx Fy Hc. exact (B4 Fx Fy Hc B1).
- exact (every_case_2 prec emax Rplus _ _ _ _ _ _ _ _ _ B1 B2 B3).
Qed.

Theorem ball_sub_2_full_correct : ball_sub_2_full_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma Hpm cx0 cx1 rx cy0 cy1 ry Bx By.
generalize (ball_sub_2_full_facts prec emax nan_plus nan_minus nan_opp nan_abs nan_fma Hpm cx0 cx1 rx cy0 cy1 ry Bx By)
           (ball_sub_2_full_finite prec emax nan_plus nan_minus nan_opp nan_abs nan_fma Hpm cx0 cx1 rx cy0 cy1 ry).
destruct (IeeeModel.ball_sub_2_full prec emax nan_plus nan_minus nan_opp nan_abs nan_fma cx0 cx1 rx cy0 cy1 ry) as [[cw0 cw1] rw].
intros [B1 [B2 B3]] B4.
split; [exact B1|split; [exact B2|split; [|split]]].
- intros Fw. destruct (B3 Fw) as [[Fx Fy] C]. split; [exact Fx|split; [exact Fy|exact C]].
- intros Fx Fy Hc. exact (B4 Fx Fy Hc B1).
- exact (every_case_2 prec emax Rminus _ _ _ _ _ _ _ _ _ B1 B2 B3).
Qed.

Theorem ball_mul_2_full_correct : ball_mul_2_full_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma Hpm cx0 cx1 rx cy0 cy1 ry Bx By.
generalize (ball_mul_2_full_facts prec emax nan_plus nan_minus nan_opp nan_abs nan_fma Hpm cx0 cx1 rx cy0 cy1 ry Bx By)
           (ball_mul_2_full_finite prec emax nan_plus nan_minus nan_opp nan_abs nan_fma Hpm cx0 cx1 rx cy0 cy1 ry).
destruct (IeeeModel.ball_mul_2_full prec emax nan_plus nan_minus nan_opp nan_abs nan_fma cx0 cx1 rx cy0 cy1 ry) as [[cw0 cw1] rw].
intros [B1 [B2 B3]] B4.
split; [exact B1|split; [exact B2|split; [|split]]].
- intros Fw. destruct (B3 Fw) as [[Fx Fy] C]. split; [exact Fx|split; [exact Fy|exact C]].
- intros Fx Fy Hc. exact (B4 Fx Fy Hc B1).
- exact (every_case_2 prec emax Rmult _ _ _ _ _ _ _ _ _ B1 B2 B3).
Qed.

Theorem ball_scale_2_full_correct : ball_scale_2_full_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma Hp2 cx0 cx1 rx a Bx.
generalize (ball_scale_2_full_facts prec emax nan_plus nan_minus nan_opp nan_abs nan_fma Hp2
              cx0 cx1 rx a Bx)
           (ball_scale_2_full_finite prec emax nan_plus nan_minus nan_opp nan_abs nan_fma Hp2
              cx0 cx1 rx a).
destruct (IeeeModel.ball_scale_2_full prec emax nan_plus nan_minus nan_opp nan_abs nan_fma
            cx0 cx1 rx a) as [[cw0 cw1] rw].
intros [B1 [B2 B3]] B4.
split; [exact B1|split; [exact B2|split; [|split]]].
- intros Fw. destruct (B3 Fw) as [[Fx Fa] C]. split; [exact Fx|split; [exact Fa|exact C]].
- intros Fx Fa Hc. exact (B4 Fx Fa Hc B1).
- intros Fa. apply (every_case_scale_2 prec emax (fun x : R => x * val a) _ _ _ _ _ _ B1 B2).
  intros Fw. destruct (B3 Fw) as [[Fx _] C]. split; [exact Fx|exact C].
Qed.

(* Ball<T, 2> * T (rule R3, the factors of a fused operation): ball_scale_2_full on the guarded
   scalar. The statement says of a only whether it is finite and its value, which the guard keeps
   (guard_finite, guard_val), so it is that of ball_scale_2_full on the guarded a. *)
Theorem ball_scale_2_full_entry_correct : ball_scale_2_full_entry_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma Hp2 cx0 cx1 rx a Bx.
generalize (ball_scale_2_full_correct prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma Hp2
              cx0 cx1 rx (IeeeOperations.guard prec emax nan_plus a) Bx).
unfold IeeeModel.ball_scale_2_full_entry. cbv zeta.
destruct (IeeeModel.ball_scale_2_full prec emax nan_plus nan_minus nan_opp nan_abs nan_fma cx0 cx1 rx
            (IeeeOperations.guard prec emax nan_plus a)) as [[cw0 cw1] rw].
assert (Fa : finite (IeeeOperations.guard prec emax nan_plus a) <-> finite a).
{ unfold finite. rewrite (guard_finite prec emax nan_plus). tauto. }
assert (Va : val (IeeeOperations.guard prec emax nan_plus a) = val a)
  by exact (guard_val prec emax nan_plus a).
rewrite Va. intros [B1 [B2 [B3 [B4 B5]]]].
split; [exact B1|split; [exact B2|split; [|split]]].
- intros Fw. destruct (B3 Fw) as [Fx [Ga C]]. split; [exact Fx|split; [now apply Fa|exact C]].
- intros Fx Ga Hc. apply (B4 Fx); [now apply Fa|exact Hc].
- intros Ga. apply B5. now apply Fa.
Qed.
