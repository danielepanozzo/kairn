(* add_2_2 in the IEEE model at the top of the range: no overflow when the leading limbs of
   both operands are below 2^(emax - 1) in magnitude, that is, at most Omega / 2, half the
   largest finite number (add_2_2_values_finite_half; the statement
   add_2_2_ieee_finite_half_spec at the end of the file). IeeeAdd22.v proves the threshold
   2^(emax - 2), a quarter of the range. This one is optimal: at |x0| = |y0| = 2^(emax - 1)
   the first sum overflows.

   Notation: H = 2^(emax - 1), U = 2^(emax - prec), the unit in the last place of the
   largest numbers, Omega = 2 H - U; x = (x0, x1) and y = (y0, y1) are the operands, finite
   and normalized, and the values of the kernel have their names in the listing:
   (sh, sl) = two_sum(x0, y0), (th, tl) = two_sum(x1, y1), c = RN(sl + th),
   (vh, vl) = fast_two_sum(sh, c), w = RN(tl + vl), (z0, z1) = fast_two_sum(vh, w).

   The proof (add_2_2_range_half) bounds the values of the real model, as that of
   IeeeAdd22.v does (IeeeBridge.run_sim: the IEEE model returns finite values exactly when
   the values of the real model are below 2^emax). A leading limb below H is at most
   Omega / 2 = H - U/2, and its tail at most U/4. So |x0 + y0| <= Omega and sh does not
   overflow; sl, th, tl, c, vl and w are a few U at most; only vh = RN(sh + c) and
   z0 = RN(vh + w) can be large. A number below Omega + U/2 in magnitude, the midpoint of
   Omega and 2^emax, rounds to at most Omega (IeeeRange.rnd_below_mid). Three cases:

   - |x0 + y0| <= H. Then |sh| <= H, |vh| <= H + U and |vh + w| <= H + 3 U <= Omega: the
     bounds of IeeeAdd22.v.
   - H < |x0 + y0| <= Omega - U/2. sh + c = (x0 + y0) + th + dc, with dc the rounding error
     of c, at most U/8: below Omega + U/2. And |sh| >= H >= |c|, so the first fast_two_sum
     is exact and vh + w = (x0 + y0) + (x1 + y1) + dc + dw, with dw the rounding error of w,
     at most U/4: at most Omega + 3 U/8.
   - Otherwise x0 = y0 = Omega / 2 or x0 = y0 = -Omega / 2 (a number of the format below
     Omega / 2 in magnitude is at most Omega / 2 - U/2: below_half_Omega), and the bounds
     above leave no margin. Here x0 + y0 = +-Omega exactly, sl = 0 and c = th. The tail of a
     normalized pair whose leading limb is +-Omega / 2 is strictly below U/4
     (tail_half_Omega_strict): at U/4 the value would be halfway between Omega / 2 and a
     neighbor, and Omega / 2 has an odd significand, so the tie rounds to the neighbor
     (rnd_tie; this is the one place where ties to even is used). Hence |th| < U/2,
     vh = RN(+-Omega + th) = +-Omega (rnd_near_top), vl = th, w = th and z0 = vh.

   Also here, because they are facts about add_2_2 on operands that are not finite numbers,
   used by ball_contains_point_2 (IeeeBallContains2.v):

   - add_2_2_zero_right: with a second operand whose two limbs are zeros, and a finite
     normalized first operand, the result is finite and its value is that of the first
     operand, exactly.
   - add_2_2_lead_not_finite: with a leading limb that is not finite and a finite second
     operand, the leading limb of the result is a NaN (the first sum is not finite, the
     difference of the two_sum that follows is that of two equal infinities, or has a NaN
     operand, and the NaN propagates). *)
From Stdlib Require Import Reals ZArith List Arith Bool Lia Lra.
From Flocq Require Import Core Binary Mult_error.
From Kairn.Gen Require Import Model Statements IeeeStatements.
From Kairn Require Import Format Normalized EFT Add22 Program IeeeBridge IeeeEFT IeeeVocabulary.
From Kairn Require Import IeeeOps IeeeAdd22 IeeeRange.
From Kairn Require IeeeOperations.
From Kairn.Gen Require IeeeModel.
Import ListNotations.
Open Scope R_scope.

Section IeeeAdd22Top.
Variable prec emax : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Context {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}.

Notation float := (binary_float prec emax).
Notation nan_of := {x : float | is_nan prec emax x = true}.
Variable nan_plus : float -> float -> nan_of.
Variable nan_minus : float -> float -> nan_of.
Variable nan_opp : float -> nan_of.
Variable nan_fma : float -> float -> float -> nan_of.

Notation emin := (3 - emax - prec)%Z.
Notation fexp := (FLT_exp emin prec).
Notation format := (generic_format radix2 fexp).
Notation rnd := (round radix2 fexp (Znearest tie_even)).
Notation fin x := (is_finite prec emax x = true).
Notation b2r := (B2R prec emax).
Notation inrange := (inrange emax).
Notation Omega := (Omega prec emax).
Notation stB := (stepB prec emax nan_plus nan_minus nan_opp nan_fma).
Notation runB := (run stB).
Notation runR := (runR emin prec tie_even).
Notation d0 := (d0 prec emax).
Notation finite_all := (Forall (fun x : float => fin x)).
Notation H := (bpow radix2 (emax - 1)).
Notation U := (bpow radix2 (emax - prec)).

Let Hprec : (0 < prec)%Z.
Proof. exact prec_gt_0_. Qed.
Let Hemax : (prec < emax)%Z.
Proof. exact prec_lt_emax_. Qed.

