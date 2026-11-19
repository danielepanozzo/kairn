(* mul_2_2 in the IEEE model (IeeeDraft.v), for finite normalized operands x and y.

   1. Bridge (mul_2_2_bridge, mul_2_2_values). If output limb 0 is finite then all nine
      values of the kernel are finite and equal, as real numbers, to those of the real
      model. Seven are in the cone of z0, which is checked by computation; the tail of
      the final fast_two_sum is finite because the result of the real model is
      normalized (IeeeBridge.bridge_f2s, with mul_2_2_correct).

   2. Correctness (mul_2_2_values_correct). Hence, if z0 is finite: z1 is finite, z is
      normalized, and |z - x y| <= 4u^2 |x y| + 3/2 eta, with eta = 2^emin the smallest
      positive number of the IEEE format.

   3. No spurious overflow (mul_2_2_values_finite). If the exact product satisfies
      |x y| <= 2^(emax - 1), half of 2^emax, then every value is finite. No condition
      on the operands. The proof bounds each value of the real model: with
      H = 2^(emax - 1) and U = 2^(emax - prec) = 2u H,
      |x0 y0| <= |x y| / (1 - u)^2 <= H + 3U/2, so |ch| <= H + 2U; the cross terms are
      at most 0.6 U each, |cl3| <= 4U, |ch + cl3| <= H + 6U <= Omega, and the tail is
      at most U.

   What exhaustive enumeration of toy formats says beyond this (not proved here): the
   kernel overflows only at the leading product or at the final sum; the smallest
   |x y| for which it does is 0.78, 0.90 and 0.94 times 2^emax at precisions 3, 4 and 5
   (the bounds above give at least (1 - u/2) (1 - u)^2), so 2^(emax - 1) is the largest
   threshold that is a power of two.

   The statements, in the form of IeeeStatementsDraft.v, are at the end of the file:
   mul_2_2_ieee_bridge, mul_2_2_ieee_correct, mul_2_2_ieee_finite. *)
From Stdlib Require Import Reals ZArith List Arith Bool Lia Lra Psatz.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements.
From Kairn Require Import Format Normalized EFT Mul22 Program IeeeBridge IeeeEFT IeeeStatementsDraft.
From Kairn Require IeeeDraft.
Import ListNotations.
Open Scope R_scope.

(* The program of IeeeDraft.v is the kernel of the real model. *)
Lemma mul_2_2_runR :
  forall emin prec choice x0 x1 y0 y1,
  mul_2_2 emin prec choice x0 x1 y0 y1 =
  (nth 10 (runR emin prec choice IeeeDraft.mul_2_2_prog [x0; x1; y0; y1]) 0,
   nth 12 (runR emin prec choice IeeeDraft.mul_2_2_prog [x0; x1; y0; y1]) 0).
Proof.
intros. cbv [mul_2_2 two_prod fast_two_sum runR run stepR nth app IeeeDraft.mul_2_2_prog].
reflexivity.
Qed.

Section IeeeMul22.
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
Lemma mul_2_2_runB :
  forall x0 x1 y0 y1 : float,
  IeeeDraft.mul_2_2 prec emax nan_plus nan_minus nan_opp nan_fma x0 x1 y0 y1 =
  (nth 10 (runB IeeeDraft.mul_2_2_prog [x0; x1; y0; y1]) d0,
   nth 12 (runB IeeeDraft.mul_2_2_prog [x0; x1; y0; y1]) d0).
Proof.
intros. cbv [IeeeDraft.mul_2_2 IeeeDraft.two_prod IeeeDraft.fast_two_sum run stepB nth app
             IeeeDraft.mul_2_2_prog].
reflexivity.
Qed.

(** * Bridge *)

