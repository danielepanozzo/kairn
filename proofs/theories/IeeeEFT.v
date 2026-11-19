(* The three error-free transformations in the IEEE model: two_sum, fast_two_sum,
   two_prod (proofs/gen/IeeeModel.v), with finite operands a and b.

   fast_two_sum, under its requirement |a| >= |b|: if s is finite then z and e are
   finite and equal to the values of the real model. So s = RN(a + b), s + e = a + b
   and (s, e) is normalized. Nothing can overflow after s.

   two_prod: if p is finite then e is finite and equal to the value of the real model.

   two_sum, in Kairn's order of operations (s = a + b, bb = s - a, t0 = s - bb,
   t1 = a - t0, t2 = b - bb, e = t1 + t2): here a finite s does not imply a finite e.
   The exact condition is

       e is finite  <=>  s is finite and bb = RN(s - a) does not overflow,

   and in that case all six values are those of the real model (two_sum_values). The
   second condition holds whenever b is not the largest number or its opposite
   (two_sum_values_not_top). Exhaustive enumeration of toy formats shows that it fails
   exactly for b = -+Omega and a = +-(2j - 1/2) 2^(emax - prec), 1 <= j < 2^(prec - 2):
   then a + b is halfway between two numbers of the top binade, s is the one farther
   from zero, and s - a is halfway between Omega and 2^emax, which rounds to 2^emax.
   In binary64: a = -1.5 * 2^971, b = Omega gives a finite s and e = NaN. (BGM17 study
   the same question for the usual order of operations.) That enumeration is not a
   proof; what is proved is the equivalence above and the sufficient condition.

   The statements, in the form of proofs/gen/IeeeStatements.v, are at the end of the file:
   fast_two_sum_ieee_correct, two_prod_ieee_correct, two_sum_ieee_correct.

   The proof for two_sum bounds the four values computed after bb (two_sum_range):
   with d = |s - (a + b)| <= 2^(emax - prec)/2, one has |bb - b| <= 2d, t0 = RN(a + th)
   with |th| <= d, and |a - t0|, |b - bb| <= 2d. Only t0 is large, and it can reach
   2^emax only if |a| = Omega; but then |b| <= |a|, s - a is exact (Sterbenz's lemma,
   twice), and t0 = a. *)
From Stdlib Require Import Reals ZArith List Arith Bool Lia Lra.
From Flocq Require Import Core Sterbenz Binary.
From Kairn.Gen Require Import Model Statements IeeeStatements.
From Kairn Require Import Format Normalized EFT Program IeeeBridge IeeeVocabulary.
From Kairn Require IeeeOperations.
From Kairn.Gen Require IeeeModel.
Import ListNotations.
Open Scope R_scope.

(** * The programs of proofs/gen/IeeeModel.v are the kernels of the real model *)

Lemma fast_two_sum_runR :
  forall emin prec choice a b,
  fast_two_sum emin prec choice a b =
  (nth 2 (runR emin prec choice IeeeModel.fast_two_sum_prog [a; b]) 0,
   nth 4 (runR emin prec choice IeeeModel.fast_two_sum_prog [a; b]) 0).
Proof.
intros. cbv [fast_two_sum runR run stepR nth app IeeeModel.fast_two_sum_prog]. reflexivity.
Qed.

Lemma two_prod_runR :
  forall emin prec choice a b,
  two_prod emin prec choice a b =
  (nth 2 (runR emin prec choice IeeeModel.two_prod_prog [a; b]) 0,
   nth 3 (runR emin prec choice IeeeModel.two_prod_prog [a; b]) 0).
Proof.
intros. cbv [two_prod runR run stepR nth app IeeeModel.two_prod_prog]. reflexivity.
Qed.

Lemma two_sum_runR :
  forall emin prec choice a b,
  two_sum emin prec choice a b =
  (nth 2 (runR emin prec choice IeeeModel.two_sum_prog [a; b]) 0,
   nth 7 (runR emin prec choice IeeeModel.two_sum_prog [a; b]) 0).
Proof.
intros. cbv [two_sum runR run stepR nth app IeeeModel.two_sum_prog]. reflexivity.
Qed.

(** * Magnitudes in the real model, near the top of the range *)

Section Top.
Variable prec emax : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Context {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}.