Let rnd_opp : forall x, rnd (- x) = - rnd x.
Proof. intros x. exact (RN_opp emin prec x). Qed.

Let Frnd : forall x, format (rnd x).
Proof. intros x. apply generic_format_round; auto with typeclass_instances. Qed.

(** * Rounding a tie, and rounding next to the largest number *)

(* A number halfway between the consecutive multiples m and m + 1 of 2^e, in a binade
   where the numbers of the format are 2^e apart, rounds to the even one. *)
Lemma rnd_tie :
  forall m e : Z, cexp radix2 fexp ((IZR m + / 2) * bpow radix2 e) = e ->
  rnd ((IZR m + / 2) * bpow radix2 e)
  = IZR (if Z.even m then m else (m + 1)%Z) * bpow radix2 e.
Proof.
intros m e Hc. unfold round, F2R, scaled_mantissa. cbn [Fnum Fexp]. rewrite Hc.
rewrite Rmult_assoc, <- bpow_plus, Z.add_opp_diag_r.
change (bpow radix2 0) with 1. rewrite Rmult_1_r.
do 2 f_equal.
assert (F : Zfloor (IZR m + / 2) = m) by (apply Zfloor_imp; rewrite plus_IZR; simpl; lra).
assert (C : Zceil (IZR m + / 2) = (m + 1)%Z).
{ apply Zceil_imp. replace (m + 1 - 1)%Z with m by ring. rewrite plus_IZR. simpl. lra. }
unfold Znearest. rewrite F, C, Rcompare_Eq by lra. unfold tie_even.
destruct (Z.even m); reflexivity.
Qed.

(* A number within less than U/2 of Omega, or of -Omega, rounds to it. *)
Lemma rnd_near_Omega :
  (2 <= prec)%Z -> forall x, Rabs (x - Omega) < / 2 * U -> rnd x = Omega.
