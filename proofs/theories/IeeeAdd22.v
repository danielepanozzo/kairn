(* add_2_2 in the IEEE model (proofs/gen/IeeeModel.v), for finite normalized operands x and y.

   1. Bridge (add_2_2_bridge, add_2_2_values). If output limb 0 is finite then all twenty
      values of the kernel are finite and equal, as real numbers, to those of the real
      model. Eighteen of them are in the cone of z0, which is checked by computation;
      the last two, the tail of the final fast_two_sum, are finite because the result
      of the real model is normalized (IeeeBridge.bridge_f2s, with add_2_2_correct).

   2. Correctness (add_2_2_values_correct). Hence, if z0 is finite: z1 is finite, z is
      normalized, and |z - (x + y)| <= 3u^2/(1 - 4u) |x + y|. An overflow inside the
      kernel never produces a finite wrong result.

   3. No spurious overflow (add_2_2_values_finite). If |x0| and |y0| are at most
      2^(emax - 2), a quarter of 2^emax, then every value is finite. No condition on
      the exact result is needed: it is then at most 2^(emax - 1) (1 + u).
      The proof bounds each value of the real model: with H = 2^(emax - 1) and
      U = 2^(emax - prec), the unit in the last place of the largest numbers,
      |sh| <= H, |sl|, |th|, |tl| <= U/2, |c| <= U, |vh| <= H + U, |vl| <= U,
      |w| <= 2U, |vh + w| <= H + 3U <= Omega, and the tail is at most U.

   Beyond this: the statement holds up to |x0|, |y0| <= Omega/2, and not beyond (at
   |x0| = |y0| = 2^(emax - 1) the leading sum overflows). That is proved in
   IeeeAdd22Top.v (add_2_2_values_finite_half), with the special case x0 = y0 = Omega/2,
   where the general bounds above leave no margin. Exhaustive enumeration of toy formats
   says that it also holds, with no condition on the operands, when
   |x + y| <= 2^(emax - 1): that statement is written down, unproved, in
   wip/IeeeSharper.v (IeeeRange.v proves it for |x + y| <= 2^(emax - 2)).

   The statements, in the form of proofs/gen/IeeeStatements.v, are at the end of the file:
   add_2_2_ieee_bridge, add_2_2_ieee_correct, add_2_2_ieee_finite. *)
From Stdlib Require Import Reals ZArith List Arith Bool Lia Lra.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements IeeeStatements.
From Kairn Require Import Format Normalized EFT Add22 Program IeeeBridge IeeeEFT IeeeVocabulary.
From Kairn Require IeeeOperations.
From Kairn.Gen Require IeeeModel.
Import ListNotations.
Open Scope R_scope.

(* The program of proofs/gen/IeeeModel.v is the kernel of the real model. *)
Lemma add_2_2_runR :
  forall emin prec choice x0 x1 y0 y1,
  add_2_2 emin prec choice x0 x1 y0 y1 =
  (nth 21 (runR emin prec choice IeeeModel.add_2_2_prog [x0; x1; y0; y1]) 0,
   nth 23 (runR emin prec choice IeeeModel.add_2_2_prog [x0; x1; y0; y1]) 0).
Proof.
intros. cbv [add_2_2 two_sum fast_two_sum runR run stepR nth app IeeeModel.add_2_2_prog].
reflexivity.
Qed.

Section IeeeAdd22.
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

(* The program is the kernel of the IEEE model. *)
Lemma add_2_2_runB :
  forall x0 x1 y0 y1 : float,
  IeeeModel.add_2_2 prec emax nan_plus nan_minus x0 x1 y0 y1 =
  (nth 21 (runB IeeeModel.add_2_2_prog [x0; x1; y0; y1]) d0,
   nth 23 (runB IeeeModel.add_2_2_prog [x0; x1; y0; y1]) d0).
Proof.
intros. cbv [IeeeModel.add_2_2 IeeeModel.two_sum IeeeModel.fast_two_sum run stepB nth app
             IeeeModel.add_2_2_prog].
reflexivity.
Qed.

(** * Bridge *)

