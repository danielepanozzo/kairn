(* Magnitudes in the real model: conditions under which no value of a kernel reaches
   2^emax, beyond those of IeeeAdd22.v and IeeeMul22.v.

   These are statements about the real model alone (the format with no largest number,
   with emin = 3 - emax - prec). By IeeeBridge.run_sim they say that the IEEE model of
   the kernel returns finite values. They serve twice in the non-finite layer: as the
   "finite when" conditions of the full kernels (F3), and, read backwards, to say what
   the operands must look like when a kernel does overflow (F4).

   Notation: H = 2^(emax - 1), Q = 2^(emax - 2), U = 2^(emax - prec), the unit in the
   last place of the largest numbers, and Omega = 2 H - U.

   1. A kernel that starts with the sum of the leading limbs (add_2_2, add_fast_2_2,
      add_2_1): if the exact result is at most Q in magnitude, every value is in range
      (K_range_sum). Whatever the operands: they may be +-Omega and cancel. The leading
      sum is then at most Q + U, so its rounding error is at most U/4, and the second
      operation of two_sum, RN (s - a), stays strictly inside the midpoint between
      Omega and 2^emax (rnd_below_mid); this is where two_sum can overflow in general
      (IeeeEFT.v). After that every value is small: |vh + w| <= Q + 19/4 U <= Omega for
      add_2_2, which has no margin to spare at prec = 3.

   2. The same kernels when both operands are at most Q in magnitude (K_range for
      add_2_1 and add_fast_2_2; add_2_2 is in IeeeAdd22.v).

   3. A kernel that starts with the product of the leading limbs (mul_2_2, mul_2_1,
      mul_pow2_2): if that product rounds to zero, every value is zero
      (K_range_zero). So a kernel that overflows has a leading product that is not
      zero.

   4. mul_2_1 and mul_pow2_2 when the exact product is at most H in magnitude
      (K_range), from prec = 3 on for mul_2_1.

   The subtractions are the additions of the opposite. *)
From Stdlib Require Import Reals ZArith List Arith Bool Lia Lra Psatz.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements.
From Kairn Require Import Format Guard Normalized EFT Program IeeeBridge IeeeEFT IeeeMul22.
From Kairn Require IeeeOperations.
From Kairn.Gen Require IeeeModel.
Import ListNotations.
Open Scope R_scope.

Section IeeeRange.
Variable prec emax : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Context {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}.

Notation float := (binary_float prec emax).

Notation emin := (3 - emax - prec)%Z.
Notation fexp := (FLT_exp emin prec).
Notation format := (generic_format radix2 fexp).
Notation rnd := (round radix2 fexp (Znearest tie_even)).
Notation b2r := (B2R prec emax).
Notation inrange := (inrange emax).
Notation Omega := (Omega prec emax).
Notation runR := (runR emin prec tie_even).
Notation H := (bpow radix2 (emax - 1)).
Notation Q := (bpow radix2 (emax - 2)).
Notation U := (bpow radix2 (emax - prec)).

Let Hprec : (0 < prec)%Z.
Proof. exact prec_gt_0_. Qed.
Let Hemax : (prec < emax)%Z.
Proof. exact prec_lt_emax_. Qed.

Let rnd_opp : forall x, rnd (- x) = - rnd x.
Proof. intros x. exact (RN_opp emin prec x). Qed.

Let Frnd : forall x, format (rnd x).
Proof. intros x. apply generic_format_round; auto with typeclass_instances. Qed.

(** * Powers of two *)

Lemma H_2Q : H = 2 * Q.
Proof. replace (emax - 1)%Z with (1 + (emax - 2))%Z by ring. now rewrite bpow_plus, pow2_1. Qed.

Lemma Omega_eq : Omega = 2 * H - U.
Proof. unfold IeeeBridge.Omega. now rewrite (top_half emax). Qed.

Lemma U_le_H : forall k : Z, (0 <= k)%Z -> (k + 1 <= prec)%Z -> bpow radix2 k * U <= H.
Proof.
intros k Hk0 Hk. rewrite <- bpow_plus. apply bpow_le. lia.
Qed.

Lemma half_U : / 2 * U = bpow radix2 (emax - prec - 1).
Proof.
replace (emax - prec)%Z with (1 + (emax - prec - 1))%Z at 1 by ring.
rewrite bpow_plus, pow2_1. field.
Qed.

Lemma two_U : 2 * U = bpow radix2 (emax - prec + 1).
Proof. rewrite bpow_plus, pow2_1. ring. Qed.

(* 3/2 U is a number of the format. *)
Lemma format_3_half_U : (2 <= prec)%Z -> format (3 / 2 * U).
Proof.
intros Hp2.
replace (3 / 2 * U) with (IZR 3 * bpow radix2 (emax - prec - 1)) by (rewrite <- half_U; field).
apply (format_multiple emin prec). lia.
generalize (bpow_gt_0 radix2 (emax - prec - 1)). intros B0.
assert (B4 : 4 <= bpow radix2 prec).
{ rewrite <- pow2_2. apply bpow_le. lia. }
rewrite Rabs_pos_eq by lra.
rewrite (bpow_plus radix2 (emax - prec - 1) prec). nra.
Qed.

(** * Rounding next to the largest number *)

Lemma succ_Omega : succ radix2 fexp Omega = bpow radix2 emax.
Proof.
rewrite <- (pred_top prec emax). apply succ_pred; auto with typeclass_instances.
apply (format_top prec emax).
Qed.

(* A number strictly inside the midpoints between Omega and 2^emax, on both sides,
   rounds into the range. *)
Lemma rnd_below_mid : forall v, Rabs v < Omega + / 2 * U -> inrange (rnd v).
Proof.
intros v Hv.
assert (EO : bpow radix2 emax = Omega + U) by (unfold IeeeBridge.Omega; ring).
assert (Up : forall w, w < Omega + / 2 * U -> rnd w <= Omega).
{ intros w Hw. apply round_N_le_midp; auto with typeclass_instances; [apply (format_Omega prec emax)|].
  rewrite succ_Omega, EO. lra. }
apply (le_Omega_inrange prec emax). apply Rabs_lt_inv in Hv. apply Rabs_le. split.
- assert (K : rnd (- v) <= Omega) by (apply Up; lra). rewrite rnd_opp in K. lra.
- apply Up. lra.
Qed.