Notation emin := (3 - emax - prec)%Z.
Notation fexp := (FLT_exp emin prec).
Notation format := (generic_format radix2 fexp).
Notation rnd := (round radix2 fexp (Znearest tie_even)).
Notation inrange := (inrange emax).
Notation Omega := (Omega prec emax).
Notation U := (bpow radix2 (emax - prec)).

Let Hprec : (0 < prec)%Z.
Proof. exact prec_gt_0_. Qed.
Let Hemax : (prec < emax)%Z.
Proof. exact prec_lt_emax_. Qed.

Let rnd_opp : forall x, rnd (- x) = - rnd x.
Proof. intros x. exact (RN_opp emin prec x). Qed.

Let Frnd : forall x, format (rnd x).
Proof. intros x. apply generic_format_round; auto with typeclass_instances. Qed.

(* The error of a rounding whose result is in range is at most half a unit in the last
   place of the largest numbers. *)
Lemma round_error_top : forall x, inrange (rnd x) -> Rabs (rnd x - x) <= / 2 * U.
Proof.
intros x Hx. apply Rle_trans with (/ 2 * ulp radix2 fexp (rnd x)).
- apply error_le_half_ulp_round; auto with typeclass_instances.
- apply Rmult_le_compat_l. lra. now apply (ulp_le_top prec emax).
Qed.

(* The result of a rounding is at least as close as any number of the format. *)
Lemma round_nearest : forall x g, format g -> Rabs (rnd x - x) <= Rabs (g - x).
Proof.
intros x g Fg. destruct (round_N_pt radix2 fexp tie_even x) as [_ H]. now apply H.
Qed.

Lemma format_half_Omega : format (Omega / 2).
Proof.
replace (Omega / 2) with (pred radix2 fexp (bpow radix2 (emax - 1))).
- apply generic_format_pred; auto with typeclass_instances.
  apply generic_format_bpow. unfold FLT_exp. lia.
- rewrite pred_bpow. unfold IeeeBridge.Omega.
  replace (fexp (emax - 1)) with (emax - prec - 1)%Z by (unfold FLT_exp; lia).
  rewrite (top_half emax).
  replace (emax - prec)%Z with (1 + (emax - prec - 1))%Z at 2 by ring.
  rewrite bpow_plus, pow2_1. field.
Qed.

(* If a = Omega and the sum is in range, s - a is a number of the format. *)
Lemma sum_top_exact_pos :
  forall b, format b -> Rabs b <= Omega ->
  inrange (rnd (Omega + b)) -> format (rnd (Omega + b) - Omega).
Proof.
intros b Fb Hb Hs.
assert (U0 : 0 < U) by apply bpow_gt_0.
generalize (format_Omega prec emax). intros FO.
assert (Opos : 0 < Omega).
{ unfold IeeeBridge.Omega. apply Rlt_0_minus. apply bpow_lt. lia. }
apply Rabs_le_inv in Hb.
destruct (Rle_or_lt 0 b) as [Hb0|Hb0].
- (* b >= 0: the sum is Omega *)
  assert (H1 : Omega <= rnd (Omega + b)).
  { apply round_ge_generic; auto with typeclass_instances. lra. }
  assert (H2 : Rabs (rnd (Omega + b)) <= Omega).
  { apply (inrange_le_Omega prec emax); trivial. }
  apply Rabs_le_inv in H2.
  replace (rnd (Omega + b) - Omega) with 0 by lra. apply generic_format_0.
- destruct (Rle_or_lt (Omega / 2) (- b)) as [Hh|Hh].
  + (* |b| >= Omega/2: the sum is exact *)
    assert (F : format (Omega + b)).
    { replace (Omega + b) with (Omega - (- b)) by ring.
      apply sterbenz; auto with typeclass_instances. now apply generic_format_opp. lra. }
    rewrite round_generic; auto with typeclass_instances.
    replace (Omega + b - Omega) with b by ring. exact Fb.
  + (* |b| < Omega/2: the sum is at least Omega/2 *)
    apply sterbenz; auto with typeclass_instances. split.
    * apply round_ge_generic; auto with typeclass_instances. apply format_half_Omega. lra.
    * apply Rle_trans with Omega; [|lra].
      apply round_le_generic; auto with typeclass_instances. lra.
Qed.

Lemma sum_top_exact :
  forall a b, format b -> Rabs b <= Omega -> Rabs a = Omega ->
  inrange (rnd (a + b)) -> rnd (rnd (a + b) - a) = rnd (a + b) - a.