Theorem add_2_2_bridge :
  (3 <= prec)%Z ->
  forall x0 x1 y0 y1 : float, fin x0 -> fin x1 -> fin y0 -> fin y1 ->
  normalized_2 emin prec (b2r x0) (b2r x1) -> normalized_2 emin prec (b2r y0) (b2r y1) ->
  fin (nth 21 (runB IeeeModel.add_2_2_prog [x0; x1; y0; y1]) d0) ->
  finite_all (runB IeeeModel.add_2_2_prog [x0; x1; y0; y1]) /\
  map b2r (runB IeeeModel.add_2_2_prog [x0; x1; y0; y1])
  = runR IeeeModel.add_2_2_prog [b2r x0; b2r x1; b2r y0; b2r y1].
Proof.
intros Hp3 x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny Hz.
apply (bridge_f2s_prog prec emax nan_plus nan_minus nan_opp nan_fma
         IeeeModel.add_2_2_prog (firstn 17 IeeeModel.add_2_2_prog) 17%nat 20%nat
         [x0; x1; y0; y1] 21%nat); trivial.
- repeat constructor; assumption.
- generalize (add_2_2_correct emin prec Hp3 (b2r x0) (b2r x1) (b2r y0) (b2r y1) Nx Ny).
  rewrite add_2_2_runR. intros [N _]. exact N.
Qed.

Theorem add_2_2_values :
  (3 <= prec)%Z ->
  forall x0 x1 y0 y1 : float, fin x0 -> fin x1 -> fin y0 -> fin y1 ->
  normalized_2 emin prec (b2r x0) (b2r x1) -> normalized_2 emin prec (b2r y0) (b2r y1) ->
  let '(z0, z1) := IeeeModel.add_2_2 prec emax nan_plus nan_minus x0 x1 y0 y1 in
  fin z0 ->
  fin z1 /\
  (b2r z0, b2r z1) = add_2_2 emin prec tie_even (b2r x0) (b2r x1) (b2r y0) (b2r y1).
Proof.
intros Hp3 x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny. rewrite add_2_2_runB. intros Hz.
destruct (add_2_2_bridge Hp3 x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny Hz) as [F M]. split.
- now apply nth_fin.
- rewrite add_2_2_runR. f_equal; now apply sim_nth.
Qed.

(** * Correctness *)

Theorem add_2_2_values_correct :
  (3 <= prec)%Z ->
  forall x0 x1 y0 y1 : float, fin x0 -> fin x1 -> fin y0 -> fin y1 ->
  normalized_2 emin prec (b2r x0) (b2r x1) -> normalized_2 emin prec (b2r y0) (b2r y1) ->
  let '(z0, z1) := IeeeModel.add_2_2 prec emax nan_plus nan_minus x0 x1 y0 y1 in
  fin z0 ->
  fin z1 /\
  normalized_2 emin prec (b2r z0) (b2r z1) /\
  Rabs ((b2r z0 + b2r z1) - ((b2r x0 + b2r x1) + (b2r y0 + b2r y1)))
  <= (3 / (1 - (4 * u prec))) * u prec ^ 2 * Rabs ((b2r x0 + b2r x1) + (b2r y0 + b2r y1)).
Proof.
intros Hp3 x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny.
generalize (add_2_2_values Hp3 x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny)
           (add_2_2_correct emin prec Hp3 (b2r x0) (b2r x1) (b2r y0) (b2r y1) Nx Ny).
destruct (IeeeModel.add_2_2 prec emax nan_plus nan_minus x0 x1 y0 y1) as [z0 z1].
intros B C Fz. destruct (B Fz) as [Fz1 E]. rewrite <- E in C. split. exact Fz1. exact C.
Qed.

(** * No spurious overflow *)

(* The number of the format just above 2^(emax - 1). *)
Lemma format_H_plus_U : format (H + U).
Proof.
replace (H + U) with (succ radix2 fexp H).
- apply generic_format_succ; auto with typeclass_instances.
  apply generic_format_bpow. unfold FLT_exp. lia.
- rewrite succ_eq_pos by apply bpow_ge_0. rewrite ulp_bpow. do 2 f_equal. unfold FLT_exp. lia.
Qed.

(* Every value of the real model is in range when the leading limbs are at most
   2^(emax - 2). *)
Lemma add_2_2_range :
  (3 <= prec)%Z ->
  forall x0 x1 y0 y1 : float,
  normalized_2 emin prec (b2r x0) (b2r x1) -> normalized_2 emin prec (b2r y0) (b2r y1) ->
  Rabs (b2r x0) <= bpow radix2 (emax - 2) -> Rabs (b2r y0) <= bpow radix2 (emax - 2) ->
  Forall inrange (runR IeeeModel.add_2_2_prog [b2r x0; b2r x1; b2r y0; b2r y1]).