Theorem mul_2_2_bridge :
  (4 <= prec)%Z ->
  forall x0 x1 y0 y1 : float, fin x0 -> fin x1 -> fin y0 -> fin y1 ->
  normalized_2 emin prec (b2r x0) (b2r x1) -> normalized_2 emin prec (b2r y0) (b2r y1) ->
  fin (nth 10 (runB IeeeDraft.mul_2_2_prog [x0; x1; y0; y1]) d0) ->
  finite_all (runB IeeeDraft.mul_2_2_prog [x0; x1; y0; y1]) /\
  map b2r (runB IeeeDraft.mul_2_2_prog [x0; x1; y0; y1])
  = runR IeeeDraft.mul_2_2_prog [b2r x0; b2r x1; b2r y0; b2r y1].
Proof.
intros Hp4 x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny Hz.
apply (bridge_f2s_prog prec emax nan_plus nan_minus nan_opp nan_fma
         IeeeDraft.mul_2_2_prog (firstn 6 IeeeDraft.mul_2_2_prog) 4%nat 9%nat
         [x0; x1; y0; y1] 10%nat); trivial.
- repeat constructor; assumption.
- generalize (mul_2_2_correct emin prec Hp4 (b2r x0) (b2r x1) (b2r y0) (b2r y1) Nx Ny).
  rewrite mul_2_2_runR. intros [N _]. exact N.
Qed.

Theorem mul_2_2_values :
  (4 <= prec)%Z ->
  forall x0 x1 y0 y1 : float, fin x0 -> fin x1 -> fin y0 -> fin y1 ->
  normalized_2 emin prec (b2r x0) (b2r x1) -> normalized_2 emin prec (b2r y0) (b2r y1) ->
  let '(z0, z1) := IeeeDraft.mul_2_2 prec emax nan_plus nan_minus nan_opp nan_fma x0 x1 y0 y1 in
  fin z0 ->
  fin z1 /\
  (b2r z0, b2r z1) = mul_2_2 emin prec tie_even (b2r x0) (b2r x1) (b2r y0) (b2r y1).
Proof.
intros Hp4 x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny. rewrite mul_2_2_runB. intros Hz.
destruct (mul_2_2_bridge Hp4 x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny Hz) as [F M]. split.
- now apply nth_fin.
- rewrite mul_2_2_runR. f_equal; now apply sim_nth.
Qed.

(** * Correctness *)

Theorem mul_2_2_values_correct :
  (4 <= prec)%Z ->
  forall x0 x1 y0 y1 : float, fin x0 -> fin x1 -> fin y0 -> fin y1 ->
  normalized_2 emin prec (b2r x0) (b2r x1) -> normalized_2 emin prec (b2r y0) (b2r y1) ->
  let '(z0, z1) := IeeeDraft.mul_2_2 prec emax nan_plus nan_minus nan_opp nan_fma x0 x1 y0 y1 in
  fin z0 ->
  fin z1 /\
  normalized_2 emin prec (b2r z0) (b2r z1) /\
  Rabs ((b2r z0 + b2r z1) - ((b2r x0 + b2r x1) * (b2r y0 + b2r y1)))
  <= 4 * u prec ^ 2 * Rabs ((b2r x0 + b2r x1) * (b2r y0 + b2r y1)) + (3 / 2) * eta emin.
Proof.
intros Hp4 x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny.
generalize (mul_2_2_values Hp4 x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny)
           (mul_2_2_correct emin prec Hp4 (b2r x0) (b2r x1) (b2r y0) (b2r y1) Nx Ny).
destruct (IeeeDraft.mul_2_2 prec emax nan_plus nan_minus nan_opp nan_fma x0 x1 y0 y1) as [z0 z1].
intros B C Fz. destruct (B Fz) as [Fz1 E]. rewrite <- E in C. split. exact Fz1. exact C.
Qed.

(** * No spurious overflow *)

(* The leading limb of a normalized pair is at most 1/(1 - u) times the value. *)
Lemma normalized_2_head_le :
  forall x0 x1, normalized_2 emin prec x0 x1 -> (1 - u prec) * Rabs x0 <= Rabs (x0 + x1).
