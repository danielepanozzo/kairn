(* The product of two ball vectors of one limb in the IEEE model, V4: under the conditions of
   its generated statement the result is a finite ball vector (bv_conv_1_ieee_v4), and the
   generated statement bv_conv_1_ieee_spec (proofs/gen/IeeeFoldStatements.v), the
   conjunction of V1 to V4 and the flag (bv_conv_1_ieee_correct).

   The conditions, for finite radii, with n = min(n_x, n_y), Q = 2^(emax - 2), u = 2^-prec,
   eta = 2^emin and eps = u / (1 + u): n (eps + eta) <= 1/16, rx ry <= Q, (|x| + rx) ry <= Q
   for every entry x, (|y| + ry) rx <= Q for every entry y, n (|x| + rx) (|y| + ry) <= Q for
   every pair. The flag is true when the convolution's mask and the bound's are true and the
   radius is finite (bv_conv_finish_facts); each is shown by bounding every value the
   IEEE model computes below 7/2 Q, under the largest number Omega = 4 Q (1 - u) >= 15/4 Q:
   an operation of the IEEE model on finite operands whose rounded real result is in range
   returns that result (fma_spec, add_spec of IeeeBridge.v).

   - The count: n <= (1 + u) / (16 u) <= 2^prec is a number of the format, so the count
     rounded up is n, finite (count_exact).
   - The bound (bound_dot_1_given): from m (eps + eta) <= 1/16, with RN(x) <= (1 + u) x + eta/2
     and RU(x) <= (1 + 2 u) x + eta for x >= 0, u <= 1/16, eta <= 1/64 and Q >= 8 (prec >= 4
     and emax > prec): a <= 0.154 <= up(1/4), aa <= 0.159, d <= 0.336, w <= 1.727,
     g <= 0.3 <= up(1), so the mask is true; the term eta / (2 u) of the constant of tm, times
     m, is at most 1 / (32 u) = 2^(prec - 5) <= Q / 16 (m eta <= 1/16 and emax >= prec + 1), so
     tm <= 0.201 + 0.0748 Q and t <= Q / 4.
   - The coefficients (dot_1_forward): coefficient j is the fused dot product of at most n
     terms, each |x y| <= Q / n; every state on the way is the real model's state on a prefix
     of the terms, within (1 + eps)^k <= 16/15 of the sum of the magnitudes of the products
     (dot_1_seq_correct of FoldSums.v, pow_mult_le_1 of Summation.v), so at most 1.1 Q.
   - The radius (conv_radius_given): with P = (Ma + rx) (Mb + ry), Ma and Mb the largest
     magnitudes of the entries (attained, maxl_attained), P <= Q and m P <= Q (the pairs'
     condition when both operands have entries, the conditions of one array or of the radii
     otherwise, P_bound); the chain of the radius kernel is then at most 1.2745 P + 3 eta at
     e, 1.65 Q at s, 0.15 Q at hm, and 3.21 Q at the radius (conv_radius_given).
   The two-limb product is not here: as printed, its V4 is false where the count overflows
   (docs/proofs/index.md). *)
From Stdlib Require Import Reals ZArith List Arith Bool Lia Lra Psatz.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements IeeeStatements FoldStatements IeeeFoldStatements.
From Kairn Require Import Format Folds Summation IeeeBridge IeeeVocabulary IeeeOps IeeeFoldNorm.
From Kairn Require Import IeeeBvConv.
From Kairn Require IeeeBv IeeeFoldConv IeeeFoldMaps IeeeAccumulator BvConv Directed2 FoldConv FoldNorm
  FoldSums BvReal.
From Kairn Require IeeeOperations.
From Kairn.Gen Require IeeeModel FoldModel IeeeFoldModel.
Import ListNotations.
Open Scope R_scope.

Local Notation maxl l := (fold_right Rmax 0 l).

(* The largest magnitude of a nonempty list is that of one of its elements. *)
Lemma maxl_attained :
  forall l : list R, l <> [] -> exists x, In x l /\ maxl (map (fun w => Rabs w) l) = Rabs x.