Proof.
intros a b Fb Hb Ha Hs. apply round_generic; auto with typeclass_instances.
destruct (Rcase_abs a) as [Hneg|Hpos].
- rewrite Rabs_left in Ha by exact Hneg.
  assert (E : a = - Omega) by lra. rewrite E in Hs |- *.
  assert (E2 : rnd (Omega + - b) = - rnd (- Omega + b)).
  { rewrite <- rnd_opp. f_equal. ring. }
  replace (rnd (- Omega + b) - - Omega) with (- (rnd (Omega + - b) - Omega)) by (rewrite E2; ring).
  apply generic_format_opp. apply sum_top_exact_pos.
  + now apply generic_format_opp.
  + now rewrite Rabs_Ropp.
  + unfold IeeeBridge.inrange in *. now rewrite E2, Rabs_Ropp.
- rewrite Rabs_right in Ha by exact Hpos. rewrite Ha in Hs |- *. now apply sum_top_exact_pos.
Qed.

(* two_sum: if s and bb are in range, so are the four values computed after them. *)
Lemma two_sum_range :
  (2 <= prec)%Z ->
  forall a b, format a -> format b -> Rabs a <= Omega -> Rabs b <= Omega ->
  let s := rnd (a + b) in
  let bb := rnd (s - a) in
  let t0 := rnd (s - bb) in
  let t1 := rnd (a - t0) in
  let t2 := rnd (b - bb) in
  let e := rnd (t1 + t2) in
  inrange s -> inrange bb -> inrange t0 /\ inrange t1 /\ inrange t2 /\ inrange e.
Proof.
intros Hp2 a b Fa Fb Ha Hb s bb t0 t1 t2 e Hs Hbb.
assert (U0 : 0 < U) by apply bpow_gt_0.
(* d = |s - (a + b)| is at most U/2 *)
assert (Hd : Rabs (s - (a + b)) <= / 2 * U) by now apply round_error_top.
(* bb is nearest to s - a, and b is a number of the format at distance d from it *)
assert (Hth : Rabs (bb - (s - a)) <= Rabs (s - (a + b))).
{ replace (s - (a + b)) with (- (b - (s - a))) by ring. rewrite Rabs_Ropp.
  now apply round_nearest. }
assert (H2 : Rabs (b - bb) <= U).
{ replace (b - bb) with (- (bb - (s - a)) + - (s - (a + b))) by ring.
  apply Rle_trans with (1 := Rabs_triang _ _). rewrite 2!Rabs_Ropp. lra. }