Proof.
intros x0 x1 N. generalize (normalized_2_tail_rel emin prec x0 x1 N). intros T.
assert (K : Rabs x0 <= Rabs (x0 + x1) + Rabs x1).
{ replace x0 with ((x0 + x1) + - x1) at 1 by ring.
  apply Rle_trans with (1 := Rabs_triang _ _). rewrite Rabs_Ropp. lra. }
lra.
Qed.

(* Every value of the real model is in range when the exact product is at most
   2^(emax - 1) in magnitude. *)
Lemma mul_2_2_range :
  (4 <= prec)%Z ->
  forall x0 x1 y0 y1 : float,
  normalized_2 emin prec (b2r x0) (b2r x1) -> normalized_2 emin prec (b2r y0) (b2r y1) ->
  Rabs ((b2r x0 + b2r x1) * (b2r y0 + b2r y1)) <= bpow radix2 (emax - 1) ->
  Forall inrange (runR IeeeDraft.mul_2_2_prog [b2r x0; b2r x1; b2r y0; b2r y1]).
Proof.
intros Hp4 x0 x1 y0 y1 Nx Ny Hxy.
(* powers of two *)
assert (U0 : 0 < U) by apply bpow_gt_0.
assert (H0 : 0 < H) by apply bpow_gt_0.
assert (T1 : bpow radix2 emax = 2 * H) by apply top_half.
assert (u0 : 0 < u prec) by apply bpow_gt_0.
assert (u16 : u prec <= / 16).
{ unfold u. change (/ 16) with (bpow radix2 (-4)). apply bpow_le. lia. }
assert (T2 : U = 2 * u prec * H).
{ unfold u. replace (emax - prec)%Z with (1 + (- prec + (emax - 1)))%Z by ring.
  rewrite 2!bpow_plus, pow2_1. ring. }
assert (HU8 : 8 * U <= H) by (rewrite T2; nra).
assert (T3 : 2 * U = bpow radix2 (emax - prec + 1)).
{ rewrite bpow_plus, pow2_1. ring. }
assert (T4 : 4 * U = bpow radix2 (emax - prec + 2)).
{ rewrite bpow_plus, pow2_2. ring. }
assert (T5 : U = 8 * bpow radix2 (emax - prec - 3)).
{ replace (emax - prec)%Z with (3 + (emax - prec - 3))%Z at 1 by ring.
  now rewrite bpow_plus, pow2_3. }
assert (EO : Omega = 2 * H - U).
{ unfold IeeeBridge.Omega. now rewrite T1. }
(* the operands *)
set (X0 := b2r x0) in *. set (X1 := b2r x1) in *. set (Y0 := b2r y0) in *. set (Y1 := b2r y1) in *.
generalize (normalized_2_tail_rel emin prec X0 X1 Nx) (normalized_2_tail_rel emin prec Y0 Y1 Ny).
intros HX1 HY1.
generalize (normalized_2_head_le X0 X1 Nx) (normalized_2_head_le Y0 Y1 Ny). intros HX HY.
generalize (Rabs_pos X0) (Rabs_pos Y0). intros A0 B0.
(* the leading product is at most H + 3U/2 *)
set (P := Rabs X0 * Rabs Y0).
assert (P0 : 0 <= P) by (unfold P; nra).
assert (HP1 : (1 - u prec) ^ 2 * P <= H).
{ apply Rle_trans with (2 := Hxy). rewrite Rabs_mult. unfold P.
  replace ((1 - u prec) ^ 2 * (Rabs X0 * Rabs Y0))
    with (((1 - u prec) * Rabs X0) * ((1 - u prec) * Rabs Y0)) by ring.
  apply Rmult_le_compat; trivial; nra. }
