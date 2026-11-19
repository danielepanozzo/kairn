(* mul_2_1: the product of a 2-limb number by a number of the format (JMP17 Algorithm 9,
   DWTimesFP3), with gradual underflow.

   Statement (mul_2_1_spec): for x normalized and a in the format, in any format with
   gradual underflow and precision at least 2, the result z is normalized and
       |z - x a| <= 2 u^2 |x a| + eta.

   Without underflow the bound 2 u^2 is in JMP17 and MR22 (DWTimesFP9_correct). The
   proof here follows the plan of Mul22.v: scale to 1 <= x0, a < 2 with eta anywhere,
   then split on the position of eta. The kernel has two inexact operations after the
   leading product (the second FMA of TwoProd and the FMA that forms cl3), each losing
   at most eta/2 by underflow; hence the constant 1. It is not attained but cannot be
   lowered: exhaustive enumeration on toy formats gives 0.949, 0.979, 0.990, 0.995 for
   prec = 5, 6, 7, 8. *)
From Stdlib Require Import Reals ZArith Lia Lra Psatz.
From Flocq Require Import Core Plus_error Mult_error Relative.
From Kairn.Gen Require Import Model Statements.
From Kairn Require Import Format Transfer EFT Mul22.
Open Scope R_scope.

(** * The kernel over an arbitrary rounding function, and its scaling *)

Definition g_mul_2_1 (rnd : R -> R) (x0 x1 a : R) : R * R :=
  let ch := rnd (x0 * a) in
  let cl1 := rnd (x0 * a - ch) in
  let cl3 := rnd (x1 * a + cl1) in
  let s := rnd (ch + cl3) in
  let z := rnd (s - ch) in
  let e := rnd (cl3 - z) in
  (s, e).

Lemma mul_2_1_g :
  forall emin prec choice x0 x1 a,
  mul_2_1 emin prec choice x0 x1 a
  = g_mul_2_1 (round radix2 (FLT_exp emin prec) (Znearest choice)) x0 x1 a.
Proof.
intros. unfold mul_2_1, two_prod, fast_two_sum, g_mul_2_1. cbv zeta beta iota.
rewrite !Rplus_0_r. reflexivity.
Qed.