(* s - bb = a + th with |th| <= d *)
set (th := s - a - bb).
assert (Hth' : Rabs th <= / 2 * U).
{ unfold th. rewrite <- Rabs_Ropp. replace (- (s - a - bb)) with (bb - (s - a)) by ring. lra. }
assert (E0 : s - bb = a + th) by (unfold th; ring).
assert (H0 : inrange t0).
{ destruct (Req_dec (Rabs a) Omega) as [Ht|Ht].
  - (* a is the largest number or its opposite: s - a is exact, and t0 = a *)
    assert (Ebb : bb = s - a) by now apply sum_top_exact.
    unfold t0. rewrite Ebb. replace (s - (s - a)) with a by ring.
    rewrite round_generic; auto with typeclass_instances. now apply le_Omega_inrange with prec.
  - generalize (below_Omega prec emax Hp2 a Fa Ha Ht). intros Ha'.
    unfold t0. rewrite E0. apply (rnd_le_Omega prec emax). apply Rle_trans with (1 := Rabs_triang _ _). lra. }
assert (H1 : Rabs (a - t0) <= U).
{ assert (K : Rabs (t0 - (a + th)) <= Rabs (a - (a + th))).
  { unfold t0. rewrite E0. now apply round_nearest. }
  replace (a - (a + th)) with (- th) in K by ring. rewrite Rabs_Ropp in K.
  replace (a - t0) with (- (t0 - (a + th)) + - th) by ring.
  apply Rle_trans with (1 := Rabs_triang _ _). rewrite 2!Rabs_Ropp. lra. }
assert (B1 : Rabs t1 <= U) by exact (RN_abs_le_bpow emin prec _ _ H1).
assert (B2 : Rabs t2 <= U) by exact (RN_abs_le_bpow emin prec _ _ H2).
assert (UU : 2 * U = bpow radix2 (emax - prec + 1)).
{ rewrite bpow_plus, pow2_1. ring. }
assert (Be : Rabs e <= bpow radix2 (emax - prec + 1)).
{ apply (RN_abs_le_bpow emin prec). rewrite <- UU.
  apply Rle_trans with (1 := Rabs_triang _ _). lra. }
assert (S1 : bpow radix2 (emax - prec + 1) < bpow radix2 emax) by (apply bpow_lt; lia).
assert (S2 : U < bpow radix2 emax) by (apply bpow_lt; lia).
unfold IeeeBridge.inrange in *. repeat split; trivial; lra.
Qed.

(* If b is not the largest number or its opposite, bb = RN(s - a) is in range. *)
Lemma two_sum_bb_range :
  (2 <= prec)%Z ->
  forall a b, format b -> Rabs b <= Omega -> Rabs b <> Omega ->
  inrange (rnd (a + b)) -> inrange (rnd (rnd (a + b) - a)).
Proof.
intros Hp2 a b Fb Hb Hne Hs.
assert (U0 : 0 < U) by apply bpow_gt_0.
generalize (round_error_top (a + b) Hs) (below_Omega prec emax Hp2 b Fb Hb Hne). intros Hd Hb'.
apply (rnd_le_Omega prec emax).
replace (rnd (a + b) - a) with (b + (rnd (a + b) - (a + b))) by ring.
apply Rle_trans with (1 := Rabs_triang _ _). lra.
Qed.

(* A call of two_sum whose second operand is not the largest number or its opposite: if
   the sum is in range then all the other values are, and the error term is exact. *)
Lemma two_sum_call_range :
  (2 <= prec)%Z ->
  forall a b, format a -> format b -> Rabs a <= Omega -> Rabs b <= Omega -> Rabs b <> Omega ->
  let s := rnd (a + b) in
  let bb := rnd (s - a) in
  let t0 := rnd (s - bb) in
  let t1 := rnd (a - t0) in
  let t2 := rnd (b - bb) in
  let e := rnd (t1 + t2) in
  inrange s ->
  inrange bb /\ inrange t0 /\ inrange t1 /\ inrange t2 /\ inrange e /\ e = a + b - s.
Proof.
intros Hp2 a b Fa Fb Ha Hb Hne s bb t0 t1 t2 e Hs.
assert (Hbb : inrange bb) by now apply two_sum_bb_range.
destruct (two_sum_range Hp2 a b Fa Fb Ha Hb Hs Hbb) as [H0 [H1 [H2 He]]].
repeat split; trivial.
generalize (two_sum_exact emin prec Hp2 a b Fa Fb). intros [_ E].
change (s + e = a + b) in E. lra.
Qed.

(* A call of fast_two_sum whose second operand b is at most Omega - U/2 in magnitude
   (for a number of the format: is not the largest number or its opposite): if s is in
   range then z is in range and |e| <= U. Nothing is assumed on a. *)
Lemma fast_two_sum_call_range :
  forall a b, format b -> Rabs b <= Omega - / 2 * U ->
  let s := rnd (a + b) in
  let z := rnd (s - a) in
  let e := rnd (b - z) in
  inrange s -> inrange z /\ Rabs e <= U.
Proof.
intros a b Fb Hb s z e Hs.
assert (U0 : 0 < U) by apply bpow_gt_0.
assert (Hd : Rabs (s - (a + b)) <= / 2 * U) by now apply round_error_top.
assert (Hz : Rabs (z - (s - a)) <= Rabs (s - (a + b))).
{ replace (s - (a + b)) with (- (b - (s - a))) by ring. rewrite Rabs_Ropp.
  now apply round_nearest. }
split.
- apply (rnd_le_Omega prec emax). replace (s - a) with (b + (s - (a + b))) by ring.
  apply Rle_trans with (1 := Rabs_triang _ _). lra.
- assert (H : Rabs (b - z) <= U).
  { replace (b - z) with (- (z - (s - a)) + - (s - (a + b))) by ring.
    apply Rle_trans with (1 := Rabs_triang _ _). rewrite 2!Rabs_Ropp. lra. }
  exact (RN_abs_le_bpow emin prec _ _ H).
Qed.

(* A value of magnitude at most 2^k, with k below emax, is in range. *)
Lemma le_bpow_inrange : forall x k, (k < emax)%Z -> Rabs x <= bpow radix2 k -> inrange x.
Proof.
intros x k Hk Hx. unfold IeeeBridge.inrange. apply Rle_lt_trans with (1 := Hx). now apply bpow_lt.
Qed.

(* two_prod: the second operation rounds the error of the first, which is small. *)
Lemma two_prod_error_le :
  forall a b, inrange (rnd (a * b + 0)) -> Rabs (rnd (a * b + - rnd (a * b + 0))) <= U.
Proof.
intros a b Hp.
assert (U0 : 0 < U) by apply bpow_gt_0.
generalize (round_error_top (a * b + 0) Hp). intros Hd.
apply (RN_abs_le_bpow emin prec).
replace (a * b + - rnd (a * b + 0)) with (- (rnd (a * b + 0) - (a * b + 0))) by ring.
rewrite Rabs_Ropp. lra.
Qed.

Lemma two_prod_range :
  forall a b, inrange (rnd (a * b + 0)) -> inrange (rnd (a * b + - rnd (a * b + 0))).
Proof.
intros a b Hp. apply le_bpow_inrange with (emax - prec)%Z. lia. now apply two_prod_error_le.
Qed.

End Top.

(** * The three kernels in the IEEE model *)

Section IeeeEFT.
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
Notation rnd := (round radix2 (FLT_exp emin prec) (Znearest tie_even)).
Notation fin x := (is_finite prec emax x = true).
Notation b2r := (B2R prec emax).
Notation inrange := (inrange emax).
Notation Omega := (Omega prec emax).
Notation stB := (stepB prec emax nan_plus nan_minus nan_opp nan_fma).
Notation runB := (run stB).
Notation runR := (runR emin prec tie_even).
Notation d0 := (d0 prec emax).
Notation finite_all := (Forall (fun x : float => fin x)).

(* The programs are the kernels of the IEEE model. *)
Lemma fast_two_sum_runB :
  forall a b : float,
  IeeeModel.fast_two_sum prec emax nan_plus nan_minus a b =
  (nth 2 (runB IeeeModel.fast_two_sum_prog [a; b]) d0,
   nth 4 (runB IeeeModel.fast_two_sum_prog [a; b]) d0).
Proof.
intros. cbv [IeeeModel.fast_two_sum run stepB nth app IeeeModel.fast_two_sum_prog]. reflexivity.
Qed.

Lemma two_prod_runB :
  forall a b : float,
  IeeeModel.two_prod prec emax nan_opp nan_fma a b =
  (nth 2 (runB IeeeModel.two_prod_prog [a; b]) d0,
   nth 3 (runB IeeeModel.two_prod_prog [a; b]) d0).
Proof.
intros. cbv [IeeeModel.two_prod run stepB nth app IeeeModel.two_prod_prog]. reflexivity.
Qed.

Lemma two_sum_runB :
  forall a b : float,
  IeeeModel.two_sum prec emax nan_plus nan_minus a b =
  (nth 2 (runB IeeeModel.two_sum_prog [a; b]) d0,
   nth 7 (runB IeeeModel.two_sum_prog [a; b]) d0).
Proof.
intros. cbv [IeeeModel.two_sum run stepB nth app IeeeModel.two_sum_prog]. reflexivity.
Qed.

(** ** fast_two_sum *)

(* Bridge: under |a| >= |b|, a finite s means that every value is finite and equal to
   that of the real model. *)
Theorem fast_two_sum_bridge :
  (2 <= prec)%Z ->
  forall a b : float, fin a -> fin b -> Rabs (b2r b) <= Rabs (b2r a) ->
  fin (nth 2 (runB IeeeModel.fast_two_sum_prog [a; b]) d0) ->
  finite_all (runB IeeeModel.fast_two_sum_prog [a; b]) /\
  map b2r (runB IeeeModel.fast_two_sum_prog [a; b]) = runR IeeeModel.fast_two_sum_prog [b2r a; b2r b].
Proof.
intros Hp2 a b Fa Fb Hab Hs.
apply (bridge_f2s_prog prec emax nan_plus nan_minus nan_opp nan_fma
         IeeeModel.fast_two_sum_prog [] 0%nat 1%nat [a; b] 2%nat); trivial.
- repeat constructor; assumption.
- generalize (fast_two_sum_correct emin prec Hp2 (b2r a) (b2r b)
                (b2r_format prec emax a) (b2r_format prec emax b) Hab).
  rewrite fast_two_sum_runR. intros [_ [_ H]]. exact H.
Qed.

Theorem fast_two_sum_values :
  (2 <= prec)%Z ->
  forall a b : float, fin a -> fin b -> Rabs (b2r b) <= Rabs (b2r a) ->
  let '(s, e) := IeeeModel.fast_two_sum prec emax nan_plus nan_minus a b in
  fin s ->
  fin e /\ (b2r s, b2r e) = fast_two_sum emin prec tie_even (b2r a) (b2r b).
Proof.
intros Hp2 a b Fa Fb Hab. rewrite fast_two_sum_runB. intros Hs.
destruct (fast_two_sum_bridge Hp2 a b Fa Fb Hab Hs) as [F M]. split.
- now apply nth_fin.
- rewrite fast_two_sum_runR. f_equal; now apply sim_nth.
Qed.

(** ** two_prod *)

Theorem two_prod_bridge :
  forall a b : float, fin a -> fin b ->
  fin (nth 2 (runB IeeeModel.two_prod_prog [a; b]) d0) ->
  finite_all (runB IeeeModel.two_prod_prog [a; b]) /\
  map b2r (runB IeeeModel.two_prod_prog [a; b]) = runR IeeeModel.two_prod_prog [b2r a; b2r b].
Proof.
intros a b Fa Fb Hp.
apply (bridge_tail_prog prec emax nan_plus nan_minus nan_opp nan_fma
         IeeeModel.two_prod_prog [Iprod 0 1] [Ifms 0 1 2] [a; b] 2%nat); trivial.
- repeat constructor; assumption.
- simpl. lia.
- intros F1 M1.
  assert (Hr : inrange (rnd (b2r a * b2r b + 0))).
  { change (rnd (b2r a * b2r b + 0)) with (nth 2 (runR [Iprod 0 1] (map b2r [a; b])) 0).
    rewrite <- M1, nth_b2r. apply b2r_inrange. }
  cbv [IeeeBridge.runR run stepR nth app map IeeeModel.two_prod_prog].
  repeat constructor; try apply b2r_inrange; trivial.
  now apply (two_prod_range prec emax).
Qed.

Theorem two_prod_values :
  forall a b : float, fin a -> fin b ->
  let '(p, e) := IeeeModel.two_prod prec emax nan_opp nan_fma a b in
  fin p ->
  fin e /\ (b2r p, b2r e) = two_prod emin prec tie_even (b2r a) (b2r b).
Proof.
intros a b Fa Fb. rewrite two_prod_runB. intros Hp.
destruct (two_prod_bridge a b Fa Fb Hp) as [F M]. split.
- now apply nth_fin.
- rewrite two_prod_runR. f_equal; now apply sim_nth.
Qed.

(** ** two_sum *)

(* The sum is one IEEE addition: when finite, it is the rounded sum. *)
Lemma two_sum_sum :
  forall a b : float, fin a -> fin b ->
  let '(s, e) := IeeeModel.two_sum prec emax nan_plus nan_minus a b in
  fin s -> b2r s = rnd (b2r a + b2r b).
Proof.
intros a b Fa Fb. cbv [IeeeModel.two_sum].
apply (add_spec prec emax nan_plus a b Fa Fb).
Qed.

(* From the error term: its cone is the whole kernel. *)
Theorem two_sum_bridge_e :
  forall a b : float, fin a -> fin b ->
  fin (nth 7 (runB IeeeModel.two_sum_prog [a; b]) d0) ->
  finite_all (runB IeeeModel.two_sum_prog [a; b]) /\
  map b2r (runB IeeeModel.two_sum_prog [a; b]) = runR IeeeModel.two_sum_prog [b2r a; b2r b].
Proof.
intros a b Fa Fb He.
assert (Fe : finite_all [a; b]) by (repeat constructor; assumption).
assert (F : finite_all (runB IeeeModel.two_sum_prog [a; b])).
{ apply (covers_sound prec emax nan_plus nan_minus nan_opp nan_fma) with 7%nat; trivial. }
split. exact F.
now apply (run_sim prec emax nan_plus nan_minus nan_opp nan_fma IeeeModel.two_sum_prog [a; b] Fe).
Qed.

(* From the sum, when bb does not overflow. *)
Theorem two_sum_bridge_s :
  (2 <= prec)%Z ->
  forall a b : float, fin a -> fin b ->
  inrange (rnd (rnd (b2r a + b2r b) - b2r a)) ->
  fin (nth 2 (runB IeeeModel.two_sum_prog [a; b]) d0) ->
  finite_all (runB IeeeModel.two_sum_prog [a; b]) /\
  map b2r (runB IeeeModel.two_sum_prog [a; b]) = runR IeeeModel.two_sum_prog [b2r a; b2r b].
Proof.
intros Hp2 a b Fa Fb Hbb Hs.
apply (bridge_tail_prog prec emax nan_plus nan_minus nan_opp nan_fma
         IeeeModel.two_sum_prog [Iadd 0 1] [Isub 2 0; Isub 2 3; Isub 0 4; Isub 1 3; Iadd 5 6]
         [a; b] 2%nat); trivial.
- repeat constructor; assumption.
- simpl. lia.
- intros F1 M1.
  assert (Hr : inrange (rnd (b2r a + b2r b))).
  { change (rnd (b2r a + b2r b)) with (nth 2 (runR [Iadd 0 1] (map b2r [a; b])) 0).
    rewrite <- M1, nth_b2r. apply b2r_inrange. }
  destruct (two_sum_range prec emax Hp2 (b2r a) (b2r b) (b2r_format prec emax a)
              (b2r_format prec emax b) (b2r_le_Omega prec emax a) (b2r_le_Omega prec emax b)
              Hr Hbb) as [H0 [H1 [H2 He]]].
  cbv [IeeeBridge.runR run stepR nth app map IeeeModel.two_sum_prog].
  repeat constructor; try apply b2r_inrange; trivial.
Qed.

(* The exact condition for a finite error term, and the values in that case. *)
Theorem two_sum_values :
  (2 <= prec)%Z ->
  forall a b : float, fin a -> fin b ->
  let '(s, e) := IeeeModel.two_sum prec emax nan_plus nan_minus a b in
  (fin e <-> fin s /\ inrange (rnd (rnd (b2r a + b2r b) - b2r a))) /\
  (fin e -> (b2r s, b2r e) = two_sum emin prec tie_even (b2r a) (b2r b)).
Proof.
intros Hp2 a b Fa Fb. rewrite two_sum_runB. split; [split|].
- intros He. destruct (two_sum_bridge_e a b Fa Fb He) as [F M]. split.
  + now apply nth_fin.
  + change (rnd (rnd (b2r a + b2r b) - b2r a))
      with (nth 3 (runR IeeeModel.two_sum_prog [b2r a; b2r b]) 0).
    rewrite <- M, nth_b2r. apply b2r_inrange.
- intros [Hs Hbb]. destruct (two_sum_bridge_s Hp2 a b Fa Fb Hbb Hs) as [F M]. now apply nth_fin.
- intros He. destruct (two_sum_bridge_e a b Fa Fb He) as [F M].
  rewrite two_sum_runR. f_equal; now apply sim_nth.
Qed.

(* A sufficient condition: b is not the largest number or its opposite. *)
Theorem two_sum_values_not_top :
  (2 <= prec)%Z ->
  forall a b : float, fin a -> fin b -> Rabs (b2r b) <> Omega ->
  let '(s, e) := IeeeModel.two_sum prec emax nan_plus nan_minus a b in
  fin s ->
  fin e /\ (b2r s, b2r e) = two_sum emin prec tie_even (b2r a) (b2r b).
Proof.
intros Hp2 a b Fa Fb Hb.
generalize (two_sum_values Hp2 a b Fa Fb). rewrite two_sum_runB.
intros [[_ H1] H2] Hs.
assert (He : fin (nth 7 (runB IeeeModel.two_sum_prog [a; b]) d0)).
{ apply H1. split. exact Hs.
  apply (two_sum_bb_range prec emax); trivial.
  - apply (b2r_format prec emax).
  - apply (b2r_le_Omega prec emax).
  - change (rnd (b2r a + b2r b)) with (nth 2 (runR [Iadd 0 1] (map b2r [a; b])) 0).
    assert (Fe : finite_all [a; b]) by (repeat constructor; assumption).
    assert (F1 : finite_all (runB [Iadd 0 1] [a; b])).
    { change (finite_all [a; b; nth 2 (runB IeeeModel.two_sum_prog [a; b]) d0]).
      repeat constructor; assumption. }
    destruct (run_sim prec emax nan_plus nan_minus nan_opp nan_fma [Iadd 0 1] [a; b] Fe) as [_ M1].
    rewrite <- (M1 F1), nth_b2r. apply b2r_inrange. }
split. exact He. now apply H2.
Qed.

End IeeeEFT.

(** * The statements of proofs/gen/IeeeStatements.v *)

Theorem fast_two_sum_ieee_correct : fast_two_sum_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus Hp2 a b Fa Fb Hab.
generalize (fast_two_sum_values prec emax nan_plus nan_minus
              (fun x => nan_plus x x) (fun x y _ => nan_plus x y) Hp2 a b Fa Fb Hab)
           (fast_two_sum_correct (ieee_emin prec emax) prec Hp2 (val a) (val b)
              (b2r_format prec emax a) (b2r_format prec emax b) Hab).
destruct (IeeeModel.fast_two_sum prec emax nan_plus nan_minus a b) as [s e].
intros B C Fs. destruct (B Fs) as [Fe E]. unfold val, ieee_emin in *.
rewrite <- E in C. split. exact Fe. exact C.
Qed.

Theorem two_prod_ieee_correct : two_prod_ieee_spec.
Proof.
intros prec emax Hp He nan_opp nan_fma Hp2 a b Fa Fb.
generalize (two_prod_values prec emax (fun x y => nan_fma x y y) (fun x y => nan_fma x y y)
              nan_opp nan_fma a b Fa Fb)
           (two_prod_correct (ieee_emin prec emax) prec Hp2 (val a) (val b)
              (b2r_format prec emax a) (b2r_format prec emax b)).
destruct (IeeeModel.two_prod prec emax nan_opp nan_fma a b) as [p e].
intros B C Fp. destruct (B Fp) as [Fe E]. unfold val, ieee_emin in *.
rewrite <- E in C. destruct C as [_ [_ C]]. split. exact Fe. exact C.
Qed.

(* The statement of two_sum, written by hand: the generator does not print it, because the
   exact condition under which its error term is finite is not a claim of the kernel. *)
Definition two_sum_ieee_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax),
  (2 <= prec)%Z ->
  forall a b : binary_float prec emax,
  finite a -> finite b ->
  let '(s, e) := IeeeModel.two_sum prec emax nan_plus nan_minus a b in
  (finite s -> val s = RN (ieee_emin prec emax) prec (val a + val b)) /\
  (finite e <->
   finite s /\ Rabs (RN (ieee_emin prec emax) prec (val s - val a)) < bpow radix2 emax) /\
  (finite s -> Rabs (val b) < omega prec emax -> finite e) /\
  (finite e -> (val s + val e) = (val a + val b)).