assert (K : 1 <= (1 - u prec) ^ 2 * (1 + 3 * u prec)) by nra.
assert (HP : P <= H + 3 / 2 * U).
{ apply Rle_trans with (P * ((1 - u prec) ^ 2 * (1 + 3 * u prec))). nra.
  replace (P * ((1 - u prec) ^ 2 * (1 + 3 * u prec)))
    with ((1 - u prec) ^ 2 * P * (1 + 3 * u prec)) by ring.
  replace (H + 3 / 2 * U) with (H * (1 + 3 * u prec)) by (rewrite T2; field).
  apply Rmult_le_compat_r; lra. }
assert (HuP : u prec * P <= 6 / 10 * U).
{ rewrite T2 in HP |- *. nra. }
assert (HX0Y0 : Rabs (X0 * Y0) = P) by apply Rabs_mult.
assert (HX0Y1 : Rabs (X0 * Y1) <= 6 / 10 * U).
{ rewrite Rabs_mult. apply Rle_trans with (2 := HuP). unfold P. nra. }
assert (HX1Y0 : Rabs (X1 * Y0) <= 6 / 10 * U).
{ rewrite Rabs_mult. apply Rle_trans with (2 := HuP). unfold P. nra. }
assert (HX1Y1 : Rabs (X1 * Y1) <= / 8 * U).
{ rewrite Rabs_mult. apply Rle_trans with (u prec * (u prec * P)).
  - unfold P. replace (u prec * (u prec * (Rabs X0 * Rabs Y0)))
      with ((u prec * Rabs X0) * (u prec * Rabs Y0)) by ring.
    apply Rmult_le_compat; trivial; apply Rabs_pos.
  - nra. }
(* the values, by their names in the kernel *)
cbv [IeeeBridge.runR run stepR nth app IeeeDraft.mul_2_2_prog].
set (ch := rnd (X0 * Y0 + 0)). set (cl1 := rnd (X0 * Y0 + - ch)).
set (tl0 := rnd (X1 * Y1 + 0)). set (tl1 := rnd (X0 * Y1 + tl0)).
set (cl2 := rnd (X1 * Y0 + tl1)). set (cl3 := rnd (cl1 + cl2)).
set (z0 := rnd (ch + cl3)). set (zz := rnd (z0 - ch)). set (z1 := rnd (cl3 - zz)).
(* two_prod(x0, y0) *)
assert (Ich : inrange ch).
{ apply (rnd_le_Omega prec emax). rewrite Rplus_0_r, HX0Y0, EO. lra. }
assert (Hch : Rabs ch <= H + 2 * U).
{ generalize (round_error_top prec emax (X0 * Y0 + 0) Ich). fold ch. intros E.
  replace ch with ((ch - (X0 * Y0 + 0)) + X0 * Y0) by ring.
  apply Rle_trans with (1 := Rabs_triang _ _). rewrite HX0Y0. lra. }
assert (Hcl1 : Rabs cl1 <= U) by exact (two_prod_error_le prec emax X0 Y0 Ich).
assert (Icl1 : inrange cl1).
{ apply (le_bpow_inrange emax) with (emax - prec)%Z. lia. exact Hcl1. }
(* the three small products *)
assert (Htl0 : Rabs tl0 <= / 8 * U).
{ replace (/ 8 * U) with (bpow radix2 (emax - prec - 3)) by lra.
  apply (RN_abs_le_bpow emin prec). rewrite Rplus_0_r. lra. }
assert (Itl0 : inrange tl0).
{ apply (le_bpow_inrange emax) with (emax - prec)%Z. lia. lra. }
assert (Htl1 : Rabs tl1 <= U).
{ apply (RN_abs_le_bpow emin prec). apply Rle_trans with (1 := Rabs_triang _ _). lra. }
assert (Itl1 : inrange tl1).
{ apply (le_bpow_inrange emax) with (emax - prec)%Z. lia. exact Htl1. }
assert (Hcl2 : Rabs cl2 <= 2 * U).
{ rewrite T3. apply (RN_abs_le_bpow emin prec). rewrite <- T3.
  apply Rle_trans with (1 := Rabs_triang _ _). lra. }