Proof.
induction l as [|a l IH]; intros H. { contradiction. }
cbn [map fold_right].
destruct l as [|b l'].
- exists a. split. left. reflexivity. cbn [map fold_right].
  apply Rmax_left. apply Rabs_pos.
- destruct (IH ltac:(discriminate)) as [x [Hx E]].
  destruct (Rle_dec (maxl (map (fun w => Rabs w) (b :: l'))) (Rabs a)) as [L|L].
  + exists a. split. left. reflexivity. apply Rmax_left. exact L.
  + exists x. split. right. exact Hx. rewrite Rmax_right by lra. exact E.
Qed.

Section V4.
Variable prec emax : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Context {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}.
Hypothesis Hp4 : (4 <= prec)%Z.

Notation float := (binary_float prec emax).
Notation nan_of := {x : float | is_nan prec emax x = true}.
Variable nan_plus : float -> float -> nan_of.
Variable nan_abs : float -> nan_of.
Variable nan_fma : float -> float -> float -> nan_of.
Variable nan_const : nan_of.

Notation emin := (3 - emax - prec)%Z.
Notation fexp := (FLT_exp emin prec).
Notation format := (generic_format radix2 fexp).
Notation rnd := (round radix2 fexp (Znearest tie_even)).
Notation RU := (round radix2 fexp Zceil).
Notation fin x := (is_finite prec emax x = true).
Notation b2r := (B2R prec emax).
Notation uu := (u prec).
Notation ee := (eta emin).
Notation Q := (bpow radix2 (emax - 2)).
Notation E1 := (1 / (1 + u prec) * u prec ^ 1).
Notation add := (IeeeOperations.add prec emax nan_plus).
Notation fma := (IeeeOperations.fma prec emax nan_fma).
Notation prod := (IeeeOperations.prod prec emax nan_fma).
Notation pzero := (IeeeOperations.pzero prec emax).

(** * The format *)

Lemma emax_gt : (prec + 1 <= emax)%Z.
Proof. generalize prec_lt_emax_. unfold BinarySingleNaN.Prec_lt_emax. lia. Qed.

Lemma uu_bounds : 0 < uu <= / 16.
Proof.
split. apply bpow_gt_0. unfold u. replace (/ 16) with (bpow radix2 (-4)) by reflexivity.
apply bpow_le. lia.
Qed.

Lemma ee_bounds : 0 < ee <= / 64.
Proof.
split. apply bpow_gt_0. unfold eta. replace (/ 64) with (bpow radix2 (-6)) by reflexivity.
apply bpow_le. generalize emax_gt. lia.
Qed.

Lemma Q_ge_8 : 8 <= Q.
Proof.
replace 8 with (bpow radix2 3) by reflexivity. apply bpow_le. generalize emax_gt. lia.
Qed.

Lemma top_Q : bpow radix2 emax = 4 * Q.
Proof.
replace emax with (2 + (emax - 2))%Z at 1 by ring. rewrite bpow_plus.
change (bpow radix2 2) with 4. ring.
Qed.

(* 1 / (2 u) = 2^(prec - 1) <= Q: emax >= prec + 1. *)
Lemma inv_2u_le : / (2 * uu) <= Q.
Proof.
assert (E : / (2 * uu) = bpow radix2 (prec - 1)).
{ unfold u. rewrite bpow_opp. replace (prec - 1)%Z with (prec + -1)%Z by ring.
  rewrite (bpow_plus radix2 prec (-1)).
  assert (B : bpow radix2 (-1) = / 2) by reflexivity.
  rewrite B. field. apply Rgt_not_eq, bpow_gt_0. }
rewrite E. apply bpow_le. generalize emax_gt. lia.
Qed.

(* eta / (2 u), the smallest normal number, is 2^(2 - emax) <= 1/8. *)
Lemma ee_2u : 0 <= ee / (2 * uu) <= / 8.
Proof.
destruct uu_bounds as [U0 U1]. split.
{ unfold Rdiv. apply Rmult_le_pos. apply bpow_ge_0. apply Rlt_le, Rinv_0_lt_compat. lra. }
unfold Rdiv. replace (eta (3 - emax - prec) * / (2 * u prec)) with (bpow radix2 (2 - emax)).
- replace (/ 8) with (bpow radix2 (-3)) by reflexivity. apply bpow_le. generalize emax_gt. lia.
- unfold eta, u. rewrite (bpow_opp radix2 prec).
  replace (2 - emax)%Z with ((3 - emax - prec) + prec + -1)%Z by ring.
  rewrite !bpow_plus. change (bpow radix2 (-1)) with (/ 2). field.
  apply Rgt_not_eq, bpow_gt_0.
Qed.

(* A rounded value at most 7/2 Q in magnitude is in range. *)
Lemma inrange_of : forall v : R, Rabs v <= 7 / 2 * Q -> inrange emax v.
Proof.
intros v H. unfold inrange. rewrite top_Q. generalize Q_ge_8. lra.
Qed.

Lemma rnd_up : forall x : R, 0 <= x -> rnd x <= (1 + uu) * x + ee / 2.
Proof. intros x Hx. exact (Directed2.rnd_upper emin prec x Hx). Qed.

Lemma rnd_nonneg : forall x : R, 0 <= x -> 0 <= rnd x.
Proof.
intros x Hx. apply round_ge_generic; auto with typeclass_instances. apply generic_format_0.
Qed.

Lemma RU_up : forall x : R, 0 <= x -> RU x <= (1 + 2 * uu) * x + ee.
Proof.
intros x Hx.
generalize (error_le_ulp radix2 fexp Zceil x) (Directed2.ulp_le_max emin prec x).
rewrite (Rabs_pos_eq x Hx). intros E M. apply Rabs_le_inv in E.
assert (K : Rmax ee (2 * uu * x) <= ee + 2 * uu * x).
{ apply Rmax_lub. generalize uu_bounds. nra. generalize ee_bounds. lra. }
lra.
Qed.

Lemma RU_nonneg : forall x : R, 0 <= x -> 0 <= RU x.
Proof.
intros x Hx. apply round_ge_generic; auto with typeclass_instances. apply generic_format_0.
Qed.

(* The two roundings, with the constants of the smallest precision. *)
Lemma rnd_bound :
  forall x X : R, 0 <= x -> x <= X -> 0 <= rnd x /\ rnd x <= 17 / 16 * X + ee / 2.
Proof.
intros x X H0 H1. split. apply rnd_nonneg; lra.
apply Rle_trans with (1 := rnd_up x H0).
destruct uu_bounds as [U0 U1].
assert (K : (1 + uu) * x <= 17 / 16 * X) by (apply Rmult_le_compat; lra). lra.
Qed.

Lemma pow_1u : forall k : nat, 1 <= (1 + uu) ^ k <= (17 / 16) ^ k.
Proof.
intros k. destruct uu_bounds as [U0 U1]. split.
- apply pow_R1_Rle. lra.
- apply pow_incr. lra.
Qed.

Lemma RU_bound :
  forall x X : R, 0 <= x -> x <= X -> 0 <= RU x /\ RU x <= 9 / 8 * X + ee.
Proof.
intros x X H0 H1. split. apply RU_nonneg; lra.
apply Rle_trans with (1 := RU_up x H0).
destruct uu_bounds as [U0 U1].
assert (K : (1 + 2 * uu) * x <= 9 / 8 * X) by (apply Rmult_le_compat; lra). lra.
Qed.

Lemma mul_le :
  forall a b A B : R, 0 <= a -> a <= A -> 0 <= b -> b <= B -> 0 <= a * b /\ a * b <= A * B.
Proof.
intros a b A B Ha HA Hb HB. split. apply Rmult_le_pos; assumption.
apply Rmult_le_compat; assumption.
Qed.

Lemma range_le : forall v B : R, 0 <= v -> v <= B -> B <= 7 / 2 * Q -> Rabs v <= 7 / 2 * Q.
Proof. intros v B H0 H1 H2. rewrite Rabs_pos_eq by exact H0. lra. Qed.

(* One fused operation, a product, an addition: on finite operands, finite with the rounded
   real result when that result is in range. *)
Lemma fma_ok :
  forall x y z : float, fin x -> fin y -> fin z ->
  Rabs (rnd (b2r x * b2r y + b2r z)) <= 7 / 2 * Q ->
  fin (fma x y z) /\ b2r (fma x y z) = rnd (b2r x * b2r y + b2r z).
Proof.
intros x y z Fx Fy Fz H. destruct (fma_spec prec emax nan_fma x y z Fx Fy Fz) as [S1 S2].
assert (F : fin (fma x y z)) by (apply S1; apply inrange_of; exact H).
split. exact F. exact (S2 F).
Qed.

Lemma prod_ok :
  forall x y : float, fin x -> fin y -> Rabs (rnd (b2r x * b2r y + 0)) <= 7 / 2 * Q ->
  fin (prod x y) /\ b2r (prod x y) = rnd (b2r x * b2r y + 0).
Proof. intros x y Fx Fy H. exact (fma_ok x y pzero Fx Fy eq_refl H). Qed.

Lemma add_ok :
  forall x y : float, fin x -> fin y -> Rabs (rnd (b2r x + b2r y)) <= 7 / 2 * Q ->
  fin (add x y) /\ b2r (add x y) = rnd (b2r x + b2r y).
Proof.
intros x y Fx Fy H. destruct (add_spec prec emax nan_plus x y Fx Fy) as [S1 S2].
assert (F : fin (add x y)) by (apply S1; apply inrange_of; exact H).
split. exact F. exact (S2 F).
Qed.

(* A constant rounded up from a nonnegative expression at most 2: finite, of that value. *)
Lemma const_ok :
  forall e : R, 0 <= e -> e <= 2 ->
  fin (IeeeOperations.const_of prec emax (RU e)) /\
  b2r (IeeeOperations.const_of prec emax (RU e)) = RU e.
Proof.
intros e H0 H2.
assert (F2 : format 2).
{ replace 2 with (bpow radix2 1) by reflexivity. apply generic_format_bpow.
  unfold FLT_exp. generalize emax_gt. lia. }
assert (L2 : 2 < bpow radix2 emax) by (rewrite top_Q; generalize Q_ge_8; lra).
destruct (const_of_RU prec emax e 2 H0 H2 F2 L2) as [F [V _]]. split; assumption.
Qed.

(** * The count *)

Lemma count_exact :
  forall n : nat, INR n <= bpow radix2 prec ->
  fin (binary_normalize prec emax prec_gt_0_ prec_lt_emax_ BinarySingleNaN.mode_UP
         (Z.of_nat n) 0 false) /\
  b2r (binary_normalize prec emax prec_gt_0_ prec_lt_emax_ BinarySingleNaN.mode_UP
         (Z.of_nat n) 0 false) = INR n.
Proof.
intros n Hn.
assert (Fn : format (INR n)).
{ rewrite INR_IZR_INZ. replace (IZR (Z.of_nat n)) with (IZR (Z.of_nat n) * bpow radix2 0)
    by (change (bpow radix2 0) with 1; ring).
  apply (format_multiple emin prec). generalize emax_gt. lia.
  rewrite Rmult_1_r, Zplus_0_l. rewrite <- INR_IZR_INZ, Rabs_pos_eq by apply pos_INR.
  exact Hn. }
assert (Rn : RU (INR n) = INR n) by (apply round_generic; auto with typeclass_instances).
generalize (binary_normalize_correct prec emax prec_gt_0_ prec_lt_emax_ BinarySingleNaN.mode_UP
              (Z.of_nat n) 0 false).
assert (E : F2R (Float radix2 (Z.of_nat n) 0) = INR n).
{ unfold F2R. cbn [Fnum Fexp]. rewrite <- INR_IZR_INZ. simpl. ring. }
rewrite E.
change (round radix2 (SpecFloat.fexp prec emax)
          (BinarySingleNaN.round_mode BinarySingleNaN.mode_UP) (INR n))
  with (RU (INR n)).
rewrite Rn.
assert (L : Rabs (INR n) < bpow radix2 emax).
{ rewrite Rabs_pos_eq by apply pos_INR. apply Rle_lt_trans with (1 := Hn). apply bpow_lt.
  generalize emax_gt. lia. }
rewrite (Rlt_bool_true _ _ L). intros [V [F _]]. split; assumption.
Qed.

(** * The bound *)

Lemma E1_bounds : 0 <= E1 <= uu.
Proof.
generalize uu_bounds. intros [U0 U1].
assert (D : 0 < 1 + uu) by lra.
split.
- apply Rmult_le_pos. unfold Rdiv. apply Rmult_le_pos. lra. apply Rlt_le, Rinv_0_lt_compat. lra.
  rewrite pow_1. lra.
- replace (1 / (1 + uu) * uu ^ 1) with (uu / (1 + uu)) by (rewrite pow_1; field; lra).
  apply Rmult_le_reg_r with (1 + uu). lra. unfold Rdiv. rewrite Rmult_assoc, Rinv_l by lra. nra.
Qed.

Lemma bound_dot_1_given :
  forall m : float, fin m -> 0 <= b2r m -> b2r m * (E1 + ee) <= / 16 ->
  fin (fst (fst (IeeeModel.bound_dot_1 prec emax nan_plus nan_fma m))) /\
  fin (snd (fst (IeeeModel.bound_dot_1 prec emax nan_plus nan_fma m))) /\
  snd (IeeeModel.bound_dot_1 prec emax nan_plus nan_fma m) = true /\
  0 <= b2r (fst (fst (IeeeModel.bound_dot_1 prec emax nan_plus nan_fma m))) <= / 2 /\
  0 <= b2r (snd (fst (IeeeModel.bound_dot_1 prec emax nan_plus nan_fma m))) <= Q / 4.
Proof.
intros m Fm Pm Hm.
destruct uu_bounds as [U0 U1]. destruct ee_bounds as [H0 H1]. destruct E1_bounds as [D0 D1].
generalize Q_ge_8 inv_2u_le. intros Q8 Iu.
set (M := b2r m) in *.
rewrite Rmult_plus_distr_l in Hm.
assert (Me0 : 0 <= M * ee) by (apply Rmult_le_pos; lra).
assert (Mf0 : 0 <= M * E1) by (apply Rmult_le_pos; lra).
assert (Me : M * ee <= / 16) by lra.
assert (Mf : M * E1 <= / 16) by lra.
(* the constants *)
assert (P1 : 1 + uu <= 17 / 16) by lra.
assert (P2 : (1 + uu) ^ 2 <= 17 / 16 * (17 / 16)).
{ replace ((1 + uu) ^ 2) with ((1 + uu) * (1 + uu)) by ring. apply Rmult_le_compat; lra. }
unfold IeeeModel.bound_dot_1. cbv zeta. cbn [fst snd].
set (c0 := IeeeModel.up_bound_dot_1_0 prec emax).
set (c1 := IeeeModel.up_bound_dot_1_1 prec emax).
set (c2 := IeeeModel.up_bound_dot_1_2 prec emax).
set (c3 := IeeeModel.up_bound_dot_1_3 prec emax).
set (c4 := IeeeModel.up_bound_dot_1_4 prec emax).
set (c5 := IeeeModel.up_bound_dot_1_5 prec emax).
set (c6 := IeeeModel.up_bound_dot_1_6 prec emax).
assert (P0 : 0 <= (1 + uu) ^ 2) by (apply pow_le; lra).
assert (X0 : 0 <= (1 + uu) * (E1 + ee / 2) <= 2).
{ split. apply Rmult_le_pos; lra.
  assert (K : (1 + uu) * (E1 + ee / 2) <= 17 / 16 * (/ 16 + / 128))
    by (apply Rmult_le_compat; lra). lra. }
assert (X1 : 0 <= (1 + uu) ^ 2 * (E1 + ee) <= 2).
{ split. apply Rmult_le_pos; lra.
  assert (K : (1 + uu) ^ 2 * (E1 + ee) <= 17 / 16 * (17 / 16) * (/ 16 + / 64))
    by (apply Rmult_le_compat; lra). lra. }
assert (X4 : 0 <= (1 + uu) ^ 2 * (1 / 2 * ee + ee) + ee / (2 * uu) <= 2).
{
  assert (I0 : 0 <= ee / (2 * uu)).
  { unfold Rdiv. apply Rmult_le_pos. lra. apply Rlt_le, Rinv_0_lt_compat. lra. }
  assert (I1 : ee / (2 * uu) <= / 8).
  { unfold Rdiv.
    (* ee / (2 u) = 2^(emin + prec - 1) = 2^(2 - emax) <= 1/8 *)
    replace (ee * / (2 * uu)) with (bpow radix2 (2 - emax)).
    - replace (/ 8) with (bpow radix2 (-3)) by reflexivity. apply bpow_le.
      generalize emax_gt. lia.
    - unfold eta, u. rewrite (bpow_opp radix2 prec).
      replace (2 - emax)%Z with ((3 - emax - prec) + prec + -1)%Z by ring.
      rewrite !bpow_plus. change (bpow radix2 (-1)) with (/ 2). field.
      apply Rgt_not_eq, bpow_gt_0. }
  assert (K0 : 0 <= (1 + uu) ^ 2 * (1 / 2 * ee + ee)) by (apply Rmult_le_pos; lra).
  assert (K : (1 + uu) ^ 2 * (1 / 2 * ee + ee) <= 17 / 16 * (17 / 16) * (3 / 2 * / 64))
    by (apply Rmult_le_compat; lra).
  split; lra. }
destruct (const_ok _ (proj1 X0) (proj2 X0)) as [Fc0 Vc0].
destruct (const_ok _ (proj1 X1) (proj2 X1)) as [Fc1 Vc1].
destruct (const_ok 2 ltac:(lra) ltac:(lra)) as [Fc2 Vc2].
destruct (const_ok (1 + 2 * uu) ltac:(lra) ltac:(lra)) as [Fc3 Vc3].
destruct (const_ok _ (proj1 X4) (proj2 X4)) as [Fc4 Vc4].
destruct (const_ok (1 / 4) ltac:(lra) ltac:(lra)) as [Fc5 Vc5].
destruct (const_ok 1 ltac:(lra) ltac:(lra)) as [Fc6 Vc6].
change (IeeeOperations.const_of prec emax (RU ((1 + uu) * (E1 + ee / 2)))) with c0 in Fc0, Vc0.
change (IeeeOperations.const_of prec emax (RU ((1 + uu) ^ 2 * (E1 + ee)))) with c1 in Fc1, Vc1.
change (IeeeOperations.const_of prec emax (RU 2)) with c2 in Fc2, Vc2.
change (IeeeOperations.const_of prec emax (RU (1 + 2 * uu))) with c3 in Fc3, Vc3.
change (IeeeOperations.const_of prec emax (RU ((1 + uu) ^ 2 * (1 / 2 * ee + ee) + ee / (2 * uu))))
  with c4 in Fc4, Vc4.
change (IeeeOperations.const_of prec emax (RU (1 / 4))) with c5 in Fc5, Vc5.
change (IeeeOperations.const_of prec emax (RU 1)) with c6 in Fc6, Vc6.
(* their values *)
assert (F14 : format (1 / 4)).
{ replace (1 / 4) with (bpow radix2 (-2)) by (change (bpow radix2 (-2)) with (/ 4); field).
  apply generic_format_bpow. unfold FLT_exp. generalize emax_gt. lia. }
assert (F1 : format 1).
{ replace 1 with (bpow radix2 0) by reflexivity. apply generic_format_bpow.
  unfold FLT_exp. generalize emax_gt. lia. }
assert (F2 : format 2).
{ replace 2 with (bpow radix2 1) by reflexivity. apply generic_format_bpow.
  unfold FLT_exp. generalize emax_gt. lia. }
rewrite (round_generic _ _ _ (1 / 4) F14) in Vc5.
rewrite (round_generic _ _ _ 1 F1) in Vc6.
rewrite (round_generic _ _ _ 2 F2) in Vc2.
assert (B0 : 0 <= b2r c0 <= 9 / 8 * (17 / 16 * (E1 + ee)) + ee).
{ rewrite Vc0. apply RU_bound. apply Rmult_le_pos; lra. apply Rmult_le_compat; lra. }
assert (B1 : 0 <= b2r c1 <= 9 / 8 * (17 / 16 * (17 / 16) * (E1 + ee)) + ee).
{ rewrite Vc1. apply RU_bound. apply Rmult_le_pos; lra. apply Rmult_le_compat; lra. }
assert (B3 : 0 <= b2r c3 <= 9 / 8 * (9 / 8) + ee).
{ rewrite Vc3. apply RU_bound; lra. }
assert (B4 : 0 <= b2r c4 <=
             9 / 8 * (17 / 16 * (17 / 16) * (1 / 2 * ee + ee) + ee / (2 * uu)) + ee).
{ rewrite Vc4. apply RU_bound. lra.
  assert (K : (1 + uu) ^ 2 * (1 / 2 * ee + ee) <= 17 / 16 * (17 / 16) * (1 / 2 * ee + ee))
    by (apply Rmult_le_compat_r; lra). lra. }
(* m times the constants *)
assert (MB0 : 0 <= M * b2r c0 <= 153 / 2048 + / 16).
{ split. apply Rmult_le_pos; lra.
  assert (K : M * b2r c0 <= M * (9 / 8 * (17 / 16 * (E1 + ee)) + ee))
    by (apply Rmult_le_compat_l; lra).
  replace (M * (9 / 8 * (17 / 16 * (E1 + ee)) + ee)) with
    (153 / 128 * (M * E1 + M * ee) + M * ee) in K by (field; lra). lra. }
assert (MB1 : 0 <= M * b2r c1 <= 9 / 8 * (289 / 256) * / 16 + / 16).
{ split. apply Rmult_le_pos; lra.
  assert (K : M * b2r c1 <= M * (9 / 8 * (17 / 16 * (17 / 16) * (E1 + ee)) + ee))
    by (apply Rmult_le_compat_l; lra).
  replace (M * (9 / 8 * (17 / 16 * (17 / 16) * (E1 + ee)) + ee)) with
    (9 / 8 * (289 / 256) * (M * E1 + M * ee) + M * ee) in K by (field; lra). lra. }
assert (MB4 : 0 <= M * b2r c4 <= 9 / 8 * (289 / 256 * (3 / 2) * / 16 + / 16 * Q) + / 16).
{ split. apply Rmult_le_pos; lra.
  assert (K : M * b2r c4 <=
              M * (9 / 8 * (17 / 16 * (17 / 16) * (1 / 2 * ee + ee) + ee / (2 * uu)) + ee))
    by (apply Rmult_le_compat_l; lra).
  replace (M * (9 / 8 * (17 / 16 * (17 / 16) * (1 / 2 * ee + ee) + ee / (2 * uu)) + ee)) with
    (9 / 8 * (289 / 256 * (3 / 2) * (M * ee) + (M * ee) * / (2 * uu)) + M * ee) in K
    by (field; lra).
  assert (I0 : 0 <= / (2 * uu)) by (apply Rlt_le, Rinv_0_lt_compat; lra).
  assert (K2 : (M * ee) * / (2 * uu) <= / 16 * Q) by (apply Rmult_le_compat; lra).
  lra. }
(* the values *)
set (a := prod m c0). set (aa := prod m c1). set (d := prod a c2). set (w := add d c3).
set (g := prod aa w). set (tm := prod m c4). set (wg := add g c3). set (t := prod tm wg).
pose proof (rnd_bound (M * b2r c0 + 0) (153 / 2048 + / 16) ltac:(lra) ltac:(lra)) as [Ra0 Ra1].
destruct (prod_ok m c0 Fm Fc0 (range_le _ _ Ra0 Ra1 ltac:(lra))) as [Fa Ea]. fold a in Fa, Ea.
fold M in Ea.
assert (Ba : 0 <= b2r a <= 154 / 1000) by (rewrite Ea; lra).
pose proof (rnd_bound (M * b2r c1 + 0) (9 / 8 * (289 / 256) * / 16 + / 16) ltac:(lra) ltac:(lra))
  as [Raa0 Raa1].
destruct (prod_ok m c1 Fm Fc1 (range_le _ _ Raa0 Raa1 ltac:(lra))) as [Faa Eaa].
fold aa in Faa, Eaa. fold M in Eaa.
assert (Baa : 0 <= b2r aa <= 159 / 1000) by (rewrite Eaa; lra).
assert (Rd : 0 <= rnd (b2r a * b2r c2 + 0) /\
             rnd (b2r a * b2r c2 + 0) <= 17 / 16 * (154 / 1000 * 2) + ee / 2).
{ rewrite Vc2. apply rnd_bound; lra. }
destruct Rd as [Rd0 Rd1].
destruct (prod_ok a c2 Fa Fc2 (range_le _ _ Rd0 Rd1 ltac:(lra))) as [Fd Ed]. fold d in Fd, Ed.
assert (Bd : 0 <= b2r d <= 336 / 1000) by (rewrite Ed; lra).
pose proof (rnd_bound (b2r d + b2r c3) (336 / 1000 + (9 / 8 * (9 / 8) + / 64)) ltac:(lra)
              ltac:(lra)) as [Rw0 Rw1].
destruct (add_ok d c3 Fd Fc3 (range_le _ _ Rw0 Rw1 ltac:(lra))) as [Fw Ew]. fold w in Fw, Ew.
assert (Bw : 0 <= b2r w <= 1727 / 1000) by (rewrite Ew; lra).
pose proof (mul_le (b2r aa) (b2r w) (159 / 1000) (1727 / 1000) ltac:(lra) ltac:(lra) ltac:(lra)
              ltac:(lra)) as [Paw0 Paw1].
pose proof (rnd_bound (b2r aa * b2r w + 0) (159 / 1000 * (1727 / 1000)) ltac:(lra) ltac:(lra))
  as [Rg0 Rg1].
destruct (prod_ok aa w Faa Fw (range_le _ _ Rg0 Rg1 ltac:(lra))) as [Fg Eg]. fold g in Fg, Eg.
assert (Bg : 0 <= b2r g <= 3 / 10) by (rewrite Eg; lra).
pose proof (rnd_bound (M * b2r c4 + 0) (9 / 8 * (289 / 256 * (3 / 2) * / 16 + / 16 * Q) + / 16)
              ltac:(lra) ltac:(lra)) as [Rtm0 Rtm1].
destruct (prod_ok m c4 Fm Fc4 (range_le _ _ Rtm0 Rtm1 ltac:(lra))) as [Ftm Etm].
fold tm in Ftm, Etm. fold M in Etm.
assert (Btm : 0 <= b2r tm <= 201 / 1000 + 748 / 10000 * Q) by (rewrite Etm; lra).
pose proof (rnd_bound (b2r g + b2r c3) (3 / 10 + (9 / 8 * (9 / 8) + / 64)) ltac:(lra) ltac:(lra))
  as [Rwg0 Rwg1].
destruct (add_ok g c3 Fg Fc3 (range_le _ _ Rwg0 Rwg1 ltac:(lra))) as [Fwg Ewg].
fold wg in Fwg, Ewg.
assert (Bwg : 0 <= b2r wg <= 1688 / 1000) by (rewrite Ewg; lra).
pose proof (mul_le (b2r tm) (b2r wg) (201 / 1000 + 748 / 10000 * Q) (1688 / 1000) ltac:(lra)
              ltac:(lra) ltac:(lra) ltac:(lra)) as [Pt0 Pt1].
pose proof (rnd_bound (b2r tm * b2r wg + 0) ((201 / 1000 + 748 / 10000 * Q) * (1688 / 1000))
              ltac:(lra) ltac:(lra)) as [Rt0 Rt1].
destruct (prod_ok tm wg Ftm Fwg (range_le _ _ Rt0 Rt1 ltac:(lra))) as [Ft Et]. fold t in Ft, Et.
assert (Bt : 0 <= b2r t <= Q / 4) by (rewrite Et; lra).
split. exact Fg. split. exact Ft. split; [|split; [lra|lra]].
rewrite (le_finite prec emax a c5 Fa Fc5), (le_finite prec emax g c6 Fg Fc6), Vc5, Vc6.
rewrite !Rle_bool_true by lra. reflexivity.
Qed.

(** * The coefficients *)

(* The fused dot product on finite terms, when the real model's state after every prefix is
   at most 7/2 Q: every IEEE state is finite and the real model's. *)
Lemma dot_1_forward :
  forall l : list (float * float),
  Forall (fun xy => fin (fst xy) /\ fin (snd xy)) l ->
  (forall l1 l2, l = l1 ++ l2 ->
     Rabs (FoldModel.dot_1_seq emin prec tie_even
             (map (fun xy => (b2r (fst xy), b2r (snd xy))) l1)) <= 7 / 2 * Q) ->
  fin (fold_seq (IeeeFoldModel.dot_1_step prec emax nan_fma) pzero l) /\
  b2r (fold_seq (IeeeFoldModel.dot_1_step prec emax nan_fma) pzero l) =
  FoldModel.dot_1_seq emin prec tie_even (map (fun xy => (b2r (fst xy), b2r (snd xy))) l).
Proof.
induction l as [|a l IH] using rev_ind; intros F H.
- split; reflexivity.
- apply Forall_app in F. destruct F as [Fl Fa]. apply Forall_inv in Fa. destruct Fa as [Fx Fy].
  assert (H' : forall l1 l2, l = l1 ++ l2 ->
     Rabs (FoldModel.dot_1_seq emin prec tie_even
             (map (fun xy => (b2r (fst xy), b2r (snd xy))) l1)) <= 7 / 2 * Q).
  { intros l1 l2 E. apply (H l1 (l2 ++ [a])). rewrite E, app_assoc. reflexivity. }
  destruct (IH Fl H') as [Fs Vs].
  specialize (H (l ++ [a]) [] (eq_sym (app_nil_r _))).
  unfold FoldModel.dot_1_seq, fold_seq in H, Vs |- *. unfold fold_seq in Fs.
  rewrite map_app, fold_left_app in H. rewrite map_app. repeat rewrite fold_left_app.
  cbn [fold_left map] in H |- *.
  set (s := fold_left (IeeeFoldModel.dot_1_step prec emax nan_fma) l pzero) in *.
  rewrite <- Vs in H |- *.
  unfold FoldModel.dot_1_step, dot_step_1 in H |- *. cbv zeta in H |- *. cbn [fst snd] in H |- *.
  unfold IeeeFoldModel.dot_1_step, IeeeModel.dot_step_1. cbv zeta.
  destruct (fma_ok (fst a) (snd a) s Fx Fy Fs H) as [Fz Vz].
  split. exact Fz. exact Vz.
Qed.

(* n times the sum of the magnitudes of terms each at most Q / n. *)
Lemma sumabs_scaled :
  forall (c : R) (l : list (R * R)),
  Forall (fun xy => c * Rabs (fst xy * snd xy) <= Q) l ->
  c * sumabs (map (fun xy => fst xy * snd xy) l) <= INR (length l) * Q.
Proof.
intros c l H. induction H as [|xy l Hxy _ IH]; cbn [map length].
- unfold sumabs. cbn. lra.
- rewrite sumabs_cons, S_INR. lra.
Qed.

(* The real model's state after a prefix of the terms of a coefficient. *)
Lemma coef_prefix :
  forall (xs ys : list float) (j : nat) (l1 l2 : list (float * float)),
  INR (Nat.min (length xs) (length ys)) * (E1 + ee) <= / 16 ->
  Forall (fun x => Forall (fun y =>
    INR (Nat.min (length xs) (length ys)) * (Rabs (b2r x) * Rabs (b2r y)) <= Q) ys) xs ->
  FoldModel.conv_terms xs ys j = l1 ++ l2 ->
  Rabs (FoldModel.dot_1_seq emin prec tie_even
          (map (fun xy => (b2r (fst xy), b2r (snd xy))) l1)) <= 7 / 2 * Q.
Proof.
intros xs ys j l1 l2 Hn Hp E.
destruct uu_bounds as [U0 U1]. destruct ee_bounds as [F0 F1]. destruct E1_bounds as [D0 D1].
generalize Q_ge_8. intros Q8.
set (n := Nat.min (length xs) (length ys)) in *.
set (vs := map (fun xy => (b2r (fst xy), b2r (snd xy))) l1).
assert (Hp1 : (1 <= prec)%Z) by lia.
assert (Fv : Forall (fun xy => fmt emin prec (fst xy) /\ fmt emin prec (snd xy)) vs).
{ unfold vs. apply Forall_map. apply Forall_forall. intros xy _. cbn [fst snd].
  split; apply (b2r_format prec emax). }
generalize (FoldSums.dot_1_seq_correct emin prec Hp1 vs Fv). cbv zeta. intros [_ Er].
assert (EE : u prec / (1 + u prec) = E1) by (rewrite pow_1; field; lra).
rewrite EE in Er.
assert (Kn : (length vs <= n)%nat).
{ unfold vs. rewrite length_map. pose proof (FoldConv.conv_terms_length _ _ xs ys j) as L.
  rewrite E, length_app in L. unfold n. lia. }
set (k := length vs) in *.
assert (Nk : INR k <= INR n) by (apply le_INR; exact Kn).
assert (Pk : 0 <= INR k) by apply pos_INR.
assert (Me : INR n * ee <= / 16).
{ assert (0 <= INR n * E1) by (apply Rmult_le_pos; [apply pos_INR|lra]). lra. }
assert (Mf : INR n * E1 <= / 16).
{ assert (0 <= INR n * ee) by (apply Rmult_le_pos; [apply pos_INR|lra]). lra. }
assert (Kf : INR k * E1 <= / 16) by (apply Rle_trans with (2 := Mf); apply Rmult_le_compat_r; lra).
assert (Ke : INR k * ee <= / 16) by (apply Rle_trans with (2 := Me); apply Rmult_le_compat_r; lra).
(* (1 + E1)^k <= 16/15 *)
generalize (pow_mult_le_1 E1 k D0). intros PW.
assert (P0 : 0 <= (1 + E1) ^ k) by (apply pow_le; lra).
assert (PK : (1 + E1) ^ k <= 16 / 15).
{ assert (K1 : (1 + E1) ^ k * (15 / 16) <= (1 + E1) ^ k * (1 - INR k * E1))
    by (apply Rmult_le_compat_l; lra). lra. }
assert (PK1 : (1 + E1) ^ (k - 1) <= (1 + E1) ^ k) by (apply Rle_pow; [lra|lia]).
assert (P1 : 0 <= (1 + E1) ^ (k - 1)) by (apply pow_le; lra).
(* the sum of the magnitudes *)
set (A := sumabs (map (fun xy => fst xy * snd xy) vs)) in *.
assert (A0 : 0 <= A) by apply sumabs_ge_0.
assert (HA : A <= Q).
{ assert (Fl : Forall (fun xy => INR n * Rabs (fst xy * snd xy) <= Q) vs).
  { assert (T : Forall (fun ab => In (fst ab) xs /\ In (snd ab) ys) l1).
    { generalize (FoldConv.conv_terms_Forall _ _ (fun x => In x xs) (fun y => In y ys) xs ys j
                    (proj2 (Forall_forall _ _) (fun x H => H))
                    (proj2 (Forall_forall _ _) (fun y H => H))).
      rewrite E. intros T. apply Forall_app in T. exact (proj1 T). }
    unfold vs. apply Forall_map. revert T. apply Forall_impl. intros [x y] [Ix Iy].
    cbn [fst snd]. rewrite Rabs_mult.
    exact (proj1 (Forall_forall _ _) (proj1 (Forall_forall _ _) Hp x Ix) y Iy). }
  pose proof (sumabs_scaled (INR n) vs Fl) as SA. fold A in SA. fold k in SA.
  destruct (Nat.eq_dec k 0) as [K0|K0].
  - assert (Ev : vs = []) by (apply length_zero_iff_nil; exact K0).
    unfold A. rewrite Ev. unfold sumabs. cbn. lra.
  - assert (N1 : 1 <= INR n).
    { change 1 with (INR 1). apply le_INR. lia. }
    assert (K2 : INR k * Q <= INR n * Q) by (apply Rmult_le_compat_r; lra).
    apply Rmult_le_reg_l with (INR n). lra. lra. }
set (S := sumR (map (fun xy => fst xy * snd xy) vs)) in *.
set (s := FoldModel.dot_1_seq emin prec tie_even vs) in *.
assert (HS : Rabs S <= A) by apply sumR_le_sumabs.
assert (T : Rabs s <= Rabs S + Rabs (s - S)) by apply Rabs_le_add.
pose proof (mul_le ((1 + E1) ^ k) A (16 / 15) Q P0 PK A0 HA) as [_ M1].
pose proof (mul_le ((1 + E1) ^ (k - 1)) (INR k * (ee / 2)) (16 / 15) (/ 32) P1 ltac:(lra)
              ltac:(apply Rmult_le_pos; lra) ltac:(lra)) as [_ M2].
lra.
Qed.

(* Every coefficient finite: the convolution's mask is true. *)
Lemma conv_1_mask_true :
  forall xs ys : list float,
  Forall (fun x => fin x) xs -> Forall (fun y => fin y) ys ->
  INR (Nat.min (length xs) (length ys)) * (E1 + ee) <= / 16 ->
  Forall (fun x => Forall (fun y =>
    INR (Nat.min (length xs) (length ys)) * (Rabs (b2r x) * Rabs (b2r y)) <= Q) ys) xs ->
  snd (IeeeFoldModel.conv_1_conv prec emax nan_abs nan_fma nan_const xs ys) = true.
Proof.
intros xs ys Fx Fy Hn Hp.
unfold IeeeFoldModel.conv_1_conv. cbv zeta. rewrite fold_seq_and.
match goal with |- context [forallb ?t ?l] => assert (Hb : forallb t l = true) end.
{ apply forallb_forall. intros w Hw. apply in_map_iff in Hw. destruct Hw as [j [Ej _]]. subst w.
  apply (proj2 (IeeeFoldMaps.check_1_flag prec emax nan_abs nan_const _)).
  destruct (dot_1_forward (FoldModel.conv_terms xs ys j)
              (FoldConv.conv_terms_Forall _ _ (fun x => fin x) (fun y => fin y) xs ys j Fx Fy)
              (fun l1 l2 E => coef_prefix xs ys j l1 l2 Hn Hp E)) as [Fw _].
  exact Fw. }
rewrite Hb. reflexivity.
Qed.

(** * The radius *)

Lemma conv_radius_given :
  forall ma mb rx ry m g t : float,
  fin ma -> fin mb -> fin rx -> fin ry -> fin m -> fin g -> fin t ->
  0 <= b2r ma -> 0 <= b2r mb -> 0 <= b2r rx -> 0 <= b2r ry -> 0 <= b2r m ->
  0 <= b2r g <= / 2 -> 0 <= b2r t <= Q / 4 -> b2r m * ee <= / 16 ->
  (b2r ma + b2r rx) * (b2r mb + b2r ry) <= Q ->
  b2r m * ((b2r ma + b2r rx) * (b2r mb + b2r ry)) <= Q ->
  fin (IeeeModel.conv_radius prec emax nan_fma ma mb rx ry m g t).
Proof.
intros ma mb rx ry m g t Fa Fb Fx Fy Fm Fg Ft Pa Pb Px Py Pm [Pg Lg] [Pt Lt] Me HP HMP.
destruct uu_bounds as [U0 U1]. destruct ee_bounds as [H0 H1]. destruct ee_2u as [I0 I1].
generalize Q_ge_8 inv_2u_le. intros Q8 Iu.
set (A := b2r ma) in *. set (B := b2r mb) in *. set (X := b2r rx) in *. set (Y := b2r ry) in *.
set (M := b2r m) in *.
assert (EP : (A + X) * (B + Y) = A * B + A * Y + B * X + X * Y) by ring.
assert (PAB : 0 <= A * B) by (apply Rmult_le_pos; lra).
assert (PAY : 0 <= A * Y) by (apply Rmult_le_pos; lra).
assert (PBX : 0 <= B * X) by (apply Rmult_le_pos; lra).
assert (PXY : 0 <= X * Y) by (apply Rmult_le_pos; lra).
unfold IeeeModel.conv_radius. cbv zeta.
set (c0 := IeeeModel.up_conv_radius_0 prec emax). set (c7 := IeeeModel.up_conv_radius_1 prec emax).
destruct (pow_1u 8) as [L8 K8]. destruct (pow_1u 7) as [L7 K7].
assert (N8 : (17 / 16) ^ 8 <= 163 / 100) by (simpl; lra).
assert (N7 : (17 / 16) ^ 7 <= 153 / 100) by (simpl; lra).
assert (X0 : 0 <= 4 * (1 + uu) ^ 8 * ee + ee / (2 * uu) <= 2).
{ assert (K : 4 * (1 + uu) ^ 8 * ee <= 4 * (163 / 100) * ee) by (apply Rmult_le_compat_r; lra).
  assert (0 <= 4 * (1 + uu) ^ 8 * ee) by (apply Rmult_le_pos; lra). split; lra. }
destruct (const_ok _ (proj1 X0) (proj2 X0)) as [Fc0 Vc0].
destruct (const_ok ((1 + uu) ^ 7) ltac:(lra) ltac:(lra)) as [Fc7 Vc7].
change (IeeeOperations.const_of prec emax (RU (4 * (1 + uu) ^ 8 * ee + ee / (2 * uu))))
  with c0 in Fc0, Vc0.
change (IeeeOperations.const_of prec emax (RU ((1 + uu) ^ 7))) with c7 in Fc7, Vc7.
assert (B0 : 0 <= b2r c0 <= 9 / 8 * (4 * (163 / 100) * ee + ee / (2 * uu)) + ee).
{ rewrite Vc0. apply RU_bound. lra.
  assert (K : 4 * (1 + uu) ^ 8 * ee <= 4 * (163 / 100) * ee) by (apply Rmult_le_compat_r; lra).
  lra. }
assert (B7 : 0 <= b2r c7 <= 1737 / 1000).
{ rewrite Vc7. destruct (RU_bound ((1 + uu) ^ 7) (153 / 100) ltac:(lra) ltac:(lra)) as [W0 W1].
  split; lra. }
assert (MB0 : 0 <= M * b2r c0 <= 9 / 8 * (4 * (163 / 100) * / 16 + / 16 * Q) + / 16).
{ split. apply Rmult_le_pos; lra.
  assert (K : M * b2r c0 <= M * (9 / 8 * (4 * (163 / 100) * ee + ee / (2 * uu)) + ee))
    by (apply Rmult_le_compat_l; lra).
  replace (M * (9 / 8 * (4 * (163 / 100) * ee + ee / (2 * uu)) + ee)) with
    (9 / 8 * (4 * (163 / 100) * (M * ee) + (M * ee) * / (2 * uu)) + M * ee) in K
    by (field; lra).
  assert (I2 : 0 <= / (2 * uu)) by (apply Rlt_le, Rinv_0_lt_compat; lra).
  assert (K2 : (M * ee) * / (2 * uu) <= / 16 * Q)
    by (apply Rmult_le_compat; [apply Rmult_le_pos; lra|lra|lra|lra]).
  lra. }
(* the chain *)
set (p := prod rx ry). set (q := fma mb rx p). set (w := fma ma ry q). set (ab := prod ma mb).
set (e := fma ab g w). set (s := fma m e t). set (hm := prod m c0). set (rz := fma s c7 hm).
pose proof (rnd_bound (X * Y + 0) (X * Y) ltac:(lra) ltac:(lra)) as [Rp0 Rp1].
destruct (prod_ok rx ry Fx Fy (range_le _ _ Rp0 Rp1 ltac:(lra))) as [Fp Ep].
fold p in Fp, Ep. fold X Y in Ep.
assert (Bp : 0 <= b2r p <= 17 / 16 * (X * Y) + ee / 2) by (rewrite Ep; lra).
pose proof (rnd_bound (B * X + b2r p) (B * X + (17 / 16 * (X * Y) + ee / 2)) ltac:(lra)
              ltac:(lra)) as [Rq0 Rq1].
destruct (fma_ok mb rx p Fb Fx Fp (range_le _ _ Rq0 Rq1 ltac:(lra))) as [Fq Eq].
fold q in Fq, Eq. fold B X in Eq.
assert (Bq : 0 <= b2r q <= 17 / 16 * (B * X + (17 / 16 * (X * Y) + ee / 2)) + ee / 2)
  by (rewrite Eq; lra).
pose proof (rnd_bound (A * Y + b2r q)
              (A * Y + (17 / 16 * (B * X + (17 / 16 * (X * Y) + ee / 2)) + ee / 2)) ltac:(lra)
              ltac:(lra)) as [Rw0 Rw1].
destruct (fma_ok ma ry q Fa Fy Fq (range_le _ _ Rw0 Rw1 ltac:(lra))) as [Fw Ew].
fold w in Fw, Ew. fold A Y in Ew.
set (Wb := 17 / 16 * (A * Y + (17 / 16 * (B * X + (17 / 16 * (X * Y) + ee / 2)) + ee / 2))
           + ee / 2) in *.
assert (Bw : 0 <= b2r w <= Wb) by (rewrite Ew; lra).
pose proof (rnd_bound (A * B + 0) (A * B) ltac:(lra) ltac:(lra)) as [Rab0 Rab1].
destruct (prod_ok ma mb Fa Fb (range_le _ _ Rab0 Rab1 ltac:(lra))) as [Fab Eab].
fold ab in Fab, Eab. fold A B in Eab.
assert (Bab : 0 <= b2r ab <= 17 / 16 * (A * B) + ee / 2) by (rewrite Eab; lra).
pose proof (mul_le (b2r ab) (b2r g) (17 / 16 * (A * B) + ee / 2) (/ 2) ltac:(lra) ltac:(lra)
              ltac:(lra) ltac:(lra)) as [Pabg0 Pabg1].
pose proof (rnd_bound (b2r ab * b2r g + b2r w) ((17 / 16 * (A * B) + ee / 2) * / 2 + Wb)
              ltac:(lra) ltac:(lra)) as [Re0 Re1].
destruct (fma_ok ab g w Fab Fg Fw (range_le _ _ Re0 Re1 ltac:(unfold Wb in *; lra))) as [Fe Ee].
fold e in Fe, Ee.
assert (Be : 0 <= b2r e <= 12745 / 10000 * ((A + X) * (B + Y)) + 3 * ee).
{ rewrite Ee. split. lra. rewrite EP. unfold Wb in Re1. lra. }
assert (MBe : M * b2r e <= 12745 / 10000 * Q + 3 / 16).
{ assert (K : M * b2r e <= M * (12745 / 10000 * ((A + X) * (B + Y)) + 3 * ee))
    by (apply Rmult_le_compat_l; lra).
  replace (M * (12745 / 10000 * ((A + X) * (B + Y)) + 3 * ee)) with
    (12745 / 10000 * (M * ((A + X) * (B + Y))) + 3 * (M * ee)) in K by (field; lra).
  lra. }
assert (PMe : 0 <= M * b2r e) by (apply Rmult_le_pos; lra).
pose proof (rnd_bound (M * b2r e + b2r t) (12745 / 10000 * Q + 3 / 16 + Q / 4) ltac:(lra)
              ltac:(lra)) as [Rs0 Rs1].
destruct (fma_ok m e t Fm Fe Ft (range_le _ _ Rs0 Rs1 ltac:(lra))) as [Fs Es].
fold s in Fs, Es. fold M in Es.
assert (Bs : 0 <= b2r s <= 165 / 100 * Q) by (rewrite Es; lra).
pose proof (rnd_bound (M * b2r c0 + 0) (9 / 8 * (4 * (163 / 100) * / 16 + / 16 * Q) + / 16)
              ltac:(lra) ltac:(lra)) as [Rh0 Rh1].
destruct (prod_ok m c0 Fm Fc0 (range_le _ _ Rh0 Rh1 ltac:(lra))) as [Fh Eh].
fold hm in Fh, Eh. fold M in Eh.
assert (Bh : 0 <= b2r hm <= 15 / 100 * Q) by (rewrite Eh; lra).
pose proof (mul_le (b2r s) (b2r c7) (165 / 100 * Q) (1737 / 1000) ltac:(lra) ltac:(lra)
              ltac:(lra) ltac:(lra)) as [Psc0 Psc1].
pose proof (rnd_bound (b2r s * b2r c7 + b2r hm) (165 / 100 * Q * (1737 / 1000) + 15 / 100 * Q)
              ltac:(lra) ltac:(lra)) as [Rz0 Rz1].
destruct (fma_ok s c7 hm Fs Fc7 Fh (range_le _ _ Rz0 Rz1 ltac:(lra))) as [Fz _].
exact Fz.
Qed.

(** * The parts of bv_conv_1 under the conditions of V4 *)

Lemma maxl_values :
  forall xs : list float,
  Forall (fun x => fin x) xs ->
  b2r (fst (fold_seq (IeeeFoldModel.norm_upper_1_step prec emax nan_abs) (pzero, true) xs)) =
  maxl (map (fun w => Rabs w) (map val xs)) /\
  fin (fst (fold_seq (IeeeFoldModel.norm_upper_1_step prec emax nan_abs) (pzero, true) xs)).
Proof.
intros xs Fxs.
destruct (seq_1_state prec emax nan_abs xs) as [_ HS].
destruct (seq_1_good prec emax nan_abs xs Fxs) as [_ [F E]].
destruct (HS F E) as [_ V].
split; [|exact F].
change (B2R prec emax (fst (fold_seq (IeeeFoldModel.norm_upper_1_step prec emax nan_abs)
                             (pzero, true) xs)))
  with (fst (IeeeFoldNorm.vals prec emax
               (fold_seq (IeeeFoldModel.norm_upper_1_step prec emax nan_abs) (pzero, true) xs))).
rewrite V. unfold FoldModel.norm_upper_1_seq.
rewrite (FoldNorm.maxc_seq_value R FoldModel.norm_upper_1_step (fun w => Rabs w)
           BvReal.record_1_eq (map val xs)).
reflexivity.
Qed.

(* The conditions of V4 bound P = (Ma + rx) (Mb + ry) and m P. *)
Lemma P_bound :
  forall (xs ys : list float) (X Y : R), 0 <= X -> 0 <= Y ->
  Rabs (X * Y) <= Q ->
  Forall (fun x => Rabs ((Rabs (val x) + X) * Y) <= Q) xs ->
  Forall (fun y => Rabs ((Rabs (val y) + Y) * X) <= Q) ys ->
  Forall (fun x => Forall (fun y =>
    Rabs (INR (Nat.min (length xs) (length ys)) * (Rabs (val x) + X) * (Rabs (val y) + Y)) <= Q)
    ys) xs ->
  let A := maxl (map (fun w => Rabs w) (map val xs)) in
  let B := maxl (map (fun w => Rabs w) (map val ys)) in
  (A + X) * (B + Y) <= Q /\ INR (Nat.min (length xs) (length ys)) * ((A + X) * (B + Y)) <= Q.
Proof.
intros xs ys X Y PX PY Hr Hx Hy Hxy A B.
assert (Ag : forall l : list float, l <> [] ->
          exists x, In x l /\ maxl (map (fun w => Rabs w) (map val l)) = Rabs (val x)).
{ intros l Hl. destruct (maxl_attained (map val l)) as [v [Hv E]].
  { destruct l. contradiction. discriminate. }
  apply in_map_iff in Hv. destruct Hv as [x [Ex Hx']]. exists x. subst v. split; assumption. }
assert (A0 : 0 <= A) by apply FoldNorm.maxl_nonneg.
assert (B0 : 0 <= B) by apply FoldNorm.maxl_nonneg.
assert (PP : 0 <= (A + X) * (B + Y)) by (apply Rmult_le_pos; lra).
generalize Q_ge_8. intros Q8.
destruct xs as [|x0 xs'].
- assert (EA : A = 0) by reflexivity.
  assert (EN : INR (Nat.min (length (@nil float)) (length ys)) = 0) by reflexivity.
  rewrite EN, Rmult_0_l. split; [|lra].
  rewrite EA, Rplus_0_l.
  destruct ys as [|y0 ys'].
  + assert (EB : B = 0) by reflexivity. rewrite EB, Rplus_0_l.
    apply Rle_trans with (2 := Hr). apply Rle_abs.
  + destruct (Ag (y0 :: ys') ltac:(discriminate)) as [y [Iy EB]]. fold B in EB. rewrite EB.
    pose proof (proj1 (Forall_forall _ _) Hy y Iy) as K.
    rewrite Rmult_comm. apply Rle_trans with (2 := K). apply Rle_abs.
- destruct (Ag (x0 :: xs') ltac:(discriminate)) as [x [Ix EA]]. fold A in EA.
  destruct ys as [|y0 ys'].
  + assert (EB : B = 0) by reflexivity.
    assert (EN : INR (Nat.min (length (x0 :: xs')) (length (@nil float))) = 0)
      by (cbn [length]; rewrite Nat.min_0_r; reflexivity).
    rewrite EN, Rmult_0_l. split; [|lra]. rewrite EB, Rplus_0_l, EA.
    pose proof (proj1 (Forall_forall _ _) Hx x Ix) as K.
    apply Rle_trans with (2 := K). apply Rle_abs.
  + destruct (Ag (y0 :: ys') ltac:(discriminate)) as [y [Iy EB]]. fold B in EB.
    pose proof (proj1 (Forall_forall _ _) (proj1 (Forall_forall _ _) Hxy x Ix) y Iy) as K.
    set (n := Nat.min (length (x0 :: xs')) (length (y0 :: ys'))) in *.
    assert (N1 : 1 <= INR n).
    { change 1 with (INR 1). apply le_INR. unfold n. cbn [length]. lia. }
    assert (E : INR n * ((A + X) * (B + Y)) = INR n * (Rabs (val x) + X) * (Rabs (val y) + Y))
      by (rewrite EA, EB; ring).
    assert (K2 : INR n * ((A + X) * (B + Y)) <= Q).
    { rewrite E. apply Rle_trans with (2 := K). apply Rle_abs. }
    split; [|exact K2].
    assert (K3 : 1 * ((A + X) * (B + Y)) <= INR n * ((A + X) * (B + Y)))
      by (apply Rmult_le_compat_r; lra).
    lra.
Qed.

Lemma bv_conv_1_finite_parts :
  forall (rx ry : float) (xs ys : list float),
  fin rx -> fin ry -> 0 <= val rx -> 0 <= val ry ->
  Forall (fun x => fin x) xs -> Forall (fun y => fin y) ys ->
  INR (Nat.min (length xs) (length ys)) * (E1 + ee) <= / 16 ->
  Rabs (val rx * val ry) <= Q ->
  Forall (fun x => Rabs ((Rabs (val x) + val rx) * val ry) <= Q) xs ->
  Forall (fun y => Rabs ((Rabs (val y) + val ry) * val rx) <= Q) ys ->
  Forall (fun x => Forall (fun y =>
    Rabs (INR (Nat.min (length xs) (length ys)) * (Rabs (val x) + val rx) * (Rabs (val y) + val ry))
      <= Q) ys) xs ->
  let c := IeeeFoldModel.conv_1_conv prec emax nan_abs nan_fma nan_const xs ys in
  let sa := fold_seq (IeeeFoldModel.bv_conv_1_record prec emax nan_abs) (pzero, true) xs in
  let sb := fold_seq (IeeeFoldModel.bv_conv_1_record prec emax nan_abs) (pzero, true) ys in
  let m := IeeeFoldModel.bv_conv_1_count prec emax xs ys in
  let b := IeeeModel.bound_dot_1 prec emax nan_plus nan_fma m in
  snd c = true /\ snd b = true /\
  fin (IeeeModel.conv_radius prec emax nan_fma (fst sa) (fst sb) rx ry m (fst (fst b))
         (snd (fst b))).
Proof.
intros rx ry xs ys Frx Fry Px Py Fxs Fys Hn Hr Hx Hy Hxy. cbv zeta.
destruct uu_bounds as [U0 U1]. destruct ee_bounds as [H0 H1]. destruct E1_bounds as [D0 D1].
set (n := Nat.min (length xs) (length ys)) in *.
assert (Pn : 0 <= INR n) by apply pos_INR.
assert (Me : INR n * ee <= / 16).
{ assert (0 <= INR n * E1) by (apply Rmult_le_pos; lra). lra. }
assert (Mf : INR n * E1 <= / 16).
{ assert (0 <= INR n * ee) by (apply Rmult_le_pos; lra). lra. }
(* the count is n *)
assert (Hu : uu * bpow radix2 prec = 1).
{ unfold u. rewrite <- bpow_plus. replace (- prec + prec)%Z with 0%Z by ring. reflexivity. }
assert (HE : uu / 2 <= E1).
{ replace (1 / (1 + uu) * uu ^ 1) with (uu * / (1 + uu)) by (rewrite pow_1; field; lra).
  unfold Rdiv. apply Rmult_le_compat_l. lra. apply Rinv_le_contravar; lra. }
assert (Nb : INR n <= bpow radix2 prec).
{ assert (K : INR n * (uu / 2) <= INR n * E1) by (apply Rmult_le_compat_l; lra).
  assert (K2 : INR n * uu <= 1) by lra.
  replace (INR n) with (INR n * uu * bpow radix2 prec) by (rewrite Rmult_assoc, Hu; ring).
  rewrite <- (Rmult_1_l (bpow radix2 prec)) at 2.
  apply Rmult_le_compat_r. apply bpow_ge_0. exact K2. }
unfold IeeeFoldModel.bv_conv_1_count. fold n.
destruct (count_exact n Nb) as [Fm Vm].
set (m := binary_normalize prec emax prec_gt_0_ prec_lt_emax_ BinarySingleNaN.mode_UP
            (Z.of_nat n) 0 false) in *.
assert (Hm : B2R prec emax m * (E1 + ee) <= / 16) by (rewrite Vm; exact Hn).
destruct (bound_dot_1_given m Fm ltac:(rewrite Vm; exact Pn) Hm) as [Fg [Ft [Eok [Bg Bt]]]].
(* the pairs, as products of magnitudes *)
assert (Hp : Forall (fun x => Forall (fun y => INR n * (Rabs (b2r x) * Rabs (b2r y)) <= Q) ys) xs).
{ revert Hxy. apply Forall_impl. intros x Hx'. revert Hx'. apply Forall_impl. intros y K.
  assert (K1 : Rabs (val x) * Rabs (val y) <= (Rabs (val x) + val rx) * (Rabs (val y) + val ry))
    by (apply Rmult_le_compat; generalize (Rabs_pos (val x)) (Rabs_pos (val y)); lra).
  assert (K2 : INR n * (Rabs (val x) * Rabs (val y)) <=
               INR n * ((Rabs (val x) + val rx) * (Rabs (val y) + val ry)))
    by (apply Rmult_le_compat_l; [exact Pn|exact K1]).
  apply Rle_trans with (1 := K2).
  replace (INR n * ((Rabs (val x) + val rx) * (Rabs (val y) + val ry))) with
    (INR n * (Rabs (val x) + val rx) * (Rabs (val y) + val ry)) by ring.
  apply Rle_trans with (2 := K). apply Rle_abs. }
split; [|split].
- exact (conv_1_mask_true xs ys Fxs Fys Hn Hp).
- exact Eok.
- change (IeeeFoldModel.bv_conv_1_record prec emax nan_abs)
    with (IeeeFoldModel.norm_upper_1_step prec emax nan_abs).
  destruct (maxl_values xs Fxs) as [Va Fa].
  destruct (maxl_values ys Fys) as [Vb Fb].
  destruct (P_bound xs ys (val rx) (val ry) Px Py Hr Hx Hy Hxy) as [HP HMP].
  set (sa := fold_seq (IeeeFoldModel.norm_upper_1_step prec emax nan_abs) (pzero, true) xs) in *.
  set (sb := fold_seq (IeeeFoldModel.norm_upper_1_step prec emax nan_abs) (pzero, true) ys) in *.
  assert (A0 : 0 <= B2R prec emax (fst sa)) by (rewrite Va; apply FoldNorm.maxl_nonneg).
  assert (B0 : 0 <= B2R prec emax (fst sb)) by (rewrite Vb; apply FoldNorm.maxl_nonneg).
  assert (M0 : 0 <= B2R prec emax m) by (rewrite Vm; exact Pn).
  assert (ME : B2R prec emax m * ee <= / 16) by (rewrite Vm; exact Me).
  assert (HP' : (B2R prec emax (fst sa) + B2R prec emax rx) *
                (B2R prec emax (fst sb) + B2R prec emax ry) <= Q)
    by (rewrite Va, Vb; exact HP).
  assert (HMP' : B2R prec emax m * ((B2R prec emax (fst sa) + B2R prec emax rx) *
                                    (B2R prec emax (fst sb) + B2R prec emax ry)) <= Q)
    by (rewrite Va, Vb, Vm; exact HMP).
  exact (conv_radius_given (fst sa) (fst sb) rx ry m _ _ Fa Fb Frx Fry Fm Fg Ft A0 B0 Px Py M0
           Bg Bt ME HP' HMP').
Qed.

End V4.

(** * V4 and the generated statement *)

Lemma bv_conv_1_ieee_v4 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus : nan2 prec emax) (nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (4 <= prec)%Z ->
  forall (rx ry : binary_float prec emax) (xs ys : list (binary_float prec emax)),
  ((finite rx /\ 0 <= val rx /\ Forall (fun x => ball_finite_1 x rx) xs) \/
  (rx = infinity prec emax false /\ Forall (fun x => ball_whole_1 x rx) xs)) ->
  ((finite ry /\ 0 <= val ry /\ Forall (fun y => ball_finite_1 y ry) ys) \/
  (ry = infinity prec emax false /\ Forall (fun y => ball_whole_1 y ry) ys)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_conv_1_conv prec emax nan_plus nan_abs nan_fma nan_const rx ry xs ys in
  (finite rx -> finite ry ->
   ((INR (Nat.min (length xs) (length ys))) *
      (((1 / (1 + u prec)) * u prec ^ 1) + eta (ieee_emin prec emax))) <= (1 / 16) ->
   Rabs (val rx * val ry) <= bpow radix2 (emax - 2) ->
   Forall (fun x => Rabs (((Rabs (val x)) + val rx) * val ry) <= bpow radix2 (emax - 2)) xs ->
   Forall (fun y => Rabs (((Rabs (val y)) + val ry) * val rx) <= bpow radix2 (emax - 2)) ys ->
   Forall (fun x => Forall (fun y =>
     Rabs (((INR (Nat.min (length xs) (length ys))) * ((Rabs (val x)) + val rx)) *
           ((Rabs (val y)) + val ry)) <= bpow radix2 (emax - 2)) ys) xs ->
   finite r_).
Proof.
intros prec emax Hp He nan_plus nan_abs nan_fma nan_const Hp4 rx ry xs ys HX HY.
unfold IeeeFoldModel.bv_conv_1_conv. cbv zeta.
match goal with
| |- context [IeeeModel.bv_conv_finish prec emax nan_abs nan_const ?z ?a ?o] =>
    generalize (bv_conv_finish_facts prec emax Hp He nan_abs nan_const z a o);
    destruct (IeeeModel.bv_conv_finish prec emax nan_abs nan_const z a o) as [r flag]
end.
intros [H1 [H2 _]].
assert (Parts : finite rx -> finite ry ->
   ((INR (Nat.min (length xs) (length ys))) *
      (((1 / (1 + u prec)) * u prec ^ 1) + eta (ieee_emin prec emax))) <= (1 / 16) ->
   Rabs (val rx * val ry) <= bpow radix2 (emax - 2) ->
   Forall (fun x => Rabs (((Rabs (val x)) + val rx) * val ry) <= bpow radix2 (emax - 2)) xs ->
   Forall (fun y => Rabs (((Rabs (val y)) + val ry) * val rx) <= bpow radix2 (emax - 2)) ys ->
   Forall (fun x => Forall (fun y =>
     Rabs (((INR (Nat.min (length xs) (length ys))) * ((Rabs (val x)) + val rx)) *
           ((Rabs (val y)) + val ry)) <= bpow radix2 (emax - 2)) ys) xs ->
   flag = true).
{ intros Frx Fry Hn Hr Hx Hy Hxy.
  assert (Bx : 0 <= val rx /\ Forall finite xs).
  { destruct HX as [[_ [P B]]|[E _]].
    - split. exact P. revert B. apply Forall_impl. intros x [F _]. exact F.
    - rewrite E in Frx. discriminate Frx. }
  assert (By : 0 <= val ry /\ Forall finite ys).
  { destruct HY as [[_ [P B]]|[E _]].
    - split. exact P. revert B. apply Forall_impl. intros y [F _]. exact F.
    - rewrite E in Fry. discriminate Fry. }
  destruct Bx as [Px Fxs]. destruct By as [Py Fys].
  assert (Hn' : INR (Nat.min (length xs) (length ys)) *
                  (1 / (1 + u prec) * u prec ^ 1 + eta (3 - emax - prec)) <= / 16)
    by (unfold ieee_emin in Hn; lra).
  generalize (bv_conv_1_finite_parts prec emax Hp4 nan_plus nan_abs nan_fma nan_const rx ry xs ys
                Frx Fry Px Py Fxs Fys Hn' Hr Hx Hy Hxy).
  cbv zeta. intros [Ec [Eb Fz]]. apply H1. split. exact Ec. split. exact Eb. exact Fz. }
destruct flag; cbv beta iota.
- intros Frx Fry _ _ _ _ _. rewrite (H2 eq_refl).
  destruct (proj1 H1 eq_refl) as [_ [_ Fz]]. exact Fz.
- intros Frx Fry Hn Hr Hx Hy Hxy. discriminate (Parts Frx Fry Hn Hr Hx Hy Hxy).
Qed.

Theorem bv_conv_1_ieee_correct : bv_conv_1_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_abs nan_fma nan_const Hp4 rx ry xs ys HX HY.
generalize (bv_conv_1_ieee_v1 prec emax Hp He nan_plus nan_abs nan_fma nan_const Hp4 rx ry xs ys
              HX HY)
           (bv_conv_1_ieee_v2 prec emax Hp He nan_plus nan_abs nan_fma nan_const Hp4 rx ry xs ys
              HX HY)
           (bv_conv_1_ieee_v3 prec emax Hp He nan_plus nan_abs nan_fma nan_const Hp4 rx ry xs ys
              HX HY)
           (bv_conv_1_ieee_v4 prec emax Hp He nan_plus nan_abs nan_fma nan_const Hp4 rx ry xs ys
              HX HY).
destruct (IeeeFoldModel.bv_conv_1_conv prec emax nan_plus nan_abs nan_fma nan_const rx ry xs ys)
  as [[ws r] flag].
intros [A1 [A2 A3]] B C D.
split. exact A1. split. exact A2. split. exact A3. split. exact B. split. exact C. exact D.
Qed.