Theorem two_sum_ieee_correct : two_sum_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus Hp2 a b Fa Fb.
set (nan_opp := fun x : binary_float prec emax => nan_plus x x).
set (nan_fma := fun x y _ : binary_float prec emax => nan_plus x y).
generalize (two_sum_sum prec emax nan_plus nan_minus a b Fa Fb)
           (two_sum_values prec emax nan_plus nan_minus nan_opp nan_fma Hp2 a b Fa Fb)
           (two_sum_values_not_top prec emax nan_plus nan_minus nan_opp nan_fma Hp2 a b Fa Fb)
           (two_sum_correct (ieee_emin prec emax) prec Hp2 (val a) (val b)
              (b2r_format prec emax a) (b2r_format prec emax b)).
destruct (IeeeModel.two_sum prec emax nan_plus nan_minus a b) as [s e].
intros S1 [V1 V2] V3 C. unfold val, ieee_emin, finite, omega in *.
split; [exact S1|split; [|split]].
- split.
  + intros Fe. destruct (proj1 V1 Fe) as [Fs Hr]. split. exact Fs. rewrite (S1 Fs). exact Hr.
  + intros [Fs Hr]. apply V1. split. exact Fs. rewrite <- (S1 Fs). exact Hr.
- intros Fs Hb. destruct (V3 (Rlt_not_eq _ _ Hb) Fs) as [Fe _]. exact Fe.
- intros Fe. rewrite <- (V2 Fe) in C. destruct C as [_ [_ [_ C]]]. exact C.
Qed.