Proof.
intros Hp3 x0 x1 y0 y1 Nx Ny Hx0 Hy0.
assert (Hp2 : (2 <= prec)%Z) by lia.
(* powers of two *)
assert (U0 : 0 < U) by apply bpow_gt_0.
assert (T1 : bpow radix2 emax = 2 * H) by apply top_half.
assert (T2 : H = 2 * bpow radix2 (emax - 2)).
{ replace (emax - 1)%Z with (1 + (emax - 2))%Z by ring. now rewrite bpow_plus, pow2_1. }
assert (T3 : 4 * U <= H).
{ replace (emax - 1)%Z with (2 + (emax - 3))%Z by ring. rewrite bpow_plus, pow2_2.
  apply Rmult_le_compat_l. lra. apply bpow_le. lia. }
assert (T4 : U = 2 * bpow radix2 (emax - prec - 1)).
{ replace (emax - prec)%Z with (1 + (emax - prec - 1))%Z at 1 by ring.
  now rewrite bpow_plus, pow2_1. }
assert (T5 : 2 * U = bpow radix2 (emax - prec + 1)).
{ rewrite bpow_plus, pow2_1. ring. }
assert (T6 : u prec * bpow radix2 (emax - 2) = / 4 * U).
{ unfold u. rewrite <- bpow_plus.
  replace (emax - prec)%Z with (2 + (- prec + (emax - 2)))%Z by ring.
  rewrite (bpow_plus radix2 2), pow2_2. field. }
assert (EO : Omega = 2 * H - U).
{ unfold IeeeBridge.Omega. now rewrite T1. }
(* the operands *)
set (X0 := b2r x0) in *. set (X1 := b2r x1) in *. set (Y0 := b2r y0) in *. set (Y1 := b2r y1) in *.
assert (FX0 : format X0) by apply (b2r_format prec emax).
assert (FX1 : format X1) by apply (b2r_format prec emax).
assert (FY0 : format Y0) by apply (b2r_format prec emax).
assert (FY1 : format Y1) by apply (b2r_format prec emax).
assert (HX1 : Rabs X1 <= / 4 * U).
{ apply Rle_trans with (1 := normalized_2_tail_rel emin prec X0 X1 Nx). rewrite <- T6.
  apply Rmult_le_compat_l. apply bpow_ge_0. exact Hx0. }
assert (HY1 : Rabs Y1 <= / 4 * U).
{ apply Rle_trans with (1 := normalized_2_tail_rel emin prec Y0 Y1 Ny). rewrite <- T6.
  apply Rmult_le_compat_l. apply bpow_ge_0. exact Hy0. }
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
assert (Hsh : Rabs sh <= H).
{ apply (RN_abs_le_bpow emin prec). apply Rle_trans with (1 := Rabs_triang _ _). lra. }
assert (Ish : inrange sh).
{ apply (le_bpow_inrange emax) with (emax - 1)%Z. lia. exact Hsh. }
assert (TS1 : inrange bb1 /\ inrange t01 /\ inrange t11 /\ inrange t21 /\ inrange sl /\
              sl = X0 + Y0 - sh).
{ apply (two_sum_call_range prec emax Hp2 X0 Y0); trivial; rewrite EO; lra. }
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
{ apply (two_sum_call_range prec emax Hp2 X1 Y1); trivial; rewrite EO; lra. }
destruct TS2 as [Ibb2 [It02 [It12 [It22 [Itl Etl]]]]].
assert (Htl : Rabs tl <= / 2 * U).
{ rewrite Etl. replace (X1 + Y1 - th) with (- (th - (X1 + Y1))) by ring. rewrite Rabs_Ropp.
  apply Rle_trans with (Rabs (0 - (X1 + Y1))).
  - apply (round_nearest prec emax). apply generic_format_0.
  - replace (0 - (X1 + Y1)) with (- (X1 + Y1)) by ring. now rewrite Rabs_Ropp. }
(* c and fast_two_sum(sh, c) *)
assert (Hc : Rabs c <= U).
{ apply (RN_abs_le_bpow emin prec). apply Rle_trans with (1 := Rabs_triang _ _). lra. }
assert (Ic : inrange c).
{ apply (le_bpow_inrange emax) with (emax - prec)%Z. lia. exact Hc. }
assert (Hvh : Rabs vh <= H + U).
{ apply round_abs_le; trivial. apply format_H_plus_U.
  apply Rle_trans with (1 := Rabs_triang _ _). lra. }