Lemma g_mul_2_1_scale :
  forall (rnd rnd' : R -> R) (c d : R),
  (forall t, rnd' (t * (c * d)) = rnd t * (c * d)) ->
  forall x0 x1 a,
  g_mul_2_1 rnd' (x0 * c) (x1 * c) (a * d)
  = (fst (g_mul_2_1 rnd x0 x1 a) * (c * d), snd (g_mul_2_1 rnd x0 x1 a) * (c * d)).
Proof.
intros rnd rnd' c d H x0 x1 a. unfold g_mul_2_1. cbv zeta. cbn [fst snd].
replace (x0 * c * (a * d)) with (x0 * a * (c * d)) by ring. rewrite H.
set (ch := rnd (x0 * a)).
replace (x0 * a * (c * d) - ch * (c * d)) with ((x0 * a - ch) * (c * d)) by ring. rewrite H.
set (cl1 := rnd (x0 * a - ch)).
replace (x1 * c * (a * d) + cl1 * (c * d)) with ((x1 * a + cl1) * (c * d)) by ring. rewrite H.
set (cl3 := rnd (x1 * a + cl1)).
rewrite <- Rmult_plus_distr_r, H.
set (s := rnd (ch + cl3)).
rewrite <- Rmult_minus_distr_r, H.
set (z := rnd (s - ch)).
rewrite <- Rmult_minus_distr_r, H.
reflexivity.
Qed.

Lemma g_mul_2_1_zero_l :
  forall (rnd : R -> R) a, rnd 0 = 0 -> g_mul_2_1 rnd 0 0 a = (0, 0).
Proof.
intros rnd a H0. unfold g_mul_2_1. cbv zeta.
repeat first [rewrite Rmult_0_l | rewrite Rminus_0_r | rewrite Rplus_0_r | rewrite H0].
reflexivity.
Qed.

Lemma g_mul_2_1_zero_r :
  forall (rnd : R -> R) x0 x1, rnd 0 = 0 -> g_mul_2_1 rnd x0 x1 0 = (0, 0).
Proof.
intros rnd x0 x1 H0. unfold g_mul_2_1. cbv zeta.
repeat first [rewrite Rmult_0_r | rewrite Rminus_0_r | rewrite Rplus_0_r | rewrite H0].
reflexivity.
Qed.

(** * The scaled problem: 1 <= x0, a < 2, and eta anywhere *)

Section Core.
Variable emin prec : Z.
Hypothesis Hp : (2 <= prec)%Z.

Local Instance prec_pos : Prec_gt_0 prec.
Proof. unfold Prec_gt_0. lia. Qed.

Let u := pow2 (- prec).
Let eta := pow2 emin.
Notation rn := (RN emin prec).
Notation format := (generic_format radix2 (FLT_exp emin prec)).
Notation formatx := (generic_format radix2 (FLX_exp prec)).

Variables x0 x1 a : R.
Hypothesis Fx0 : formatx x0.
Hypothesis Fa : formatx a.
Hypothesis Hx0 : 1 <= x0 <= 2 - 2 * u.
Hypothesis Ha : 1 <= a <= 2 - 2 * u.
Hypothesis Hx1 : Rabs x1 <= u.

Let ch := rn (x0 * a).
Let cl1 := rn (x0 * a - ch).
Let cl3 := rn (x1 * a + cl1).
Let xa := (x0 + x1) * a.

Let core_goal : Prop :=
  normalized_2 emin prec (fst (mul_2_1 emin prec tie_even x0 x1 a))
                         (snd (mul_2_1 emin prec tie_even x0 x1 a)) /\
  Rabs (fst (mul_2_1 emin prec tie_even x0 x1 a)
        + snd (mul_2_1 emin prec tie_even x0 x1 a) - xa)
  <= 2 * (u * u) * xa + eta.

Let upos : 0 < u.
Proof. apply bpow_gt_0. Qed.
Let u4 : u <= / 4.
Proof. unfold u. change (/ 4) with (pow2 (-2)). apply bpow_le. lia. Qed.
Let etapos : 0 < eta.
Proof. apply bpow_gt_0. Qed.
Let P1 : pow2 (1 - prec) = 2 * u.
Proof. unfold u. replace (1 - prec)%Z with (1 + - prec)%Z by ring. now rewrite bpow_plus, pow2_1. Qed.
Let P2 : pow2 (2 - prec) = 4 * u.
Proof. unfold u. replace (2 - prec)%Z with (2 + - prec)%Z by ring. now rewrite bpow_plus, pow2_2. Qed.
Let Q0 : pow2 (- prec - prec) = u * u.
Proof. unfold u. replace (- prec - prec)%Z with (- prec + - prec)%Z by ring. apply bpow_plus. Qed.
Let Q1 : pow2 (1 - prec - prec) = 2 * (u * u).
Proof. rewrite <- Q0. replace (1 - prec - prec)%Z with (1 + (- prec - prec))%Z by ring. now rewrite bpow_plus, pow2_1. Qed.
Let Q2 : pow2 (2 - prec - prec) = 4 * (u * u).
Proof. rewrite <- Q0. replace (2 - prec - prec)%Z with (2 + (- prec - prec))%Z by ring. now rewrite bpow_plus, pow2_2. Qed.

Let err : forall t k B, Rabs t <= pow2 k -> pow2 (k - prec) <= 2 * B -> eta <= 2 * B ->
  Rabs (rn t - t) <= B.
Proof. intros t k B. apply (round_error_le emin prec tie_even). Qed.
Let Frn : forall t, format (rn t).
Proof. intros t. apply generic_format_round; auto with typeclass_instances. Qed.
Let mag_le : forall t k, Rabs t <= pow2 k -> Rabs (rn t) <= pow2 k.
Proof. intros t k H. exact (RN_abs_le_bpow emin prec t k H). Qed.
Let zero : forall t, Rabs t <= / 2 * eta -> rn t = 0.
Proof.
intros t Ht. apply (RN_small_zero emin prec). unfold eta in Ht.
replace (emin - 1)%Z with (-1 + emin)%Z by ring. now rewrite bpow_plus, pow2_m1.
Qed.

Let Hx1a : Rabs (x1 * a) <= u * (2 - 2 * u).
Proof. apply Rabs_mult_le; trivial. rewrite Rabs_pos_eq; lra. Qed.
Let Hx0a : 1 <= x0 * a <= 4.
Proof. split; nra. Qed.
Let Hxa : (x0 - u) * a <= xa.
Proof. unfold xa. generalize (Rabs_le_inv _ _ Hx1). intros H. apply Rmult_le_compat_r; lra. Qed.

Let decomp : ch + cl3 - xa = (ch + cl1 - x0 * a) + (cl3 - (x1 * a + cl1)).
Proof. unfold xa. ring. Qed.

Lemma core_finish :
  forall B, Rabs cl3 <= Rabs ch -> Rabs (ch + cl3 - xa) <= B ->
  B <= 2 * (u * u) * xa + eta -> core_goal.
Proof.
intros B H1 H2 H3. unfold core_goal.
assert (E : mul_2_1 emin prec tie_even x0 x1 a = fast_two_sum emin prec tie_even ch cl3).
{ unfold mul_2_1, two_prod. cbv zeta beta iota. rewrite !Rplus_0_r, pair_eta. reflexivity. }
rewrite E.
destruct (fast_two_sum_norm emin prec Hp ch cl3 (Frn _) (Frn _) H1) as [N S].
split. exact N. rewrite S. now apply Rle_trans with B.
Qed.

(** ** eta >= 4u: only the leading product survives *)

Lemma regime_deep : (2 - prec <= emin)%Z -> core_goal.
Proof.
intros He.
assert (Heta : 4 * u <= eta). { rewrite <- P2. apply bpow_le. exact He. }
assert (Hc : Rabs (ch - x0 * a) <= / 2 * eta).
{ apply err with 2%Z. rewrite pow2_2, Rabs_pos_eq; lra. rewrite P2; lra. lra. }
assert (Z1 : cl1 = 0). { apply zero. rewrite <- Rabs_Ropp, Ropp_minus_distr. exact Hc. }
assert (Z3 : cl3 = 0).
{ unfold cl3. rewrite Z1, Rplus_0_r. apply zero. apply Rle_trans with (1 := Hx1a). nra. }
apply core_finish with (/ 2 * eta + u * (2 - 2 * u)).
- rewrite Z3, Rabs_R0. apply Rabs_pos.
- rewrite Z3, Rplus_0_r.
  replace (ch - xa) with ((ch - x0 * a) + - (x1 * a)) by (unfold xa; ring).
  apply Rabs_plus_le; trivial. now rewrite Rabs_Ropp.
- assert (0 <= xa) by (apply Rle_trans with (2 := Hxa); nra). nra.
Qed.

(** ** eta <= 2u: each of the two inexact operations loses at most eta/2 more *)

Lemma regime_shallow : (emin <= 1 - prec)%Z -> core_goal.
Proof.
intros He.
assert (Heta : eta <= 2 * u). { rewrite <- P1. apply bpow_le. exact He. }
assert (Ec : Rabs (ch + cl1 - x0 * a) <= / 2 * eta).
{ apply (two_prod_defect emin prec tie_even x0 a Fx0 Fa). }
assert (C1 : 1 <= Rabs ch).
{ apply (round_abs_ge emin prec tie_even).
  - change 1 with (pow2 0). apply generic_format_bpow. unfold FLT_exp. lia.
  - rewrite Rabs_pos_eq; lra. }
destruct (Rlt_or_le 2 (x0 * a)) as [H2|H2].
- (* x0 a > 2 *)
  assert (Hc : Rabs (x0 * a - ch) <= pow2 (1 - prec)).
  { rewrite P1, <- Rabs_Ropp, Ropp_minus_distr.
    apply err with 2%Z. rewrite pow2_2, Rabs_pos_eq; lra. rewrite P2; lra. lra. }
  assert (Mc : Rabs cl1 <= 2 * u). { rewrite <- P1. now apply mag_le. }
  assert (T : Rabs (x1 * a + cl1) <= pow2 (2 - prec)).
  { rewrite P2. apply Rle_trans with (u * (2 - 2 * u) + 2 * u). now apply Rabs_plus_le. nra. }
  assert (E3 : Rabs (cl3 - (x1 * a + cl1)) <= 2 * (u * u) + / 2 * eta).
  { apply err with (1 := T). rewrite Q2; lra. nra. }
  assert (M3 : Rabs cl3 <= 4 * u). { rewrite <- P2. now apply mag_le. }
  apply core_finish with (/ 2 * eta + (2 * (u * u) + / 2 * eta)).
  + lra.
  + rewrite decomp. now apply Rabs_plus_le.
  + assert (1 <= xa) by (apply Rle_trans with (2 := Hxa); nra). nra.
- destruct (Req_dec x0 1) as [Hx|Hx].
  + (* x0 = 1: the leading product is exact *)
    assert (Fa' : format a).
    { apply generic_format_FLT_FLX; trivial.
      apply Rle_trans with (pow2 0). apply bpow_le; lia. rewrite Rabs_pos_eq; simpl; lra. }
    assert (Ech : ch = a).
    { unfold ch. rewrite Hx, Rmult_1_l. apply round_generic; auto with typeclass_instances. }
    assert (Z1 : cl1 = 0).
    { unfold cl1. rewrite Ech, Hx, Rmult_1_l. unfold Rminus. rewrite Rplus_opp_r.
      apply round_0; auto with typeclass_instances. }
    assert (Ec' : Rabs (ch + cl1 - x0 * a) <= 0).
    { rewrite Ech, Z1, Hx. replace (a + 0 - 1 * a) with 0 by ring. rewrite Rabs_R0. lra. }
    assert (T : Rabs (x1 * a + cl1) <= pow2 (1 - prec)).
    { rewrite Z1, Rplus_0_r, P1. apply Rle_trans with (1 := Hx1a). nra. }
    assert (E3 : Rabs (cl3 - (x1 * a + cl1)) <= u * u + / 2 * eta).
    { apply err with (1 := T). rewrite Q1; lra. nra. }
    assert (M3 : Rabs cl3 <= 2 * u). { rewrite <- P1. now apply mag_le. }
    apply core_finish with (0 + (u * u + / 2 * eta)).
    * lra.
    * rewrite decomp. now apply Rabs_plus_le.
    * assert (/ 2 <= xa) by (apply Rle_trans with (2 := Hxa); nra). nra.
  + (* 1 < x0 and x0 a <= 2 *)
    assert (F1 : formatx 1).
    { change 1 with (pow2 0). apply generic_format_bpow. unfold FLX_exp. lia. }
    assert (Hx' : 1 + 2 * u <= x0).
    { rewrite <- P1. replace (1 - prec)%Z with (- prec + 1)%Z by ring.
      rewrite <- (succ_FLX_1 radix2 prec). apply succ_le_lt; auto with typeclass_instances. lra. }
    assert (Hc : Rabs (x0 * a - ch) <= pow2 (- prec)).
    { fold u. rewrite <- Rabs_Ropp, Ropp_minus_distr.
      apply err with 1%Z. rewrite pow2_1, Rabs_pos_eq; lra. rewrite P1; lra. lra. }
    assert (Mc : Rabs cl1 <= u) by now apply mag_le.
    assert (T : Rabs (x1 * a + cl1) <= pow2 (2 - prec)).
    { rewrite P2. apply Rle_trans with (u * (2 - 2 * u) + u). now apply Rabs_plus_le. nra. }
    assert (E3 : Rabs (cl3 - (x1 * a + cl1)) <= 2 * (u * u) + / 2 * eta).
    { apply err with (1 := T). rewrite Q2; lra. nra. }
    assert (M3 : Rabs cl3 <= 4 * u). { rewrite <- P2. now apply mag_le. }
    apply core_finish with (/ 2 * eta + (2 * (u * u) + / 2 * eta)).
    * lra.
    * rewrite decomp. now apply Rabs_plus_le.
    * assert (1 <= xa) by (apply Rle_trans with (2 := Hxa); nra). nra.
Qed.

Theorem core21 : core_goal.
Proof.
destruct (Z_le_gt_dec emin (1 - prec)) as [H|H]. now apply regime_shallow.
apply regime_deep. lia.
Qed.

End Core.

(** * The generated statement (proofs/gen/Statements.v) *)

Theorem mul_2_1_correct : mul_2_1_spec.
Proof.
intros emin prec Hp x0 x1 a [F0 [F1 Hx]] Fa.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 2%Z; lia).
unfold fmt in F0, F1, Fa.
assert (R0 : RN emin prec 0 = 0) by (apply round_0; auto with typeclass_instances).
assert (Hu2 : u prec ^ 2 = pow2 (- prec) * pow2 (- prec)) by (unfold u; ring).
assert (Hpos : forall v, 0 <= 2 * u prec ^ 2 * Rabs v + 1 * eta emin).
{ intros v. rewrite Hu2. unfold eta.
  generalize (bpow_gt_0 radix2 (- prec)) (bpow_gt_0 radix2 emin) (Rabs_pos v). nra. }
assert (Hzero : normalized_2 emin prec 0 0).
{ repeat split; try apply generic_format_0. now rewrite Rplus_0_l. }
destruct (Req_dec x0 0) as [Zx|Zx].
{ assert (Zx1 : x1 = 0).
  { rewrite Zx, Rplus_0_l in Hx. unfold RN in Hx.
    rewrite round_generic in Hx; auto with typeclass_instances. }
  rewrite Zx, Zx1, mul_2_1_g, g_mul_2_1_zero_l by exact R0.
  split. exact Hzero.
  replace (0 + 0 - (0 + 0) * a) with 0 by ring. rewrite Rabs_R0. apply Hpos. }
destruct (Req_dec a 0) as [Za|Za].
{ rewrite Za, mul_2_1_g, g_mul_2_1_zero_r by exact R0.
  split. exact Hzero.
  replace (0 + 0 - (x0 + x1) * 0) with 0 by ring. rewrite Rabs_R0. apply Hpos. }
assert (FX0 : generic_format radix2 (FLX_exp prec) x0) by now apply generic_format_FLX_FLT with emin.
assert (FA : generic_format radix2 (FLX_exp prec) a) by now apply generic_format_FLX_FLT with emin.
destruct (scale_to_12 prec x0 FX0 Zx) as [c [Sc Hc]].
destruct (scale_to_12 prec a FA Za) as [d [Sd Hd]].
set (kc := (1 - mag radix2 x0)%Z) in *. set (kd := (1 - mag radix2 a)%Z) in *.
assert (Scd : spow (c * d) (kc + kd)) by now apply spow_mult.
assert (Hcd : Rabs (c * d) = pow2 (kc + kd)) by now apply spow_abs.
assert (Hcd0 : 0 < Rabs (c * d)) by (rewrite Hcd; apply bpow_gt_0).
assert (Zcd : c * d <> 0). { intros Z. rewrite Z, Rabs_R0 in Hcd0. lra. }
assert (Tx : Rabs (x1 * c) <= pow2 (- prec)).
{ rewrite Rabs_mult, (spow_abs c kc Sc).
  assert (Hn : x0 = round radix2 (FLX_exp prec) (Znearest tie_even) (x0 + x1)).
  { rewrite Hx at 1. unfold RN. apply round_plus_FLT_FLX; auto with typeclass_instances. }
  generalize (normalized_tail_FLX prec tie_even x0 x1 Hn Zx). intros H.
  apply Rle_trans with (/ 2 * pow2 (mag radix2 x0 - prec) * pow2 kc).
  - apply Rmult_le_compat_r. apply bpow_ge_0. exact H.
  - rewrite Rmult_assoc, <- bpow_plus. unfold kc.
    replace (mag radix2 x0 - prec + (1 - mag radix2 x0))%Z with (1 + - prec)%Z by ring.
    rewrite bpow_plus, pow2_1. lra. }
assert (FXc : generic_format radix2 (FLX_exp prec) (x0 * c)).
{ destruct Sc as [-> | ->]. now apply formatx_scale.
  replace (x0 * - pow2 kc) with (- (x0 * pow2 kc)) by ring.
  apply generic_format_opp. now apply formatx_scale. }
assert (FAd : generic_format radix2 (FLX_exp prec) (a * d)).
{ destruct Sd as [-> | ->]. now apply formatx_scale.
  replace (a * - pow2 kd) with (- (a * pow2 kd)) by ring.
  apply generic_format_opp. now apply formatx_scale. }
generalize (core21 (emin + (kc + kd)) prec Hp (x0 * c) (x1 * c) (a * d) FXc FAd Hc Hd Tx).
set (rnd := round radix2 (FLT_exp emin prec) (Znearest tie_even)).
rewrite (mul_2_1_g (emin + (kc + kd))).
rewrite (g_mul_2_1_scale rnd
           (round radix2 (FLT_exp (emin + (kc + kd)) prec) (Znearest tie_even)) c d)
  by (intros t; exact (RN_scale_spow emin prec (c * d) (kc + kd) t Scd)).
rewrite mul_2_1_g. fold rnd.
assert (Fz : fmt emin prec (fst (g_mul_2_1 rnd x0 x1 a)) /\
             fmt emin prec (snd (g_mul_2_1 rnd x0 x1 a))).
{ unfold g_mul_2_1, rnd. cbv zeta. cbn [fst snd].
  split; apply generic_format_round; auto with typeclass_instances. }
destruct Fz as [Fz0 Fz1].
destruct (g_mul_2_1 rnd x0 x1 a) as [z0 z1]. cbn [fst snd] in *.
intros [[_ [_ N]] B]. split.
- repeat split; trivial.
  apply Rmult_eq_reg_r with (c * d); trivial.
  rewrite N at 1. rewrite <- Rmult_plus_distr_r. now apply RN_scale_spow.
- apply Rmult_le_reg_r with (Rabs (c * d)); trivial.
  rewrite <- Rabs_mult.
  replace ((z0 + z1 - (x0 + x1) * a) * (c * d))
    with (z0 * (c * d) + z1 * (c * d) - (x0 * c + x1 * c) * (a * d)) by ring.
  apply Rle_trans with (1 := B).
  rewrite Hu2.
  replace ((2 * (pow2 (- prec) * pow2 (- prec)) * Rabs ((x0 + x1) * a) + 1 * eta emin) * Rabs (c * d))
    with (2 * (pow2 (- prec) * pow2 (- prec)) * (Rabs ((x0 + x1) * a) * Rabs (c * d))
          + eta emin * Rabs (c * d)) by ring.
  apply Rplus_le_compat.
  + apply Rmult_le_compat_l.
    * generalize (bpow_gt_0 radix2 (- prec)). nra.
    * rewrite <- Rabs_mult.
      replace ((x0 * c + x1 * c) * (a * d)) with ((x0 + x1) * a * (c * d)) by ring.
      apply Rle_abs.
  + rewrite Hcd. unfold eta. rewrite bpow_plus. lra.
Qed.