assert (Icl2 : inrange cl2).
{ apply (le_bpow_inrange emax) with (emax - prec + 1)%Z. lia. now rewrite <- T3. }
assert (Hcl3 : Rabs cl3 <= 4 * U).
{ rewrite T4. apply (RN_abs_le_bpow emin prec). rewrite <- T4.
  apply Rle_trans with (1 := Rabs_triang _ _). lra. }
assert (Icl3 : inrange cl3).
{ apply (le_bpow_inrange emax) with (emax - prec + 2)%Z. lia. now rewrite <- T4. }
(* fast_two_sum(ch, cl3) *)
assert (Iz0 : inrange z0).
{ apply (rnd_le_Omega prec emax). rewrite EO.
  apply Rle_trans with (1 := Rabs_triang _ _). lra. }
assert (FS : inrange zz /\ Rabs z1 <= U).
{ apply (fast_two_sum_call_range prec emax ch cl3); trivial.
  - apply generic_format_round; auto with typeclass_instances.
  - rewrite EO. lra. }
destruct FS as [Izz Hz1].
assert (Iz1 : inrange z1).
{ apply (le_bpow_inrange emax) with (emax - prec)%Z. lia. exact Hz1. }
repeat constructor; trivial; apply b2r_inrange.
Qed.

Theorem mul_2_2_values_finite :
  (4 <= prec)%Z ->
  forall x0 x1 y0 y1 : float, fin x0 -> fin x1 -> fin y0 -> fin y1 ->
  normalized_2 emin prec (b2r x0) (b2r x1) -> normalized_2 emin prec (b2r y0) (b2r y1) ->
  Rabs ((b2r x0 + b2r x1) * (b2r y0 + b2r y1)) <= bpow radix2 (emax - 1) ->
  finite_all (runB IeeeDraft.mul_2_2_prog [x0; x1; y0; y1]) /\
  let '(z0, z1) := IeeeDraft.mul_2_2 prec emax nan_plus nan_minus nan_opp nan_fma x0 x1 y0 y1 in
  fin z0 /\ fin z1.
Proof.
intros Hp4 x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny Hxy.
assert (Fe : finite_all [x0; x1; y0; y1]) by (repeat constructor; assumption).
assert (F : finite_all (runB IeeeDraft.mul_2_2_prog [x0; x1; y0; y1])).
{ apply (run_sim prec emax nan_plus nan_minus nan_opp nan_fma IeeeDraft.mul_2_2_prog _ Fe).
  now apply mul_2_2_range. }
split. exact F. rewrite mul_2_2_runB. split; now apply nth_fin.
Qed.

End IeeeMul22.

(** * The statements of IeeeStatementsDraft.v *)

Theorem mul_2_2_ieee_bridge : mul_2_2_ieee_bridge_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp4 x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny.
generalize (mul_2_2_bridge prec emax nan_plus nan_minus nan_opp nan_fma Hp4 x0 x1 y0 y1
              F0 F1 G0 G1 Nx Ny)
           (mul_2_2_values prec emax nan_plus nan_minus nan_opp nan_fma Hp4 x0 x1 y0 y1
              F0 F1 G0 G1 Nx Ny).
rewrite (mul_2_2_runB prec emax nan_plus nan_minus nan_opp nan_fma).
intros B V Fz. destruct (B Fz) as [F _]. destruct (V Fz) as [Fz1 E].
split. exact F. split. exact Fz1. exact E.
Qed.

Theorem mul_2_2_ieee_correct : mul_2_2_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp4 x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny.
exact (mul_2_2_values_correct prec emax nan_plus nan_minus nan_opp nan_fma Hp4 x0 x1 y0 y1
         F0 F1 G0 G1 Nx Ny).
Qed.

Theorem mul_2_2_ieee_finite : mul_2_2_ieee_finite_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp4 x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny Hxy.
exact (mul_2_2_values_finite prec emax nan_plus nan_minus nan_opp nan_fma Hp4 x0 x1 y0 y1
         F0 F1 G0 G1 Nx Ny Hxy).
Qed.