assert (Ivh : inrange vh).
{ apply (le_Omega_inrange prec emax). rewrite EO. lra. }
assert (FS1 : inrange z /\ Rabs vl <= U).
{ apply (fast_two_sum_call_range prec emax sh c); trivial.
  - apply generic_format_round; auto with typeclass_instances.
  - rewrite EO. lra. }
destruct FS1 as [Iz Hvl].
assert (Ivl : inrange vl).
{ apply (le_bpow_inrange emax) with (emax - prec)%Z. lia. exact Hvl. }
(* w and fast_two_sum(vh, w) *)
assert (Hw : Rabs w <= 2 * U).
{ rewrite T5. apply (RN_abs_le_bpow emin prec). rewrite <- T5.
  apply Rle_trans with (1 := Rabs_triang _ _). lra. }
assert (Iw : inrange w).
{ apply (le_bpow_inrange emax) with (emax - prec + 1)%Z. lia. now rewrite <- T5. }
assert (Iz0 : inrange z0).
{ apply (rnd_le_Omega prec emax). rewrite EO.
  apply Rle_trans with (1 := Rabs_triang _ _). lra. }
assert (FS2 : inrange zz /\ Rabs z1 <= U).
{ apply (fast_two_sum_call_range prec emax vh w); trivial.
  - apply generic_format_round; auto with typeclass_instances.
  - rewrite EO. lra. }
destruct FS2 as [Izz Hz1].
assert (Iz1 : inrange z1).
{ apply (le_bpow_inrange emax) with (emax - prec)%Z. lia. exact Hz1. }
repeat constructor; trivial; apply b2r_inrange.
Qed.

Theorem add_2_2_values_finite :
  (3 <= prec)%Z ->
  forall x0 x1 y0 y1 : float, fin x0 -> fin x1 -> fin y0 -> fin y1 ->
  normalized_2 emin prec (b2r x0) (b2r x1) -> normalized_2 emin prec (b2r y0) (b2r y1) ->
  Rabs (b2r x0) <= bpow radix2 (emax - 2) -> Rabs (b2r y0) <= bpow radix2 (emax - 2) ->
  finite_all (runB IeeeModel.add_2_2_prog [x0; x1; y0; y1]) /\
  let '(z0, z1) := IeeeModel.add_2_2 prec emax nan_plus nan_minus x0 x1 y0 y1 in
  fin z0 /\ fin z1.
Proof.
intros Hp3 x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny Hx0 Hy0.
assert (Fe : finite_all [x0; x1; y0; y1]) by (repeat constructor; assumption).
assert (F : finite_all (runB IeeeModel.add_2_2_prog [x0; x1; y0; y1])).
{ apply (run_sim prec emax nan_plus nan_minus nan_opp nan_fma IeeeModel.add_2_2_prog _ Fe).
  now apply add_2_2_range. }
split. exact F. rewrite add_2_2_runB. split; now apply nth_fin.
Qed.

End IeeeAdd22.

(** * The statements of proofs/gen/IeeeStatements.v *)

Theorem add_2_2_ieee_bridge : add_2_2_ieee_bridge_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp3 x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny.
generalize (add_2_2_bridge prec emax nan_plus nan_minus nan_opp nan_fma Hp3 x0 x1 y0 y1
              F0 F1 G0 G1 Nx Ny)
           (add_2_2_values prec emax nan_plus nan_minus nan_opp nan_fma Hp3 x0 x1 y0 y1
              F0 F1 G0 G1 Nx Ny).
rewrite (add_2_2_runB prec emax nan_plus nan_minus nan_opp nan_fma).
intros B V Fz. destruct (B Fz) as [F _]. destruct (V Fz) as [Fz1 E].
split. exact F. split. exact Fz1. exact E.
Qed.

Theorem add_2_2_ieee_correct : add_2_2_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus Hp3 x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny.
exact (add_2_2_values_correct prec emax nan_plus nan_minus
         (fun x => nan_plus x x) (fun x y _ => nan_plus x y) Hp3 x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny).
Qed.

Theorem add_2_2_ieee_finite : add_2_2_ieee_finite_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp3 x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny Hx Hy.
exact (add_2_2_values_finite prec emax nan_plus nan_minus nan_opp nan_fma Hp3 x0 x1 y0 y1
         F0 F1 G0 G1 Nx Ny Hx Hy).
Qed.