Proof.
intros Hp2 x Hx.
assert (U0 : 0 < U) by apply bpow_gt_0.
generalize (top_half emax) (top_ulp_le prec emax Hp2). intros T1 T2.
assert (EO : bpow radix2 emax = Omega + U) by (unfold IeeeBridge.Omega; ring).
assert (K : Rabs (rnd x - x) <= Rabs (Omega - x)).
{ apply (round_nearest prec emax). apply (format_Omega prec emax). }
replace (Omega - x) with (- (x - Omega)) in K by ring. rewrite Rabs_Ropp in K.
assert (K' : Rabs (rnd x - x) < / 2 * U) by lra.
apply Rabs_lt_inv in Hx. apply Rabs_lt_inv in K'.
assert (P : 0 < rnd x) by lra.
assert (I : inrange (rnd x)).
{ unfold IeeeBridge.inrange. rewrite Rabs_pos_eq by lra. lra. }
assert (L := inrange_le_Omega prec emax (rnd x) (Frnd x) I).
destruct (Req_dec (Rabs (rnd x)) Omega) as [E|N].
- rewrite Rabs_pos_eq in E by lra. exact E.
- exfalso. generalize (below_Omega prec emax Hp2 (rnd x) (Frnd x) L N).
  rewrite Rabs_pos_eq by lra. lra.
Qed.

Lemma rnd_near_top :
  (2 <= prec)%Z -> forall g x, Rabs g = Omega -> Rabs (x - g) < / 2 * U -> rnd x = g.
Proof.
intros Hp2 g x Hg Hx. revert Hg. unfold Rabs at 1. destruct (Rcase_abs g) as [Neg|Pos]; intros Hg.
- assert (E : rnd (- x) = Omega).
  { apply (rnd_near_Omega Hp2). replace (- x - Omega) with (- (x - g)) by lra.
    now rewrite Rabs_Ropp. }
  rewrite rnd_opp in E. lra.
- rewrite Hg in *. now apply rnd_near_Omega.
Qed.

(** * The leading limbs below 2^(emax - 1), and their tails *)

Lemma pred_H : pred radix2 fexp H = Omega / 2.
Proof.
rewrite pred_bpow. unfold IeeeBridge.Omega.
replace (fexp (emax - 1)) with (emax - prec - 1)%Z by (unfold FLT_exp; lia).
rewrite (top_half emax).
replace (emax - prec)%Z with (1 + (emax - prec - 1))%Z at 2 by ring.
rewrite bpow_plus, pow2_1. field.
Qed.

(* A number of the format below H in magnitude is at most Omega / 2. *)
Lemma lt_H_le_half_Omega : forall x, format x -> Rabs x < H -> Rabs x <= Omega / 2.
Proof.
intros x Fx Hx. rewrite <- pred_H. apply pred_ge_gt; auto with typeclass_instances.
- now apply generic_format_abs.
- apply generic_format_bpow. unfold FLT_exp. lia.
Qed.

(* A number of the format other than Omega / 2 and its opposite, and at most that in
   magnitude, is at most Omega / 2 - U/2: twice it is a number of the format below Omega. *)
Lemma below_half_Omega :
  (2 <= prec)%Z -> forall x, format x -> Rabs x <= Omega / 2 -> Rabs x <> Omega / 2 ->
  Rabs x <= Omega / 2 - / 2 * U.
Proof.
intros Hp2 x Fx Hx Hne.
assert (F2 : format (x * bpow radix2 1)) by (apply mult_bpow_pos_exact_FLT; [exact Fx|lia]).
rewrite pow2_1 in F2.
assert (K := below_Omega prec emax Hp2 (x * 2) F2).
rewrite Rabs_mult, (Rabs_pos_eq 2) in K by lra.
assert (K' : Rabs x * 2 <= Omega - U) by (apply K; lra).
lra.
Qed.

(* Below H the numbers of the format are at most U/2 apart. *)
Lemma ulp_below_H : forall x, Rabs x < H -> ulp radix2 fexp x <= / 2 * U.
Proof.
intros x Hx. rewrite (half_U prec emax). destruct (Req_dec x 0) as [Z|Z].
- rewrite Z, ulp_FLT_0 by exact prec_gt_0_. apply bpow_le. lia.
- rewrite ulp_neq_0 by exact Z. apply bpow_le. unfold cexp, FLT_exp.
  assert (mag radix2 x <= emax - 1)%Z by now apply mag_le_bpow.
  lia.
Qed.

Lemma tail_below_H :
  forall x0 x1, normalized_2 emin prec x0 x1 -> Rabs x0 < H -> Rabs x1 <= / 4 * U.
Proof.
intros x0 x1 Hn Hx. apply Rle_trans with (1 := normalized_2_tail_ulp emin prec x0 x1 Hn).
generalize (ulp_below_H x0 Hx). lra.
Qed.

(* The tail of a normalized pair whose leading limb is the number of the format just below
   2^k is strictly below half the gap 2^(k - prec) of its binade: at half the gap the value
   is halfway between that number and a neighbor, and the tie goes to the neighbor, whose
   significand is even (that of the number just below 2^k is 2^prec - 1). *)
Lemma tail_pred_pow2_strict :
  (2 <= prec)%Z -> forall k : Z, (emin + prec <= k)%Z ->
  forall x1, normalized_2 emin prec (bpow radix2 k - bpow radix2 (k - prec)) x1 ->
  Rabs x1 < / 2 * bpow radix2 (k - prec).
Proof.
intros Hp2 k Hk x1 Hn.
assert (W0 : 0 < bpow radix2 (k - prec)) by apply bpow_gt_0.
assert (EM : IZR (2 ^ prec) = bpow radix2 prec) by (apply (IZR_Zpower radix2); lia).
assert (EB : bpow radix2 k = bpow radix2 prec * bpow radix2 (k - prec)).
{ rewrite <- bpow_plus. f_equal. ring. }
assert (P4 : 4 <= bpow radix2 prec).
{ rewrite <- pow2_2. apply bpow_le. lia. }
assert (B4 : 4 * bpow radix2 (k - prec) <= bpow radix2 k) by (rewrite EB; nra).
assert (HB : bpow radix2 (k - 1) = / 2 * bpow radix2 k).
{ replace k with (1 + (k - 1))%Z at 2 by ring. rewrite bpow_plus, pow2_1. field. }
assert (Cx : forall x, / 2 * bpow radix2 k <= x < bpow radix2 k ->
             cexp radix2 fexp x = (k - prec)%Z).
{ intros x Hx. unfold cexp. rewrite (mag_unique_pos radix2 x k).
  - unfold FLT_exp. lia.
  - rewrite HB. exact Hx. }
assert (Hx1 : Rabs x1 <= / 2 * bpow radix2 (k - prec)).
{ apply Rle_trans with (1 := normalized_2_tail_ulp emin prec _ _ Hn).
  rewrite ulp_neq_0 by lra. rewrite Cx by lra. lra. }
destruct Hx1 as [Hlt|Heq]; [exact Hlt|exfalso].
destruct Hn as [_ [_ E]]. unfold RN in E.
destruct (Rcase_abs x1) as [Neg|Pos].
- (* x1 is minus half the gap: halfway between the number below, even, and this one *)
  rewrite Rabs_left in Heq by exact Neg.
  assert (Ex : bpow radix2 k - bpow radix2 (k - prec) + x1
               = (IZR (2 ^ prec - 2) + / 2) * bpow radix2 (k - prec)).
  { rewrite minus_IZR, EM. replace x1 with (- (/ 2 * bpow radix2 (k - prec))) by lra.
    rewrite EB. field. }
  assert (Ev : Z.even (2 ^ prec - 2) = true).
  { rewrite Z.even_sub, Z.even_pow by lia. reflexivity. }
  rewrite Ex, rnd_tie, Ev, minus_IZR, EM in E.
  + rewrite EB in E. nra.
  + apply Cx. rewrite <- Ex. lra.
- (* x1 is half the gap: halfway between this number, odd, and 2^k *)
  rewrite Rabs_pos_eq in Heq by lra.
  assert (Ex : bpow radix2 k - bpow radix2 (k - prec) + x1
               = (IZR (2 ^ prec - 1) + / 2) * bpow radix2 (k - prec)).
  { rewrite minus_IZR, EM. replace x1 with (/ 2 * bpow radix2 (k - prec)) by lra.
    rewrite EB. field. }
  assert (Ev : Z.even (2 ^ prec - 1) = false).
  { rewrite Z.even_sub, Z.even_pow by lia. reflexivity. }
  rewrite Ex, rnd_tie, Ev in E.
  + replace (2 ^ prec - 1 + 1)%Z with (2 ^ prec)%Z in E by ring.
    rewrite EM in E. rewrite EB in E. nra.
  + apply Cx. rewrite <- Ex. lra.
Qed.

(* The same for a leading limb of either sign. *)
Lemma tail_strict_sym :
  forall g b : R,
  (forall x1, normalized_2 emin prec g x1 -> Rabs x1 < b) ->
  forall x0 x1, normalized_2 emin prec x0 x1 -> Rabs x0 = g -> Rabs x1 < b.
Proof.
intros g b Hpos x0 x1 Hn. unfold Rabs at 1. destruct (Rcase_abs x0) as [Neg|Pos]; intros Hx.
- rewrite <- Rabs_Ropp. apply Hpos. rewrite <- Hx. now apply normalized_2_opp.
- apply Hpos. now rewrite <- Hx.
Qed.

(* A leading limb Omega / 2 or its opposite: the tail is strictly below U/4. *)
Lemma tail_half_Omega_strict :
  (2 <= prec)%Z -> forall x0 x1, normalized_2 emin prec x0 x1 -> Rabs x0 = Omega / 2 ->
  Rabs x1 < / 4 * U.
Proof.
intros Hp2. apply tail_strict_sym. intros x1 Hn.
assert (E0 : bpow radix2 (emax - 1 - prec) = / 2 * U).
{ replace (emax - 1 - prec)%Z with (emax - prec - 1)%Z by ring. symmetry. apply half_U. }
assert (E1 : Omega / 2 = H - bpow radix2 (emax - 1 - prec)).
{ rewrite E0. unfold IeeeBridge.Omega. rewrite (top_half emax). field. }
rewrite E1 in Hn.
generalize (tail_pred_pow2_strict Hp2 (emax - 1)%Z ltac:(lia) x1 Hn). rewrite E0. lra.
Qed.

(* A leading limb Omega or its opposite: the tail is strictly below U/2. *)
Lemma tail_Omega_strict :
  (2 <= prec)%Z -> forall x0 x1, normalized_2 emin prec x0 x1 -> Rabs x0 = Omega ->
  Rabs x1 < / 2 * U.
Proof.
intros Hp2. apply tail_strict_sym. intros x1 Hn.
exact (tail_pred_pow2_strict Hp2 emax ltac:(lia) x1 Hn).
Qed.

(* A number strictly inside the midpoints between Omega / 2 and H, on both sides, rounds to
   at most Omega / 2 in magnitude. *)
Lemma rnd_below_half_mid :
  forall v, Rabs v < Omega / 2 + / 4 * U -> Rabs (rnd v) <= Omega / 2.
Proof.
intros v Hv.
assert (EO := Omega_eq prec emax).
assert (S : succ radix2 fexp (Omega / 2) = H).
{ rewrite <- pred_H. apply succ_pred; auto with typeclass_instances.
  apply generic_format_bpow. unfold FLT_exp. lia. }
assert (Up : forall w, w < Omega / 2 + / 4 * U -> rnd w <= Omega / 2).
{ intros w Hw. apply round_N_le_midp; auto with typeclass_instances.
  - apply (format_half_Omega prec emax).
  - rewrite S. lra. }
apply Rabs_lt_inv in Hv. apply Rabs_le. split.
- assert (K : rnd (- v) <= Omega / 2) by (apply Up; lra). rewrite rnd_opp in K. lra.
- apply Up. lra.
Qed.

(** * Every value of the real model is in range *)

Lemma add_2_2_range_half :
  (3 <= prec)%Z ->
  forall X0 X1 Y0 Y1 : R,
  normalized_2 emin prec X0 X1 -> normalized_2 emin prec Y0 Y1 ->
  Rabs X0 < H -> Rabs Y0 < H ->
  Forall inrange (runR IeeeModel.add_2_2_prog [X0; X1; Y0; Y1]).
Proof.
intros Hp3 X0 X1 Y0 Y1 Nx Ny Hx0 Hy0.
assert (Hp2 : (2 <= prec)%Z) by lia.
(* powers of two *)
assert (U0 : 0 < U) by apply bpow_gt_0.
assert (T1 : bpow radix2 emax = 2 * H) by apply top_half.
assert (T3 : 4 * U <= H).
{ replace (emax - 1)%Z with (2 + (emax - 3))%Z by ring. rewrite bpow_plus, pow2_2.
  apply Rmult_le_compat_l. lra. apply bpow_le. lia. }
assert (T4 : U = 2 * bpow radix2 (emax - prec - 1)).
{ replace (emax - prec)%Z with (1 + (emax - prec - 1))%Z at 1 by ring.
  now rewrite bpow_plus, pow2_1. }
assert (T5 : 2 * U = bpow radix2 (emax - prec + 1)).
{ rewrite bpow_plus, pow2_1. ring. }
assert (Q4 : bpow radix2 (emax - prec - 2) = / 4 * U).
{ replace (emax - prec - 2)%Z with (-2 + (emax - prec))%Z by ring. rewrite bpow_plus. reflexivity. }
assert (EO : Omega = 2 * H - U).
{ unfold IeeeBridge.Omega. now rewrite T1. }
(* the operands *)
assert (FX0 : format X0) by apply Nx. assert (FX1 : format X1) by apply Nx.
assert (FY0 : format Y0) by apply Ny. assert (FY1 : format Y1) by apply Ny.
assert (BX0 : Rabs X0 <= Omega / 2) by now apply lt_H_le_half_Omega.
assert (BY0 : Rabs Y0 <= Omega / 2) by now apply lt_H_le_half_Omega.
assert (HX1 : Rabs X1 <= / 4 * U) by exact (tail_below_H X0 X1 Nx Hx0).
assert (HY1 : Rabs Y1 <= / 4 * U) by exact (tail_below_H Y0 Y1 Ny Hy0).
assert (IX0 : inrange X0) by (unfold IeeeBridge.inrange; lra).
assert (IX1 : inrange X1) by (unfold IeeeBridge.inrange; lra).
assert (IY0 : inrange Y0) by (unfold IeeeBridge.inrange; lra).
assert (IY1 : inrange Y1) by (unfold IeeeBridge.inrange; lra).
(* the values, by their names in the kernel *)
cbv [IeeeBridge.runR run stepR nth app IeeeModel.add_2_2_prog].
set (sh := rnd (X0 + Y0)). set (bb1 := rnd (sh - X0)). set (t01 := rnd (sh - bb1)).
set (t11 := rnd (X0 - t01)). set (t21 := rnd (Y0 - bb1)). set (sl := rnd (t11 + t21)).
set (th := rnd (X1 + Y1)). set (bb2 := rnd (th - X1)). set (t02 := rnd (th - bb2)).
set (t12 := rnd (X1 - t02)). set (t22 := rnd (Y1 - bb2)). set (tl := rnd (t12 + t22)).
set (c := rnd (sl + th)). set (vh := rnd (sh + c)). set (z := rnd (vh - sh)).
set (vl := rnd (c - z)). set (w := rnd (tl + vl)). set (z0 := rnd (vh + w)).
set (zz := rnd (z0 - vh)). set (z1 := rnd (w - zz)).
(* two_sum(x0, y0) *)
assert (Ish : inrange sh).
{ apply (rnd_le_Omega prec emax). apply Rle_trans with (1 := Rabs_triang _ _). lra. }
assert (TS1 : inrange bb1 /\ inrange t01 /\ inrange t11 /\ inrange t21 /\ inrange sl /\
              sl = X0 + Y0 - sh).
{ apply (two_sum_call_range prec emax Hp2 X0 Y0); trivial; lra. }
destruct TS1 as [Ibb1 [It01 [It11 [It21 [Isl Esl]]]]].
assert (Hsl : Rabs sl <= / 2 * U).
{ rewrite Esl. replace (X0 + Y0 - sh) with (- (sh - (X0 + Y0))) by ring. rewrite Rabs_Ropp.
  exact (round_error_top prec emax (X0 + Y0) Ish). }
(* two_sum(x1, y1) *)
assert (HXY1 : Rabs (X1 + Y1) <= / 2 * U).
{ apply Rle_trans with (1 := Rabs_triang _ _). lra. }
assert (Hth : Rabs th <= / 2 * U).
{ replace (/ 2 * U) with (bpow radix2 (emax - prec - 1)) by lra.
  apply (RN_abs_le_bpow emin prec). lra. }
assert (Ith : inrange th).
{ apply (le_bpow_inrange emax) with (emax - prec)%Z. lia. lra. }
assert (TS2 : inrange bb2 /\ inrange t02 /\ inrange t12 /\ inrange t22 /\ inrange tl /\
              tl = X1 + Y1 - th).
{ apply (two_sum_call_range prec emax Hp2 X1 Y1); trivial; lra. }
destruct TS2 as [Ibb2 [It02 [It12 [It22 [Itl Etl]]]]].
assert (Htl : Rabs tl <= / 2 * U).
{ rewrite Etl. replace (X1 + Y1 - th) with (- (th - (X1 + Y1))) by ring. rewrite Rabs_Ropp.
  apply Rle_trans with (Rabs (0 - (X1 + Y1))).
  - apply (round_nearest prec emax). apply generic_format_0.
  - replace (0 - (X1 + Y1)) with (- (X1 + Y1)) by ring. now rewrite Rabs_Ropp. }
(* c and its rounding error *)
assert (Hc : Rabs c <= U).
{ apply (RN_abs_le_bpow emin prec). apply Rle_trans with (1 := Rabs_triang _ _). lra. }
assert (Ic : inrange c).
{ apply (le_bpow_inrange emax) with (emax - prec)%Z. lia. exact Hc. }
assert (Dc : Rabs (c - (sl + th)) <= / 8 * U).
{ apply (round_error_le emin prec tie_even (sl + th) (emax - prec)).
  - apply Rle_trans with (1 := Rabs_triang _ _). lra.
  - replace (2 * (/ 8 * U)) with (bpow radix2 (emax - prec - 2)) by lra. apply bpow_le. lia.
  - replace (2 * (/ 8 * U)) with (bpow radix2 (emax - prec - 2)) by lra. apply bpow_le. lia. }
(* what follows a vh that is in range *)
assert (FS1 : inrange vh -> inrange z /\ Rabs vl <= U).
{ intros Ivh. apply (fast_two_sum_call_range prec emax sh c); trivial.
  - apply Frnd.
  - lra. }
assert (HW : Rabs vl <= U -> Rabs w <= 2 * U).
{ intros Hvl. rewrite T5. apply (RN_abs_le_bpow emin prec). rewrite <- T5.
  apply Rle_trans with (1 := Rabs_triang _ _). lra. }
(* the three cases *)
assert (Cases : Rabs (X0 + Y0) <= Omega - / 2 * U \/
                (Rabs (X0 + Y0) = Omega /\ Rabs th < / 2 * U)).
{ destruct (Req_dec (Rabs X0) (Omega / 2)) as [EX|NX].
  2:{ left. generalize (below_half_Omega Hp2 X0 FX0 BX0 NX) (Rabs_triang X0 Y0). lra. }
  destruct (Req_dec (Rabs Y0) (Omega / 2)) as [EY|NY].
  2:{ left. generalize (below_half_Omega Hp2 Y0 FY0 BY0 NY) (Rabs_triang X0 Y0). lra. }
  assert (SX := tail_half_Omega_strict Hp2 X0 X1 Nx EX).
  assert (SY := tail_half_Omega_strict Hp2 Y0 Y1 Ny EY).
  assert (STh : Rabs th < / 2 * U).
  { assert (FQ : format (/ 4 * U)).
    { rewrite <- Q4. apply generic_format_bpow. unfold FLT_exp. lia. }
    set (P := pred radix2 fexp (/ 4 * U)).
    assert (FP : format P) by (apply generic_format_pred; auto with typeclass_instances).
    assert (LP : P < / 4 * U) by (apply pred_lt_id; lra).
    assert (PX : Rabs X1 <= P).
    { apply pred_ge_gt; auto with typeclass_instances. now apply generic_format_abs. }
    assert (PY : Rabs Y1 <= P).
    { apply pred_ge_gt; auto with typeclass_instances. now apply generic_format_abs. }
    assert (F2P : format (P * bpow radix2 1)) by (apply mult_bpow_pos_exact_FLT; [exact FP|lia]).
    rewrite pow2_1 in F2P.
    assert (K : Rabs th <= P * 2).
    { apply (Format.round_abs_le emin prec tie_even); [exact F2P|].
      apply Rle_trans with (1 := Rabs_triang _ _). lra. }
    lra. }
  assert (CX : X0 = Omega / 2 \/ X0 = - (Omega / 2)).
  { revert EX. unfold Rabs. destruct (Rcase_abs X0); intros EX; [right|left]; lra. }
  assert (CY : Y0 = Omega / 2 \/ Y0 = - (Omega / 2)).
  { revert EY. unfold Rabs. destruct (Rcase_abs Y0); intros EY; [right|left]; lra. }
  destruct CX as [CX|CX]; destruct CY as [CY|CY].
  - right. split; [|exact STh]. replace (X0 + Y0) with Omega by lra. apply Rabs_pos_eq. lra.
  - left. replace (X0 + Y0) with 0 by lra. rewrite Rabs_R0. lra.
  - left. replace (X0 + Y0) with 0 by lra. rewrite Rabs_R0. lra.
  - right. split; [|exact STh]. replace (X0 + Y0) with (- Omega) by lra.
    rewrite Rabs_Ropp. apply Rabs_pos_eq. lra. }
assert (Main : inrange vh /\ inrange z0).
{ destruct Cases as [CA|[CB Sth]].
  - (* |x0 + y0| <= Omega - U/2 *)
    assert (Ivh : inrange vh).
    { apply (rnd_below_mid prec emax).
      replace (sh + c) with ((X0 + Y0) + th + (c - (sl + th))) by lra.
      assert (Tr := Rabs_triang ((X0 + Y0) + th) (c - (sl + th))).
      assert (Tr2 := Rabs_triang (X0 + Y0) th).
      lra. }
    split; [exact Ivh|].
    destruct (FS1 Ivh) as [Iz Hvl]. assert (Hw := HW Hvl).
    destruct (Rle_or_lt (Rabs (X0 + Y0)) H) as [Small|Large].
    + (* the bounds of the quarter of the range *)
      assert (Hsh : Rabs sh <= H) by (apply (RN_abs_le_bpow emin prec); exact Small).
      assert (Hvh : Rabs vh <= H + U).
      { apply (Format.round_abs_le emin prec tie_even). apply (format_H_plus_U prec emax).
        apply Rle_trans with (1 := Rabs_triang _ _). lra. }
      apply (rnd_le_Omega prec emax). apply Rle_trans with (1 := Rabs_triang _ _). lra.
    + (* the first fast_two_sum is exact *)
      assert (Hsh : H <= Rabs sh).
      { apply (Format.round_abs_ge emin prec tie_even).
        - apply generic_format_bpow. unfold FLT_exp. lia.
        - lra. }
      assert (Ex : vh + vl = sh + c).
      { assert (Hcs : Rabs c <= Rabs sh) by lra.
        destruct (fast_two_sum_exact emin prec Hp2 sh c (Frnd _) (Frnd _) Hcs) as [_ E].
        exact E. }
      assert (Dw : Rabs (w - (tl + vl)) <= / 4 * U).
      { apply (round_error_le emin prec tie_even (tl + vl) (emax - prec + 1)).
        - rewrite <- T5. apply Rle_trans with (1 := Rabs_triang _ _). lra.
        - replace (2 * (/ 4 * U)) with (bpow radix2 (emax - prec - 1)) by lra. apply bpow_le. lia.
        - replace (2 * (/ 4 * U)) with (bpow radix2 (emax - prec - 1)) by lra. apply bpow_le. lia. }
      apply (rnd_below_mid prec emax).
      replace (vh + w) with ((X0 + Y0) + (X1 + Y1) + (c - (sl + th)) + (w - (tl + vl))) by lra.
      assert (Tr := Rabs_triang ((X0 + Y0) + (X1 + Y1) + (c - (sl + th))) (w - (tl + vl))).
      assert (Tr2 := Rabs_triang ((X0 + Y0) + (X1 + Y1)) (c - (sl + th))).
      assert (Tr3 := Rabs_triang (X0 + Y0) (X1 + Y1)).
      lra.
  - (* x0 = y0 = Omega / 2, or both its opposite *)
    assert (Fg : format (X0 + Y0)).
    { apply generic_format_abs_inv. rewrite CB. apply (format_Omega prec emax). }
    assert (Esh : sh = X0 + Y0) by (unfold sh; apply round_generic; auto with typeclass_instances).
    assert (Esl0 : sl = 0) by lra.
    assert (Fth : format th) by (unfold th; apply Frnd).
    assert (Ec : c = th).
    { unfold c. rewrite Esl0, Rplus_0_l. apply round_generic; auto with typeclass_instances. }
    assert (Evh : vh = X0 + Y0).
    { unfold vh. rewrite Esh, Ec. apply (rnd_near_top Hp2); [exact CB|].
      replace (X0 + Y0 + th - (X0 + Y0)) with th by ring. exact Sth. }
    assert (Ez : z = 0).
    { unfold z. rewrite Evh, Esh. unfold Rminus. rewrite Rplus_opp_r.
      apply round_0; auto with typeclass_instances. }
    assert (Evl : vl = th).
    { unfold vl. rewrite Ec, Ez, Rminus_0_r. apply round_generic; auto with typeclass_instances. }
    assert (Ew : w = th).
    { unfold w. rewrite Evl. replace (tl + th) with (X1 + Y1) by lra. reflexivity. }
    assert (Ez0 : z0 = X0 + Y0).
    { unfold z0. rewrite Evh, Ew. apply (rnd_near_top Hp2); [exact CB|].
      replace (X0 + Y0 + th - (X0 + Y0)) with th by ring. exact Sth. }
    split.
    + rewrite Evh. apply (le_Omega_inrange prec emax). lra.
    + rewrite Ez0. apply (le_Omega_inrange prec emax). lra. }
destruct Main as [Ivh Iz0].
destruct (FS1 Ivh) as [Iz Hvl].
assert (Ivl : inrange vl).
{ apply (le_bpow_inrange emax) with (emax - prec)%Z. lia. exact Hvl. }
assert (Hw := HW Hvl).
assert (Iw : inrange w).
{ apply (le_bpow_inrange emax) with (emax - prec + 1)%Z. lia. now rewrite <- T5. }
assert (FS2 : inrange zz /\ Rabs z1 <= U).
{ apply (fast_two_sum_call_range prec emax vh w); trivial.
  - apply Frnd.
  - lra. }
destruct FS2 as [Izz Hz1].
assert (Iz1 : inrange z1).
{ apply (le_bpow_inrange emax) with (emax - prec)%Z. lia. exact Hz1. }
repeat constructor; trivial.
Qed.

(** * No overflow below half the range *)

Theorem add_2_2_values_finite_half :
  (3 <= prec)%Z ->
  forall x0 x1 y0 y1 : float, fin x0 -> fin x1 -> fin y0 -> fin y1 ->
  normalized_2 emin prec (b2r x0) (b2r x1) -> normalized_2 emin prec (b2r y0) (b2r y1) ->
  Rabs (b2r x0) < H -> Rabs (b2r y0) < H ->
  finite_all (runB IeeeModel.add_2_2_prog [x0; x1; y0; y1]) /\
  let '(z0, z1) := IeeeModel.add_2_2 prec emax nan_plus nan_minus x0 x1 y0 y1 in
  fin z0 /\ fin z1.
Proof.
intros Hp3 x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny Hx0 Hy0.
assert (Fe : finite_all [x0; x1; y0; y1]) by (repeat constructor; assumption).
assert (F : finite_all (runB IeeeModel.add_2_2_prog [x0; x1; y0; y1])).
{ apply (run_sim prec emax nan_plus nan_minus nan_opp nan_fma IeeeModel.add_2_2_prog _ Fe).
  now apply add_2_2_range_half. }
split. exact F.
rewrite (add_2_2_runB prec emax nan_plus nan_minus nan_opp nan_fma).
split; now apply (nth_fin prec emax).
Qed.

(** * add_2_2 with a zero operand, and with an operand that is not finite *)

(* With a second operand (0, 0): the values of the real model, one by one. Nothing is
   rounded: the result is the first operand. *)
Lemma add_2_2_zero_run :
  forall X0 X1 : R, normalized_2 emin prec X0 X1 ->
  runR IeeeModel.add_2_2_prog [X0; X1; 0; 0]
  = [X0; X1; 0; 0; X0; 0; X0; 0; 0; 0; X1; 0; X1; 0; 0; 0; X1; X0; 0; X1; X1; X0; 0; X1].
Proof.
intros X0 X1 [F0 [F1 E]]. unfold RN in E. unfold fmt in F0, F1.
cbv [IeeeBridge.runR run stepR nth app IeeeModel.add_2_2_prog]. unfold Rminus.
repeat first
  [ rewrite Rplus_0_r | rewrite Rplus_0_l | rewrite Ropp_0 | rewrite Rplus_opp_r
  | rewrite (round_0 radix2 fexp (Znearest tie_even))
  | rewrite (round_generic radix2 fexp (Znearest tie_even) X0 F0)
  | rewrite (round_generic radix2 fexp (Znearest tie_even) X1 F1)
  | rewrite <- E ].
reflexivity.
Qed.

(* add_2_2 of a finite normalized pair and a pair of zeros, of either sign: finite, and the
   value of each limb is that of the first operand. No condition on its magnitude. *)
Lemma add_2_2_zero_right :
  forall x0 x1 y0 y1 : float, fin x0 -> fin x1 -> normalized_2 emin prec (b2r x0) (b2r x1) ->
  zero y0 -> zero y1 ->
  let '(z0, z1) := IeeeModel.add_2_2 prec emax nan_plus nan_minus x0 x1 y0 y1 in
  fin z0 /\ fin z1 /\ b2r z0 = b2r x0 /\ b2r z1 = b2r x1.
Proof.
intros x0 x1 y0 y1 F0 F1 Nx [s0 E0] [s1 E1]. subst y0 y1.
assert (Fe : finite_all [x0; x1; B754_zero prec emax s0; B754_zero prec emax s1])
  by (repeat constructor; assumption).
destruct (run_sim prec emax nan_plus nan_minus nan_opp nan_fma IeeeModel.add_2_2_prog _ Fe)
  as [S1 S2].
assert (R : runR IeeeModel.add_2_2_prog
              (map b2r [x0; x1; B754_zero prec emax s0; B754_zero prec emax s1])
            = [b2r x0; b2r x1; 0; 0; b2r x0; 0; b2r x0; 0; 0; 0; b2r x1; 0; b2r x1; 0; 0; 0;
               b2r x1; b2r x0; 0; b2r x1; b2r x1; b2r x0; 0; b2r x1])
  by exact (add_2_2_zero_run (b2r x0) (b2r x1) Nx).
assert (F : finite_all (runB IeeeModel.add_2_2_prog
                          [x0; x1; B754_zero prec emax s0; B754_zero prec emax s1])).
{ apply S1. rewrite R.
  repeat constructor; try apply (b2r_inrange prec emax);
    unfold IeeeBridge.inrange; rewrite Rabs_R0; apply bpow_gt_0. }
assert (M := S2 F). rewrite R in M.
rewrite (add_2_2_runB prec emax nan_plus nan_minus nan_opp nan_fma).
split; [now apply (nth_fin prec emax)|split; [now apply (nth_fin prec emax)|]].
split.
- rewrite (sim_nth prec emax _ _ 21%nat M). reflexivity.
- rewrite (sim_nth prec emax _ _ 23%nat M). reflexivity.
Qed.

Lemma sub_nan_r :
  forall x y : float, is_nan prec emax y = true ->
  is_nan prec emax (IeeeOperations.sub prec emax nan_minus x y) = true.
Proof.
intros x [s|s|s pl H|s m e H]; try discriminate; intros _. destruct x; reflexivity.
Qed.

(* add_2_2 with a first operand whose leading limb is an infinity or a NaN, and a second
   operand whose leading limb is finite: the leading limb of the result is a NaN. The first
   sum, sh, is that infinity or a NaN; the next operation of two_sum, sh - x0, is the
   difference of two equal infinities or has a NaN operand; and every value that follows on
   the way to z0 has a NaN operand. *)
Lemma add_2_2_lead_not_finite :
  forall x0 x1 y0 y1 : float, is_finite prec emax x0 = false -> fin y0 ->
  is_nan prec emax (fst (IeeeModel.add_2_2 prec emax nan_plus nan_minus x0 x1 y0 y1)) = true.
Proof.
intros x0 x1 y0 y1 Nx Fy.
cbv beta iota zeta delta [IeeeModel.add_2_2 IeeeModel.two_sum IeeeModel.fast_two_sum fst].
assert (Nbb : is_nan prec emax
                (IeeeOperations.sub prec emax nan_minus
                   (IeeeOperations.add prec emax nan_plus x0 y0) x0) = true).
{ destruct x0 as [s|s|s pl Hx|s m e Hx]; try discriminate Nx.
  - destruct s; destruct y0 as [t|t|t pl Hy|t m e Hy]; try discriminate Fy; reflexivity.
  - apply sub_nan_r. reflexivity. }
apply (add_nan_l prec emax nan_plus). apply (add_nan_r prec emax nan_plus).
apply (add_nan_l prec emax nan_plus). apply (add_nan_r prec emax nan_plus).
apply sub_nan_r. exact Nbb.
Qed.

End IeeeAdd22Top.

(** * The statements *)

(* Written by hand: the generator prints the threshold of a quarter of the range
   (add_2_2_ieee_finite_spec), which is the claim of the kernel. The first is the statement
   that proofs/wip/IeeeSharper.v conjectured, as it was written there; the second says the
   same of every value that the kernel computes, in the form of the generated statement. *)
Definition add_2_2_ieee_finite_half_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax),
  (3 <= prec)%Z ->
  forall x0 x1 y0 y1 : binary_float prec emax,
  finite x0 -> finite x1 -> finite y0 -> finite y1 ->
  normalized_2 (ieee_emin prec emax) prec (val x0) (val x1) ->
  normalized_2 (ieee_emin prec emax) prec (val y0) (val y1) ->
  Rabs (val x0) < bpow radix2 (emax - 1) ->
  Rabs (val y0) < bpow radix2 (emax - 1) ->
  let '(z0, z1) := IeeeModel.add_2_2 prec emax nan_plus nan_minus x0 x1 y0 y1 in
  finite z0 /\ finite z1.

Definition add_2_2_ieee_finite_half_values_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_opp : nan1 prec emax) (nan_fma : nan3 prec emax),
  (3 <= prec)%Z ->
  forall x0 x1 y0 y1 : binary_float prec emax,
  finite x0 -> finite x1 -> finite y0 -> finite y1 ->
  normalized_2 (ieee_emin prec emax) prec (val x0) (val x1) ->
  normalized_2 (ieee_emin prec emax) prec (val y0) (val y1) ->
  Rabs (val x0) < bpow radix2 (emax - 1) ->
  Rabs (val y0) < bpow radix2 (emax - 1) ->
  Forall finite (run (stepB prec emax nan_plus nan_minus nan_opp nan_fma)
                     IeeeModel.add_2_2_prog [x0; x1; y0; y1]) /\
  let '(z0, z1) := IeeeModel.add_2_2 prec emax nan_plus nan_minus x0 x1 y0 y1 in
  finite z0 /\ finite z1.

Theorem add_2_2_ieee_finite_half_values : add_2_2_ieee_finite_half_values_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp3 x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny Hx Hy.
exact (add_2_2_values_finite_half prec emax nan_plus nan_minus nan_opp nan_fma Hp3 x0 x1 y0 y1
         F0 F1 G0 G1 Nx Ny Hx Hy).
Qed.

Theorem add_2_2_ieee_finite_half : add_2_2_ieee_finite_half_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus Hp3 x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny Hx Hy.
exact (proj2 (add_2_2_values_finite_half prec emax nan_plus nan_minus
                (fun x => nan_plus x x) (fun x y _ => nan_plus x y) Hp3 x0 x1 y0 y1
                F0 F1 G0 G1 Nx Ny Hx Hy)).
Qed.