(* If rounding gives zero, the number was at most half the smallest positive number. *)
Lemma rnd_zero_inv : forall v, rnd v = 0 -> Rabs v <= bpow radix2 (emin - 1).
Proof.
assert (E1 : bpow radix2 emin = 2 * bpow radix2 (emin - 1)).
{ replace emin with (1 + (emin - 1))%Z at 1 by ring. now rewrite bpow_plus, pow2_1. }
assert (Feta : format (bpow radix2 emin)).
{ apply generic_format_bpow. unfold FLT_exp. lia. }
assert (Peta : pred radix2 fexp (bpow radix2 emin) = 0).
{ rewrite <- (ulp_FLT_0 radix2 emin prec) at 1. apply pred_ulp_0; auto with typeclass_instances. }
assert (Up : forall w, bpow radix2 (emin - 1) < w -> bpow radix2 emin <= rnd w).
{ intros w Hw. apply round_N_ge_midp; auto with typeclass_instances. rewrite Peta. lra. }
intros v Hv. generalize (bpow_gt_0 radix2 emin). intros E0.
apply Rabs_le. split.
- destruct (Rle_or_lt (- bpow radix2 (emin - 1)) v) as [K|K]; trivial. exfalso.
  assert (K' : bpow radix2 emin <= rnd (- v)) by (apply Up; lra).
  rewrite rnd_opp, Hv in K'. lra.
- destruct (Rle_or_lt v (bpow radix2 (emin - 1))) as [K|K]; trivial. exfalso.
  generalize (Up v K). rewrite Hv. lra.
Qed.

(* The limbs of a pair of the IEEE format. *)
Lemma tail_le_half_U :
  forall x0 x1 : float, normalized_2 emin prec (b2r x0) (b2r x1) -> Rabs (b2r x1) <= / 2 * U.
Proof.
intros x0 x1 N. apply Rle_trans with (1 := normalized_2_tail_ulp emin prec _ _ N).
apply Rmult_le_compat_l. lra. apply (ulp_le_top prec emax). apply (b2r_inrange prec emax).
Qed.

(* The rounding error of a number of magnitude at most H is at most U/4. *)
Lemma round_error_below_H : forall v, Rabs v <= H -> Rabs (rnd v - v) <= / 4 * U.
Proof.
intros v Hv. generalize (round_error_bpow emin prec tie_even v (emax - 1) Hv).
rewrite Z.max_l by lia.
replace (emax - 1 - prec)%Z with (emax - prec - 1)%Z by ring. rewrite <- half_U. lra.
Qed.

(** * add_2_2 when the exact sum is at most Q *)

Lemma add_2_2_range_sum :
  (3 <= prec)%Z ->
  forall x0 x1 y0 y1 : float,
  normalized_2 emin prec (b2r x0) (b2r x1) -> normalized_2 emin prec (b2r y0) (b2r y1) ->
  Rabs ((b2r x0 + b2r x1) + (b2r y0 + b2r y1)) <= Q ->
  Forall inrange (runR IeeeModel.add_2_2_prog [b2r x0; b2r x1; b2r y0; b2r y1]).
Proof.
intros Hp3 x0 x1 y0 y1 Nx Ny Hxy.
assert (Hp2 : (2 <= prec)%Z) by lia.
assert (U0 : 0 < U) by apply bpow_gt_0.
generalize H_2Q Omega_eq (U_le_H 2 ltac:(lia) ltac:(lia)). rewrite pow2_2. intros T2 EO T3.
generalize (tail_le_half_U x0 x1 Nx) (tail_le_half_U y0 y1 Ny). intros HX1 HY1.
generalize (b2r_le_Omega prec emax x0) (b2r_le_Omega prec emax y0). intros OX0 OY0.
set (X0 := b2r x0) in *. set (X1 := b2r x1) in *. set (Y0 := b2r y0) in *. set (Y1 := b2r y1) in *.
assert (FX0 : format X0) by apply (b2r_format prec emax).
assert (FX1 : format X1) by apply (b2r_format prec emax).
assert (FY0 : format Y0) by apply (b2r_format prec emax).
assert (FY1 : format Y1) by apply (b2r_format prec emax).
assert (HS : Rabs (X0 + Y0) <= Q + U).
{ replace (X0 + Y0) with ((X0 + X1 + (Y0 + Y1)) + - (X1 + Y1)) by ring.
  apply Rle_trans with (1 := Rabs_triang _ _). rewrite Rabs_Ropp.
  generalize (Rabs_triang X1 Y1). lra. }
cbv [IeeeBridge.runR run stepR nth app IeeeModel.add_2_2_prog].
set (sh := rnd (X0 + Y0)). set (bb1 := rnd (sh - X0)). set (t01 := rnd (sh - bb1)).
set (t11 := rnd (X0 - t01)). set (t21 := rnd (Y0 - bb1)). set (sl := rnd (t11 + t21)).
set (th := rnd (X1 + Y1)). set (bb2 := rnd (th - X1)). set (t02 := rnd (th - bb2)).
set (t12 := rnd (X1 - t02)). set (t22 := rnd (Y1 - bb2)). set (tl := rnd (t12 + t22)).
set (c := rnd (sl + th)). set (vh := rnd (sh + c)). set (z := rnd (vh - sh)).
set (vl := rnd (c - z)). set (w := rnd (tl + vl)). set (z0 := rnd (vh + w)).
set (zz := rnd (z0 - vh)). set (z1 := rnd (w - zz)).
(* two_sum(x0, y0): the leading sum is small, so its error is at most U/4 *)
assert (Hd : Rabs (sh - (X0 + Y0)) <= / 4 * U) by (apply round_error_below_H; lra).
assert (Hsh : Rabs sh <= Q + 5 / 4 * U).
{ replace sh with ((sh - (X0 + Y0)) + (X0 + Y0)) by ring.
  apply Rle_trans with (1 := Rabs_triang _ _). lra. }
assert (Ish : inrange sh).
{ apply (le_Omega_inrange prec emax). rewrite EO. lra. }
assert (Ibb1 : inrange bb1).
{ apply rnd_below_mid. replace (sh - X0) with (Y0 + (sh - (X0 + Y0))) by ring.
  apply Rle_lt_trans with (1 := Rabs_triang _ _). lra. }
destruct (two_sum_range prec emax Hp2 X0 Y0 FX0 FY0 OX0 OY0 Ish Ibb1) as [It01 [It11 [It21 Isl]]].
assert (Esl : sl = X0 + Y0 - sh).
{ generalize (two_sum_exact emin prec Hp2 X0 Y0 FX0 FY0). intros [_ E].
  change (sh + sl = X0 + Y0) in E. lra. }
assert (Hsl : Rabs sl <= / 4 * U).
{ rewrite Esl. replace (X0 + Y0 - sh) with (- (sh - (X0 + Y0))) by ring. now rewrite Rabs_Ropp. }
(* two_sum(x1, y1) *)
assert (HXY1 : Rabs (X1 + Y1) <= U).
{ apply Rle_trans with (1 := Rabs_triang _ _). lra. }
assert (Hth : Rabs th <= U) by (apply (RN_abs_le_bpow emin prec); exact HXY1).
assert (Ith : inrange th).
{ apply (le_bpow_inrange emax) with (emax - prec)%Z. lia. exact Hth. }
assert (TS2 : inrange bb2 /\ inrange t02 /\ inrange t12 /\ inrange t22 /\ inrange tl /\
              tl = X1 + Y1 - th).
{ apply (two_sum_call_range prec emax Hp2 X1 Y1); trivial; rewrite EO; lra. }
destruct TS2 as [Ibb2 [It02 [It12 [It22 [Itl Etl]]]]].
assert (Htl : Rabs tl <= / 2 * U).
{ rewrite Etl. replace (X1 + Y1 - th) with (- (th - (X1 + Y1))) by ring. rewrite Rabs_Ropp.
  exact (round_error_top prec emax (X1 + Y1) Ith). }
(* c and fast_two_sum(sh, c) *)
assert (F32 : format (3 / 2 * U)) by now apply format_3_half_U.
assert (Hc : Rabs c <= 3 / 2 * U).
{ apply round_abs_le; trivial. apply Rle_trans with (1 := Rabs_triang _ _). lra. }
assert (Ic : inrange c).
{ apply (le_Omega_inrange prec emax). rewrite EO. lra. }
assert (Fc : format c) by apply Frnd.
assert (Ivh : inrange vh).
{ apply (rnd_le_Omega prec emax). rewrite EO.
  apply Rle_trans with (1 := Rabs_triang _ _). lra. }
assert (Hvh : Rabs vh <= Q + 13 / 4 * U).
{ generalize (round_error_top prec emax (sh + c) Ivh). fold vh. intros E.
  replace vh with ((vh - (sh + c)) + (sh + c)) by ring.
  apply Rle_trans with (1 := Rabs_triang _ _).
  generalize (Rabs_triang sh c). lra. }
assert (FS1 : inrange z /\ Rabs vl <= U).
{ apply (fast_two_sum_call_range prec emax sh c); trivial. rewrite EO. lra. }
destruct FS1 as [Iz Hvl].
assert (Ivl : inrange vl).
{ apply (le_bpow_inrange emax) with (emax - prec)%Z. lia. exact Hvl. }
(* w and fast_two_sum(vh, w) *)
assert (Hw : Rabs w <= 3 / 2 * U).
{ apply round_abs_le; trivial. apply Rle_trans with (1 := Rabs_triang _ _). lra. }
assert (Iw : inrange w).
{ apply (le_Omega_inrange prec emax). rewrite EO. lra. }
assert (Fw : format w) by apply Frnd.
assert (Iz0 : inrange z0).
{ apply (rnd_le_Omega prec emax). rewrite EO.
  apply Rle_trans with (1 := Rabs_triang _ _). lra. }
assert (FS2 : inrange zz /\ Rabs z1 <= U).
{ apply (fast_two_sum_call_range prec emax vh w); trivial. rewrite EO. lra. }
destruct FS2 as [Izz Hz1].
assert (Iz1 : inrange z1).
{ apply (le_bpow_inrange emax) with (emax - prec)%Z. lia. exact Hz1. }
repeat constructor; trivial; apply b2r_inrange.
Qed.

(** * mul_2_2 when the leading product rounds to zero *)

(* The products of the other limbs are then at most half the smallest positive number. *)
Lemma small_products :
  forall x0 x1 y0 y1 : R,
  normalized_2 emin prec x0 x1 -> normalized_2 emin prec y0 y1 ->
  Rabs (x0 * y0) <= bpow radix2 (emin - 1) ->
  Rabs (x0 * y1) <= bpow radix2 (emin - 1) /\
  Rabs (x1 * y0) <= bpow radix2 (emin - 1) /\
  Rabs (x1 * y1) <= bpow radix2 (emin - 1).
Proof.
intros x0 x1 y0 y1 Nx Ny Hp.
generalize (normalized_2_tail_rel emin prec x0 x1 Nx) (normalized_2_tail_rel emin prec y0 y1 Ny).
intros HX HY.
assert (u0 : 0 < u prec) by apply bpow_gt_0.
assert (u1 : u prec <= 1).
{ unfold u. change 1 with (bpow radix2 0). apply bpow_le. lia. }
generalize (Rabs_pos x0) (Rabs_pos y0) (Rabs_pos x1) (Rabs_pos y1). intros A0 B0 A1 B1.
rewrite Rabs_mult in Hp. rewrite 3!Rabs_mult.
set (P := Rabs x0 * Rabs y0) in *.
assert (P0 : 0 <= P) by (unfold P; now apply Rmult_le_pos).
assert (K0 : u prec * P <= P) by nra.
assert (K1 : Rabs x0 * Rabs y1 <= u prec * P).
{ unfold P. replace (u prec * (Rabs x0 * Rabs y0)) with (Rabs x0 * (u prec * Rabs y0)) by ring.
  now apply Rmult_le_compat_l. }
assert (K2 : Rabs x1 * Rabs y0 <= u prec * P).
{ unfold P. replace (u prec * (Rabs x0 * Rabs y0)) with (u prec * Rabs x0 * Rabs y0) by ring.
  now apply Rmult_le_compat_r. }
assert (K3 : Rabs x1 * Rabs y1 <= u prec * (u prec * P)).
{ unfold P. replace (u prec * (u prec * (Rabs x0 * Rabs y0)))
    with ((u prec * Rabs x0) * (u prec * Rabs y0)) by ring.
  now apply Rmult_le_compat. }
assert (K4 : u prec * (u prec * P) <= P) by nra.
repeat split; lra.
Qed.

Lemma mul_2_2_range_zero :
  forall x0 x1 y0 y1 : float,
  normalized_2 emin prec (b2r x0) (b2r x1) -> normalized_2 emin prec (b2r y0) (b2r y1) ->
  rnd (b2r x0 * b2r y0 + 0) = 0 ->
  Forall inrange (runR IeeeModel.mul_2_2_prog [b2r x0; b2r x1; b2r y0; b2r y1]).
Proof.
intros x0 x1 y0 y1 Nx Ny Hch.
assert (I0 : inrange 0).
{ unfold IeeeBridge.inrange. rewrite Rabs_R0. apply bpow_gt_0. }
assert (Hp : Rabs (b2r x0 * b2r y0) <= bpow radix2 (emin - 1)).
{ apply rnd_zero_inv. now rewrite Rplus_0_r in Hch. }
destruct (small_products _ _ _ _ Nx Ny Hp) as [H01 [H10 H11]].
set (X0 := b2r x0) in *. set (X1 := b2r x1) in *. set (Y0 := b2r y0) in *. set (Y1 := b2r y1) in *.
assert (R0 : rnd 0 = 0) by (apply round_0; auto with typeclass_instances).
cbv [IeeeBridge.runR run stepR nth app IeeeModel.mul_2_2_prog].
set (ch := rnd (X0 * Y0 + 0)) in *. set (cl1 := rnd (X0 * Y0 + - ch)).
set (tl0 := rnd (X1 * Y1 + 0)). set (tl1 := rnd (X0 * Y1 + tl0)).
set (cl2 := rnd (X1 * Y0 + tl1)). set (cl3 := rnd (cl1 + cl2)).
set (z0 := rnd (ch + cl3)). set (zz := rnd (z0 - ch)). set (z1 := rnd (cl3 - zz)).
assert (Ecl1 : cl1 = 0).
{ unfold cl1. rewrite Hch, Ropp_0. exact Hch. }
assert (Etl0 : tl0 = 0).
{ unfold tl0. rewrite Rplus_0_r. now apply (RN_small_zero emin prec). }
assert (Etl1 : tl1 = 0).
{ unfold tl1. rewrite Etl0, Rplus_0_r. now apply (RN_small_zero emin prec). }
assert (Ecl2 : cl2 = 0).
{ unfold cl2. rewrite Etl1, Rplus_0_r. now apply (RN_small_zero emin prec). }
assert (Ecl3 : cl3 = 0).
{ unfold cl3. rewrite Ecl1, Ecl2, Rplus_0_r. exact R0. }
assert (Ez0 : z0 = 0).
{ unfold z0. rewrite Hch, Ecl3, Rplus_0_r. exact R0. }
assert (Ezz : zz = 0).
{ unfold zz. rewrite Ez0, Hch, Rminus_0_r. exact R0. }
assert (Ez1 : z1 = 0).
{ unfold z1. rewrite Ecl3, Ezz, Rminus_0_r. exact R0. }
rewrite Ez1, Ezz, Ez0, Ecl3, Ecl2, Etl1, Etl0, Ecl1, Hch.
repeat constructor; trivial; apply b2r_inrange.
Qed.

(** * add_2_1 *)

Lemma uQ : u prec * Q = / 4 * U.
Proof.
unfold u. rewrite <- bpow_plus.
replace (emax - prec)%Z with (2 + (- prec + (emax - 2)))%Z by ring.
rewrite (bpow_plus radix2 2), pow2_2. field.
Qed.

(* When both operands are at most Q in magnitude. *)
Lemma add_2_1_range :
  (3 <= prec)%Z ->
  forall x0 x1 a : float,
  normalized_2 emin prec (b2r x0) (b2r x1) ->
  Rabs (b2r x0) <= Q -> Rabs (b2r a) <= Q ->
  Forall inrange (runR IeeeModel.add_2_1_prog [b2r x0; b2r x1; b2r a]).
Proof.
intros Hp3 x0 x1 a Nx Hx0 Ha.
assert (Hp2 : (2 <= prec)%Z) by lia.
assert (U0 : 0 < U) by apply bpow_gt_0.
generalize H_2Q Omega_eq (U_le_H 2 ltac:(lia) ltac:(lia)). rewrite pow2_2. intros T2 EO T3.
generalize (b2r_le_Omega prec emax x0) (b2r_le_Omega prec emax a). intros OX0 OA.
set (X0 := b2r x0) in *. set (X1 := b2r x1) in *. set (A := b2r a) in *.
assert (FX0 : format X0) by apply (b2r_format prec emax).
assert (FX1 : format X1) by apply (b2r_format prec emax).
assert (FA : format A) by apply (b2r_format prec emax).
assert (HX1 : Rabs X1 <= / 4 * U).
{ apply Rle_trans with (1 := normalized_2_tail_rel emin prec X0 X1 Nx). rewrite <- uQ.
  apply Rmult_le_compat_l. apply bpow_ge_0. exact Hx0. }
cbv [IeeeBridge.runR run stepR nth app IeeeModel.add_2_1_prog].
rewrite (guard_real_any emin prec tie_even A FA).
set (sh := rnd (X0 + A)). set (bb := rnd (sh - X0)). set (t0 := rnd (sh - bb)).
set (t1 := rnd (X0 - t0)). set (t2 := rnd (A - bb)). set (sl := rnd (t1 + t2)).
set (v := rnd (X1 + sl)). set (z0 := rnd (sh + v)). set (zz := rnd (z0 - sh)).
set (z1 := rnd (v - zz)).
assert (Hsh : Rabs sh <= H).
{ apply (RN_abs_le_bpow emin prec). apply Rle_trans with (1 := Rabs_triang _ _). lra. }
assert (Ish : inrange sh).
{ apply (le_bpow_inrange emax) with (emax - 1)%Z. lia. exact Hsh. }
assert (TS1 : inrange bb /\ inrange t0 /\ inrange t1 /\ inrange t2 /\ inrange sl /\
              sl = X0 + A - sh).
{ apply (two_sum_call_range prec emax Hp2 X0 A); trivial; rewrite EO; lra. }
destruct TS1 as [Ibb [It0 [It1 [It2 [Isl Esl]]]]].
assert (Hsl : Rabs sl <= / 2 * U).
{ rewrite Esl. replace (X0 + A - sh) with (- (sh - (X0 + A))) by ring. rewrite Rabs_Ropp.
  exact (round_error_top prec emax (X0 + A) Ish). }
assert (Hv : Rabs v <= U).
{ apply (RN_abs_le_bpow emin prec). apply Rle_trans with (1 := Rabs_triang _ _). lra. }
assert (Iv : inrange v).
{ apply (le_bpow_inrange emax) with (emax - prec)%Z. lia. exact Hv. }
assert (Fv : format v) by apply Frnd.
assert (Iz0 : inrange z0).
{ apply (rnd_le_Omega prec emax). rewrite EO.
  apply Rle_trans with (1 := Rabs_triang _ _). lra. }
assert (FS : inrange zz /\ Rabs z1 <= U).
{ apply (fast_two_sum_call_range prec emax sh v); trivial. rewrite EO. lra. }
destruct FS as [Izz Hz1].
assert (Iz1 : inrange z1).
{ apply (le_bpow_inrange emax) with (emax - prec)%Z. lia. exact Hz1. }
repeat constructor; trivial; apply b2r_inrange.
Qed.

(* When the exact sum is at most Q in magnitude. *)
Lemma add_2_1_range_sum :
  (3 <= prec)%Z ->
  forall x0 x1 a : float,
  normalized_2 emin prec (b2r x0) (b2r x1) ->
  Rabs ((b2r x0 + b2r x1) + b2r a) <= Q ->
  Forall inrange (runR IeeeModel.add_2_1_prog [b2r x0; b2r x1; b2r a]).
Proof.
intros Hp3 x0 x1 a Nx Hxa.
assert (Hp2 : (2 <= prec)%Z) by lia.
assert (U0 : 0 < U) by apply bpow_gt_0.
generalize H_2Q Omega_eq (U_le_H 2 ltac:(lia) ltac:(lia)). rewrite pow2_2. intros T2 EO T3.
generalize (tail_le_half_U x0 x1 Nx). intros HX1.
generalize (b2r_le_Omega prec emax x0) (b2r_le_Omega prec emax a). intros OX0 OA.
set (X0 := b2r x0) in *. set (X1 := b2r x1) in *. set (A := b2r a) in *.
assert (FX0 : format X0) by apply (b2r_format prec emax).
assert (FX1 : format X1) by apply (b2r_format prec emax).
assert (FA : format A) by apply (b2r_format prec emax).
assert (HS : Rabs (X0 + A) <= Q + / 2 * U).
{ replace (X0 + A) with ((X0 + X1 + A) + - X1) by ring.
  apply Rle_trans with (1 := Rabs_triang _ _). rewrite Rabs_Ropp. lra. }
cbv [IeeeBridge.runR run stepR nth app IeeeModel.add_2_1_prog].
rewrite (guard_real_any emin prec tie_even A FA).
set (sh := rnd (X0 + A)). set (bb := rnd (sh - X0)). set (t0 := rnd (sh - bb)).
set (t1 := rnd (X0 - t0)). set (t2 := rnd (A - bb)). set (sl := rnd (t1 + t2)).
set (v := rnd (X1 + sl)). set (z0 := rnd (sh + v)). set (zz := rnd (z0 - sh)).
set (z1 := rnd (v - zz)).
assert (Hd : Rabs (sh - (X0 + A)) <= / 4 * U) by (apply round_error_below_H; lra).
assert (Hsh : Rabs sh <= Q + 3 / 4 * U).
{ replace sh with ((sh - (X0 + A)) + (X0 + A)) by ring.
  apply Rle_trans with (1 := Rabs_triang _ _). lra. }
assert (Ish : inrange sh).
{ apply (le_Omega_inrange prec emax). rewrite EO. lra. }
assert (Ibb : inrange bb).
{ apply rnd_below_mid. replace (sh - X0) with (A + (sh - (X0 + A))) by ring.
  apply Rle_lt_trans with (1 := Rabs_triang _ _). lra. }
destruct (two_sum_range prec emax Hp2 X0 A FX0 FA OX0 OA Ish Ibb) as [It0 [It1 [It2 Isl]]].
assert (Esl : sl = X0 + A - sh).
{ generalize (two_sum_exact emin prec Hp2 X0 A FX0 FA). intros [_ E].
  change (sh + sl = X0 + A) in E. lra. }
assert (Hsl : Rabs sl <= / 4 * U).
{ rewrite Esl. replace (X0 + A - sh) with (- (sh - (X0 + A))) by ring. now rewrite Rabs_Ropp. }
assert (Hv : Rabs v <= U).
{ apply (RN_abs_le_bpow emin prec). apply Rle_trans with (1 := Rabs_triang _ _). lra. }
assert (Iv : inrange v).
{ apply (le_bpow_inrange emax) with (emax - prec)%Z. lia. exact Hv. }
assert (Fv : format v) by apply Frnd.
assert (Iz0 : inrange z0).
{ apply (rnd_le_Omega prec emax). rewrite EO.
  apply Rle_trans with (1 := Rabs_triang _ _). lra. }
assert (FS : inrange zz /\ Rabs z1 <= U).
{ apply (fast_two_sum_call_range prec emax sh v); trivial. rewrite EO. lra. }
destruct FS as [Izz Hz1].
assert (Iz1 : inrange z1).
{ apply (le_bpow_inrange emax) with (emax - prec)%Z. lia. exact Hz1. }
repeat constructor; trivial; apply b2r_inrange.
Qed.

(** * add_fast_2_2 *)

(* When both operands are at most Q in magnitude. *)
Lemma add_fast_2_2_range :
  (2 <= prec)%Z ->
  forall x0 x1 y0 y1 : float,
  normalized_2 emin prec (b2r x0) (b2r x1) -> normalized_2 emin prec (b2r y0) (b2r y1) ->
  Rabs (b2r x0) <= Q -> Rabs (b2r y0) <= Q ->
  Forall inrange (runR IeeeModel.add_fast_2_2_prog [b2r x0; b2r x1; b2r y0; b2r y1]).
Proof.
intros Hp2 x0 x1 y0 y1 Nx Ny Hx0 Hy0.
assert (U0 : 0 < U) by apply bpow_gt_0.
generalize H_2Q Omega_eq (U_le_H 1 ltac:(lia) ltac:(lia)). rewrite pow2_1. intros T2 EO T3.
generalize (b2r_le_Omega prec emax x0) (b2r_le_Omega prec emax y0). intros OX0 OY0.
set (X0 := b2r x0) in *. set (X1 := b2r x1) in *. set (Y0 := b2r y0) in *. set (Y1 := b2r y1) in *.
assert (FX0 : format X0) by apply (b2r_format prec emax).
assert (FX1 : format X1) by apply (b2r_format prec emax).
assert (FY0 : format Y0) by apply (b2r_format prec emax).
assert (FY1 : format Y1) by apply (b2r_format prec emax).
assert (HX1 : Rabs X1 <= / 4 * U).
{ apply Rle_trans with (1 := normalized_2_tail_rel emin prec X0 X1 Nx). rewrite <- uQ.
  apply Rmult_le_compat_l. apply bpow_ge_0. exact Hx0. }
assert (HY1 : Rabs Y1 <= / 4 * U).
{ apply Rle_trans with (1 := normalized_2_tail_rel emin prec Y0 Y1 Ny). rewrite <- uQ.
  apply Rmult_le_compat_l. apply bpow_ge_0. exact Hy0. }
cbv [IeeeBridge.runR run stepR nth app IeeeModel.add_fast_2_2_prog].
set (sh := rnd (X0 + Y0)). set (bb := rnd (sh - X0)). set (t0 := rnd (sh - bb)).
set (t1 := rnd (X0 - t0)). set (t2 := rnd (Y0 - bb)). set (sl := rnd (t1 + t2)).
set (v := rnd (X1 + Y1)). set (w := rnd (sl + v)). set (z0 := rnd (sh + w)).
set (zz := rnd (z0 - sh)). set (z1 := rnd (w - zz)).
assert (Hsh : Rabs sh <= H).
{ apply (RN_abs_le_bpow emin prec). apply Rle_trans with (1 := Rabs_triang _ _). lra. }
assert (Ish : inrange sh).
{ apply (le_bpow_inrange emax) with (emax - 1)%Z. lia. exact Hsh. }
assert (TS1 : inrange bb /\ inrange t0 /\ inrange t1 /\ inrange t2 /\ inrange sl /\
              sl = X0 + Y0 - sh).
{ apply (two_sum_call_range prec emax Hp2 X0 Y0); trivial; rewrite EO; lra. }
destruct TS1 as [Ibb [It0 [It1 [It2 [Isl Esl]]]]].
assert (Hsl : Rabs sl <= / 2 * U).
{ rewrite Esl. replace (X0 + Y0 - sh) with (- (sh - (X0 + Y0))) by ring. rewrite Rabs_Ropp.
  exact (round_error_top prec emax (X0 + Y0) Ish). }
assert (Hv : Rabs v <= / 2 * U).
{ rewrite half_U. apply (RN_abs_le_bpow emin prec). rewrite <- half_U.
  apply Rle_trans with (1 := Rabs_triang _ _). lra. }
assert (Iv : inrange v).
{ apply (le_bpow_inrange emax) with (emax - prec)%Z. lia. lra. }
assert (Hw : Rabs w <= U).
{ apply (RN_abs_le_bpow emin prec). apply Rle_trans with (1 := Rabs_triang _ _). lra. }
assert (Iw : inrange w).
{ apply (le_bpow_inrange emax) with (emax - prec)%Z. lia. exact Hw. }
assert (Fw : format w) by apply Frnd.
assert (Iz0 : inrange z0).
{ apply (rnd_le_Omega prec emax). rewrite EO.
  apply Rle_trans with (1 := Rabs_triang _ _). lra. }
assert (FS : inrange zz /\ Rabs z1 <= U).
{ apply (fast_two_sum_call_range prec emax sh w); trivial. rewrite EO. lra. }
destruct FS as [Izz Hz1].
assert (Iz1 : inrange z1).
{ apply (le_bpow_inrange emax) with (emax - prec)%Z. lia. exact Hz1. }
repeat constructor; trivial; apply b2r_inrange.
Qed.

(* When the exact sum is at most Q in magnitude. Here sh + w is the exact sum plus the
   rounding errors of v and w, which leaves room at prec = 2 too. *)
Lemma add_fast_2_2_range_sum :
  (2 <= prec)%Z ->
  forall x0 x1 y0 y1 : float,
  normalized_2 emin prec (b2r x0) (b2r x1) -> normalized_2 emin prec (b2r y0) (b2r y1) ->
  Rabs ((b2r x0 + b2r x1) + (b2r y0 + b2r y1)) <= Q ->
  Forall inrange (runR IeeeModel.add_fast_2_2_prog [b2r x0; b2r x1; b2r y0; b2r y1]).
Proof.
intros Hp2 x0 x1 y0 y1 Nx Ny Hxy.
assert (U0 : 0 < U) by apply bpow_gt_0.
generalize H_2Q Omega_eq (U_le_H 1 ltac:(lia) ltac:(lia)). rewrite pow2_1. intros T2 EO T3.
generalize (tail_le_half_U x0 x1 Nx) (tail_le_half_U y0 y1 Ny). intros HX1 HY1.
generalize (b2r_le_Omega prec emax x0) (b2r_le_Omega prec emax y0). intros OX0 OY0.
set (X0 := b2r x0) in *. set (X1 := b2r x1) in *. set (Y0 := b2r y0) in *. set (Y1 := b2r y1) in *.
assert (FX0 : format X0) by apply (b2r_format prec emax).
assert (FX1 : format X1) by apply (b2r_format prec emax).
assert (FY0 : format Y0) by apply (b2r_format prec emax).
assert (FY1 : format Y1) by apply (b2r_format prec emax).
assert (HS : Rabs (X0 + Y0) <= Q + U).
{ replace (X0 + Y0) with ((X0 + X1 + (Y0 + Y1)) + - (X1 + Y1)) by ring.
  apply Rle_trans with (1 := Rabs_triang _ _). rewrite Rabs_Ropp.
  generalize (Rabs_triang X1 Y1). lra. }
cbv [IeeeBridge.runR run stepR nth app IeeeModel.add_fast_2_2_prog].
set (sh := rnd (X0 + Y0)). set (bb := rnd (sh - X0)). set (t0 := rnd (sh - bb)).
set (t1 := rnd (X0 - t0)). set (t2 := rnd (Y0 - bb)). set (sl := rnd (t1 + t2)).
set (v := rnd (X1 + Y1)). set (w := rnd (sl + v)). set (z0 := rnd (sh + w)).
set (zz := rnd (z0 - sh)). set (z1 := rnd (w - zz)).
assert (Hd : Rabs (sh - (X0 + Y0)) <= / 4 * U) by (apply round_error_below_H; lra).
assert (Hsh : Rabs sh <= Q + 5 / 4 * U).
{ replace sh with ((sh - (X0 + Y0)) + (X0 + Y0)) by ring.
  apply Rle_trans with (1 := Rabs_triang _ _). lra. }
assert (Ish : inrange sh).
{ apply (le_Omega_inrange prec emax). rewrite EO. lra. }
assert (Ibb : inrange bb).
{ apply rnd_below_mid. replace (sh - X0) with (Y0 + (sh - (X0 + Y0))) by ring.
  apply Rle_lt_trans with (1 := Rabs_triang _ _). lra. }
destruct (two_sum_range prec emax Hp2 X0 Y0 FX0 FY0 OX0 OY0 Ish Ibb) as [It0 [It1 [It2 Isl]]].
assert (Esl : sl = X0 + Y0 - sh).
{ generalize (two_sum_exact emin prec Hp2 X0 Y0 FX0 FY0). intros [_ E].
  change (sh + sl = X0 + Y0) in E. lra. }
assert (Hsl : Rabs sl <= / 4 * U).
{ rewrite Esl. replace (X0 + Y0 - sh) with (- (sh - (X0 + Y0))) by ring. now rewrite Rabs_Ropp. }
assert (HXY1 : Rabs (X1 + Y1) <= U).
{ apply Rle_trans with (1 := Rabs_triang _ _). lra. }
assert (Hv : Rabs v <= U) by (apply (RN_abs_le_bpow emin prec); exact HXY1).
assert (Iv : inrange v).
{ apply (le_bpow_inrange emax) with (emax - prec)%Z. lia. exact Hv. }
assert (Ev : Rabs (v - (X1 + Y1)) <= / 2 * U) by exact (round_error_top prec emax (X1 + Y1) Iv).
assert (Hw : Rabs w <= 2 * U).
{ rewrite two_U. apply (RN_abs_le_bpow emin prec). rewrite <- two_U.
  apply Rle_trans with (1 := Rabs_triang _ _). lra. }
assert (Iw : inrange w).
{ apply (le_bpow_inrange emax) with (emax - prec + 1)%Z. lia. now rewrite <- two_U. }
assert (Ew : Rabs (w - (sl + v)) <= / 2 * U) by exact (round_error_top prec emax (sl + v) Iw).
assert (Fw : format w) by apply Frnd.
assert (Iz0 : inrange z0).
{ apply (rnd_le_Omega prec emax). rewrite EO.
  replace (sh + w) with ((X0 + X1 + (Y0 + Y1)) + (w - (sl + v)) + (v - (X1 + Y1)))
    by (rewrite Esl; ring).
  apply Rle_trans with (1 := Rabs_triang _ _).
  generalize (Rabs_triang (X0 + X1 + (Y0 + Y1)) (w - (sl + v))). lra. }
assert (FS : inrange zz /\ Rabs z1 <= U).
{ apply (fast_two_sum_call_range prec emax sh w); trivial. rewrite EO. lra. }
destruct FS as [Izz Hz1].
assert (Iz1 : inrange z1).
{ apply (le_bpow_inrange emax) with (emax - prec)%Z. lia. exact Hz1. }
repeat constructor; trivial; apply b2r_inrange.
Qed.

(** * mul_2_1 and mul_pow2_2 *)

Lemma small_product_1 :
  forall x0 x1 a : R,
  normalized_2 emin prec x0 x1 ->
  Rabs (x0 * a) <= bpow radix2 (emin - 1) -> Rabs (x1 * a) <= bpow radix2 (emin - 1).
Proof.
intros x0 x1 a Nx Hp.
generalize (normalized_2_tail_rel emin prec x0 x1 Nx). intros HX.
assert (u0 : 0 < u prec) by apply bpow_gt_0.
assert (u1 : u prec <= 1).
{ unfold u. change 1 with (bpow radix2 0). apply bpow_le. lia. }
generalize (Rabs_pos x0) (Rabs_pos a) (Rabs_pos x1). intros A0 B0 A1.
rewrite Rabs_mult in Hp |- *.
apply Rle_trans with (2 := Hp). apply Rmult_le_compat_r. exact B0. nra.
Qed.

(* The leading product of a pair whose exact product with a is at most H. *)
Lemma lead_product_le :
  (2 <= prec)%Z ->
  forall x0 x1 a : R, normalized_2 emin prec x0 x1 ->
  Rabs ((x0 + x1) * a) <= H ->
  Rabs (x0 * a) <= H + U /\ Rabs (x1 * a) <= 3 / 4 * U.
Proof.
intros Hp2 x0 x1 a Nx Hxa.
assert (U0 : 0 < U) by apply bpow_gt_0.
assert (H0 : 0 < H) by apply bpow_gt_0.
assert (u0 : 0 < u prec) by apply bpow_gt_0.
assert (u4 : u prec <= / 4).
{ unfold u. change (/ 4) with (bpow radix2 (-2)). apply bpow_le. lia. }
assert (T : U = 2 * u prec * H).
{ unfold u. replace (emax - prec)%Z with (1 + (- prec + (emax - 1)))%Z by ring.
  rewrite 2!bpow_plus, pow2_1. ring. }
generalize (normalized_2_head_le prec emax x0 x1 Nx) (normalized_2_tail_rel emin prec x0 x1 Nx).
intros HX HX1.
generalize (Rabs_pos x0) (Rabs_pos a) (Rabs_pos x1). intros A0 B0 A1.
rewrite Rabs_mult in Hxa. rewrite 2!Rabs_mult.
set (P := Rabs x0 * Rabs a).
assert (P0 : 0 <= P) by (unfold P; now apply Rmult_le_pos).
assert (HP1 : (1 - u prec) * P <= H).
{ apply Rle_trans with (2 := Hxa). unfold P.
  rewrite <- Rmult_assoc. apply Rmult_le_compat_r; assumption. }
assert (K : 1 <= (1 - u prec) * (1 + 2 * u prec)) by nra.
assert (HP : P <= H + U).
{ apply Rle_trans with (P * ((1 - u prec) * (1 + 2 * u prec))). nra.
  replace (P * ((1 - u prec) * (1 + 2 * u prec))) with ((1 - u prec) * P * (1 + 2 * u prec)) by ring.
  replace (H + U) with (H * (1 + 2 * u prec)) by (rewrite T; ring).
  apply Rmult_le_compat_r; lra. }
split. exact HP.
apply Rle_trans with (u prec * P).
- unfold P. rewrite <- Rmult_assoc. apply Rmult_le_compat_r; assumption.
- rewrite T in HP |- *. nra.
Qed.

Lemma mul_2_1_range_zero :
  forall x0 x1 a : float,
  normalized_2 emin prec (b2r x0) (b2r x1) ->
  rnd (b2r x0 * b2r a + 0) = 0 ->
  Forall inrange (runR IeeeModel.mul_2_1_prog [b2r x0; b2r x1; b2r a]).
Proof.
intros x0 x1 a Nx Hch.
assert (I0 : inrange 0).
{ unfold IeeeBridge.inrange. rewrite Rabs_R0. apply bpow_gt_0. }
assert (Hp : Rabs (b2r x0 * b2r a) <= bpow radix2 (emin - 1)).
{ apply rnd_zero_inv. now rewrite Rplus_0_r in Hch. }
generalize (small_product_1 _ _ _ Nx Hp). intros H1.
set (X0 := b2r x0) in *. set (X1 := b2r x1) in *. set (A := b2r a) in *.
assert (R0 : rnd 0 = 0) by (apply round_0; auto with typeclass_instances).
cbv [IeeeBridge.runR run stepR nth app IeeeModel.mul_2_1_prog].
set (ch := rnd (X0 * A + 0)) in *. set (cl1 := rnd (X0 * A + - ch)).
set (cl3 := rnd (X1 * A + cl1)).
set (z0 := rnd (ch + cl3)). set (zz := rnd (z0 - ch)). set (z1 := rnd (cl3 - zz)).
assert (Ecl1 : cl1 = 0).
{ unfold cl1. rewrite Hch, Ropp_0. exact Hch. }
assert (Ecl3 : cl3 = 0).
{ unfold cl3. rewrite Ecl1, Rplus_0_r. now apply (RN_small_zero emin prec). }
assert (Ez0 : z0 = 0).
{ unfold z0. rewrite Hch, Ecl3, Rplus_0_r. exact R0. }
assert (Ezz : zz = 0).
{ unfold zz. rewrite Ez0, Hch, Rminus_0_r. exact R0. }
assert (Ez1 : z1 = 0).
{ unfold z1. rewrite Ecl3, Ezz, Rminus_0_r. exact R0. }
rewrite Ez1, Ezz, Ez0, Ecl3, Ecl1, Hch.
repeat constructor; trivial; apply b2r_inrange.
Qed.

(* When the exact product is at most H in magnitude: ch + cl3 is the exact product plus
   the defect of the two_prod (at most eta/2) and the rounding error of cl3. *)
Lemma mul_2_1_range :
  (2 <= prec)%Z ->
  forall x0 x1 a : float,
  normalized_2 emin prec (b2r x0) (b2r x1) ->
  Rabs ((b2r x0 + b2r x1) * b2r a) <= H ->
  Forall inrange (runR IeeeModel.mul_2_1_prog [b2r x0; b2r x1; b2r a]).
Proof.
intros Hp2 x0 x1 a Nx Hxa.
assert (U0 : 0 < U) by apply bpow_gt_0.
generalize Omega_eq (U_le_H 1 ltac:(lia) ltac:(lia)). rewrite pow2_1. intros EO T3.
destruct (lead_product_le Hp2 _ _ _ Nx Hxa) as [HP HP1].
set (X0 := b2r x0) in *. set (X1 := b2r x1) in *. set (A := b2r a) in *.
assert (FX0 : format X0) by apply (b2r_format prec emax).
assert (FA : format A) by apply (b2r_format prec emax).
cbv [IeeeBridge.runR run stepR nth app IeeeModel.mul_2_1_prog].
set (ch := rnd (X0 * A + 0)). set (cl1 := rnd (X0 * A + - ch)).
set (cl3 := rnd (X1 * A + cl1)).
set (z0 := rnd (ch + cl3)). set (zz := rnd (z0 - ch)). set (z1 := rnd (cl3 - zz)).
assert (Ich : inrange ch).
{ apply (rnd_le_Omega prec emax). rewrite Rplus_0_r, EO. lra. }
assert (Hcl1 : Rabs cl1 <= U) by exact (two_prod_error_le prec emax X0 A Ich).
assert (Icl1 : inrange cl1).
{ apply (le_bpow_inrange emax) with (emax - prec)%Z. lia. exact Hcl1. }
assert (Hs3 : Rabs (X1 * A + cl1) <= 2 * U).
{ apply Rle_trans with (1 := Rabs_triang _ _). lra. }
assert (Hcl3 : Rabs cl3 <= 2 * U).
{ rewrite two_U. apply (RN_abs_le_bpow emin prec). now rewrite <- two_U. }
assert (Icl3 : inrange cl3).
{ apply (le_bpow_inrange emax) with (emax - prec + 1)%Z. lia. now rewrite <- two_U. }
assert (Ecl3 : Rabs (cl3 - (X1 * A + cl1)) <= / 4 * U).
{ rewrite two_U in Hs3.
  apply Rle_trans with (1 := round_error_bpow emin prec tie_even _ _ Hs3).
  replace (/ 4 * U) with (/ 2 * (/ 2 * U)) by field. rewrite half_U.
  apply Rmult_le_compat_l. lra. apply bpow_le. lia. }
assert (Eprod : Rabs (ch + cl1 - X0 * A) <= / 4 * U).
{ generalize (two_prod_correct emin prec Hp2 X0 A FX0 FA).
  unfold two_prod. cbv zeta. fold ch. fold cl1. intros [_ [_ [_ [E _]]]].
  apply Rle_trans with (1 := E).
  replace (/ 4 * U) with (1 / 2 * (/ 2 * U)) by field. rewrite half_U.
  apply Rmult_le_compat_l. lra. unfold eta. apply bpow_le. lia. }
assert (Fcl3 : format cl3) by apply Frnd.
assert (Iz0 : inrange z0).
{ apply (rnd_le_Omega prec emax). rewrite EO.
  replace (ch + cl3) with ((X0 + X1) * A + (ch + cl1 - X0 * A) + (cl3 - (X1 * A + cl1))) by ring.
  apply Rle_trans with (1 := Rabs_triang _ _).
  generalize (Rabs_triang ((X0 + X1) * A) (ch + cl1 - X0 * A)). lra. }
assert (FS : inrange zz /\ Rabs z1 <= U).
{ apply (fast_two_sum_call_range prec emax ch cl3); trivial. rewrite EO. lra. }
destruct FS as [Izz Hz1].
assert (Iz1 : inrange z1).
{ apply (le_bpow_inrange emax) with (emax - prec)%Z. lia. exact Hz1. }
repeat constructor; trivial; apply b2r_inrange.
Qed.

Lemma mul_pow2_2_range_zero :
  forall x0 x1 c : float,
  normalized_2 emin prec (b2r x0) (b2r x1) ->
  rnd (b2r x0 * b2r c + 0) = 0 ->
  Forall inrange (runR IeeeModel.mul_pow2_2_prog [b2r x0; b2r x1; b2r c]).
Proof.
intros x0 x1 c Nx Hh.
assert (I0 : inrange 0).
{ unfold IeeeBridge.inrange. rewrite Rabs_R0. apply bpow_gt_0. }
assert (Hp : Rabs (b2r x0 * b2r c) <= bpow radix2 (emin - 1)).
{ apply rnd_zero_inv. now rewrite Rplus_0_r in Hh. }
generalize (small_product_1 _ _ _ Nx Hp). intros H1.
set (X0 := b2r x0) in *. set (X1 := b2r x1) in *. set (C := b2r c) in *.
assert (R0 : rnd 0 = 0) by (apply round_0; auto with typeclass_instances).
cbv [IeeeBridge.runR run stepR nth app IeeeModel.mul_pow2_2_prog].
set (h := rnd (X0 * C + 0)) in *. set (l := rnd (X1 * C + 0)).
set (z0 := rnd (h + l)). set (zz := rnd (z0 - h)). set (z1 := rnd (l - zz)).
assert (El : l = 0).
{ unfold l. rewrite Rplus_0_r. now apply (RN_small_zero emin prec). }
assert (Ez0 : z0 = 0).
{ unfold z0. rewrite Hh, El, Rplus_0_r. exact R0. }
assert (Ezz : zz = 0).
{ unfold zz. rewrite Ez0, Hh, Rminus_0_r. exact R0. }
assert (Ez1 : z1 = 0).
{ unfold z1. rewrite El, Ezz, Rminus_0_r. exact R0. }
rewrite Ez1, Ezz, Ez0, El, Hh.
repeat constructor; trivial; apply b2r_inrange.
Qed.

(* When the exact product is at most H in magnitude. Nothing is assumed of c. *)
Lemma mul_pow2_2_range :
  (2 <= prec)%Z ->
  forall x0 x1 c : float,
  normalized_2 emin prec (b2r x0) (b2r x1) ->
  Rabs ((b2r x0 + b2r x1) * b2r c) <= H ->
  Forall inrange (runR IeeeModel.mul_pow2_2_prog [b2r x0; b2r x1; b2r c]).
Proof.
intros Hp2 x0 x1 c Nx Hxc.
assert (U0 : 0 < U) by apply bpow_gt_0.
generalize Omega_eq (U_le_H 1 ltac:(lia) ltac:(lia)). rewrite pow2_1. intros EO T3.
destruct (lead_product_le Hp2 _ _ _ Nx Hxc) as [HP HP1].
set (X0 := b2r x0) in *. set (X1 := b2r x1) in *. set (C := b2r c) in *.
cbv [IeeeBridge.runR run stepR nth app IeeeModel.mul_pow2_2_prog].
set (h := rnd (X0 * C + 0)). set (l := rnd (X1 * C + 0)).
set (z0 := rnd (h + l)). set (zz := rnd (z0 - h)). set (z1 := rnd (l - zz)).
assert (Ih : inrange h).
{ apply (rnd_le_Omega prec emax). rewrite Rplus_0_r, EO. lra. }
assert (Eh : Rabs (h - X0 * C) <= / 2 * U).
{ generalize (round_error_top prec emax (X0 * C + 0) Ih). fold h. now rewrite Rplus_0_r. }
assert (Hl : Rabs l <= U).
{ apply (RN_abs_le_bpow emin prec). rewrite Rplus_0_r. lra. }
assert (Il : inrange l).
{ apply (le_bpow_inrange emax) with (emax - prec)%Z. lia. exact Hl. }
assert (El : Rabs (l - X1 * C) <= / 2 * U).
{ generalize (round_error_top prec emax (X1 * C + 0) Il). fold l. now rewrite Rplus_0_r. }
assert (Fl : format l) by apply Frnd.
assert (Iz0 : inrange z0).
{ apply (rnd_le_Omega prec emax). rewrite EO.
  replace (h + l) with ((X0 + X1) * C + (h - X0 * C) + (l - X1 * C)) by ring.
  apply Rle_trans with (1 := Rabs_triang _ _).
  generalize (Rabs_triang ((X0 + X1) * C) (h - X0 * C)). lra. }
assert (FS : inrange zz /\ Rabs z1 <= U).
{ apply (fast_two_sum_call_range prec emax h l); trivial. rewrite EO. lra. }
destruct FS as [Izz Hz1].
assert (Iz1 : inrange z1).
{ apply (le_bpow_inrange emax) with (emax - prec)%Z. lia. exact Hz1. }
repeat constructor; trivial; apply b2r_inrange.
Qed.

End IeeeRange.
