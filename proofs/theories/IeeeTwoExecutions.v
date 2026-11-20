(* The two executions of the kernels whose only fused operations are `prod`, in the IEEE
   model (docs/developer/design/milestone2.md, "The two executions of a product").

   Such a kernel runs with each `prod a b` computed as fma(a, b, +0) at run time and as the
   plain product a * b in constant evaluation. IeeeProduct.v compares the two products.
   This file compares the two executions of a whole kernel, for the eight kernels of the
   rule that are more than one product: split, two_prod_dekker, mul_pow2_2,
   mul_pow2_2_full, ball_mul_pow2_1, ball_mul_pow2_2 and the full forms of the last two.

   Same value. Two limbs have the same value when they stand for the same extended real
   number (xval a = xval b). That is: they are equal, or both are zeros (of any signs), or
   both are NaN (of any sign and payload) (same_value_iff). Two limbs of the same value are
   finite together, NaN together, and have the same real value (same_finite, same_nan,
   same_val).

   Every operation is a function of the values of its operands. For each operation of
   IeeeOperations.v that these kernels use, the value of the result is given as a function
   of the values of the operands, for all operands (finite numbers, signed zeros,
   infinities, NaN) and whatever NaN the operation returns:

     add a b        xround RN (xadd (xval a) (xval b))               xval_add
     sub a b        xround RN (xadd (xval a) (xopp (xval b)))        xval_sub
     prod a b       xround RN (xmul (xval a) (xval b))               xval_prod
     a * b (plain)  xround RN (xmul (xval a) (xval b))               xval_mult
     abs a          xabs (xval a)                                    xval_abs
     succ a         xsucc (xval a)                                   next_up_ieee (IeeeEntry.v)
     times_inf t    xmul (xval t) (+infinity)                        xval_times_inf
     lt, eq         xlt, xeq of the values                           lt_xval, eq_xval (IeeeExt.v)

   and likewise neg, pred, le and guard, which these kernels do not use (xval_neg of
   IeeeDirected.v, next_down_ieee and xval_guard of IeeeEntry.v, le_xval of IeeeExt.v).
   xround, xadd, xmul are those of IeeeVocabulary.v: the exact result rounded to nearest,
   with the infinity of its sign when the rounding reaches 2^emax, and the sums and
   products of IEEE 754 on infinities and NaN. A select returns one of its arms, and the
   constants are the same in both executions.

   Hence each operation is compatible with "same value": operands of the same value give
   results of the same value, and comparisons the same mask (the lemmas same_add, same_sub,
   same_prod, same_mult, same_mult_prod, same_abs, same_succ, same_times_inf, same_lt,
   same_eq, same_select, and same_neg, same_pred, same_le, same_guard). None of these
   operations tells the two zeros apart in its value, and none lets the sign or the payload
   of a NaN reach a comparison: zero times infinity is a NaN for either zero, the step from
   either zero is the smallest positive number, and a comparison with a NaN is false. The
   two families of NaN functions of the statements (nan_plus and nan_plus', and so on) say
   that the two executions need not return the same NaN from any operation.

   The kernels. The generator emits one IEEE model per kernel, with `prod` the fused
   product; it does not emit the model of the plain-product execution. So each of the eight
   listings is written here once more with the product as an argument (K_with p ...), and
   two facts tie it down:
   - K_with_prod: with p the fused product it is the generated definition IeeeModel.K, by
     reflexivity, so a change of a generated listing that is not made here stops the build;
   - K_same: for two products p and p' that give results of the same value on operands of
     the same value, K_with p and K_with p' give outputs of the same value on operands of
     the same value.
   The theorems K_two_executions follow: on all operands, the listing with the plain
   product and the generated kernel return outputs of the same value.

   What this does not say. That the C++ of constant evaluation is K_with with the plain
   product rests on the listings written here, not on a generated definition. And the
   outputs have the same value, not the same bits: a zero output may differ in sign and a
   NaN output in sign and payload. (For rmul and mul_1_1, IeeeProduct.v says more.) *)
From Stdlib Require Import Reals ZArith Bool Lia Lra.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements IeeeStatements.
From Kairn Require Import Format IeeeBridge IeeeVocabulary IeeeOps IeeeExt IeeeDirected
  IeeeDirectedProd IeeeEntry IeeeProduct.
From Kairn Require IeeeOperations.
From Kairn.Gen Require IeeeModel.
Open Scope R_scope.

(** * Limbs of the same value *)

Lemma XFin_inj : forall x y : R, XFin x = XFin y -> x = y.
Proof. intros x y H. injection H. trivial. Qed.

Lemma XInf_inj : forall s s' : bool, XInf s = XInf s' -> s = s'.
Proof. intros s s' H. injection H. trivial. Qed.

Section SameValue.
Variable prec emax : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Context {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}.

Notation float := (binary_float prec emax).
Notation fin x := (is_finite prec emax x = true).
Notation b2r := (B2R prec emax).
Notation xv := (@xval prec emax).

(* a and b stand for the same extended real number. *)
Definition same_value (a b : float) : Prop := xv a = xv b.

(* Two products that give results of the same value on operands of the same value. *)
Definition same_products (p p' : float -> float -> float) : Prop :=
  forall a a' b b' : float,
  same_value a a' -> same_value b b' -> same_value (p a b) (p' a' b').

Lemma same_refl : forall a : float, same_value a a.
Proof. intros a. reflexivity. Qed.

Lemma same_sym : forall a b : float, same_value a b -> same_value b a.
Proof. unfold same_value. intros a b H. now symmetry. Qed.

Lemma same_trans :
  forall a b c : float, same_value a b -> same_value b c -> same_value a c.
Proof. unfold same_value. intros a b c H K. now rewrite H. Qed.

(* Equal, or two zeros, or two NaN. *)
Theorem same_value_iff :
  forall a b : float,
  same_value a b <-> a = b \/ (zero a /\ zero b) \/ (nan a /\ nan b).
Proof.
intros a b. unfold same_value. split.
- intros H.
  destruct a as [sa|sa|sa pa Ha|sa ma ea Ha]; destruct b as [sb|sb|sb pb Hb|sb mb eb Hb];
    try discriminate H.
  + right. left. split; eexists; reflexivity.
  + exfalso.
    assert (K : XFin 0 = XFin (b2r (B754_finite prec emax sb mb eb Hb))) by exact H.
    apply XFin_inj in K. destruct sb.
    * generalize (finite_sign_neg prec emax mb eb Hb). lra.
    * generalize (finite_sign_pos prec emax mb eb Hb). lra.
  + assert (K : XInf sa = XInf sb) by exact H. apply XInf_inj in K. left. now rewrite K.
  + right. right. split; reflexivity.
  + exfalso.
    assert (K : XFin (b2r (B754_finite prec emax sa ma ea Ha)) = XFin 0) by exact H.
    apply XFin_inj in K. destruct sa.
    * generalize (finite_sign_neg prec emax ma ea Ha). lra.
    * generalize (finite_sign_pos prec emax ma ea Ha). lra.
  + left.
    assert (K : XFin (b2r (B754_finite prec emax sa ma ea Ha))
                = XFin (b2r (B754_finite prec emax sb mb eb Hb))) by exact H.
    apply XFin_inj in K. apply (B2R_inj prec emax); [reflexivity|reflexivity|exact K].
- intros [E|[[[s E] [s' E']]|[N N']]].
  + now rewrite E.
  + now rewrite E, E'.
  + now rewrite (xval_nan prec emax a N), (xval_nan prec emax b N').
Qed.

(* What two limbs of the same value share: being finite, being a NaN, and the real
   value (0 for an infinity and for a NaN, as B2R defines it). *)
Lemma same_finite :
  forall a b : float, same_value a b -> is_finite prec emax a = is_finite prec emax b.
Proof.
intros a b H. apply same_value_iff in H. destruct H as [E|[[[s E] [s' E']]|[N N']]].
- now rewrite E.
- now rewrite E, E'.
- unfold nan in *. now rewrite (nan_not_finite prec emax a N), (nan_not_finite prec emax b N').
Qed.

Lemma same_nan :
  forall a b : float, same_value a b -> is_nan prec emax a = is_nan prec emax b.
Proof.
intros a b H. apply same_value_iff in H. destruct H as [E|[[[s E] [s' E']]|[N N']]].
- now rewrite E.
- now rewrite E, E'.
- unfold nan in *. now rewrite N, N'.
Qed.

Lemma same_val : forall a b : float, same_value a b -> b2r a = b2r b.
Proof.
intros a b H. apply same_value_iff in H. destruct H as [E|[[[s E] [s' E']]|[N N']]].
- now rewrite E.
- now rewrite E, E'.
- unfold nan in *.
  destruct a as [sa|sa|sa pa Ha|sa ma ea Ha]; try discriminate N.
  destruct b as [sb|sb|sb pb Hb|sb mb eb Hb]; try discriminate N'. reflexivity.
Qed.

End SameValue.

Arguments same_value {prec emax} a b.
Arguments same_products {prec emax} p p'.

(** * The value of each operation, as a function of the values of its operands *)

Section Values.
Variable prec emax : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Context {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}.

Notation float := (binary_float prec emax).
Notation nan_of := {x : float | is_nan prec emax x = true}.
Variable nan_plus : float -> float -> nan_of.
Variable nan_minus : float -> float -> nan_of.
Variable nan_abs : float -> nan_of.
Variable nan_fma : float -> float -> float -> nan_of.
Variable nan_mult : float -> float -> nan_of.

Notation emin := (3 - emax - prec)%Z.
Notation fexp := (FLT_exp emin prec).
Notation format := (generic_format radix2 fexp).
Notation rnd := (round radix2 fexp (Znearest tie_even)).
Notation fin x := (is_finite prec emax x = true).
Notation b2r := (B2R prec emax).
Notation inrange := (inrange emax).
Notation add := (IeeeOperations.add prec emax nan_plus).
Notation sub := (IeeeOperations.sub prec emax nan_minus).
Notation fabs := (IeeeOperations.abs prec emax nan_abs).
Notation prod := (IeeeOperations.prod prec emax nan_fma).
Notation times_inf := (IeeeOperations.times_inf prec emax nan_mult).
Notation xv := (@xval prec emax).
(* A real result rounded to nearest as an operation of the format returns it. *)
Notation xrn := (xround emax (RN emin prec)).

Let Hprec : (0 < prec)%Z.
Proof. exact prec_gt_0_. Qed.
Let Hemax : (prec < emax)%Z.
Proof. exact prec_lt_emax_. Qed.

(* A rounding that is not zero has the sign of the number it rounds. *)
Lemma sign_round : forall t : R, rnd t <> 0 -> Rlt_bool (rnd t) 0 = Rlt_bool t 0.
Proof.
intros t Z. destruct (Rlt_bool_spec t 0) as [H|H].
- apply Rlt_bool_true.
  assert (L : rnd t <= 0).
  { apply round_le_generic; auto with typeclass_instances. apply generic_format_0. lra. }
  destruct (Rle_lt_or_eq_dec _ _ L) as [K|K]; [exact K|contradiction].
- apply Rlt_bool_false.
  apply round_ge_generic; auto with typeclass_instances. apply generic_format_0.
Qed.

Lemma nonpos_nonzero : forall x : R, x <= 0 -> x <> 0 -> x < 0.
Proof. intros x L Z. destruct (Rle_lt_or_eq_dec _ _ L) as [K|K]; [exact K|contradiction]. Qed.

(* A result z that is the rounding of the real number t when that is in range, and
   otherwise the infinity of the sign of t: its value is t rounded in the format with
   overflow. *)
Lemma xval_rounded :
  forall (z : float) (t : R) (s : bool),
  (fin z /\ b2r z = rnd t) \/ (z = B754_infinity prec emax s /\ ~ inrange (rnd t)) ->
  (~ inrange (rnd t) -> s = Rlt_bool t 0) ->
  xv z = overflow_of emax (rnd t).
Proof.
intros z t s [[F E]|[E N]] Hs; unfold overflow_of.
- rewrite (xval_fin prec emax z F), E. rewrite Rlt_bool_true; [reflexivity|].
  rewrite <- E. apply (b2r_inrange prec emax).
- assert (L : bpow radix2 emax <= Rabs (rnd t)).
  { unfold IeeeBridge.inrange in N. lra. }
  rewrite E. rewrite Rlt_bool_false by exact L.
  rewrite sign_round.
  + rewrite <- (Hs N). reflexivity.
  + intros Z. rewrite Z, Rabs_R0 in L. generalize (bpow_gt_0 radix2 emax). lra.
Qed.

(* The sign of an operand of a sum or of a difference that overflows. *)
Lemma add_sign :
  forall x y : float, fin x -> fin y ->
  Bsign prec emax x = Bsign prec emax y -> b2r x + b2r y <> 0 ->
  Bsign prec emax x = Rlt_bool (b2r x + b2r y) 0.
Proof.
intros x y Fx Fy S Z. revert S.
destruct (Bsign prec emax x) eqn:Sx; intros S; symmetry in S; symmetry.
- generalize (sign_true_nonpos prec emax x Fx Sx) (sign_true_nonpos prec emax y Fy S).
  intros A B. apply Rlt_bool_true. apply nonpos_nonzero; [lra|exact Z].
- generalize (sign_false_nonneg prec emax x Fx Sx) (sign_false_nonneg prec emax y Fy S).
  intros A B. apply Rlt_bool_false. lra.
Qed.

Lemma sub_sign :
  forall x y : float, fin x -> fin y ->
  Bsign prec emax x = negb (Bsign prec emax y) -> b2r x - b2r y <> 0 ->
  Bsign prec emax x = Rlt_bool (b2r x - b2r y) 0.
Proof.
intros x y Fx Fy S Z. revert S.
destruct (Bsign prec emax x) eqn:Sx; destruct (Bsign prec emax y) eqn:Sy; intros S;
  try discriminate S; symmetry.
- generalize (sign_true_nonpos prec emax x Fx Sx) (sign_false_nonneg prec emax y Fy Sy).
  intros A B. apply Rlt_bool_true. apply nonpos_nonzero; [lra|exact Z].
- generalize (sign_false_nonneg prec emax x Fx Sx) (sign_true_nonpos prec emax y Fy Sy).
  intros A B. apply Rlt_bool_false. lra.
Qed.

(* A rounding out of range is not the rounding of zero. *)
Lemma out_of_range_nonzero : forall t : R, ~ inrange (rnd t) -> t <> 0.
Proof.
intros t N Z. apply N. rewrite Z, round_0 by auto with typeclass_instances.
unfold IeeeBridge.inrange. rewrite Rabs_R0. apply bpow_gt_0.
Qed.

(** ** add *)

Theorem xval_add : forall a b : float, xv (add a b) = xrn (xadd (xv a) (xv b)).
Proof.
intros a b.
destruct (finite_dec prec emax a) as [Fa|Fa]; [destruct (finite_dec prec emax b) as [Fb|Fb]|].
- rewrite (xval_fin prec emax a Fa), (xval_fin prec emax b Fb). cbn [xadd xround]. unfold RN.
  destruct (add_finite_cases prec emax nan_plus a b Fa Fb) as [K|[E [S N]]].
  + apply (xval_rounded _ _ false); [now left|].
    intros N. exfalso. apply N. destruct K as [_ E]. rewrite <- E. apply (b2r_inrange prec emax).
  + apply (xval_rounded _ _ (Bsign prec emax a)); [right; now split|]. intros _.
    exact (add_sign a b Fa Fb S (out_of_range_nonzero _ N)).
- destruct b as [sb|sb|sb pb Hb|sb mb eb Hb]; try discriminate Fb;
  destruct a as [sa|sa|sa pa Ha|sa ma ea Ha]; try discriminate Fa; reflexivity.
- destruct a as [sa|sa|sa pa Ha|sa ma ea Ha]; try discriminate Fa;
  destruct b as [sb|sb|sb pb Hb|sb mb eb Hb]; try reflexivity; destruct sa, sb; reflexivity.
Qed.

(** ** sub *)

(* The difference of two finite numbers: finite, with the rounded real difference as its
   value, or the infinity of the sign of the first operand when that is out of range. *)
Lemma sub_finite_cases :
  forall h l : float, fin h -> fin l ->
  (fin (sub h l) /\ b2r (sub h l) = rnd (b2r h - b2r l)) \/
  (sub h l = B754_infinity prec emax (Bsign prec emax h) /\
   Bsign prec emax h = negb (Bsign prec emax l) /\ ~ inrange (rnd (b2r h - b2r l))).
Proof.
intros h l Fh Fl.
generalize (Bminus_correct prec emax prec_gt_0_ prec_lt_emax_ nan_minus
              BinarySingleNaN.mode_NE h l Fh Fl).
fold (sub h l).
change (round radix2 (SpecFloat.fexp prec emax)
          (BinarySingleNaN.round_mode BinarySingleNaN.mode_NE) (b2r h - b2r l))
  with (rnd (b2r h - b2r l)).
destruct (Rlt_bool_spec (Rabs (rnd (b2r h - b2r l))) (bpow radix2 emax)) as [H|H].
- intros [E [F _]]. left. split; assumption.
- intros [E S]. right. split; [|split; [exact S|]].
  + apply B2FF_inf_inv. rewrite E. apply overflow_NE.
  + unfold IeeeBridge.inrange. lra.
Qed.

Theorem xval_sub : forall a b : float, xv (sub a b) = xrn (xadd (xv a) (xopp (xv b))).
Proof.
intros a b.
destruct (finite_dec prec emax a) as [Fa|Fa]; [destruct (finite_dec prec emax b) as [Fb|Fb]|].
- rewrite (xval_fin prec emax a Fa), (xval_fin prec emax b Fb). cbn [xadd xopp xround].
  unfold RN. change (b2r a + - b2r b) with (b2r a - b2r b).
  destruct (sub_finite_cases a b Fa Fb) as [K|[E [S N]]].
  + apply (xval_rounded _ _ false); [now left|].
    intros N. exfalso. apply N. destruct K as [_ E]. rewrite <- E. apply (b2r_inrange prec emax).
  + apply (xval_rounded _ _ (Bsign prec emax a)); [right; now split|]. intros _.
    exact (sub_sign a b Fa Fb S (out_of_range_nonzero _ N)).
- destruct b as [sb|sb|sb pb Hb|sb mb eb Hb]; try discriminate Fb;
  destruct a as [sa|sa|sa pa Ha|sa ma ea Ha]; try discriminate Fa; reflexivity.
- destruct a as [sa|sa|sa pa Ha|sa ma ea Ha]; try discriminate Fa;
  destruct b as [sb|sb|sb pb Hb|sb mb eb Hb]; try reflexivity; destruct sa, sb; reflexivity.
Qed.

(** ** prod, the fused product with a zero addend *)

(* The product of IEEE 754 with an operand that is not finite is an infinity or a NaN,
   which the rounding leaves as it is. *)
Lemma xround_xmul_nonfinite :
  forall a b : float,
  is_finite prec emax a = false \/ is_finite prec emax b = false ->
  xrn (xmul (xv a) (xv b)) = xmul (xv a) (xv b).
Proof.
intros a b H.
destruct (xval_cases prec emax a) as [[Fa Ea]|[[sa Ea]|Ea]];
destruct (xval_cases prec emax b) as [[Fb Eb]|[[sb Eb]|Eb]];
  rewrite Ea, Eb;
  try (exfalso; destruct H; congruence);
  cbn [xmul];
  repeat match goal with |- context [Req_bool ?x ?y] => destruct (Req_bool x y) end;
  reflexivity.
Qed.

Theorem xval_prod : forall a b : float, xv (prod a b) = xrn (xmul (xv a) (xv b)).
Proof.
intros a b.
destruct (finite_dec prec emax a) as [Fa|Fa]; [destruct (finite_dec prec emax b) as [Fb|Fb]|].
- rewrite (xval_fin prec emax a Fa), (xval_fin prec emax b Fb). cbn [xmul xround]. unfold RN.
  destruct (prod_finite_cases prec emax nan_fma a b Fa Fb) as [K|[E N]].
  + apply (xval_rounded _ _ false); [now left|].
    intros N. exfalso. apply N. destruct K as [_ E]. rewrite <- E. apply (b2r_inrange prec emax).
  + apply (xval_rounded _ _ (Rlt_bool (b2r a * b2r b) 0)); [right; now split|]. reflexivity.
- rewrite (xval_prod_nonfinite prec emax nan_fma a b (or_intror Fb)).
  symmetry. apply xround_xmul_nonfinite. now right.
- rewrite (xval_prod_nonfinite prec emax nan_fma a b (or_introl Fa)).
  symmetry. apply xround_xmul_nonfinite. now left.
Qed.

(** ** abs and times_inf *)

Theorem xval_abs : forall a : float, xv (fabs a) = xabs (xv a).
Proof.
intros a. destruct (finite_dec prec emax a) as [F|F].
- assert (F' : fin (fabs a)) by now rewrite (abs_finite prec emax nan_abs).
  rewrite (xval_fin prec emax a F), (xval_fin prec emax (fabs a) F'). cbn [xabs].
  now rewrite (abs_val prec emax nan_abs).
- destruct a as [s|s|s pl H|s m e H]; try discriminate F; reflexivity.
Qed.

(* The multiplication by +infinity of the fix-ups: the product of IEEE 754 of the value
   and +infinity, a NaN for either zero. *)
Theorem xval_times_inf : forall t : float, xv (times_inf t) = xmul (xv t) (XInf false).
Proof.
intros [s|s|s pl H|s m e H].
- rewrite (xval_nan prec emax _ (times_inf_zero prec emax nan_mult s)).
  change (xv (B754_zero prec emax s)) with (XFin 0). cbn [xmul].
  now rewrite Req_bool_true.
- rewrite (times_inf_inf prec emax nan_mult s). destruct s; reflexivity.
- rewrite (xval_nan prec emax _
             (times_inf_nan prec emax nan_mult (B754_nan prec emax s pl H) eq_refl)).
  reflexivity.
- rewrite (times_inf_finite prec emax nan_mult s m e H).
  rewrite (xval_fin prec emax (B754_finite prec emax s m e H) eq_refl).
  change (xv (B754_infinity prec emax s)) with (XInf s). cbn [xmul].
  destruct (finite_nonzero_tests prec emax s m e H) as [S1 S2]. rewrite S1, S2.
  destruct s; reflexivity.
Qed.

End Values.

(** ** The plain product *)

Section PlainProduct.
Variable prec emax : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Context {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}.

Notation float := (binary_float prec emax).
Notation nan_of := {x : float | is_nan prec emax x = true}.
Variable nan_mult : float -> float -> nan_of.

Notation emin := (3 - emax - prec)%Z.
Notation xv := (@xval prec emax).
Notation mult := (Bmult prec emax prec_gt_0_ prec_lt_emax_ nan_mult BinarySingleNaN.mode_NE).

(* The plain product has the value of the fused one (mult_prod_xval of IeeeProduct.v). *)
Theorem xval_mult :
  forall a b : float, xv (mult a b) = xround emax (RN emin prec) (xmul (xv a) (xv b)).
Proof.
intros a b.
rewrite (mult_prod_xval prec emax (fun x y _ => nan_mult x y) nan_mult a b).
apply xval_prod.
Qed.

End PlainProduct.

(** * Each operation is compatible with "same value" *)

(* The two executions are given two families of NaN functions: no operation need return
   the same NaN in both. *)
Section Compatible.
Variable prec emax : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Context {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}.

Notation float := (binary_float prec emax).
Notation nan_of := {x : float | is_nan prec emax x = true}.
Variable nan_plus nan_plus' : float -> float -> nan_of.
Variable nan_minus nan_minus' : float -> float -> nan_of.
Variable nan_opp nan_opp' : float -> nan_of.
Variable nan_abs nan_abs' : float -> nan_of.
Variable nan_fma nan_fma' : float -> float -> float -> nan_of.
Variable nan_mult nan_mult' : float -> float -> nan_of.

Notation xv := (@xval prec emax).
Notation sv := (@same_value prec emax).
Notation add := (IeeeOperations.add prec emax nan_plus).
Notation add' := (IeeeOperations.add prec emax nan_plus').
Notation sub := (IeeeOperations.sub prec emax nan_minus).
Notation sub' := (IeeeOperations.sub prec emax nan_minus').
Notation neg := (IeeeOperations.neg prec emax nan_opp).
Notation neg' := (IeeeOperations.neg prec emax nan_opp').
Notation fabs := (IeeeOperations.abs prec emax nan_abs).
Notation fabs' := (IeeeOperations.abs prec emax nan_abs').
Notation prod := (IeeeOperations.prod prec emax nan_fma).
Notation prod' := (IeeeOperations.prod prec emax nan_fma').
Notation mult := (Bmult prec emax prec_gt_0_ prec_lt_emax_ nan_mult BinarySingleNaN.mode_NE).
Notation mult' := (Bmult prec emax prec_gt_0_ prec_lt_emax_ nan_mult' BinarySingleNaN.mode_NE).
Notation times_inf := (IeeeOperations.times_inf prec emax nan_mult).
Notation times_inf' := (IeeeOperations.times_inf prec emax nan_mult').
Notation guard := (IeeeOperations.guard prec emax nan_plus).
Notation guard' := (IeeeOperations.guard prec emax nan_plus').
Notation flt := (IeeeOperations.lt prec emax).
Notation fle := (IeeeOperations.le prec emax).
Notation feq := (IeeeOperations.eq prec emax).
Notation fsucc := (IeeeOperations.succ prec emax).
Notation fpred := (IeeeOperations.pred prec emax).

Lemma same_add :
  forall a a' b b' : float, sv a a' -> sv b b' -> sv (add a b) (add' a' b').
Proof.
unfold same_value. intros a a' b b' Ha Hb.
now rewrite (xval_add prec emax nan_plus), (xval_add prec emax nan_plus'), Ha, Hb.
Qed.

Lemma same_sub :
  forall a a' b b' : float, sv a a' -> sv b b' -> sv (sub a b) (sub' a' b').
Proof.
unfold same_value. intros a a' b b' Ha Hb.
now rewrite (xval_sub prec emax nan_minus), (xval_sub prec emax nan_minus'), Ha, Hb.
Qed.

(* The product in its two forms, and one form against the other. *)
Lemma same_prod :
  forall a a' b b' : float, sv a a' -> sv b b' -> sv (prod a b) (prod' a' b').
Proof.
unfold same_value. intros a a' b b' Ha Hb.
now rewrite (xval_prod prec emax nan_fma), (xval_prod prec emax nan_fma'), Ha, Hb.
Qed.

Lemma same_mult :
  forall a a' b b' : float, sv a a' -> sv b b' -> sv (mult a b) (mult' a' b').
Proof.
unfold same_value. intros a a' b b' Ha Hb.
now rewrite (xval_mult prec emax nan_mult), (xval_mult prec emax nan_mult'), Ha, Hb.
Qed.

Lemma same_mult_prod :
  forall a a' b b' : float, sv a a' -> sv b b' -> sv (mult a b) (prod' a' b').
Proof.
unfold same_value. intros a a' b b' Ha Hb.
now rewrite (xval_mult prec emax nan_mult), (xval_prod prec emax nan_fma'), Ha, Hb.
Qed.

Lemma same_prod_mult :
  forall a a' b b' : float, sv a a' -> sv b b' -> sv (prod a b) (mult' a' b').
Proof.
unfold same_value. intros a a' b b' Ha Hb.
now rewrite (xval_prod prec emax nan_fma), (xval_mult prec emax nan_mult'), Ha, Hb.
Qed.

Lemma same_abs : forall a a' : float, sv a a' -> sv (fabs a) (fabs' a').
Proof.
unfold same_value. intros a a' Ha.
now rewrite (xval_abs prec emax nan_abs), (xval_abs prec emax nan_abs'), Ha.
Qed.

Lemma same_neg : forall a a' : float, sv a a' -> sv (neg a) (neg' a').
Proof.
unfold same_value. intros a a' Ha.
now rewrite (xval_neg prec emax nan_opp), (xval_neg prec emax nan_opp'), Ha.
Qed.

Lemma same_succ : forall a a' : float, sv a a' -> sv (fsucc a) (fsucc a').
Proof.
unfold same_value. intros a a' Ha.
now rewrite (next_up_ieee prec emax a), (next_up_ieee prec emax a'), Ha.
Qed.

Lemma same_pred : forall a a' : float, sv a a' -> sv (fpred a) (fpred a').
Proof.
unfold same_value. intros a a' Ha.
now rewrite (next_down_ieee prec emax a), (next_down_ieee prec emax a'), Ha.
Qed.

Lemma same_times_inf : forall t t' : float, sv t t' -> sv (times_inf t) (times_inf' t').
Proof.
unfold same_value. intros t t' Ht.
now rewrite (xval_times_inf prec emax nan_mult), (xval_times_inf prec emax nan_mult'), Ht.
Qed.

Lemma same_guard : forall a a' : float, sv a a' -> sv (guard a) (guard' a').
Proof.
unfold same_value. intros a a' Ha.
now rewrite (xval_guard prec emax nan_plus), (xval_guard prec emax nan_plus'), Ha.
Qed.

(* Comparisons give the same mask, and a select the same value. *)
Lemma same_lt : forall a a' b b' : float, sv a a' -> sv b b' -> flt a b = flt a' b'.
Proof.
unfold same_value. intros a a' b b' Ha Hb.
now rewrite (lt_xval prec emax a b), (lt_xval prec emax a' b'), Ha, Hb.
Qed.

Lemma same_le : forall a a' b b' : float, sv a a' -> sv b b' -> fle a b = fle a' b'.
Proof.
unfold same_value. intros a a' b b' Ha Hb.
now rewrite (le_xval prec emax a b), (le_xval prec emax a' b'), Ha, Hb.
Qed.

Lemma same_eq : forall a a' b b' : float, sv a a' -> sv b b' -> feq a b = feq a' b'.
Proof.
unfold same_value. intros a a' b b' Ha Hb.
now rewrite (eq_xval prec emax a b), (eq_xval prec emax a' b'), Ha, Hb.
Qed.

Lemma same_select :
  forall (m m' : bool) (x x' y y' : float),
  m = m' -> sv x x' -> sv y y' -> sv (if m then x else y) (if m' then x' else y').
Proof. intros m m' x x' y y' Hm Hx Hy. rewrite Hm. destruct m'; assumption. Qed.

(* The products of the two executions. *)
Lemma mult_prod_products : same_products mult prod'.
Proof. intros a a' b b'. apply same_mult_prod. Qed.

Lemma prod_prod_products : same_products prod prod'.
Proof. intros a a' b b'. apply same_prod. Qed.

Lemma mult_mult_products : same_products mult mult'.
Proof. intros a a' b b'. apply same_mult. Qed.

End Compatible.

(** * The eight listings, with the product as an argument *)

(* Each definition is the one of proofs/gen/IeeeModel.v with every `prod` replaced by the
   argument p, and with a call of one of these kernels replaced by its definition here.
   The names of the values are those of the kernel descriptions. *)
Section Listings.
Variable prec emax : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Context {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}.

Notation float := (binary_float prec emax).
Notation nan_of := {x : float | is_nan prec emax x = true}.
Variable nan_plus : float -> float -> nan_of.
Variable nan_minus : float -> float -> nan_of.
Variable nan_abs : float -> nan_of.
Variable nan_fma : float -> float -> float -> nan_of.
Variable nan_mult : float -> float -> nan_of.

Notation pzero := (IeeeOperations.pzero prec emax).
Notation pinf := (IeeeOperations.pinf prec emax).
Notation add := (IeeeOperations.add prec emax nan_plus).
Notation sub := (IeeeOperations.sub prec emax nan_minus).
Notation fabs := (IeeeOperations.abs prec emax nan_abs).
Notation prod := (IeeeOperations.prod prec emax nan_fma).
Notation times_inf := (IeeeOperations.times_inf prec emax nan_mult).
Notation flt := (IeeeOperations.lt prec emax).
Notation feq := (IeeeOperations.eq prec emax).
Notation fsucc := (IeeeOperations.succ prec emax).
Notation splitter := (IeeeModel.splitter prec emax).
Notation up_ball_mul_pow2_1_0 := (IeeeModel.up_ball_mul_pow2_1_0 prec emax).
Notation fast_two_sum := (IeeeModel.fast_two_sum prec emax nan_plus nan_minus).

Definition split_with (p : float -> float -> float) (a : float) : float * float :=
  let g := p splitter a in
  let d := sub a g in
  let ah := add g d in
  let al := sub a ah in
  (ah, al).

Definition two_prod_dekker_with (p : float -> float -> float) (a b : float) : float * float :=
  let '(ah, al) := split_with p a in
  let '(bh, bl) := split_with p b in
  let pr := p a b in
  let q0 := p ah bh in
  let t1 := sub q0 pr in
  let q1 := p ah bl in
  let t2 := add t1 q1 in
  let q2 := p al bh in
  let t3 := add t2 q2 in
  let q3 := p al bl in
  let e := add t3 q3 in
  (pr, e).

Definition mul_pow2_2_with (p : float -> float -> float) (x0 x1 c : float) : float * float :=
  let h := p x0 c in
  let l := p x1 c in
  let '(z0, z1) := fast_two_sum h l in
  (z0, z1).

Definition mul_pow2_2_full_with (p : float -> float -> float) (x0 x1 c : float)
  : float * float :=
  let '(z0, z1) := mul_pow2_2_with p x0 x1 c in
  let t := p x0 c in
  let a := fabs z0 in
  let f := flt a pinf in
  let r0 := times_inf t in
  let n := feq r0 r0 in
  let r1 := if n then pzero else r0 in
  let w0 := if f then z0 else r0 in
  let w1 := if f then z1 else r1 in
  (w0, w1).

Definition ball_mul_pow2_1_with (p : float -> float -> float) (cx rx c : float)
  : float * float :=
  let cz := p cx c in
  let rr := p rx c in
  let am := fabs cz in
  let bc := flt up_ball_mul_pow2_1_0 am in
  let zc := feq cx pzero in
  let ec := orb bc zc in
  let br := flt up_ball_mul_pow2_1_0 rr in
  let zr := feq rx pzero in
  let er := orb br zr in
  let ex := andb ec er in
  let su := fsucc rr in
  let rw := fsucc su in
  let rz := if ex then rr else rw in
  (cz, rz).

Definition ball_mul_pow2_1_full_with (p : float -> float -> float) (cx rx c : float)
  : float * float :=
  let '(cz, rz) := ball_mul_pow2_1_with p cx rx c in
  let e := feq rx rx in
  let az := fabs cz in
  let f1 := flt az pinf in
  let f2 := flt rz pinf in
  let f := andb f1 f2 in
  let c0 := if f then cz else pzero in
  let r := if f then rz else pinf in
  let cw := if e then c0 else rx in
  let rw := if e then r else rx in
  (cw, rw).

Definition ball_mul_pow2_2_with (p : float -> float -> float) (cx0 cx1 rx c : float)
  : float * float * float :=
  let h := p cx0 c in
  let l := p cx1 c in
  let '(cz0, cz1) := fast_two_sum h l in
  let rr := p rx c in
  let ze := feq cx1 pzero in
  let m := if ze then h else l in
  let am := fabs m in
  let bc := flt up_ball_mul_pow2_1_0 am in
  let zc := feq cx0 pzero in
  let ec := orb bc zc in
  let br := flt up_ball_mul_pow2_1_0 rr in
  let zr := feq rx pzero in
  let er := orb br zr in
  let ex := andb ec er in
  let su := fsucc rr in
  let rw := fsucc su in
  let rz := if ex then rr else rw in
  (cz0, cz1, rz).

Definition ball_mul_pow2_2_full_with (p : float -> float -> float) (cx0 cx1 rx c : float)
  : float * float * float :=
  let '(cz0, cz1, rz) := ball_mul_pow2_2_with p cx0 cx1 rx c in
  let e := feq rx rx in
  let az := fabs cz0 in
  let f1 := flt az pinf in
  let f2 := flt rz pinf in
  let f := andb f1 f2 in
  let c0 := if f then cz0 else pzero in
  let c1 := if f then cz1 else pzero in
  let r := if f then rz else pinf in
  let cw0 := if e then c0 else rx in
  let cw1 := if e then c1 else rx in
  let rw := if e then r else rx in
  (cw0, cw1, rw).

(* With the fused product, each listing is the generated definition: the two are
   convertible, so that a change of a generated listing that is not made above stops the
   build here. *)
Lemma split_with_prod :
  forall a : float,
  split_with prod a = IeeeModel.split prec emax nan_plus nan_minus nan_fma a.
Proof. reflexivity. Qed.

Lemma two_prod_dekker_with_prod :
  forall a b : float,
  two_prod_dekker_with prod a b
  = IeeeModel.two_prod_dekker prec emax nan_plus nan_minus nan_fma a b.
Proof. reflexivity. Qed.

Lemma mul_pow2_2_with_prod :
  forall x0 x1 c : float,
  mul_pow2_2_with prod x0 x1 c = IeeeModel.mul_pow2_2 prec emax nan_plus nan_minus nan_fma x0 x1 c.
Proof. reflexivity. Qed.

Lemma mul_pow2_2_full_with_prod :
  forall x0 x1 c : float,
  mul_pow2_2_full_with prod x0 x1 c
  = IeeeModel.mul_pow2_2_full prec emax nan_plus nan_minus nan_abs nan_fma nan_mult x0 x1 c.
Proof. reflexivity. Qed.

Lemma ball_mul_pow2_1_with_prod :
  forall cx rx c : float,
  ball_mul_pow2_1_with prod cx rx c = IeeeModel.ball_mul_pow2_1 prec emax nan_abs nan_fma cx rx c.
Proof. reflexivity. Qed.

Lemma ball_mul_pow2_1_full_with_prod :
  forall cx rx c : float,
  ball_mul_pow2_1_full_with prod cx rx c
  = IeeeModel.ball_mul_pow2_1_full prec emax nan_abs nan_fma cx rx c.
Proof. reflexivity. Qed.

Lemma ball_mul_pow2_2_with_prod :
  forall cx0 cx1 rx c : float,
  ball_mul_pow2_2_with prod cx0 cx1 rx c
  = IeeeModel.ball_mul_pow2_2 prec emax nan_plus nan_minus nan_abs nan_fma cx0 cx1 rx c.
Proof. reflexivity. Qed.

Lemma ball_mul_pow2_2_full_with_prod :
  forall cx0 cx1 rx c : float,
  ball_mul_pow2_2_full_with prod cx0 cx1 rx c
  = IeeeModel.ball_mul_pow2_2_full prec emax nan_plus nan_minus nan_abs nan_fma cx0 cx1 rx c.
Proof. reflexivity. Qed.

End Listings.

(** * The two executions of each kernel *)

Section TwoExecutions.
Variable prec emax : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Context {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}.

Notation float := (binary_float prec emax).
Notation nan_of := {x : float | is_nan prec emax x = true}.
(* The NaN functions of the first execution, and those of the second. *)
Variable nan_plus nan_plus' : float -> float -> nan_of.
Variable nan_minus nan_minus' : float -> float -> nan_of.
Variable nan_abs nan_abs' : float -> nan_of.
Variable nan_fma' : float -> float -> float -> nan_of.
Variable nan_mult nan_mult' : float -> float -> nan_of.

Notation sv := (@same_value prec emax).
Notation same_ps := (@same_products prec emax).
(* The plain product of constant evaluation, and the fused product of run time. *)
Notation mult := (Bmult prec emax prec_gt_0_ prec_lt_emax_ nan_mult BinarySingleNaN.mode_NE).
Notation prod' := (IeeeOperations.prod prec emax nan_fma').
Notation fts := (IeeeModel.fast_two_sum prec emax nan_plus nan_minus).
Notation fts' := (IeeeModel.fast_two_sum prec emax nan_plus' nan_minus').
Notation split1 := (split_with prec emax nan_plus nan_minus).
Notation split2 := (split_with prec emax nan_plus' nan_minus').
Notation dekker1 := (two_prod_dekker_with prec emax nan_plus nan_minus).
Notation dekker2 := (two_prod_dekker_with prec emax nan_plus' nan_minus').
Notation scale1 := (mul_pow2_2_with prec emax nan_plus nan_minus).
Notation scale2 := (mul_pow2_2_with prec emax nan_plus' nan_minus').
Notation scale_full1 := (mul_pow2_2_full_with prec emax nan_plus nan_minus nan_abs nan_mult).
Notation scale_full2 := (mul_pow2_2_full_with prec emax nan_plus' nan_minus' nan_abs' nan_mult').
Notation ball1 := (ball_mul_pow2_1_with prec emax nan_abs).
Notation ball2 := (ball_mul_pow2_1_with prec emax nan_abs').
Notation ball_full1 := (ball_mul_pow2_1_full_with prec emax nan_abs).
Notation ball_full2 := (ball_mul_pow2_1_full_with prec emax nan_abs').
Notation bball1 := (ball_mul_pow2_2_with prec emax nan_plus nan_minus nan_abs).
Notation bball2 := (ball_mul_pow2_2_with prec emax nan_plus' nan_minus' nan_abs').
Notation bball_full1 := (ball_mul_pow2_2_full_with prec emax nan_plus nan_minus nan_abs).
Notation bball_full2 := (ball_mul_pow2_2_full_with prec emax nan_plus' nan_minus' nan_abs').

(* One step per operation: the two sides are the same operation, of the first execution on
   the left and of the second on the right, on operands of the same value. *)
Ltac same_ops :=
  repeat first
    [ assumption
    | apply same_refl
    | match goal with H : same_products _ _ |- _ => apply H end
    | apply same_add | apply same_sub | apply same_abs | apply same_succ
    | apply same_times_inf | apply same_select | apply same_lt | apply same_eq
    | apply (f_equal2 orb) | apply (f_equal2 andb) ].

(** ** For any two products of the same value, on operands of the same value *)

Lemma fast_two_sum_same :
  forall h h' l l' : float, sv h h' -> sv l l' ->
  sv (fst (fts h l)) (fst (fts' h' l')) /\ sv (snd (fts h l)) (snd (fts' h' l')).
Proof.
intros h h' l l' Hh Hl. unfold IeeeModel.fast_two_sum. cbv zeta. cbn [fst snd].
split; same_ops.
Qed.

Lemma split_same :
  forall p p' : float -> float -> float, same_ps p p' ->
  forall a a' : float, sv a a' ->
  sv (fst (split1 p a)) (fst (split2 p' a')) /\ sv (snd (split1 p a)) (snd (split2 p' a')).
Proof.
intros p p' Hp a a' Ha. unfold split_with. cbv zeta. cbn [fst snd]. split; same_ops.
Qed.

Lemma two_prod_dekker_same :
  forall p p' : float -> float -> float, same_ps p p' ->
  forall a a' b b' : float, sv a a' -> sv b b' ->
  sv (fst (dekker1 p a b)) (fst (dekker2 p' a' b')) /\
  sv (snd (dekker1 p a b)) (snd (dekker2 p' a' b')).
Proof.
intros p p' Hp a a' b b' Ha Hb. unfold two_prod_dekker_with.
generalize (split_same p p' Hp a a' Ha) (split_same p p' Hp b b' Hb).
destruct (split1 p a) as [ah al]. destruct (split2 p' a') as [ah' al'].
destruct (split1 p b) as [bh bl]. destruct (split2 p' b') as [bh' bl'].
cbn [fst snd]. intros [H1 H2] [H3 H4]. split; same_ops.
Qed.

Lemma mul_pow2_2_same :
  forall p p' : float -> float -> float, same_ps p p' ->
  forall x0 x0' x1 x1' c c' : float, sv x0 x0' -> sv x1 x1' -> sv c c' ->
  sv (fst (scale1 p x0 x1 c)) (fst (scale2 p' x0' x1' c')) /\
  sv (snd (scale1 p x0 x1 c)) (snd (scale2 p' x0' x1' c')).
Proof.
intros p p' Hp x0 x0' x1 x1' c c' H0 H1 Hc. unfold mul_pow2_2_with. cbv zeta.
generalize (fast_two_sum_same (p x0 c) (p' x0' c') (p x1 c) (p' x1' c')
              (Hp _ _ _ _ H0 Hc) (Hp _ _ _ _ H1 Hc)).
destruct (fts (p x0 c) (p x1 c)) as [z0 z1].
destruct (fts' (p' x0' c') (p' x1' c')) as [z0' z1'].
cbn [fst snd]. exact (fun H => H).
Qed.

Lemma mul_pow2_2_full_same :
  forall p p' : float -> float -> float, same_ps p p' ->
  forall x0 x0' x1 x1' c c' : float, sv x0 x0' -> sv x1 x1' -> sv c c' ->
  sv (fst (scale_full1 p x0 x1 c)) (fst (scale_full2 p' x0' x1' c')) /\
  sv (snd (scale_full1 p x0 x1 c)) (snd (scale_full2 p' x0' x1' c')).
Proof.
intros p p' Hp x0 x0' x1 x1' c c' H0 H1 Hc. unfold mul_pow2_2_full_with.
generalize (mul_pow2_2_same p p' Hp x0 x0' x1 x1' c c' H0 H1 Hc).
destruct (scale1 p x0 x1 c) as [z0 z1]. destruct (scale2 p' x0' x1' c') as [z0' z1'].
cbn [fst snd]. intros [Hz0 Hz1]. split; same_ops.
Qed.

Lemma ball_mul_pow2_1_same :
  forall p p' : float -> float -> float, same_ps p p' ->
  forall cx cx' rx rx' c c' : float, sv cx cx' -> sv rx rx' -> sv c c' ->
  sv (fst (ball1 p cx rx c)) (fst (ball2 p' cx' rx' c')) /\
  sv (snd (ball1 p cx rx c)) (snd (ball2 p' cx' rx' c')).
Proof.
intros p p' Hp cx cx' rx rx' c c' Hx Hr Hc. unfold ball_mul_pow2_1_with. cbv zeta.
cbn [fst snd]. split; same_ops.
Qed.

Lemma ball_mul_pow2_1_full_same :
  forall p p' : float -> float -> float, same_ps p p' ->
  forall cx cx' rx rx' c c' : float, sv cx cx' -> sv rx rx' -> sv c c' ->
  sv (fst (ball_full1 p cx rx c)) (fst (ball_full2 p' cx' rx' c')) /\
  sv (snd (ball_full1 p cx rx c)) (snd (ball_full2 p' cx' rx' c')).
Proof.
intros p p' Hp cx cx' rx rx' c c' Hx Hr Hc. unfold ball_mul_pow2_1_full_with.
generalize (ball_mul_pow2_1_same p p' Hp cx cx' rx rx' c c' Hx Hr Hc).
destruct (ball1 p cx rx c) as [cz rz]. destruct (ball2 p' cx' rx' c') as [cz' rz'].
cbn [fst snd]. intros [Hz Hrz]. split; same_ops.
Qed.

Lemma ball_mul_pow2_2_same :
  forall p p' : float -> float -> float, same_ps p p' ->
  forall cx0 cx0' cx1 cx1' rx rx' c c' : float,
  sv cx0 cx0' -> sv cx1 cx1' -> sv rx rx' -> sv c c' ->
  sv (fst (fst (bball1 p cx0 cx1 rx c))) (fst (fst (bball2 p' cx0' cx1' rx' c'))) /\
  sv (snd (fst (bball1 p cx0 cx1 rx c))) (snd (fst (bball2 p' cx0' cx1' rx' c'))) /\
  sv (snd (bball1 p cx0 cx1 rx c)) (snd (bball2 p' cx0' cx1' rx' c')).
Proof.
intros p p' Hp cx0 cx0' cx1 cx1' rx rx' c c' H0 H1 Hr Hc.
unfold ball_mul_pow2_2_with. cbv zeta.
generalize (fast_two_sum_same (p cx0 c) (p' cx0' c') (p cx1 c) (p' cx1' c')
              (Hp _ _ _ _ H0 Hc) (Hp _ _ _ _ H1 Hc)).
destruct (fts (p cx0 c) (p cx1 c)) as [cz0 cz1].
destruct (fts' (p' cx0' c') (p' cx1' c')) as [cz0' cz1'].
cbn [fst snd]. intros [Hz0 Hz1]. split; [|split]; same_ops.
Qed.

Lemma ball_mul_pow2_2_full_same :
  forall p p' : float -> float -> float, same_ps p p' ->
  forall cx0 cx0' cx1 cx1' rx rx' c c' : float,
  sv cx0 cx0' -> sv cx1 cx1' -> sv rx rx' -> sv c c' ->
  sv (fst (fst (bball_full1 p cx0 cx1 rx c))) (fst (fst (bball_full2 p' cx0' cx1' rx' c'))) /\
  sv (snd (fst (bball_full1 p cx0 cx1 rx c))) (snd (fst (bball_full2 p' cx0' cx1' rx' c'))) /\
  sv (snd (bball_full1 p cx0 cx1 rx c)) (snd (bball_full2 p' cx0' cx1' rx' c')).
Proof.
intros p p' Hp cx0 cx0' cx1 cx1' rx rx' c c' H0 H1 Hr Hc.
unfold ball_mul_pow2_2_full_with.
generalize (ball_mul_pow2_2_same p p' Hp cx0 cx0' cx1 cx1' rx rx' c c' H0 H1 Hr Hc).
destruct (bball1 p cx0 cx1 rx c) as [[cz0 cz1] rz].
destruct (bball2 p' cx0' cx1' rx' c') as [[cz0' cz1'] rz'].
cbn [fst snd]. intros [Hz0 [Hz1 Hrz]]. split; [|split]; same_ops.
Qed.

(** ** The plain product against the generated kernel, on the same operands *)

(* On the left the listing with the plain product (constant evaluation), on the right the
   generated IEEE model of the kernel (run time), on the same operands, with any NaN
   functions on either side. *)
Let Hmp : same_ps mult prod'.
Proof. exact (mult_prod_products prec emax nan_fma' nan_mult). Qed.

Theorem split_two_executions :
  forall a : float,
  let '(ah, al) := split1 mult a in
  let '(bh, bl) := IeeeModel.split prec emax nan_plus' nan_minus' nan_fma' a in
  sv ah bh /\ sv al bl.
Proof.
intros a. rewrite <- (split_with_prod prec emax nan_plus' nan_minus' nan_fma' a).
generalize (split_same mult prod' Hmp a a (same_refl prec emax a)).
destruct (split1 mult a) as [ah al]. destruct (split2 prod' a) as [bh bl].
exact (fun H => H).
Qed.

Theorem two_prod_dekker_two_executions :
  forall a b : float,
  let '(p, e) := dekker1 mult a b in
  let '(q, f) := IeeeModel.two_prod_dekker prec emax nan_plus' nan_minus' nan_fma' a b in
  sv p q /\ sv e f.
Proof.
intros a b. rewrite <- (two_prod_dekker_with_prod prec emax nan_plus' nan_minus' nan_fma' a b).
generalize (two_prod_dekker_same mult prod' Hmp a a b b
              (same_refl prec emax a) (same_refl prec emax b)).
destruct (dekker1 mult a b) as [p e]. destruct (dekker2 prod' a b) as [q f].
exact (fun H => H).
Qed.

Theorem mul_pow2_2_two_executions :
  forall x0 x1 c : float,
  let '(z0, z1) := scale1 mult x0 x1 c in
  let '(w0, w1) := IeeeModel.mul_pow2_2 prec emax nan_plus' nan_minus' nan_fma' x0 x1 c in
  sv z0 w0 /\ sv z1 w1.
Proof.
intros x0 x1 c.
rewrite <- (mul_pow2_2_with_prod prec emax nan_plus' nan_minus' nan_fma' x0 x1 c).
generalize (mul_pow2_2_same mult prod' Hmp x0 x0 x1 x1 c c (same_refl prec emax x0)
              (same_refl prec emax x1) (same_refl prec emax c)).
destruct (scale1 mult x0 x1 c) as [z0 z1]. destruct (scale2 prod' x0 x1 c) as [w0 w1].
exact (fun H => H).
Qed.

Theorem mul_pow2_2_full_two_executions :
  forall x0 x1 c : float,
  let '(z0, z1) := scale_full1 mult x0 x1 c in
  let '(w0, w1) := IeeeModel.mul_pow2_2_full prec emax nan_plus' nan_minus' nan_abs' nan_fma'
                     nan_mult' x0 x1 c in
  sv z0 w0 /\ sv z1 w1.
Proof.
intros x0 x1 c.
rewrite <- (mul_pow2_2_full_with_prod prec emax nan_plus' nan_minus' nan_abs' nan_fma'
              nan_mult' x0 x1 c).
generalize (mul_pow2_2_full_same mult prod' Hmp x0 x0 x1 x1 c c (same_refl prec emax x0)
              (same_refl prec emax x1) (same_refl prec emax c)).
destruct (scale_full1 mult x0 x1 c) as [z0 z1].
destruct (scale_full2 prod' x0 x1 c) as [w0 w1].
exact (fun H => H).
Qed.

Theorem ball_mul_pow2_1_two_executions :
  forall cx rx c : float,
  let '(cz, rz) := ball1 mult cx rx c in
  let '(cw, rw) := IeeeModel.ball_mul_pow2_1 prec emax nan_abs' nan_fma' cx rx c in
  sv cz cw /\ sv rz rw.
Proof.
intros cx rx c. rewrite <- (ball_mul_pow2_1_with_prod prec emax nan_abs' nan_fma' cx rx c).
generalize (ball_mul_pow2_1_same mult prod' Hmp cx cx rx rx c c (same_refl prec emax cx)
              (same_refl prec emax rx) (same_refl prec emax c)).
destruct (ball1 mult cx rx c) as [cz rz]. destruct (ball2 prod' cx rx c) as [cw rw].
exact (fun H => H).
Qed.

Theorem ball_mul_pow2_1_full_two_executions :
  forall cx rx c : float,
  let '(cz, rz) := ball_full1 mult cx rx c in
  let '(cw, rw) := IeeeModel.ball_mul_pow2_1_full prec emax nan_abs' nan_fma' cx rx c in
  sv cz cw /\ sv rz rw.
Proof.
intros cx rx c.
rewrite <- (ball_mul_pow2_1_full_with_prod prec emax nan_abs' nan_fma' cx rx c).
generalize (ball_mul_pow2_1_full_same mult prod' Hmp cx cx rx rx c c (same_refl prec emax cx)
              (same_refl prec emax rx) (same_refl prec emax c)).
destruct (ball_full1 mult cx rx c) as [cz rz]. destruct (ball_full2 prod' cx rx c) as [cw rw].
exact (fun H => H).
Qed.

Theorem ball_mul_pow2_2_two_executions :
  forall cx0 cx1 rx c : float,
  let '(cz0, cz1, rz) := bball1 mult cx0 cx1 rx c in
  let '(cw0, cw1, rw) := IeeeModel.ball_mul_pow2_2 prec emax nan_plus' nan_minus' nan_abs'
                           nan_fma' cx0 cx1 rx c in
  sv cz0 cw0 /\ sv cz1 cw1 /\ sv rz rw.
Proof.
intros cx0 cx1 rx c.
rewrite <- (ball_mul_pow2_2_with_prod prec emax nan_plus' nan_minus' nan_abs' nan_fma'
              cx0 cx1 rx c).
generalize (ball_mul_pow2_2_same mult prod' Hmp cx0 cx0 cx1 cx1 rx rx c c
              (same_refl prec emax cx0) (same_refl prec emax cx1) (same_refl prec emax rx)
              (same_refl prec emax c)).
destruct (bball1 mult cx0 cx1 rx c) as [[cz0 cz1] rz].
destruct (bball2 prod' cx0 cx1 rx c) as [[cw0 cw1] rw].
exact (fun H => H).
Qed.

Theorem ball_mul_pow2_2_full_two_executions :
  forall cx0 cx1 rx c : float,
  let '(cz0, cz1, rz) := bball_full1 mult cx0 cx1 rx c in
  let '(cw0, cw1, rw) := IeeeModel.ball_mul_pow2_2_full prec emax nan_plus' nan_minus' nan_abs'
                           nan_fma' cx0 cx1 rx c in
  sv cz0 cw0 /\ sv cz1 cw1 /\ sv rz rw.
Proof.
intros cx0 cx1 rx c.
rewrite <- (ball_mul_pow2_2_full_with_prod prec emax nan_plus' nan_minus' nan_abs' nan_fma'
              cx0 cx1 rx c).
generalize (ball_mul_pow2_2_full_same mult prod' Hmp cx0 cx0 cx1 cx1 rx rx c c
              (same_refl prec emax cx0) (same_refl prec emax cx1) (same_refl prec emax rx)
              (same_refl prec emax c)).
destruct (bball_full1 mult cx0 cx1 rx c) as [[cz0 cz1] rz].
destruct (bball_full2 prod' cx0 cx1 rx c) as [[cw0 cw1] rw].
exact (fun H => H).
Qed.

End TwoExecutions.
