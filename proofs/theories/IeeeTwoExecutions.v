(* The two executions of the kernels whose C++ computes an operation otherwise in constant
   evaluation than at run time, in the IEEE model (docs/developer/design/milestone2.md, "The
   two executions of a product").

   A kernel whose only fused operations are `prod` runs with each `prod a b` computed as
   fma(a, b, +0) at run time and as the plain product a * b in constant evaluation.
   IeeeProduct.v compares the two products. Two more operations run otherwise in constant
   evaluation, in every kernel constexpr without a variant: `guard a`, which returns a there
   and a + 0 at run time, and `times_inf t`, which there compares t with zero (times_inf_ce of
   the C++ prelude) and at run time multiplies it by +infinity. This file compares the two
   executions of a whole kernel, with all three, for every kernel that computes one of them:
   the 63 of proofs/gen/IeeeWith.v.

   The thirty that the rule of the product makes constexpr are the products and scalings
   mul_1_1, rmul, mul_pow2_step_1, scale_step_1, mul_pow2_2, mul_pow2_2_full,
   mul_pow2_step_2, split and two_prod_dekker; the steps of axpy, axpy_step_1 and
   axpy_entry_step_1; the scalings of a ball, ball_mul_pow2_1, ball_mul_pow2_2 and their
   full forms, and the steps of the scaling of a ball vector, bv_mul_pow2_radius,
   bv_mul_pow2_step_1 and bv_mul_pow2_step_2; the bound kernels of the folds, bound_sum_1,
   bound_sum_2, bound_dot_1 and bound_dot_2; and the conversions that halve with `prod`:
   interval_mid_rad_1, interval_to_ball_1, interval_split_1, interval_split_2,
   ball_from_interval_1, ball_from_interval_2, ball_hull_1 and ball_intersection_1.

   The 33 without a product guard an operand or fix up a non-finite result: the entry
   kernels and steps that guard what the program supplies (add_down_entry, add_up_entry,
   sub_down_entry, sub_up_entry, add_entry_step_1, sub_entry_step_1, sum_entry_step_1,
   add_entry_step_2, sub_entry_step_2, sum_entry_step_2, sum_fast_entry_step_2,
   fast_two_sum_entry, two_sum_entry, radd_entry, acc_add_1, acc_add_2, bv_center_entry_1,
   bv_make_radius, ball_contains_point_1), the constructors (make_2, make_2_limbs,
   ball_make_1, ball_make_2, interval_make_1), the sums and differences of a number and a
   pair (add_2_1, sub_1_2, sub_2_1, each with a guard), and the full sums and differences,
   whose fix-ups use times_inf (add_2_1_full, sub_1_2_full, sub_2_1_full with a guard too,
   add_2_2_full, add_fast_2_2_full, sub_2_2_full).

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
     neg a          xopp (xval a)                                    xval_neg (IeeeDirected.v)
     succ a         xsucc (xval a)                                   next_up_ieee (IeeeEntry.v)
     pred a         xpred (xval a)                                   next_down_ieee (IeeeEntry.v)
     guard a        xval a                                           xval_guard (IeeeEntry.v)
     a (the guard   xval a                                           (by definition)
       of constant evaluation)
     times_inf t    xmul (xval t) (+infinity)                        xval_times_inf
     times_inf_ce t xmul (xval t) (+infinity)                        xval_times_inf_ce
     lt, le, eq     xlt, xle, xeq of the values                      lt_xval, le_xval, eq_xval
                                                                     (IeeeExt.v)
     const nan      NaN                                              same_cnan

   xround, xadd, xmul are those of IeeeVocabulary.v: the exact result rounded to nearest,
   with the infinity of its sign when the rounding reaches 2^emax, and the sums and
   products of IEEE 754 on infinities and NaN. A select returns one of its arms, a mask
   operation (and, or, not) is one of its masks, and the other constants (+0, +infinity,
   the constants up(EXPR) of the listings) are the same in both executions.

   Hence each operation is compatible with "same value": operands of the same value give
   results of the same value, and comparisons the same mask (the lemmas same_add, same_sub,
   same_prod, same_mult, same_mult_prod, same_abs, same_neg, same_succ, same_pred,
   same_guard, same_times_inf, same_lt, same_le, same_eq, same_select, same_cnan), and so
   is each operation of constant evaluation with its form of run time (same_prod_ce,
   same_guard_ce, same_times_inf_ce: no hypothesis, every operand, signed zeros, infinities
   and NaN included). None of
   these operations tells the two zeros apart in its value, and none lets the sign or the
   payload of a NaN reach a comparison: zero times infinity is a NaN for either zero, the
   step up from either zero is the smallest positive number and the step down its
   opposite, the guard and the absolute value of either zero are +0 and its opposite is a
   zero, and a comparison with a NaN is false. The IR has no division, no copy of a sign
   and no test of a sign bit. The two families of NaN functions of the statements
   (nan_plus and nan_plus', and so on) say that the two executions need not return the
   same NaN from any operation, nor be the same NaN for `const nan`.

   The kernels. The generator emits the IEEE model of each kernel with `prod` the fused
   product (IeeeModel.K), and, for each of the 63 kernels, the same listing with the three
   operations as arguments, those it computes (proofs/gen/IeeeWith.v: K_with p_ for most of
   the rule of the product, K_with p_ g_ for axpy_entry_step_1 and the two balls from an
   interval, K_with p_ t_ for mul_pow2_2_full; K_with g_, K_with t_ or K_with g_ t_ for the
   kernels without a product; a call of another kernel of the file is that kernel's K_with
   on the arguments it takes). Three facts tie the two executions:
   - K_with_prod: with p_ the fused product, and g_ and t_ the guard and times_inf of
     IeeeOperations.v, K_with is the generated definition IeeeModel.K, by reflexivity, so
     that the build stops if the two files disagree (the name is that of the first lemmas,
     about the product alone; a kernel without a product has one too);
   - K_same: for two products p and p' that give results of the same value on operands of
     the same value (same_products), and two guards g and g', or two forms t and t' of
     times_inf, of which the same holds (same_unary), K_with p and K_with p' (with g and g',
     or t and t'), each with its own NaN functions, give outputs of the same value and the
     same masks on operands of the same value. Each is proved
     by going through the two listings together, one definition at a time (the tactic
     lockstep): each value defined has the same value in both, by the compatibility lemma
     of its operation, each mask is the same, and a call of another kernel gives outputs
     of the same value by that kernel's lemma: K_same for a kernel of IeeeWith.v, and for a
     kernel of IeeeModel.v that computes none of the three the lemmas of the first part of
     the last section (two_sum, two_sum_ord, the directed sums and differences of one limb,
     ball_to_interval_1, interval_hull_1, add_2_2, lt_2_2, abs_2, le_2_1, radd, sub_1_1,
     sub_2_2, add_fast_2_2). The eight kernels proved first
     (split, two_prod_dekker, mul_pow2_2, mul_pow2_2_full, ball_mul_pow2_k and their full
     forms) keep the statements of their K_same with fst and snd; the others use the
     relations same_pair, same_triple, same_value_mask, same_pair_mask, same_four and
     same_eight, which unfold to the conjunction of the statements;
   - K_two_executions: on all operands (finite numbers, signed zeros, infinities, NaN),
     K_with at the operations of constant evaluation (prod_ce, guard_ce, times_inf_ce of
     IeeeWith.v) with the NaN functions of one execution, and the generated kernel
     IeeeModel.K with those of the other, return outputs of the same value and the same
     masks. No hypothesis on the operands. Each is the statement K_two_executions_spec that
     the generator prints in IeeeWith.v, and proofs/gen/IeeeAudit.v checks it.

   The names. rmul_two_executions and mul_1_1_two_executions of this file are not the
   corollaries of the same names of IeeeProduct.v, which say more of fewer operands (the
   same bits unless the product is a NaN, or a NaN or an exact zero): these are the same
   values on all operands, in the form of the others. A file that imports both names them
   IeeeProduct.K_two_executions and IeeeTwoExecutions.K_two_executions.

   What this does not say. That the C++ of constant evaluation is K_with at prod_ce,
   guard_ce and times_inf_ce rests on the generator: it prints IeeeWith.v, IeeeModel.v and
   the C++ from the same listing, it defines the three operations of constant evaluation in
   IeeeWith.v from the spellings of its C++ printer, it refuses a listing of IeeeWith.v whose
   callee outside it computes one of them, and its tests compare the two executions of the
   C++. That the compiler evaluates a constant expression with the operations of IEEE 754
   rounded to nearest is the compiler's. And the outputs have the same value, not the same
   bits: a zero output may differ in sign (the center of ball_from_interval_1 on [-0, -0],
   for one) and a NaN output in sign and payload. *)
From Stdlib Require Import Reals ZArith Bool Lia Lra.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements IeeeStatements.
From Kairn Require Import Format IeeeBridge IeeeVocabulary IeeeOps IeeeExt IeeeDirected
  IeeeDirectedProd IeeeEntry IeeeProduct.
From Kairn Require IeeeOperations Split TwoProdDekker IeeeEFT.
From Kairn.Gen Require IeeeModel IeeeWith.
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

(* Two operations of one operand that give results of the same value on operands of the
   same value: the two guards, the two forms of times_inf. *)
Definition same_unary (f f' : float -> float) : Prop :=
  forall a a' : float, same_value a a' -> same_value (f a) (f' a').

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

(* Outputs of the same value: each limb of the same value as the one in the same place, and
   each mask (a bool) equal. These unfold to the conjunctions of the theorems below. *)
Definition same_pair (x y : float * float) : Prop :=
  let '(a, b) := x in let '(a', b') := y in same_value a a' /\ same_value b b'.

Definition same_triple (x y : float * float * float) : Prop :=
  let '(a, b, c) := x in let '(a', b', c') := y in
  same_value a a' /\ same_value b b' /\ same_value c c'.

Definition same_value_mask (x y : float * bool) : Prop :=
  let '(a, m) := x in let '(a', m') := y in same_value a a' /\ m = m'.

Definition same_pair_mask (x y : float * float * bool) : Prop :=
  let '(a, b, m) := x in let '(a', b', m') := y in
  same_value a a' /\ same_value b b' /\ m = m'.

Definition same_four (x y : float * float * float * float) : Prop :=
  let '(a, b, c, d) := x in let '(a', b', c', d') := y in
  same_value a a' /\ same_value b b' /\ same_value c c' /\ same_value d d'.

Definition same_eight
  (x y : float * float * float * float * float * float * float * float) : Prop :=
  let '(a, b, c, d, e, f, g, h) := x in let '(a', b', c', d', e', f', g', h') := y in
  same_value a a' /\ same_value b b' /\ same_value c c' /\ same_value d d' /\
  same_value e e' /\ same_value f f' /\ same_value g g' /\ same_value h h'.

(* The form of the lemmas of the first eight kernels, with fst and snd, is same_pair. *)
Lemma same_pair_fst_snd :
  forall x y : float * float,
  same_value (fst x) (fst y) /\ same_value (snd x) (snd y) -> same_pair x y.
Proof. intros [a b] [a' b'] H. exact H. Qed.

End SameValue.

Arguments same_value {prec emax} a b.
Arguments same_products {prec emax} p p'.
Arguments same_unary {prec emax} f f'.
Arguments same_pair {prec emax} x y.
Arguments same_triple {prec emax} x y.
Arguments same_value_mask {prec emax} x y.
Arguments same_pair_mask {prec emax} x y.
Arguments same_four {prec emax} x y.
Arguments same_eight {prec emax} x y.

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
Variable nan_const nan_const' : nan_of.

Notation xv := (@xval prec emax).
Notation sv := (@same_value prec emax).
Notation cnan := (IeeeOperations.cnan prec emax nan_const).
Notation cnan' := (IeeeOperations.cnan prec emax nan_const').
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

(* In constant evaluation the guard returns its operand: the same value as at run time. *)
Lemma same_guard_operand : forall a a' : float, sv a a' -> sv (guard a) a'.
Proof. unfold same_value. intros a a' Ha. now rewrite (xval_guard prec emax nan_plus), Ha. Qed.

(* The NaN of `const nan`: a NaN in each execution, not necessarily the same one. *)
Lemma same_cnan : sv cnan cnan'.
Proof.
unfold same_value, IeeeOperations.cnan.
now rewrite (xval_nan prec emax _ (proj2_sig nan_const)),
  (xval_nan prec emax _ (proj2_sig nan_const')).
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

(** * The operations of constant evaluation against those of run time *)

(* In constant evaluation, the C++ of a kernel constexpr by the rule of the product computes
   three operations otherwise than at run time (proofs/gen/IeeeWith.v, where their forms of
   constant evaluation are defined from the C++): prod is the plain product (prod_ce), guard
   returns its operand (guard_ce), and times_inf compares instead of multiplying
   (times_inf_ce). Each gives a result of the same value as its form of run time, on every
   operand: finite numbers, signed zeros, infinities and NaN. *)
Section ConstantEvaluation.
Variable prec emax : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Context {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}.

Notation float := (binary_float prec emax).
Notation nan_of := {x : float | is_nan prec emax x = true}.
(* The NaN functions of run time (nan_plus, nan_fma, nan_mult'), and those of constant
   evaluation (nan_mult, nan_const). *)
Variable nan_plus : float -> float -> nan_of.
Variable nan_fma : float -> float -> float -> nan_of.
Variable nan_mult nan_mult' : float -> float -> nan_of.
Variable nan_const : nan_of.

Notation xv := (@xval prec emax).
Notation sv := (@same_value prec emax).
Notation b2r := (B2R prec emax).
Notation prod_ce := (IeeeWith.prod_ce prec emax nan_mult).
Notation guard_ce := (IeeeWith.guard_ce prec emax).
Notation times_inf_ce := (IeeeWith.times_inf_ce prec emax nan_const).
Notation prod := (IeeeOperations.prod prec emax nan_fma).
Notation guard := (IeeeOperations.guard prec emax nan_plus).
Notation times_inf := (IeeeOperations.times_inf prec emax nan_mult').

(* times_inf_ce is t > 0 ? +infinity : 0 > t ? -infinity : NaN. Its value is that of t times
   +infinity on every t: the infinity of the sign of t when t is not a zero and not a NaN (a
   number or an infinity), and a NaN for either zero and for a NaN. *)
Theorem xval_times_inf_ce : forall t : float, xv (times_inf_ce t) = xmul (xv t) (XInf false).
Proof.
intros t. unfold IeeeWith.times_inf_ce.
rewrite (lt_xval prec emax (IeeeOperations.pzero prec emax) t),
  (lt_xval prec emax t (IeeeOperations.pzero prec emax)), (xval_pzero prec emax).
assert (N : xv (IeeeOperations.cnan prec emax nan_const) = XNaN).
{ unfold IeeeOperations.cnan. exact (xval_nan prec emax _ (proj2_sig nan_const)). }
destruct (xval_cases prec emax t) as [[F E]|[[s E]|E]]; rewrite E.
- cbn [xlt xmul]. destruct (Rtotal_order (b2r t) 0) as [L|[Z|G]].
  + rewrite (Rlt_bool_false 0 (b2r t)) by lra. rewrite (Rlt_bool_true (b2r t) 0 L).
    rewrite Req_bool_false by lra. reflexivity.
  + rewrite Z, Rlt_bool_false by lra. rewrite Req_bool_true by reflexivity. exact N.
  + rewrite (Rlt_bool_true 0 (b2r t) G). rewrite Req_bool_false by lra.
    rewrite (Rlt_bool_false (b2r t) 0) by lra. reflexivity.
- destruct s; reflexivity.
- exact N.
Qed.

(* The two forms of times_inf on operands of the same value give results of the same value. *)
Lemma same_times_inf_ce : forall t t' : float, sv t t' -> sv (times_inf_ce t) (times_inf t').
Proof.
unfold same_value. intros t t' Ht.
now rewrite xval_times_inf_ce, (xval_times_inf prec emax nan_mult'), Ht.
Qed.

(* The guard of constant evaluation is its operand, which has the value of the guard of run
   time (same_guard_operand, the other way round). *)
Lemma same_guard_ce : forall a a' : float, sv a a' -> sv (guard_ce a) (guard a').
Proof.
unfold same_value, IeeeWith.guard_ce. intros a a' Ha.
now rewrite (xval_guard prec emax nan_plus), Ha.
Qed.

(* The plain product, under its name of IeeeWith.v, has the value of the fused one. *)
Lemma same_prod_ce : forall a a' b b' : float, sv a a' -> sv b b' -> sv (prod_ce a b) (prod a' b').
Proof. unfold IeeeWith.prod_ce. intros a a' b b'. apply same_mult_prod. Qed.

(* The three pairs, as the lemmas K_same take them. *)
Lemma prod_ce_products : same_products prod_ce prod.
Proof. intros a a' b b'. apply same_prod_ce. Qed.

Lemma guard_ce_unary : same_unary guard_ce guard.
Proof. intros a a'. apply same_guard_ce. Qed.

Lemma times_inf_ce_unary : same_unary times_inf_ce times_inf.
Proof. intros t t'. apply same_times_inf_ce. Qed.

End ConstantEvaluation.

(** * The generated listings with the fused product are the generated kernels *)

(* Each K_with of proofs/gen/IeeeWith.v at the operations of run time, the fused product, the
   guard and times_inf of IeeeOperations.v, for those it takes, is the generated definition
   IeeeModel.K: the two are convertible, so that the build stops here if the two generated
   files disagree. *)
Section Listings.
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
Variable nan_mult : float -> float -> nan_of.
Variable nan_const : nan_of.

Notation prod := (IeeeOperations.prod prec emax nan_fma).
Notation guard := (IeeeOperations.guard prec emax nan_plus).
Notation times_inf := (IeeeOperations.times_inf prec emax nan_mult).

Lemma mul_1_1_with_prod :
  forall a b : float,
  IeeeWith.mul_1_1_with prec emax prod a b = IeeeModel.mul_1_1 prec emax nan_fma a b.
Proof. reflexivity. Qed.

Lemma axpy_entry_step_1_with_prod :
  forall a x y : float,
  IeeeWith.axpy_entry_step_1_with prec emax nan_plus prod guard a x y
  = IeeeModel.axpy_entry_step_1 prec emax nan_plus nan_fma a x y.
Proof. reflexivity. Qed.

Lemma axpy_step_1_with_prod :
  forall a x y : float,
  IeeeWith.axpy_step_1_with prec emax nan_plus prod a x y
  = IeeeModel.axpy_step_1 prec emax nan_plus nan_fma a x y.
Proof. reflexivity. Qed.

Lemma interval_mid_rad_1_with_prod :
  forall xl xu : float,
  IeeeWith.interval_mid_rad_1_with prec emax nan_plus nan_minus nan_opp nan_abs nan_const prod
    xl xu
  = IeeeModel.interval_mid_rad_1 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const
      xl xu.
Proof. reflexivity. Qed.

Lemma interval_to_ball_1_with_prod :
  forall xl xu : float,
  IeeeWith.interval_to_ball_1_with prec emax nan_plus nan_minus nan_opp nan_abs nan_const prod
    xl xu
  = IeeeModel.interval_to_ball_1 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const
      xl xu.
Proof. reflexivity. Qed.

Lemma ball_from_interval_1_with_prod :
  forall lo hi : float,
  IeeeWith.ball_from_interval_1_with prec emax nan_plus nan_minus nan_opp nan_abs nan_const prod
    guard lo hi
  = IeeeModel.ball_from_interval_1 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma
      nan_const lo hi.
Proof. reflexivity. Qed.

Lemma ball_from_interval_2_with_prod :
  forall lo hi : float,
  IeeeWith.ball_from_interval_2_with prec emax nan_plus nan_minus nan_opp nan_abs nan_const prod
    guard lo hi
  = IeeeModel.ball_from_interval_2 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma
      nan_const lo hi.
Proof. reflexivity. Qed.

Lemma ball_hull_1_with_prod :
  forall cx rx cy ry : float,
  IeeeWith.ball_hull_1_with prec emax nan_plus nan_minus nan_opp nan_abs nan_const prod
    cx rx cy ry
  = IeeeModel.ball_hull_1 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const
      cx rx cy ry.
Proof. reflexivity. Qed.

Lemma ball_intersection_1_with_prod :
  forall cx rx cy ry : float,
  IeeeWith.ball_intersection_1_with prec emax nan_plus nan_minus nan_opp nan_abs nan_const prod
    cx rx cy ry
  = IeeeModel.ball_intersection_1 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma
      nan_const cx rx cy ry.
Proof. reflexivity. Qed.

Lemma ball_mul_pow2_1_with_prod :
  forall cx rx c : float,
  IeeeWith.ball_mul_pow2_1_with prec emax nan_abs prod cx rx c
  = IeeeModel.ball_mul_pow2_1 prec emax nan_abs nan_fma cx rx c.
Proof. reflexivity. Qed.

Lemma ball_mul_pow2_1_full_with_prod :
  forall cx rx c : float,
  IeeeWith.ball_mul_pow2_1_full_with prec emax nan_abs prod cx rx c
  = IeeeModel.ball_mul_pow2_1_full prec emax nan_abs nan_fma cx rx c.
Proof. reflexivity. Qed.

Lemma bound_dot_1_with_prod :
  forall m : float,
  IeeeWith.bound_dot_1_with prec emax nan_plus prod m
  = IeeeModel.bound_dot_1 prec emax nan_plus nan_fma m.
Proof. reflexivity. Qed.

Lemma bound_dot_2_with_prod :
  forall m : float,
  IeeeWith.bound_dot_2_with prec emax nan_plus prod m
  = IeeeModel.bound_dot_2 prec emax nan_plus nan_fma m.
Proof. reflexivity. Qed.

Lemma bound_sum_1_with_prod :
  forall m : float,
  IeeeWith.bound_sum_1_with prec emax nan_plus prod m
  = IeeeModel.bound_sum_1 prec emax nan_plus nan_fma m.
Proof. reflexivity. Qed.

Lemma bound_sum_2_with_prod :
  forall m : float,
  IeeeWith.bound_sum_2_with prec emax nan_plus prod m
  = IeeeModel.bound_sum_2 prec emax nan_plus nan_fma m.
Proof. reflexivity. Qed.

Lemma bv_mul_pow2_radius_with_prod :
  forall (m : float) (ex : bool) (rx c : float),
  IeeeWith.bv_mul_pow2_radius_with prec emax nan_plus nan_minus prod m ex rx c
  = IeeeModel.bv_mul_pow2_radius prec emax nan_plus nan_minus nan_fma m ex rx c.
Proof. reflexivity. Qed.

Lemma bv_mul_pow2_step_1_with_prod :
  forall x c : float,
  IeeeWith.bv_mul_pow2_step_1_with prec emax nan_abs prod x c
  = IeeeModel.bv_mul_pow2_step_1 prec emax nan_abs nan_fma x c.
Proof. reflexivity. Qed.

Lemma interval_split_1_with_prod :
  forall xl xu : float,
  IeeeWith.interval_split_1_with prec emax nan_plus nan_minus nan_opp nan_abs nan_const prod
    xl xu
  = IeeeModel.interval_split_1 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const
      xl xu.
Proof. reflexivity. Qed.

Lemma mul_pow2_step_1_with_prod :
  forall x c : float,
  IeeeWith.mul_pow2_step_1_with prec emax prod x c
  = IeeeModel.mul_pow2_step_1 prec emax nan_fma x c.
Proof. reflexivity. Qed.

Lemma rmul_with_prod :
  forall a b : float,
  IeeeWith.rmul_with prec emax prod a b = IeeeModel.rmul prec emax nan_fma a b.
Proof. reflexivity. Qed.

Lemma scale_step_1_with_prod :
  forall x a : float,
  IeeeWith.scale_step_1_with prec emax prod x a = IeeeModel.scale_step_1 prec emax nan_fma x a.
Proof. reflexivity. Qed.

Lemma split_with_prod :
  forall a : float,
  IeeeWith.split_with prec emax nan_plus nan_minus prod a
  = IeeeModel.split prec emax nan_plus nan_minus nan_fma a.
Proof. reflexivity. Qed.

Lemma two_prod_dekker_with_prod :
  forall a b : float,
  IeeeWith.two_prod_dekker_with prec emax nan_plus nan_minus prod a b
  = IeeeModel.two_prod_dekker prec emax nan_plus nan_minus nan_fma a b.
Proof. reflexivity. Qed.

Lemma mul_pow2_2_with_prod :
  forall x0 x1 c : float,
  IeeeWith.mul_pow2_2_with prec emax nan_plus nan_minus prod x0 x1 c
  = IeeeModel.mul_pow2_2 prec emax nan_plus nan_minus nan_fma x0 x1 c.
Proof. reflexivity. Qed.

Lemma ball_mul_pow2_2_with_prod :
  forall cx0 cx1 rx c : float,
  IeeeWith.ball_mul_pow2_2_with prec emax nan_plus nan_minus nan_abs prod cx0 cx1 rx c
  = IeeeModel.ball_mul_pow2_2 prec emax nan_plus nan_minus nan_abs nan_fma cx0 cx1 rx c.
Proof. reflexivity. Qed.

Lemma ball_mul_pow2_2_full_with_prod :
  forall cx0 cx1 rx c : float,
  IeeeWith.ball_mul_pow2_2_full_with prec emax nan_plus nan_minus nan_abs prod cx0 cx1 rx c
  = IeeeModel.ball_mul_pow2_2_full prec emax nan_plus nan_minus nan_abs nan_fma cx0 cx1 rx c.
Proof. reflexivity. Qed.

Lemma bv_mul_pow2_step_2_with_prod :
  forall x0 x1 c : float,
  IeeeWith.bv_mul_pow2_step_2_with prec emax nan_plus nan_minus nan_abs prod x0 x1 c
  = IeeeModel.bv_mul_pow2_step_2 prec emax nan_plus nan_minus nan_abs nan_fma x0 x1 c.
Proof. reflexivity. Qed.

Lemma interval_split_2_with_prod :
  forall xl0 xl1 xu0 xu1 : float,
  IeeeWith.interval_split_2_with prec emax nan_plus nan_minus nan_opp prod xl0 xl1 xu0 xu1
  = IeeeModel.interval_split_2 prec emax nan_plus nan_minus nan_opp nan_fma xl0 xl1 xu0 xu1.
Proof. reflexivity. Qed.

Lemma mul_pow2_2_full_with_prod :
  forall x0 x1 c : float,
  IeeeWith.mul_pow2_2_full_with prec emax nan_plus nan_minus nan_abs prod times_inf x0 x1 c
  = IeeeModel.mul_pow2_2_full prec emax nan_plus nan_minus nan_abs nan_fma nan_mult x0 x1 c.
Proof. reflexivity. Qed.

Lemma mul_pow2_step_2_with_prod :
  forall x0 x1 c : float,
  IeeeWith.mul_pow2_step_2_with prec emax nan_plus nan_minus prod x0 x1 c
  = IeeeModel.mul_pow2_step_2 prec emax nan_plus nan_minus nan_fma x0 x1 c.
Proof. reflexivity. Qed.

(* The kernels without a product. *)
Lemma acc_add_1_with_prod :
  forall s a x : float,
  IeeeWith.acc_add_1_with prec emax nan_plus nan_abs guard s a x
  = IeeeModel.acc_add_1 prec emax nan_plus nan_abs s a x.
Proof. reflexivity. Qed.

Lemma add_down_entry_with_prod :
  forall a b : float,
  IeeeWith.add_down_entry_with prec emax nan_plus nan_minus nan_abs guard a b
  = IeeeModel.add_down_entry prec emax nan_plus nan_minus nan_abs a b.
Proof. reflexivity. Qed.

Lemma add_entry_step_1_with_prod :
  forall x y : float,
  IeeeWith.add_entry_step_1_with prec emax nan_plus guard x y
  = IeeeModel.add_entry_step_1 prec emax nan_plus x y.
Proof. reflexivity. Qed.

Lemma add_up_entry_with_prod :
  forall a b : float,
  IeeeWith.add_up_entry_with prec emax nan_plus nan_minus nan_abs guard a b
  = IeeeModel.add_up_entry prec emax nan_plus nan_minus nan_abs a b.
Proof. reflexivity. Qed.

Lemma ball_contains_point_1_with_prod :
  forall c r t : float,
  IeeeWith.ball_contains_point_1_with prec emax nan_plus nan_minus nan_opp nan_abs guard c r t
  = IeeeModel.ball_contains_point_1 prec emax nan_plus nan_minus nan_opp nan_abs c r t.
Proof. reflexivity. Qed.

Lemma ball_make_1_with_prod :
  forall c r : float,
  IeeeWith.ball_make_1_with prec emax nan_abs nan_const guard c r
  = IeeeModel.ball_make_1 prec emax nan_plus nan_abs nan_const c r.
Proof. reflexivity. Qed.

Lemma bv_center_entry_1_with_prod :
  forall c : float,
  IeeeWith.bv_center_entry_1_with prec emax guard c
  = IeeeModel.bv_center_entry_1 prec emax nan_plus c.
Proof. reflexivity. Qed.

Lemma bv_make_radius_with_prod :
  forall m r : float,
  IeeeWith.bv_make_radius_with prec emax nan_plus nan_minus guard m r
  = IeeeModel.bv_make_radius prec emax nan_plus nan_minus m r.
Proof. reflexivity. Qed.

Lemma fast_two_sum_entry_with_prod :
  forall a b : float,
  IeeeWith.fast_two_sum_entry_with prec emax nan_plus nan_minus guard a b
  = IeeeModel.fast_two_sum_entry prec emax nan_plus nan_minus a b.
Proof. reflexivity. Qed.

Lemma interval_make_1_with_prod :
  forall lo hi : float,
  IeeeWith.interval_make_1_with prec emax nan_opp guard lo hi
  = IeeeModel.interval_make_1 prec emax nan_plus nan_opp lo hi.
Proof. reflexivity. Qed.

Lemma make_2_with_prod :
  forall a : float,
  IeeeWith.make_2_with prec emax guard a
  = IeeeModel.make_2 prec emax nan_plus a.
Proof. reflexivity. Qed.

Lemma radd_entry_with_prod :
  forall a b : float,
  IeeeWith.radd_entry_with prec emax nan_plus guard a b
  = IeeeModel.radd_entry prec emax nan_plus a b.
Proof. reflexivity. Qed.

Lemma sub_down_entry_with_prod :
  forall a b : float,
  IeeeWith.sub_down_entry_with prec emax nan_plus nan_minus nan_opp nan_abs guard a b
  = IeeeModel.sub_down_entry prec emax nan_plus nan_minus nan_opp nan_abs a b.
Proof. reflexivity. Qed.

Lemma sub_entry_step_1_with_prod :
  forall x y : float,
  IeeeWith.sub_entry_step_1_with prec emax nan_minus guard x y
  = IeeeModel.sub_entry_step_1 prec emax nan_plus nan_minus x y.
Proof. reflexivity. Qed.

Lemma sub_up_entry_with_prod :
  forall a b : float,
  IeeeWith.sub_up_entry_with prec emax nan_plus nan_minus nan_opp nan_abs guard a b
  = IeeeModel.sub_up_entry prec emax nan_plus nan_minus nan_opp nan_abs a b.
Proof. reflexivity. Qed.

Lemma sum_entry_step_1_with_prod :
  forall s x : float,
  IeeeWith.sum_entry_step_1_with prec emax nan_plus guard s x
  = IeeeModel.sum_entry_step_1 prec emax nan_plus s x.
Proof. reflexivity. Qed.

Lemma two_sum_entry_with_prod :
  forall a b : float,
  IeeeWith.two_sum_entry_with prec emax nan_plus nan_minus guard a b
  = IeeeModel.two_sum_entry prec emax nan_plus nan_minus a b.
Proof. reflexivity. Qed.

Lemma acc_add_2_with_prod :
  forall s0 s1 a x0 x1 : float,
  IeeeWith.acc_add_2_with prec emax nan_plus nan_minus nan_abs guard s0 s1 a x0 x1
  = IeeeModel.acc_add_2 prec emax nan_plus nan_minus nan_abs s0 s1 a x0 x1.
Proof. reflexivity. Qed.

Lemma add_2_1_with_prod :
  forall x0 x1 a : float,
  IeeeWith.add_2_1_with prec emax nan_plus nan_minus guard x0 x1 a
  = IeeeModel.add_2_1 prec emax nan_plus nan_minus x0 x1 a.
Proof. reflexivity. Qed.

Lemma add_2_1_full_with_prod :
  forall x0 x1 a : float,
  IeeeWith.add_2_1_full_with prec emax nan_plus nan_minus nan_abs guard times_inf x0 x1 a
  = IeeeModel.add_2_1_full prec emax nan_plus nan_minus nan_abs nan_mult x0 x1 a.
Proof. reflexivity. Qed.

Lemma add_2_2_full_with_prod :
  forall x0 x1 y0 y1 : float,
  IeeeWith.add_2_2_full_with prec emax nan_plus nan_minus nan_abs times_inf x0 x1 y0 y1
  = IeeeModel.add_2_2_full prec emax nan_plus nan_minus nan_abs nan_mult x0 x1 y0 y1.
Proof. reflexivity. Qed.

Lemma add_entry_step_2_with_prod :
  forall x0 x1 y0 y1 : float,
  IeeeWith.add_entry_step_2_with prec emax nan_plus nan_minus guard x0 x1 y0 y1
  = IeeeModel.add_entry_step_2 prec emax nan_plus nan_minus x0 x1 y0 y1.
Proof. reflexivity. Qed.

Lemma add_fast_2_2_full_with_prod :
  forall x0 x1 y0 y1 : float,
  IeeeWith.add_fast_2_2_full_with prec emax nan_plus nan_minus nan_abs times_inf x0 x1 y0 y1
  = IeeeModel.add_fast_2_2_full prec emax nan_plus nan_minus nan_abs nan_mult x0 x1 y0 y1.
Proof. reflexivity. Qed.

Lemma ball_make_2_with_prod :
  forall c0 c1 r : float,
  IeeeWith.ball_make_2_with prec emax nan_abs nan_const guard c0 c1 r
  = IeeeModel.ball_make_2 prec emax nan_plus nan_abs nan_const c0 c1 r.
Proof. reflexivity. Qed.

Lemma make_2_limbs_with_prod :
  forall h l : float,
  IeeeWith.make_2_limbs_with prec emax guard h l
  = IeeeModel.make_2_limbs prec emax nan_plus h l.
Proof. reflexivity. Qed.

Lemma sub_1_2_with_prod :
  forall a y0 y1 : float,
  IeeeWith.sub_1_2_with prec emax nan_plus nan_minus nan_opp guard a y0 y1
  = IeeeModel.sub_1_2 prec emax nan_plus nan_minus nan_opp a y0 y1.
Proof. reflexivity. Qed.

Lemma sub_1_2_full_with_prod :
  forall a y0 y1 : float,
  IeeeWith.sub_1_2_full_with prec emax nan_plus nan_minus nan_opp nan_abs guard times_inf a y0 y1
  = IeeeModel.sub_1_2_full prec emax nan_plus nan_minus nan_opp nan_abs nan_mult a y0 y1.
Proof. reflexivity. Qed.

Lemma sub_2_1_with_prod :
  forall x0 x1 a : float,
  IeeeWith.sub_2_1_with prec emax nan_plus nan_minus nan_opp guard x0 x1 a
  = IeeeModel.sub_2_1 prec emax nan_plus nan_minus nan_opp x0 x1 a.
Proof. reflexivity. Qed.

Lemma sub_2_1_full_with_prod :
  forall x0 x1 a : float,
  IeeeWith.sub_2_1_full_with prec emax nan_plus nan_minus nan_opp nan_abs guard times_inf x0 x1 a
  = IeeeModel.sub_2_1_full prec emax nan_plus nan_minus nan_opp nan_abs nan_mult x0 x1 a.
Proof. reflexivity. Qed.

Lemma sub_2_2_full_with_prod :
  forall x0 x1 y0 y1 : float,
  IeeeWith.sub_2_2_full_with prec emax nan_plus nan_minus nan_opp nan_abs times_inf x0 x1 y0 y1
  = IeeeModel.sub_2_2_full prec emax nan_plus nan_minus nan_opp nan_abs nan_mult x0 x1 y0 y1.
Proof. reflexivity. Qed.

Lemma sub_entry_step_2_with_prod :
  forall x0 x1 y0 y1 : float,
  IeeeWith.sub_entry_step_2_with prec emax nan_plus nan_minus nan_opp guard x0 x1 y0 y1
  = IeeeModel.sub_entry_step_2 prec emax nan_plus nan_minus nan_opp x0 x1 y0 y1.
Proof. reflexivity. Qed.

Lemma sum_entry_step_2_with_prod :
  forall s0 s1 x0 x1 : float,
  IeeeWith.sum_entry_step_2_with prec emax nan_plus nan_minus guard s0 s1 x0 x1
  = IeeeModel.sum_entry_step_2 prec emax nan_plus nan_minus s0 s1 x0 x1.
Proof. reflexivity. Qed.

Lemma sum_fast_entry_step_2_with_prod :
  forall s0 s1 x0 x1 : float,
  IeeeWith.sum_fast_entry_step_2_with prec emax nan_plus nan_minus guard s0 s1 x0 x1
  = IeeeModel.sum_fast_entry_step_2 prec emax nan_plus nan_minus s0 s1 x0 x1.
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
Variable nan_opp nan_opp' : float -> nan_of.
Variable nan_abs nan_abs' : float -> nan_of.
Variable nan_fma' : float -> float -> float -> nan_of.
Variable nan_mult nan_mult' : float -> float -> nan_of.
Variable nan_const nan_const' : nan_of.

Notation sv := (@same_value prec emax).
Notation same_ps := (@same_products prec emax).
Notation same_un := (@same_unary prec emax).
(* The operations of constant evaluation (proofs/gen/IeeeWith.v), with the NaN functions of
   the first execution: the plain product, the guard that returns its operand, and times_inf
   from comparisons. *)
Notation prod_ce := (IeeeWith.prod_ce prec emax nan_mult).
Notation guard_ce := (IeeeWith.guard_ce prec emax).
Notation times_inf_ce := (IeeeWith.times_inf_ce prec emax nan_const).
(* The operations of run time (IeeeOperations.v), with those of the second: the fused product,
   the guard that adds +0, and times_inf, a multiplication. *)
Notation prod' := (IeeeOperations.prod prec emax nan_fma').
Notation guard' := (IeeeOperations.guard prec emax nan_plus').
Notation times_inf' := (IeeeOperations.times_inf prec emax nan_mult').

(* The kernels of IeeeModel.v without a product that the listings call. *)
Notation fts := (IeeeModel.fast_two_sum prec emax nan_plus nan_minus).
Notation fts' := (IeeeModel.fast_two_sum prec emax nan_plus' nan_minus').
Notation m_add_1_1 := (IeeeModel.add_1_1 prec emax nan_plus).
Notation m_add_1_1' := (IeeeModel.add_1_1 prec emax nan_plus').
Notation m_two_sum := (IeeeModel.two_sum prec emax nan_plus nan_minus).
Notation m_two_sum' := (IeeeModel.two_sum prec emax nan_plus' nan_minus').
Notation m_two_sum_ord := (IeeeModel.two_sum_ord prec emax nan_plus nan_minus nan_abs).
Notation m_two_sum_ord' := (IeeeModel.two_sum_ord prec emax nan_plus' nan_minus' nan_abs').
Notation m_add_up_1 := (IeeeModel.add_up_1 prec emax nan_plus nan_minus nan_abs).
Notation m_add_up_1' := (IeeeModel.add_up_1 prec emax nan_plus' nan_minus' nan_abs').
Notation m_add_down_1 := (IeeeModel.add_down_1 prec emax nan_plus nan_minus nan_abs).
Notation m_add_down_1' := (IeeeModel.add_down_1 prec emax nan_plus' nan_minus' nan_abs').
Notation m_sub_up_1 := (IeeeModel.sub_up_1 prec emax nan_plus nan_minus nan_opp nan_abs).
Notation m_sub_up_1' := (IeeeModel.sub_up_1 prec emax nan_plus' nan_minus' nan_opp' nan_abs').
Notation m_sub_down_1 := (IeeeModel.sub_down_1 prec emax nan_plus nan_minus nan_opp nan_abs).
Notation m_sub_down_1' := (IeeeModel.sub_down_1 prec emax nan_plus' nan_minus' nan_opp' nan_abs').
Notation m_ball_to_interval_1 :=
  (IeeeModel.ball_to_interval_1 prec emax nan_plus nan_minus nan_opp nan_abs).
Notation m_ball_to_interval_1' :=
  (IeeeModel.ball_to_interval_1 prec emax nan_plus' nan_minus' nan_opp' nan_abs').
Notation m_interval_hull_1 := (IeeeModel.interval_hull_1 prec emax).
Notation m_add_2_2 := (IeeeModel.add_2_2 prec emax nan_plus nan_minus).
Notation m_add_2_2' := (IeeeModel.add_2_2 prec emax nan_plus' nan_minus').
Notation m_lt_2_2 := (IeeeModel.lt_2_2 prec emax).
Notation m_abs_2 := (IeeeModel.abs_2 prec emax nan_opp).
Notation m_abs_2' := (IeeeModel.abs_2 prec emax nan_opp').
Notation m_le_2_1 := (IeeeModel.le_2_1 prec emax).
Notation m_radd := (IeeeModel.radd prec emax nan_plus).
Notation m_radd' := (IeeeModel.radd prec emax nan_plus').
Notation m_sub_1_1 := (IeeeModel.sub_1_1 prec emax nan_minus).
Notation m_sub_1_1' := (IeeeModel.sub_1_1 prec emax nan_minus').
Notation m_sub_2_2 := (IeeeModel.sub_2_2 prec emax nan_plus nan_minus nan_opp).
Notation m_sub_2_2' := (IeeeModel.sub_2_2 prec emax nan_plus' nan_minus' nan_opp').
Notation m_add_fast_2_2 := (IeeeModel.add_fast_2_2 prec emax nan_plus nan_minus).
Notation m_add_fast_2_2' := (IeeeModel.add_fast_2_2 prec emax nan_plus' nan_minus').

(* The listings of proofs/gen/IeeeWith.v, with the NaN functions of each execution. *)
Notation split1 := (IeeeWith.split_with prec emax nan_plus nan_minus).
Notation split2 := (IeeeWith.split_with prec emax nan_plus' nan_minus').
Notation dekker1 := (IeeeWith.two_prod_dekker_with prec emax nan_plus nan_minus).
Notation dekker2 := (IeeeWith.two_prod_dekker_with prec emax nan_plus' nan_minus').
Notation scale1 := (IeeeWith.mul_pow2_2_with prec emax nan_plus nan_minus).
Notation scale2 := (IeeeWith.mul_pow2_2_with prec emax nan_plus' nan_minus').
Notation scale_full1 := (IeeeWith.mul_pow2_2_full_with prec emax nan_plus nan_minus nan_abs).
Notation scale_full2 := (IeeeWith.mul_pow2_2_full_with prec emax nan_plus' nan_minus' nan_abs').
Notation ball1 := (IeeeWith.ball_mul_pow2_1_with prec emax nan_abs).
Notation ball2 := (IeeeWith.ball_mul_pow2_1_with prec emax nan_abs').
Notation ball_full1 := (IeeeWith.ball_mul_pow2_1_full_with prec emax nan_abs).
Notation ball_full2 := (IeeeWith.ball_mul_pow2_1_full_with prec emax nan_abs').
Notation bball1 := (IeeeWith.ball_mul_pow2_2_with prec emax nan_plus nan_minus nan_abs).
Notation bball2 := (IeeeWith.ball_mul_pow2_2_with prec emax nan_plus' nan_minus' nan_abs').
Notation bball_full1 := (IeeeWith.ball_mul_pow2_2_full_with prec emax nan_plus nan_minus nan_abs).
Notation bball_full2 :=
  (IeeeWith.ball_mul_pow2_2_full_with prec emax nan_plus' nan_minus' nan_abs').

Notation w_mul_1_1 := (IeeeWith.mul_1_1_with prec emax).
Notation w_axpy_entry_step_1 := (IeeeWith.axpy_entry_step_1_with prec emax nan_plus).
Notation w_axpy_entry_step_1' := (IeeeWith.axpy_entry_step_1_with prec emax nan_plus').
Notation w_axpy_step_1 := (IeeeWith.axpy_step_1_with prec emax nan_plus).
Notation w_axpy_step_1' := (IeeeWith.axpy_step_1_with prec emax nan_plus').
Notation w_interval_mid_rad_1 :=
  (IeeeWith.interval_mid_rad_1_with prec emax nan_plus nan_minus nan_opp nan_abs nan_const).
Notation w_interval_mid_rad_1' :=
  (IeeeWith.interval_mid_rad_1_with prec emax nan_plus' nan_minus' nan_opp' nan_abs' nan_const').
Notation w_interval_to_ball_1 :=
  (IeeeWith.interval_to_ball_1_with prec emax nan_plus nan_minus nan_opp nan_abs nan_const).
Notation w_interval_to_ball_1' :=
  (IeeeWith.interval_to_ball_1_with prec emax nan_plus' nan_minus' nan_opp' nan_abs' nan_const').
Notation w_ball_from_interval_1 :=
  (IeeeWith.ball_from_interval_1_with prec emax nan_plus nan_minus nan_opp nan_abs nan_const).
Notation w_ball_from_interval_1' :=
  (IeeeWith.ball_from_interval_1_with prec emax nan_plus' nan_minus' nan_opp' nan_abs'
     nan_const').
Notation w_ball_from_interval_2 :=
  (IeeeWith.ball_from_interval_2_with prec emax nan_plus nan_minus nan_opp nan_abs nan_const).
Notation w_ball_from_interval_2' :=
  (IeeeWith.ball_from_interval_2_with prec emax nan_plus' nan_minus' nan_opp' nan_abs'
     nan_const').
Notation w_ball_hull_1 :=
  (IeeeWith.ball_hull_1_with prec emax nan_plus nan_minus nan_opp nan_abs nan_const).
Notation w_ball_hull_1' :=
  (IeeeWith.ball_hull_1_with prec emax nan_plus' nan_minus' nan_opp' nan_abs' nan_const').
Notation w_ball_intersection_1 :=
  (IeeeWith.ball_intersection_1_with prec emax nan_plus nan_minus nan_opp nan_abs nan_const).
Notation w_ball_intersection_1' :=
  (IeeeWith.ball_intersection_1_with prec emax nan_plus' nan_minus' nan_opp' nan_abs'
     nan_const').
Notation w_bound_dot_1 := (IeeeWith.bound_dot_1_with prec emax nan_plus).
Notation w_bound_dot_1' := (IeeeWith.bound_dot_1_with prec emax nan_plus').
Notation w_bound_dot_2 := (IeeeWith.bound_dot_2_with prec emax nan_plus).
Notation w_bound_dot_2' := (IeeeWith.bound_dot_2_with prec emax nan_plus').
Notation w_bound_sum_1 := (IeeeWith.bound_sum_1_with prec emax nan_plus).
Notation w_bound_sum_1' := (IeeeWith.bound_sum_1_with prec emax nan_plus').
Notation w_bound_sum_2 := (IeeeWith.bound_sum_2_with prec emax nan_plus).
Notation w_bound_sum_2' := (IeeeWith.bound_sum_2_with prec emax nan_plus').
Notation w_bv_mul_pow2_radius := (IeeeWith.bv_mul_pow2_radius_with prec emax nan_plus nan_minus).
Notation w_bv_mul_pow2_radius' :=
  (IeeeWith.bv_mul_pow2_radius_with prec emax nan_plus' nan_minus').
Notation w_bv_mul_pow2_step_1 := (IeeeWith.bv_mul_pow2_step_1_with prec emax nan_abs).
Notation w_bv_mul_pow2_step_1' := (IeeeWith.bv_mul_pow2_step_1_with prec emax nan_abs').
Notation w_interval_split_1 :=
  (IeeeWith.interval_split_1_with prec emax nan_plus nan_minus nan_opp nan_abs nan_const).
Notation w_interval_split_1' :=
  (IeeeWith.interval_split_1_with prec emax nan_plus' nan_minus' nan_opp' nan_abs' nan_const').
Notation w_mul_pow2_step_1 := (IeeeWith.mul_pow2_step_1_with prec emax).
Notation w_rmul := (IeeeWith.rmul_with prec emax).
Notation w_scale_step_1 := (IeeeWith.scale_step_1_with prec emax).
Notation w_bv_mul_pow2_step_2 :=
  (IeeeWith.bv_mul_pow2_step_2_with prec emax nan_plus nan_minus nan_abs).
Notation w_bv_mul_pow2_step_2' :=
  (IeeeWith.bv_mul_pow2_step_2_with prec emax nan_plus' nan_minus' nan_abs').
Notation w_interval_split_2 :=
  (IeeeWith.interval_split_2_with prec emax nan_plus nan_minus nan_opp).
Notation w_interval_split_2' :=
  (IeeeWith.interval_split_2_with prec emax nan_plus' nan_minus' nan_opp').
Notation w_mul_pow2_step_2 := (IeeeWith.mul_pow2_step_2_with prec emax nan_plus nan_minus).
Notation w_mul_pow2_step_2' := (IeeeWith.mul_pow2_step_2_with prec emax nan_plus' nan_minus').
(* The kernels without a product: those that guard an operand, and the full sums and
   differences, whose fix-ups use times_inf. *)
Notation w_acc_add_1 := (IeeeWith.acc_add_1_with prec emax nan_plus nan_abs).
Notation w_acc_add_1' := (IeeeWith.acc_add_1_with prec emax nan_plus' nan_abs').
Notation w_add_down_entry := (IeeeWith.add_down_entry_with prec emax nan_plus nan_minus nan_abs).
Notation w_add_down_entry' := (IeeeWith.add_down_entry_with prec emax nan_plus' nan_minus'
  nan_abs').
Notation w_add_entry_step_1 := (IeeeWith.add_entry_step_1_with prec emax nan_plus).
Notation w_add_entry_step_1' := (IeeeWith.add_entry_step_1_with prec emax nan_plus').
Notation w_add_up_entry := (IeeeWith.add_up_entry_with prec emax nan_plus nan_minus nan_abs).
Notation w_add_up_entry' := (IeeeWith.add_up_entry_with prec emax nan_plus' nan_minus' nan_abs').
Notation w_ball_contains_point_1 := (IeeeWith.ball_contains_point_1_with prec emax nan_plus
  nan_minus nan_opp nan_abs).
Notation w_ball_contains_point_1' := (IeeeWith.ball_contains_point_1_with prec emax nan_plus'
  nan_minus' nan_opp' nan_abs').
Notation w_ball_make_1 := (IeeeWith.ball_make_1_with prec emax nan_abs nan_const).
Notation w_ball_make_1' := (IeeeWith.ball_make_1_with prec emax nan_abs' nan_const').
Notation w_bv_center_entry_1 := (IeeeWith.bv_center_entry_1_with prec emax).
Notation w_bv_make_radius := (IeeeWith.bv_make_radius_with prec emax nan_plus nan_minus).
Notation w_bv_make_radius' := (IeeeWith.bv_make_radius_with prec emax nan_plus' nan_minus').
Notation w_fast_two_sum_entry := (IeeeWith.fast_two_sum_entry_with prec emax nan_plus nan_minus).
Notation w_fast_two_sum_entry' := (IeeeWith.fast_two_sum_entry_with prec emax nan_plus'
  nan_minus').
Notation w_interval_make_1 := (IeeeWith.interval_make_1_with prec emax nan_opp).
Notation w_interval_make_1' := (IeeeWith.interval_make_1_with prec emax nan_opp').
Notation w_make_2 := (IeeeWith.make_2_with prec emax).
Notation w_radd_entry := (IeeeWith.radd_entry_with prec emax nan_plus).
Notation w_radd_entry' := (IeeeWith.radd_entry_with prec emax nan_plus').
Notation w_sub_down_entry := (IeeeWith.sub_down_entry_with prec emax nan_plus nan_minus nan_opp
  nan_abs).
Notation w_sub_down_entry' := (IeeeWith.sub_down_entry_with prec emax nan_plus' nan_minus' nan_opp'
  nan_abs').
Notation w_sub_entry_step_1 := (IeeeWith.sub_entry_step_1_with prec emax nan_minus).
Notation w_sub_entry_step_1' := (IeeeWith.sub_entry_step_1_with prec emax nan_minus').
Notation w_sub_up_entry := (IeeeWith.sub_up_entry_with prec emax nan_plus nan_minus nan_opp
  nan_abs).
Notation w_sub_up_entry' := (IeeeWith.sub_up_entry_with prec emax nan_plus' nan_minus' nan_opp'
  nan_abs').
Notation w_sum_entry_step_1 := (IeeeWith.sum_entry_step_1_with prec emax nan_plus).
Notation w_sum_entry_step_1' := (IeeeWith.sum_entry_step_1_with prec emax nan_plus').
Notation w_two_sum_entry := (IeeeWith.two_sum_entry_with prec emax nan_plus nan_minus).
Notation w_two_sum_entry' := (IeeeWith.two_sum_entry_with prec emax nan_plus' nan_minus').
Notation w_acc_add_2 := (IeeeWith.acc_add_2_with prec emax nan_plus nan_minus nan_abs).
Notation w_acc_add_2' := (IeeeWith.acc_add_2_with prec emax nan_plus' nan_minus' nan_abs').
Notation w_add_2_1 := (IeeeWith.add_2_1_with prec emax nan_plus nan_minus).
Notation w_add_2_1' := (IeeeWith.add_2_1_with prec emax nan_plus' nan_minus').
Notation w_add_2_1_full := (IeeeWith.add_2_1_full_with prec emax nan_plus nan_minus nan_abs).
Notation w_add_2_1_full' := (IeeeWith.add_2_1_full_with prec emax nan_plus' nan_minus' nan_abs').
Notation w_add_2_2_full := (IeeeWith.add_2_2_full_with prec emax nan_plus nan_minus nan_abs).
Notation w_add_2_2_full' := (IeeeWith.add_2_2_full_with prec emax nan_plus' nan_minus' nan_abs').
Notation w_add_entry_step_2 := (IeeeWith.add_entry_step_2_with prec emax nan_plus nan_minus).
Notation w_add_entry_step_2' := (IeeeWith.add_entry_step_2_with prec emax nan_plus' nan_minus').
Notation w_add_fast_2_2_full := (IeeeWith.add_fast_2_2_full_with prec emax nan_plus nan_minus
  nan_abs).
Notation w_add_fast_2_2_full' := (IeeeWith.add_fast_2_2_full_with prec emax nan_plus' nan_minus'
  nan_abs').
Notation w_ball_make_2 := (IeeeWith.ball_make_2_with prec emax nan_abs nan_const).
Notation w_ball_make_2' := (IeeeWith.ball_make_2_with prec emax nan_abs' nan_const').
Notation w_make_2_limbs := (IeeeWith.make_2_limbs_with prec emax).
Notation w_sub_1_2 := (IeeeWith.sub_1_2_with prec emax nan_plus nan_minus nan_opp).
Notation w_sub_1_2' := (IeeeWith.sub_1_2_with prec emax nan_plus' nan_minus' nan_opp').
Notation w_sub_1_2_full := (IeeeWith.sub_1_2_full_with prec emax nan_plus nan_minus nan_opp
  nan_abs).
Notation w_sub_1_2_full' := (IeeeWith.sub_1_2_full_with prec emax nan_plus' nan_minus' nan_opp'
  nan_abs').
Notation w_sub_2_1 := (IeeeWith.sub_2_1_with prec emax nan_plus nan_minus nan_opp).
Notation w_sub_2_1' := (IeeeWith.sub_2_1_with prec emax nan_plus' nan_minus' nan_opp').
Notation w_sub_2_1_full := (IeeeWith.sub_2_1_full_with prec emax nan_plus nan_minus nan_opp
  nan_abs).
Notation w_sub_2_1_full' := (IeeeWith.sub_2_1_full_with prec emax nan_plus' nan_minus' nan_opp'
  nan_abs').
Notation w_sub_2_2_full := (IeeeWith.sub_2_2_full_with prec emax nan_plus nan_minus nan_opp
  nan_abs).
Notation w_sub_2_2_full' := (IeeeWith.sub_2_2_full_with prec emax nan_plus' nan_minus' nan_opp'
  nan_abs').
Notation w_sub_entry_step_2 := (IeeeWith.sub_entry_step_2_with prec emax nan_plus nan_minus
  nan_opp).
Notation w_sub_entry_step_2' := (IeeeWith.sub_entry_step_2_with prec emax nan_plus' nan_minus'
  nan_opp').
Notation w_sum_entry_step_2 := (IeeeWith.sum_entry_step_2_with prec emax nan_plus nan_minus).
Notation w_sum_entry_step_2' := (IeeeWith.sum_entry_step_2_with prec emax nan_plus' nan_minus').
Notation w_sum_fast_entry_step_2 := (IeeeWith.sum_fast_entry_step_2_with prec emax nan_plus
  nan_minus).
Notation w_sum_fast_entry_step_2' := (IeeeWith.sum_fast_entry_step_2_with prec emax nan_plus'
  nan_minus').

(* One step per operation: the two sides are the same operation, of the first execution on
   the left and of the second on the right, on operands of the same value. *)
Ltac same_ops :=
  repeat first
    [ assumption
    | apply same_refl
    | match goal with H : same_products _ _ |- _ => apply H end
    | match goal with H : same_unary _ _ |- _ => apply H end
    | apply same_add | apply same_sub | apply same_abs | apply same_succ
    | apply same_times_inf | apply same_select | apply same_lt | apply same_eq
    | apply (f_equal2 orb) | apply (f_equal2 andb) ].

(** ** Two listings in lockstep *)

(* A let of a value, a let of a mask, and the pair of values that a call returns: when the
   two definitions have the same value (are the same mask), the rest of each listing may be
   taken on any two values of the same value (on the same mask). *)
Lemma let_value :
  forall (A B : Type) (R : A -> B -> Prop) (e e' : float) (f : float -> A) (g : float -> B),
  sv e e' -> (forall x x' : float, sv x x' -> R (f x) (g x')) ->
  R (let x := e in f x) (let x' := e' in g x').
Proof. intros A B R e e' f g H K. exact (K e e' H). Qed.

Lemma let_mask :
  forall (A B : Type) (R : A -> B -> Prop) (e e' : bool) (f : bool -> A) (g : bool -> B),
  e = e' -> (forall m : bool, R (f m) (g m)) -> R (let m := e in f m) (let m' := e' in g m').
Proof. intros A B R e e' f g H K. rewrite <- H. exact (K e). Qed.

Lemma let_pair :
  forall (A B : Type) (R : A -> B -> Prop) (c c' : float * float)
    (f : float -> float -> A) (g : float -> float -> B),
  same_pair c c' -> (forall x x' y y' : float, sv x x' -> sv y y' -> R (f x y) (g x' y')) ->
  R (let '(x, y) := c in f x y) (let '(x', y') := c' in g x' y').
Proof.
intros A B R [x y] [x' y'] f g [Hx Hy] K. exact (K x x' y y' Hx Hy).
Qed.

(* An operand: a value already compared, a constant of the listing (the same in both), or
   the NaN of `const nan`. *)
Ltac leaf :=
  first [ assumption
        | match goal with |- same_value ?a ?a => apply same_refl end
        | apply same_cnan ].

(* One operation on values and masks already compared; `calls` proves the calls of other
   kernels. *)
Ltac same_op calls :=
  lazymatch goal with
  | |- @eq bool ?m ?m => reflexivity
  | |- @eq bool _ _ =>
      first [ apply same_lt; leaf | apply same_le; leaf | apply same_eq; leaf | solve [calls] ]
  | |- same_value (if _ then _ else _) _ => apply same_select; [reflexivity | leaf | leaf]
  | |- same_value _ _ =>
      first [ leaf
            | match goal with
              | Hp : same_products ?p ?p' |- same_value (?p _ _) (?p' _ _) => apply Hp; leaf
              | Hf : same_unary ?f ?f' |- same_value (?f _) (?f' _) => apply Hf; leaf
              end
            | apply same_add; leaf | apply same_sub; leaf | apply same_neg; leaf
            | apply same_abs; leaf | apply same_succ; leaf | apply same_pred; leaf
            | apply same_guard; leaf | apply same_times_inf; leaf | solve [calls] ]
  | |- _ => solve [calls]
  end.

(* Through the two listings, one definition at a time: the goal is R (listing) (listing'),
   for one of the relations same_value, same_pair, ... and equality of masks. *)
Ltac step calls :=
  lazymatch goal with
  | |- ?R (let x := ?e in @?f x) (let y := ?e' in @?g y) =>
      lazymatch type of e with
      | bool => refine (let_mask _ _ R e e' f g _ _); [same_op calls | intros ?; cbv beta]
      | _ => refine (let_value _ _ R e e' f g _ _); [same_op calls | intros ? ? ?; cbv beta]
      end
  | |- ?R (match ?c with pair x y => @?f x y end) (match ?c' with pair x' y' => @?g x' y' end) =>
      refine (let_pair _ _ R c c' f g _ _); [solve [calls] | intros ? ? ? ? ? ?; cbv beta]
  end.

(* The outputs: limbs of the same value and the same masks. *)
Ltac finish :=
  cbv beta iota delta [same_pair same_triple same_value_mask same_pair_mask same_four
                       same_eight];
  repeat match goal with |- _ /\ _ => split end;
  first [ leaf | reflexivity ].

Ltac lockstep calls :=
  lazymatch goal with
  | |- ?R (let _ := _ in _) _ => step calls; lockstep calls
  | |- ?R (match _ with pair _ _ => _ end) _ => step calls; lockstep calls
  | |- _ => finish
  end.

(** ** The kernels of IeeeModel.v without a product that the listings call *)

Lemma fast_two_sum_same :
  forall h h' l l' : float, sv h h' -> sv l l' ->
  sv (fst (fts h l)) (fst (fts' h' l')) /\ sv (snd (fts h l)) (snd (fts' h' l')).
Proof.
intros h h' l l' Hh Hl. unfold IeeeModel.fast_two_sum. cbv zeta. cbn [fst snd].
split; same_ops.
Qed.

Lemma fast_two_sum_pair :
  forall h h' l l' : float, sv h h' -> sv l l' -> same_pair (fts h l) (fts' h' l').
Proof. intros h h' l l' Hh Hl. apply same_pair_fst_snd. now apply fast_two_sum_same. Qed.

Lemma add_1_1_same :
  forall a a' b b' : float, sv a a' -> sv b b' -> sv (m_add_1_1 a b) (m_add_1_1' a' b').
Proof. intros a a' b b' Ha Hb. cbv beta delta [IeeeModel.add_1_1]. lockstep fail. Qed.

Lemma two_sum_same :
  forall a a' b b' : float, sv a a' -> sv b b' -> same_pair (m_two_sum a b) (m_two_sum' a' b').
Proof. intros a a' b b' Ha Hb. cbv beta delta [IeeeModel.two_sum]. lockstep fail. Qed.

Lemma two_sum_ord_same :
  forall a a' b b' : float, sv a a' -> sv b b' ->
  same_pair (m_two_sum_ord a b) (m_two_sum_ord' a' b').
Proof.
intros a a' b b' Ha Hb. cbv beta delta [IeeeModel.two_sum_ord].
lockstep ltac:(apply fast_two_sum_pair; leaf).
Qed.

Lemma add_up_1_same :
  forall a a' b b' : float, sv a a' -> sv b b' -> sv (m_add_up_1 a b) (m_add_up_1' a' b').
Proof.
intros a a' b b' Ha Hb. cbv beta delta [IeeeModel.add_up_1].
lockstep ltac:(apply two_sum_ord_same; leaf).
Qed.

Lemma add_down_1_same :
  forall a a' b b' : float, sv a a' -> sv b b' -> sv (m_add_down_1 a b) (m_add_down_1' a' b').
Proof.
intros a a' b b' Ha Hb. cbv beta delta [IeeeModel.add_down_1].
lockstep ltac:(apply two_sum_ord_same; leaf).
Qed.

Lemma sub_up_1_same :
  forall a a' b b' : float, sv a a' -> sv b b' -> sv (m_sub_up_1 a b) (m_sub_up_1' a' b').
Proof.
intros a a' b b' Ha Hb. cbv beta delta [IeeeModel.sub_up_1].
lockstep ltac:(apply add_up_1_same; leaf).
Qed.

Lemma sub_down_1_same :
  forall a a' b b' : float, sv a a' -> sv b b' -> sv (m_sub_down_1 a b) (m_sub_down_1' a' b').
Proof.
intros a a' b b' Ha Hb. cbv beta delta [IeeeModel.sub_down_1].
lockstep ltac:(apply add_down_1_same; leaf).
Qed.

Lemma ball_to_interval_1_same :
  forall c c' r r' : float, sv c c' -> sv r r' ->
  same_pair (m_ball_to_interval_1 c r) (m_ball_to_interval_1' c' r').
Proof.
intros c c' r r' Hc Hr. cbv beta delta [IeeeModel.ball_to_interval_1].
lockstep ltac:(first [apply sub_down_1_same; leaf | apply add_up_1_same; leaf]).
Qed.

Lemma interval_hull_1_same :
  forall xl xl' xu xu' yl yl' yu yu' : float,
  sv xl xl' -> sv xu xu' -> sv yl yl' -> sv yu yu' ->
  same_pair (m_interval_hull_1 xl xu yl yu) (m_interval_hull_1 xl' xu' yl' yu').
Proof.
intros xl xl' xu xu' yl yl' yu yu' Hxl Hxu Hyl Hyu. cbv beta delta [IeeeModel.interval_hull_1].
lockstep fail.
Qed.

Lemma add_2_2_same :
  forall x0 x0' x1 x1' y0 y0' y1 y1' : float,
  sv x0 x0' -> sv x1 x1' -> sv y0 y0' -> sv y1 y1' ->
  same_pair (m_add_2_2 x0 x1 y0 y1) (m_add_2_2' x0' x1' y0' y1').
Proof.
intros x0 x0' x1 x1' y0 y0' y1 y1' H0 H1 K0 K1. cbv beta delta [IeeeModel.add_2_2].
lockstep ltac:(first [apply two_sum_same; leaf | apply fast_two_sum_pair; leaf]).
Qed.

Lemma lt_2_2_same :
  forall x0 x0' x1 x1' y0 y0' y1 y1' : float,
  sv x0 x0' -> sv x1 x1' -> sv y0 y0' -> sv y1 y1' ->
  m_lt_2_2 x0 x1 y0 y1 = m_lt_2_2 x0' x1' y0' y1'.
Proof.
intros x0 x0' x1 x1' y0 y0' y1 y1' H0 H1 K0 K1. cbv beta delta [IeeeModel.lt_2_2].
lockstep fail.
Qed.

(* The callees of the kernels without a product (the entry kernels, the constructors, the full
   sums and differences). *)
Lemma abs_2_same :
  forall x0 x0' x1 x1' : float, sv x0 x0' -> sv x1 x1' ->
  same_pair (m_abs_2 x0 x1) (m_abs_2' x0' x1').
Proof. intros x0 x0' x1 x1' H0 H1. cbv beta delta [IeeeModel.abs_2]. lockstep fail. Qed.

Lemma le_2_1_same :
  forall x0 x0' x1 x1' a a' : float, sv x0 x0' -> sv x1 x1' -> sv a a' ->
  m_le_2_1 x0 x1 a = m_le_2_1 x0' x1' a'.
Proof. intros x0 x0' x1 x1' a a' H0 H1 Ha. cbv beta delta [IeeeModel.le_2_1]. lockstep fail. Qed.

Lemma radd_same :
  forall a a' b b' : float, sv a a' -> sv b b' -> sv (m_radd a b) (m_radd' a' b').
Proof. intros a a' b b' Ha Hb. cbv beta delta [IeeeModel.radd]. lockstep fail. Qed.

Lemma sub_1_1_same :
  forall a a' b b' : float, sv a a' -> sv b b' -> sv (m_sub_1_1 a b) (m_sub_1_1' a' b').
Proof. intros a a' b b' Ha Hb. cbv beta delta [IeeeModel.sub_1_1]. lockstep fail. Qed.

Lemma sub_2_2_same :
  forall x0 x0' x1 x1' y0 y0' y1 y1' : float,
  sv x0 x0' -> sv x1 x1' -> sv y0 y0' -> sv y1 y1' ->
  same_pair (m_sub_2_2 x0 x1 y0 y1) (m_sub_2_2' x0' x1' y0' y1').
Proof.
intros x0 x0' x1 x1' y0 y0' y1 y1' H0 H1 K0 K1. cbv beta delta [IeeeModel.sub_2_2].
lockstep ltac:(apply add_2_2_same; leaf).
Qed.

Lemma add_fast_2_2_same :
  forall x0 x0' x1 x1' y0 y0' y1 y1' : float,
  sv x0 x0' -> sv x1 x1' -> sv y0 y0' -> sv y1 y1' ->
  same_pair (m_add_fast_2_2 x0 x1 y0 y1) (m_add_fast_2_2' x0' x1' y0' y1').
Proof.
intros x0 x0' x1 x1' y0 y0' y1 y1' H0 H1 K0 K1. cbv beta delta [IeeeModel.add_fast_2_2].
lockstep ltac:(first [apply two_sum_same; leaf | apply fast_two_sum_pair; leaf]).
Qed.

(** ** The kernels of the rule, for any two products of the same value *)

(* The eight kernels proved first, with fst and snd. *)
Lemma split_same :
  forall p p' : float -> float -> float, same_ps p p' ->
  forall a a' : float, sv a a' ->
  sv (fst (split1 p a)) (fst (split2 p' a')) /\ sv (snd (split1 p a)) (snd (split2 p' a')).
Proof.
intros p p' Hp a a' Ha. unfold IeeeWith.split_with. cbv zeta. cbn [fst snd]. split; same_ops.
Qed.

Lemma two_prod_dekker_same :
  forall p p' : float -> float -> float, same_ps p p' ->
  forall a a' b b' : float, sv a a' -> sv b b' ->
  sv (fst (dekker1 p a b)) (fst (dekker2 p' a' b')) /\
  sv (snd (dekker1 p a b)) (snd (dekker2 p' a' b')).
Proof.
intros p p' Hp a a' b b' Ha Hb. unfold IeeeWith.two_prod_dekker_with.
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
intros p p' Hp x0 x0' x1 x1' c c' H0 H1 Hc. unfold IeeeWith.mul_pow2_2_with. cbv zeta.
generalize (fast_two_sum_same (p x0 c) (p' x0' c') (p x1 c) (p' x1' c')
              (Hp _ _ _ _ H0 Hc) (Hp _ _ _ _ H1 Hc)).
destruct (fts (p x0 c) (p x1 c)) as [z0 z1].
destruct (fts' (p' x0' c') (p' x1' c')) as [z0' z1'].
cbn [fst snd]. exact (fun H => H).
Qed.

Lemma mul_pow2_2_full_same :
  forall p p' : float -> float -> float, same_ps p p' ->
  forall ti ti' : float -> float, same_un ti ti' ->
  forall x0 x0' x1 x1' c c' : float, sv x0 x0' -> sv x1 x1' -> sv c c' ->
  sv (fst (scale_full1 p ti x0 x1 c)) (fst (scale_full2 p' ti' x0' x1' c')) /\
  sv (snd (scale_full1 p ti x0 x1 c)) (snd (scale_full2 p' ti' x0' x1' c')).
Proof.
intros p p' Hp ti ti' Ht x0 x0' x1 x1' c c' H0 H1 Hc. unfold IeeeWith.mul_pow2_2_full_with.
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
intros p p' Hp cx cx' rx rx' c c' Hx Hr Hc. unfold IeeeWith.ball_mul_pow2_1_with. cbv zeta.
cbn [fst snd]. split; same_ops.
Qed.

Lemma ball_mul_pow2_1_full_same :
  forall p p' : float -> float -> float, same_ps p p' ->
  forall cx cx' rx rx' c c' : float, sv cx cx' -> sv rx rx' -> sv c c' ->
  sv (fst (ball_full1 p cx rx c)) (fst (ball_full2 p' cx' rx' c')) /\
  sv (snd (ball_full1 p cx rx c)) (snd (ball_full2 p' cx' rx' c')).
Proof.
intros p p' Hp cx cx' rx rx' c c' Hx Hr Hc. unfold IeeeWith.ball_mul_pow2_1_full_with.
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
unfold IeeeWith.ball_mul_pow2_2_with. cbv zeta.
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
unfold IeeeWith.ball_mul_pow2_2_full_with.
generalize (ball_mul_pow2_2_same p p' Hp cx0 cx0' cx1 cx1' rx rx' c c' H0 H1 Hr Hc).
destruct (bball1 p cx0 cx1 rx c) as [[cz0 cz1] rz].
destruct (bball2 p' cx0' cx1' rx' c') as [[cz0' cz1'] rz'].
cbn [fst snd]. intros [Hz0 [Hz1 Hrz]]. split; [|split]; same_ops.
Qed.

Lemma mul_pow2_2_pair :
  forall p p' : float -> float -> float, same_ps p p' ->
  forall x0 x0' x1 x1' c c' : float, sv x0 x0' -> sv x1 x1' -> sv c c' ->
  same_pair (scale1 p x0 x1 c) (scale2 p' x0' x1' c').
Proof.
intros p p' Hp x0 x0' x1 x1' c c' H0 H1 Hc. apply same_pair_fst_snd.
now apply mul_pow2_2_same.
Qed.

(* The others, in the order of IeeeWith.v. *)
Lemma mul_1_1_same :
  forall p p' : float -> float -> float, same_ps p p' ->
  forall a a' b b' : float, sv a a' -> sv b b' -> sv (w_mul_1_1 p a b) (w_mul_1_1 p' a' b').
Proof. intros p p' Hp a a' b b' Ha Hb. cbv beta delta [IeeeWith.mul_1_1_with]. lockstep fail. Qed.

Lemma axpy_entry_step_1_same :
  forall p p' : float -> float -> float, same_ps p p' ->
  forall g g' : float -> float, same_un g g' ->
  forall a a' x x' y y' : float, sv a a' -> sv x x' -> sv y y' ->
  sv (w_axpy_entry_step_1 p g a x y) (w_axpy_entry_step_1' p' g' a' x' y').
Proof.
intros p p' Hp g g' Hg a a' x x' y y' Ha Hx Hy. cbv beta delta [IeeeWith.axpy_entry_step_1_with].
lockstep ltac:(first [apply mul_1_1_same; leaf | apply add_1_1_same; leaf]).
Qed.

Lemma axpy_step_1_same :
  forall p p' : float -> float -> float, same_ps p p' ->
  forall a a' x x' y y' : float, sv a a' -> sv x x' -> sv y y' ->
  sv (w_axpy_step_1 p a x y) (w_axpy_step_1' p' a' x' y').
Proof.
intros p p' Hp a a' x x' y y' Ha Hx Hy. cbv beta delta [IeeeWith.axpy_step_1_with].
lockstep ltac:(first [apply mul_1_1_same; leaf | apply add_1_1_same; leaf]).
Qed.

Lemma interval_mid_rad_1_same :
  forall p p' : float -> float -> float, same_ps p p' ->
  forall xl xl' xu xu' : float, sv xl xl' -> sv xu xu' ->
  same_pair (w_interval_mid_rad_1 p xl xu) (w_interval_mid_rad_1' p' xl' xu').
Proof.
intros p p' Hp xl xl' xu xu' Hl Hu. cbv beta delta [IeeeWith.interval_mid_rad_1_with].
lockstep ltac:(apply sub_up_1_same; leaf).
Qed.

Lemma interval_to_ball_1_same :
  forall p p' : float -> float -> float, same_ps p p' ->
  forall xl xl' xu xu' : float, sv xl xl' -> sv xu xu' ->
  same_pair (w_interval_to_ball_1 p xl xu) (w_interval_to_ball_1' p' xl' xu').
Proof.
intros p p' Hp xl xl' xu xu' Hl Hu. cbv beta delta [IeeeWith.interval_to_ball_1_with].
lockstep ltac:(apply interval_mid_rad_1_same; leaf).
Qed.

Lemma ball_from_interval_1_same :
  forall p p' : float -> float -> float, same_ps p p' ->
  forall g g' : float -> float, same_un g g' ->
  forall lo lo' hi hi' : float, sv lo lo' -> sv hi hi' ->
  same_pair (w_ball_from_interval_1 p g lo hi) (w_ball_from_interval_1' p' g' lo' hi').
Proof.
intros p p' Hp g g' Hg lo lo' hi hi' Hl Hh. cbv beta delta [IeeeWith.ball_from_interval_1_with].
lockstep ltac:(apply interval_to_ball_1_same; leaf).
Qed.

Lemma ball_from_interval_2_same :
  forall p p' : float -> float -> float, same_ps p p' ->
  forall g g' : float -> float, same_un g g' ->
  forall lo lo' hi hi' : float, sv lo lo' -> sv hi hi' ->
  same_triple (w_ball_from_interval_2 p g lo hi) (w_ball_from_interval_2' p' g' lo' hi').
Proof.
intros p p' Hp g g' Hg lo lo' hi hi' Hl Hh. cbv beta delta [IeeeWith.ball_from_interval_2_with].
lockstep ltac:(first [apply two_sum_ord_same; leaf | apply add_up_1_same; leaf]).
Qed.

Lemma ball_hull_1_same :
  forall p p' : float -> float -> float, same_ps p p' ->
  forall cx cx' rx rx' cy cy' ry ry' : float,
  sv cx cx' -> sv rx rx' -> sv cy cy' -> sv ry ry' ->
  same_pair (w_ball_hull_1 p cx rx cy ry) (w_ball_hull_1' p' cx' rx' cy' ry').
Proof.
intros p p' Hp cx cx' rx rx' cy cy' ry ry' Hcx Hrx Hcy Hry.
cbv beta delta [IeeeWith.ball_hull_1_with].
lockstep ltac:(first [ apply ball_to_interval_1_same; leaf | apply interval_hull_1_same; leaf
                     | apply interval_to_ball_1_same; leaf ]).
Qed.

Lemma ball_intersection_1_same :
  forall p p' : float -> float -> float, same_ps p p' ->
  forall cx cx' rx rx' cy cy' ry ry' : float,
  sv cx cx' -> sv rx rx' -> sv cy cy' -> sv ry ry' ->
  same_pair (w_ball_intersection_1 p cx rx cy ry) (w_ball_intersection_1' p' cx' rx' cy' ry').
Proof.
intros p p' Hp cx cx' rx rx' cy cy' ry ry' Hcx Hrx Hcy Hry.
cbv beta delta [IeeeWith.ball_intersection_1_with].
lockstep ltac:(first [ apply sub_down_1_same; leaf | apply add_up_1_same; leaf
                     | apply interval_to_ball_1_same; leaf ]).
Qed.

Lemma bound_dot_1_same :
  forall p p' : float -> float -> float, same_ps p p' ->
  forall m m' : float, sv m m' -> same_pair_mask (w_bound_dot_1 p m) (w_bound_dot_1' p' m').
Proof. intros p p' Hp m m' Hm. cbv beta delta [IeeeWith.bound_dot_1_with]. lockstep fail. Qed.

Lemma bound_dot_2_same :
  forall p p' : float -> float -> float, same_ps p p' ->
  forall m m' : float, sv m m' -> same_pair_mask (w_bound_dot_2 p m) (w_bound_dot_2' p' m').
Proof. intros p p' Hp m m' Hm. cbv beta delta [IeeeWith.bound_dot_2_with]. lockstep fail. Qed.

Lemma bound_sum_1_same :
  forall p p' : float -> float -> float, same_ps p p' ->
  forall m m' : float, sv m m' -> same_value_mask (w_bound_sum_1 p m) (w_bound_sum_1' p' m').
Proof. intros p p' Hp m m' Hm. cbv beta delta [IeeeWith.bound_sum_1_with]. lockstep fail. Qed.

Lemma bound_sum_2_same :
  forall p p' : float -> float -> float, same_ps p p' ->
  forall m m' : float, sv m m' -> same_value_mask (w_bound_sum_2 p m) (w_bound_sum_2' p' m').
Proof. intros p p' Hp m m' Hm. cbv beta delta [IeeeWith.bound_sum_2_with]. lockstep fail. Qed.

(* The mask ex is an operand: the same in both executions. *)
Lemma bv_mul_pow2_radius_same :
  forall p p' : float -> float -> float, same_ps p p' ->
  forall (m m' : float) (ex : bool) (rx rx' c c' : float), sv m m' -> sv rx rx' -> sv c c' ->
  sv (w_bv_mul_pow2_radius p m ex rx c) (w_bv_mul_pow2_radius' p' m' ex rx' c').
Proof.
intros p p' Hp m m' ex rx rx' c c' Hm Hr Hc. cbv beta delta [IeeeWith.bv_mul_pow2_radius_with].
lockstep fail.
Qed.

Lemma bv_mul_pow2_step_1_same :
  forall p p' : float -> float -> float, same_ps p p' ->
  forall x x' c c' : float, sv x x' -> sv c c' ->
  same_value_mask (w_bv_mul_pow2_step_1 p x c) (w_bv_mul_pow2_step_1' p' x' c').
Proof.
intros p p' Hp x x' c c' Hx Hc. cbv beta delta [IeeeWith.bv_mul_pow2_step_1_with].
lockstep fail.
Qed.

Lemma interval_split_1_same :
  forall p p' : float -> float -> float, same_ps p p' ->
  forall xl xl' xu xu' : float, sv xl xl' -> sv xu xu' ->
  same_four (w_interval_split_1 p xl xu) (w_interval_split_1' p' xl' xu').
Proof.
intros p p' Hp xl xl' xu xu' Hl Hu. cbv beta delta [IeeeWith.interval_split_1_with].
lockstep ltac:(apply interval_mid_rad_1_same; leaf).
Qed.

Lemma mul_pow2_step_1_same :
  forall p p' : float -> float -> float, same_ps p p' ->
  forall x x' c c' : float, sv x x' -> sv c c' ->
  sv (w_mul_pow2_step_1 p x c) (w_mul_pow2_step_1 p' x' c').
Proof.
intros p p' Hp x x' c c' Hx Hc. cbv beta delta [IeeeWith.mul_pow2_step_1_with].
lockstep fail.
Qed.

Lemma rmul_same :
  forall p p' : float -> float -> float, same_ps p p' ->
  forall a a' b b' : float, sv a a' -> sv b b' -> sv (w_rmul p a b) (w_rmul p' a' b').
Proof. intros p p' Hp a a' b b' Ha Hb. cbv beta delta [IeeeWith.rmul_with]. lockstep fail. Qed.

Lemma scale_step_1_same :
  forall p p' : float -> float -> float, same_ps p p' ->
  forall x x' a a' : float, sv x x' -> sv a a' ->
  sv (w_scale_step_1 p x a) (w_scale_step_1 p' x' a').
Proof.
intros p p' Hp x x' a a' Hx Ha. cbv beta delta [IeeeWith.scale_step_1_with].
lockstep ltac:(apply mul_1_1_same; leaf).
Qed.

Lemma bv_mul_pow2_step_2_same :
  forall p p' : float -> float -> float, same_ps p p' ->
  forall x0 x0' x1 x1' c c' : float, sv x0 x0' -> sv x1 x1' -> sv c c' ->
  same_pair_mask (w_bv_mul_pow2_step_2 p x0 x1 c) (w_bv_mul_pow2_step_2' p' x0' x1' c').
Proof.
intros p p' Hp x0 x0' x1 x1' c c' H0 H1 Hc. cbv beta delta [IeeeWith.bv_mul_pow2_step_2_with].
lockstep ltac:(apply fast_two_sum_pair; leaf).
Qed.

Lemma interval_split_2_same :
  forall p p' : float -> float -> float, same_ps p p' ->
  forall xl0 xl0' xl1 xl1' xu0 xu0' xu1 xu1' : float,
  sv xl0 xl0' -> sv xl1 xl1' -> sv xu0 xu0' -> sv xu1 xu1' ->
  same_eight (w_interval_split_2 p xl0 xl1 xu0 xu1) (w_interval_split_2' p' xl0' xl1' xu0' xu1').
Proof.
intros p p' Hp xl0 xl0' xl1 xl1' xu0 xu0' xu1 xu1' Hl0 Hl1 Hu0 Hu1.
cbv beta delta [IeeeWith.interval_split_2_with].
lockstep ltac:(first [ apply mul_pow2_2_pair; leaf | apply add_2_2_same; leaf
                     | apply lt_2_2_same; leaf ]).
Qed.

Lemma mul_pow2_step_2_same :
  forall p p' : float -> float -> float, same_ps p p' ->
  forall x0 x0' x1 x1' c c' : float, sv x0 x0' -> sv x1 x1' -> sv c c' ->
  same_pair (w_mul_pow2_step_2 p x0 x1 c) (w_mul_pow2_step_2' p' x0' x1' c').
Proof.
intros p p' Hp x0 x0' x1 x1' c c' H0 H1 Hc. cbv beta delta [IeeeWith.mul_pow2_step_2_with].
lockstep ltac:(apply mul_pow2_2_pair; leaf).
Qed.

(** ** The kernels without a product, for any two guards and two forms of times_inf of the same
    value *)

Lemma acc_add_1_same :
  forall g g' : float -> float, same_un g g' ->
  forall s s' a a' x x' : float, sv s s' -> sv a a' -> sv x x' ->
  same_pair (w_acc_add_1 g s a x) (w_acc_add_1' g' s' a' x').
Proof.
intros g g' Hg s s' a a' x x' Hs Ha Hx. cbv beta delta [IeeeWith.acc_add_1_with].
lockstep fail.
Qed.

Lemma add_down_entry_same :
  forall g g' : float -> float, same_un g g' ->
  forall a a' b b' : float, sv a a' -> sv b b' ->
  sv (w_add_down_entry g a b) (w_add_down_entry' g' a' b').
Proof.
intros g g' Hg a a' b b' Ha Hb. cbv beta delta [IeeeWith.add_down_entry_with].
lockstep ltac:(apply add_down_1_same; leaf).
Qed.

Lemma add_entry_step_1_same :
  forall g g' : float -> float, same_un g g' ->
  forall x x' y y' : float, sv x x' -> sv y y' ->
  sv (w_add_entry_step_1 g x y) (w_add_entry_step_1' g' x' y').
Proof.
intros g g' Hg x x' y y' Hx Hy. cbv beta delta [IeeeWith.add_entry_step_1_with].
lockstep ltac:(apply add_1_1_same; leaf).
Qed.

Lemma add_up_entry_same :
  forall g g' : float -> float, same_un g g' ->
  forall a a' b b' : float, sv a a' -> sv b b' ->
  sv (w_add_up_entry g a b) (w_add_up_entry' g' a' b').
Proof.
intros g g' Hg a a' b b' Ha Hb. cbv beta delta [IeeeWith.add_up_entry_with].
lockstep ltac:(apply add_up_1_same; leaf).
Qed.

Lemma ball_contains_point_1_same :
  forall g g' : float -> float, same_un g g' ->
  forall c c' r r' t t' : float, sv c c' -> sv r r' -> sv t t' ->
  (w_ball_contains_point_1 g c r t) = (w_ball_contains_point_1' g' c' r' t').
Proof.
intros g g' Hg c c' r r' t t' Hc Hr Ht. cbv beta delta [IeeeWith.ball_contains_point_1_with].
lockstep ltac:(first [apply two_sum_ord_same; leaf | apply abs_2_same; leaf | apply le_2_1_same;
  leaf]).
Qed.

Lemma ball_make_1_same :
  forall g g' : float -> float, same_un g g' ->
  forall c c' r r' : float, sv c c' -> sv r r' ->
  same_pair (w_ball_make_1 g c r) (w_ball_make_1' g' c' r').
Proof.
intros g g' Hg c c' r r' Hc Hr. cbv beta delta [IeeeWith.ball_make_1_with].
lockstep fail.
Qed.

Lemma bv_center_entry_1_same :
  forall g g' : float -> float, same_un g g' ->
  forall c c' : float, sv c c' ->
  sv (w_bv_center_entry_1 g c) (w_bv_center_entry_1 g' c').
Proof.
intros g g' Hg c c' Hc. cbv beta delta [IeeeWith.bv_center_entry_1_with].
lockstep fail.
Qed.

Lemma bv_make_radius_same :
  forall g g' : float -> float, same_un g g' ->
  forall m m' r r' : float, sv m m' -> sv r r' ->
  sv (w_bv_make_radius g m r) (w_bv_make_radius' g' m' r').
Proof.
intros g g' Hg m m' r r' Hm Hr. cbv beta delta [IeeeWith.bv_make_radius_with].
lockstep fail.
Qed.

Lemma fast_two_sum_entry_same :
  forall g g' : float -> float, same_un g g' ->
  forall a a' b b' : float, sv a a' -> sv b b' ->
  same_pair (w_fast_two_sum_entry g a b) (w_fast_two_sum_entry' g' a' b').
Proof.
intros g g' Hg a a' b b' Ha Hb. cbv beta delta [IeeeWith.fast_two_sum_entry_with].
lockstep ltac:(apply fast_two_sum_pair; leaf).
Qed.

Lemma interval_make_1_same :
  forall g g' : float -> float, same_un g g' ->
  forall lo lo' hi hi' : float, sv lo lo' -> sv hi hi' ->
  same_pair (w_interval_make_1 g lo hi) (w_interval_make_1' g' lo' hi').
Proof.
intros g g' Hg lo lo' hi hi' Hlo Hhi. cbv beta delta [IeeeWith.interval_make_1_with].
lockstep fail.
Qed.

Lemma make_2_same :
  forall g g' : float -> float, same_un g g' ->
  forall a a' : float, sv a a' ->
  same_pair (w_make_2 g a) (w_make_2 g' a').
Proof.
intros g g' Hg a a' Ha. cbv beta delta [IeeeWith.make_2_with].
lockstep fail.
Qed.

Lemma radd_entry_same :
  forall g g' : float -> float, same_un g g' ->
  forall a a' b b' : float, sv a a' -> sv b b' ->
  sv (w_radd_entry g a b) (w_radd_entry' g' a' b').
Proof.
intros g g' Hg a a' b b' Ha Hb. cbv beta delta [IeeeWith.radd_entry_with].
lockstep ltac:(apply radd_same; leaf).
Qed.

Lemma sub_down_entry_same :
  forall g g' : float -> float, same_un g g' ->
  forall a a' b b' : float, sv a a' -> sv b b' ->
  sv (w_sub_down_entry g a b) (w_sub_down_entry' g' a' b').
Proof.
intros g g' Hg a a' b b' Ha Hb. cbv beta delta [IeeeWith.sub_down_entry_with].
lockstep ltac:(apply sub_down_1_same; leaf).
Qed.

Lemma sub_entry_step_1_same :
  forall g g' : float -> float, same_un g g' ->
  forall x x' y y' : float, sv x x' -> sv y y' ->
  sv (w_sub_entry_step_1 g x y) (w_sub_entry_step_1' g' x' y').
Proof.
intros g g' Hg x x' y y' Hx Hy. cbv beta delta [IeeeWith.sub_entry_step_1_with].
lockstep ltac:(apply sub_1_1_same; leaf).
Qed.

Lemma sub_up_entry_same :
  forall g g' : float -> float, same_un g g' ->
  forall a a' b b' : float, sv a a' -> sv b b' ->
  sv (w_sub_up_entry g a b) (w_sub_up_entry' g' a' b').
Proof.
intros g g' Hg a a' b b' Ha Hb. cbv beta delta [IeeeWith.sub_up_entry_with].
lockstep ltac:(apply sub_up_1_same; leaf).
Qed.

Lemma sum_entry_step_1_same :
  forall g g' : float -> float, same_un g g' ->
  forall s s' x x' : float, sv s s' -> sv x x' ->
  sv (w_sum_entry_step_1 g s x) (w_sum_entry_step_1' g' s' x').
Proof.
intros g g' Hg s s' x x' Hs Hx. cbv beta delta [IeeeWith.sum_entry_step_1_with].
lockstep fail.
Qed.

Lemma two_sum_entry_same :
  forall g g' : float -> float, same_un g g' ->
  forall a a' b b' : float, sv a a' -> sv b b' ->
  same_pair (w_two_sum_entry g a b) (w_two_sum_entry' g' a' b').
Proof.
intros g g' Hg a a' b b' Ha Hb. cbv beta delta [IeeeWith.two_sum_entry_with].
lockstep ltac:(apply two_sum_same; leaf).
Qed.

Lemma acc_add_2_same :
  forall g g' : float -> float, same_un g g' ->
forall s0 s0' s1 s1' a a' x0 x0' x1 x1' : float, sv s0 s0' -> sv s1 s1' -> sv a a' -> sv x0 x0' ->
    sv x1 x1' ->
  same_triple (w_acc_add_2 g s0 s1 a x0 x1) (w_acc_add_2' g' s0' s1' a' x0' x1').
Proof.
intros g g' Hg s0 s0' s1 s1' a a' x0 x0' x1 x1' Hs0 Hs1 Ha Hx0 Hx1. cbv beta delta
  [IeeeWith.acc_add_2_with].
lockstep ltac:(apply add_2_2_same; leaf).
Qed.

Lemma add_2_1_same :
  forall g g' : float -> float, same_un g g' ->
  forall x0 x0' x1 x1' a a' : float, sv x0 x0' -> sv x1 x1' -> sv a a' ->
  same_pair (w_add_2_1 g x0 x1 a) (w_add_2_1' g' x0' x1' a').
Proof.
intros g g' Hg x0 x0' x1 x1' a a' Hx0 Hx1 Ha. cbv beta delta [IeeeWith.add_2_1_with].
lockstep ltac:(first [apply two_sum_same; leaf | apply fast_two_sum_pair; leaf]).
Qed.

Lemma add_2_1_full_same :
  forall g g' : float -> float, same_un g g' ->
  forall ti ti' : float -> float, same_un ti ti' ->
  forall x0 x0' x1 x1' a a' : float, sv x0 x0' -> sv x1 x1' -> sv a a' ->
  same_pair (w_add_2_1_full g ti x0 x1 a) (w_add_2_1_full' g' ti' x0' x1' a').
Proof.
intros g g' Hg ti ti' Ht x0 x0' x1 x1' a a' Hx0 Hx1 Ha. cbv beta delta
  [IeeeWith.add_2_1_full_with].
lockstep ltac:(apply add_2_1_same; leaf).
Qed.

Lemma add_2_2_full_same :
  forall ti ti' : float -> float, same_un ti ti' ->
  forall x0 x0' x1 x1' y0 y0' y1 y1' : float, sv x0 x0' -> sv x1 x1' -> sv y0 y0' -> sv y1 y1' ->
  same_pair (w_add_2_2_full ti x0 x1 y0 y1) (w_add_2_2_full' ti' x0' x1' y0' y1').
Proof.
intros ti ti' Ht x0 x0' x1 x1' y0 y0' y1 y1' Hx0 Hx1 Hy0 Hy1. cbv beta delta
  [IeeeWith.add_2_2_full_with].
lockstep ltac:(apply add_2_2_same; leaf).
Qed.

Lemma add_entry_step_2_same :
  forall g g' : float -> float, same_un g g' ->
  forall x0 x0' x1 x1' y0 y0' y1 y1' : float, sv x0 x0' -> sv x1 x1' -> sv y0 y0' -> sv y1 y1' ->
  same_pair (w_add_entry_step_2 g x0 x1 y0 y1) (w_add_entry_step_2' g' x0' x1' y0' y1').
Proof.
intros g g' Hg x0 x0' x1 x1' y0 y0' y1 y1' Hx0 Hx1 Hy0 Hy1. cbv beta delta
  [IeeeWith.add_entry_step_2_with].
lockstep ltac:(apply add_2_2_same; leaf).
Qed.

Lemma add_fast_2_2_full_same :
  forall ti ti' : float -> float, same_un ti ti' ->
  forall x0 x0' x1 x1' y0 y0' y1 y1' : float, sv x0 x0' -> sv x1 x1' -> sv y0 y0' -> sv y1 y1' ->
  same_pair (w_add_fast_2_2_full ti x0 x1 y0 y1) (w_add_fast_2_2_full' ti' x0' x1' y0' y1').
Proof.
intros ti ti' Ht x0 x0' x1 x1' y0 y0' y1 y1' Hx0 Hx1 Hy0 Hy1. cbv beta delta
  [IeeeWith.add_fast_2_2_full_with].
lockstep ltac:(apply add_fast_2_2_same; leaf).
Qed.

Lemma ball_make_2_same :
  forall g g' : float -> float, same_un g g' ->
  forall c0 c0' c1 c1' r r' : float, sv c0 c0' -> sv c1 c1' -> sv r r' ->
  same_triple (w_ball_make_2 g c0 c1 r) (w_ball_make_2' g' c0' c1' r').
Proof.
intros g g' Hg c0 c0' c1 c1' r r' Hc0 Hc1 Hr. cbv beta delta [IeeeWith.ball_make_2_with].
lockstep fail.
Qed.

Lemma make_2_limbs_same :
  forall g g' : float -> float, same_un g g' ->
  forall h h' l l' : float, sv h h' -> sv l l' ->
  same_pair (w_make_2_limbs g h l) (w_make_2_limbs g' h' l').
Proof.
intros g g' Hg h h' l l' Hh Hl. cbv beta delta [IeeeWith.make_2_limbs_with].
lockstep fail.
Qed.

Lemma sub_1_2_same :
  forall g g' : float -> float, same_un g g' ->
  forall a a' y0 y0' y1 y1' : float, sv a a' -> sv y0 y0' -> sv y1 y1' ->
  same_pair (w_sub_1_2 g a y0 y1) (w_sub_1_2' g' a' y0' y1').
Proof.
intros g g' Hg a a' y0 y0' y1 y1' Ha Hy0 Hy1. cbv beta delta [IeeeWith.sub_1_2_with].
lockstep ltac:(apply add_2_1_same; leaf).
Qed.

Lemma sub_1_2_full_same :
  forall g g' : float -> float, same_un g g' ->
  forall ti ti' : float -> float, same_un ti ti' ->
  forall a a' y0 y0' y1 y1' : float, sv a a' -> sv y0 y0' -> sv y1 y1' ->
  same_pair (w_sub_1_2_full g ti a y0 y1) (w_sub_1_2_full' g' ti' a' y0' y1').
Proof.
intros g g' Hg ti ti' Ht a a' y0 y0' y1 y1' Ha Hy0 Hy1. cbv beta delta
  [IeeeWith.sub_1_2_full_with].
lockstep ltac:(apply sub_1_2_same; leaf).
Qed.

Lemma sub_2_1_same :
  forall g g' : float -> float, same_un g g' ->
  forall x0 x0' x1 x1' a a' : float, sv x0 x0' -> sv x1 x1' -> sv a a' ->
  same_pair (w_sub_2_1 g x0 x1 a) (w_sub_2_1' g' x0' x1' a').
Proof.
intros g g' Hg x0 x0' x1 x1' a a' Hx0 Hx1 Ha. cbv beta delta [IeeeWith.sub_2_1_with].
lockstep ltac:(apply add_2_1_same; leaf).
Qed.

Lemma sub_2_1_full_same :
  forall g g' : float -> float, same_un g g' ->
  forall ti ti' : float -> float, same_un ti ti' ->
  forall x0 x0' x1 x1' a a' : float, sv x0 x0' -> sv x1 x1' -> sv a a' ->
  same_pair (w_sub_2_1_full g ti x0 x1 a) (w_sub_2_1_full' g' ti' x0' x1' a').
Proof.
intros g g' Hg ti ti' Ht x0 x0' x1 x1' a a' Hx0 Hx1 Ha. cbv beta delta
  [IeeeWith.sub_2_1_full_with].
lockstep ltac:(apply sub_2_1_same; leaf).
Qed.

Lemma sub_2_2_full_same :
  forall ti ti' : float -> float, same_un ti ti' ->
  forall x0 x0' x1 x1' y0 y0' y1 y1' : float, sv x0 x0' -> sv x1 x1' -> sv y0 y0' -> sv y1 y1' ->
  same_pair (w_sub_2_2_full ti x0 x1 y0 y1) (w_sub_2_2_full' ti' x0' x1' y0' y1').
Proof.
intros ti ti' Ht x0 x0' x1 x1' y0 y0' y1 y1' Hx0 Hx1 Hy0 Hy1. cbv beta delta
  [IeeeWith.sub_2_2_full_with].
lockstep ltac:(apply sub_2_2_same; leaf).
Qed.

Lemma sub_entry_step_2_same :
  forall g g' : float -> float, same_un g g' ->
  forall x0 x0' x1 x1' y0 y0' y1 y1' : float, sv x0 x0' -> sv x1 x1' -> sv y0 y0' -> sv y1 y1' ->
  same_pair (w_sub_entry_step_2 g x0 x1 y0 y1) (w_sub_entry_step_2' g' x0' x1' y0' y1').
Proof.
intros g g' Hg x0 x0' x1 x1' y0 y0' y1 y1' Hx0 Hx1 Hy0 Hy1. cbv beta delta
  [IeeeWith.sub_entry_step_2_with].
lockstep ltac:(apply sub_2_2_same; leaf).
Qed.

Lemma sum_entry_step_2_same :
  forall g g' : float -> float, same_un g g' ->
  forall s0 s0' s1 s1' x0 x0' x1 x1' : float, sv s0 s0' -> sv s1 s1' -> sv x0 x0' -> sv x1 x1' ->
  same_pair (w_sum_entry_step_2 g s0 s1 x0 x1) (w_sum_entry_step_2' g' s0' s1' x0' x1').
Proof.
intros g g' Hg s0 s0' s1 s1' x0 x0' x1 x1' Hs0 Hs1 Hx0 Hx1. cbv beta delta
  [IeeeWith.sum_entry_step_2_with].
lockstep ltac:(apply add_2_2_same; leaf).
Qed.

Lemma sum_fast_entry_step_2_same :
  forall g g' : float -> float, same_un g g' ->
  forall s0 s0' s1 s1' x0 x0' x1 x1' : float, sv s0 s0' -> sv s1 s1' -> sv x0 x0' -> sv x1 x1' ->
  same_pair (w_sum_fast_entry_step_2 g s0 s1 x0 x1) (w_sum_fast_entry_step_2' g' s0' s1' x0' x1').
Proof.
intros g g' Hg s0 s0' s1 s1' x0 x0' x1 x1' Hs0 Hs1 Hx0 Hx1. cbv beta delta
  [IeeeWith.sum_fast_entry_step_2_with].
lockstep ltac:(apply add_fast_2_2_same; leaf).
Qed.

(** ** Constant evaluation against the generated kernel, on the same operands *)

(* On the left the listing at the operations of constant evaluation, prod_ce, guard_ce and
   times_inf_ce (the execution of constant evaluation), on the right the generated IEEE model
   of the kernel (the execution of run time), on the same operands, with any NaN functions on
   either side. Each theorem is the statement K_two_executions_spec of proofs/gen/IeeeWith.v,
   which proofs/gen/IeeeAudit.v checks. *)
Let Hmp : same_ps prod_ce prod'.
Proof. exact (prod_ce_products prec emax nan_fma' nan_mult). Qed.

Let Hgc : same_un guard_ce guard'.
Proof. exact (guard_ce_unary prec emax nan_plus'). Qed.

Let Htc : same_un times_inf_ce times_inf'.
Proof. exact (times_inf_ce_unary prec emax nan_mult' nan_const). Qed.

(* The eight kernels proved first. *)
Theorem split_two_executions :
  forall a : float,
  let '(ah, al) := split1 prod_ce a in
  let '(bh, bl) := IeeeModel.split prec emax nan_plus' nan_minus' nan_fma' a in
  sv ah bh /\ sv al bl.
Proof.
intros a. rewrite <- (split_with_prod prec emax nan_plus' nan_minus' nan_fma' a).
generalize (split_same prod_ce prod' Hmp a a (same_refl prec emax a)).
destruct (split1 prod_ce a) as [ah al]. destruct (split2 prod' a) as [bh bl].
exact (fun H => H).
Qed.

Theorem two_prod_dekker_two_executions :
  forall a b : float,
  let '(p, e) := dekker1 prod_ce a b in
  let '(q, f) := IeeeModel.two_prod_dekker prec emax nan_plus' nan_minus' nan_fma' a b in
  sv p q /\ sv e f.
Proof.
intros a b. rewrite <- (two_prod_dekker_with_prod prec emax nan_plus' nan_minus' nan_fma' a b).
generalize (two_prod_dekker_same prod_ce prod' Hmp a a b b
              (same_refl prec emax a) (same_refl prec emax b)).
destruct (dekker1 prod_ce a b) as [p e]. destruct (dekker2 prod' a b) as [q f].
exact (fun H => H).
Qed.

Theorem mul_pow2_2_two_executions :
  forall x0 x1 c : float,
  let '(z0, z1) := scale1 prod_ce x0 x1 c in
  let '(w0, w1) := IeeeModel.mul_pow2_2 prec emax nan_plus' nan_minus' nan_fma' x0 x1 c in
  sv z0 w0 /\ sv z1 w1.
Proof.
intros x0 x1 c.
rewrite <- (mul_pow2_2_with_prod prec emax nan_plus' nan_minus' nan_fma' x0 x1 c).
generalize (mul_pow2_2_same prod_ce prod' Hmp x0 x0 x1 x1 c c (same_refl prec emax x0)
              (same_refl prec emax x1) (same_refl prec emax c)).
destruct (scale1 prod_ce x0 x1 c) as [z0 z1]. destruct (scale2 prod' x0 x1 c) as [w0 w1].
exact (fun H => H).
Qed.

Theorem mul_pow2_2_full_two_executions :
  forall x0 x1 c : float,
  let '(z0, z1) := scale_full1 prod_ce times_inf_ce x0 x1 c in
  let '(w0, w1) := IeeeModel.mul_pow2_2_full prec emax nan_plus' nan_minus' nan_abs' nan_fma'
                     nan_mult' x0 x1 c in
  sv z0 w0 /\ sv z1 w1.
Proof.
intros x0 x1 c.
rewrite <- (mul_pow2_2_full_with_prod prec emax nan_plus' nan_minus' nan_abs' nan_fma'
              nan_mult' x0 x1 c).
generalize (mul_pow2_2_full_same prod_ce prod' Hmp times_inf_ce times_inf' Htc x0 x0 x1 x1 c c
              (same_refl prec emax x0) (same_refl prec emax x1) (same_refl prec emax c)).
destruct (scale_full1 prod_ce times_inf_ce x0 x1 c) as [z0 z1].
destruct (scale_full2 prod' times_inf' x0 x1 c) as [w0 w1].
exact (fun H => H).
Qed.

Theorem ball_mul_pow2_1_two_executions :
  forall cx rx c : float,
  let '(cz, rz) := ball1 prod_ce cx rx c in
  let '(cw, rw) := IeeeModel.ball_mul_pow2_1 prec emax nan_abs' nan_fma' cx rx c in
  sv cz cw /\ sv rz rw.
Proof.
intros cx rx c. rewrite <- (ball_mul_pow2_1_with_prod prec emax nan_abs' nan_fma' cx rx c).
generalize (ball_mul_pow2_1_same prod_ce prod' Hmp cx cx rx rx c c (same_refl prec emax cx)
              (same_refl prec emax rx) (same_refl prec emax c)).
destruct (ball1 prod_ce cx rx c) as [cz rz]. destruct (ball2 prod' cx rx c) as [cw rw].
exact (fun H => H).
Qed.

Theorem ball_mul_pow2_1_full_two_executions :
  forall cx rx c : float,
  let '(cz, rz) := ball_full1 prod_ce cx rx c in
  let '(cw, rw) := IeeeModel.ball_mul_pow2_1_full prec emax nan_abs' nan_fma' cx rx c in
  sv cz cw /\ sv rz rw.
Proof.
intros cx rx c.
rewrite <- (ball_mul_pow2_1_full_with_prod prec emax nan_abs' nan_fma' cx rx c).
generalize (ball_mul_pow2_1_full_same prod_ce prod' Hmp cx cx rx rx c c (same_refl prec emax cx)
              (same_refl prec emax rx) (same_refl prec emax c)).
destruct (ball_full1 prod_ce cx rx c) as [cz rz]. destruct (ball_full2 prod' cx rx c) as [cw rw].
exact (fun H => H).
Qed.

Theorem ball_mul_pow2_2_two_executions :
  forall cx0 cx1 rx c : float,
  let '(cz0, cz1, rz) := bball1 prod_ce cx0 cx1 rx c in
  let '(cw0, cw1, rw) := IeeeModel.ball_mul_pow2_2 prec emax nan_plus' nan_minus' nan_abs'
                           nan_fma' cx0 cx1 rx c in
  sv cz0 cw0 /\ sv cz1 cw1 /\ sv rz rw.
Proof.
intros cx0 cx1 rx c.
rewrite <- (ball_mul_pow2_2_with_prod prec emax nan_plus' nan_minus' nan_abs' nan_fma'
              cx0 cx1 rx c).
generalize (ball_mul_pow2_2_same prod_ce prod' Hmp cx0 cx0 cx1 cx1 rx rx c c
              (same_refl prec emax cx0) (same_refl prec emax cx1) (same_refl prec emax rx)
              (same_refl prec emax c)).
destruct (bball1 prod_ce cx0 cx1 rx c) as [[cz0 cz1] rz].
destruct (bball2 prod' cx0 cx1 rx c) as [[cw0 cw1] rw].
exact (fun H => H).
Qed.

Theorem ball_mul_pow2_2_full_two_executions :
  forall cx0 cx1 rx c : float,
  let '(cz0, cz1, rz) := bball_full1 prod_ce cx0 cx1 rx c in
  let '(cw0, cw1, rw) := IeeeModel.ball_mul_pow2_2_full prec emax nan_plus' nan_minus' nan_abs'
                           nan_fma' cx0 cx1 rx c in
  sv cz0 cw0 /\ sv cz1 cw1 /\ sv rz rw.
Proof.
intros cx0 cx1 rx c.
rewrite <- (ball_mul_pow2_2_full_with_prod prec emax nan_plus' nan_minus' nan_abs' nan_fma'
              cx0 cx1 rx c).
generalize (ball_mul_pow2_2_full_same prod_ce prod' Hmp cx0 cx0 cx1 cx1 rx rx c c
              (same_refl prec emax cx0) (same_refl prec emax cx1) (same_refl prec emax rx)
              (same_refl prec emax c)).
destruct (bball_full1 prod_ce cx0 cx1 rx c) as [[cz0 cz1] rz].
destruct (bball_full2 prod' cx0 cx1 rx c) as [[cw0 cw1] rw].
exact (fun H => H).
Qed.

(* The others, in the order of IeeeWith.v. Each is its lemma K_same on the plain product and
   the fused one, on the same operands. *)
Theorem mul_1_1_two_executions :
  forall a b : float, sv (w_mul_1_1 prod_ce a b) (IeeeModel.mul_1_1 prec emax nan_fma' a b).
Proof.
intros a b. rewrite <- mul_1_1_with_prod.
exact (mul_1_1_same prod_ce prod' Hmp a a b b (same_refl prec emax a) (same_refl prec emax b)).
Qed.

Theorem axpy_entry_step_1_two_executions :
  forall a x y : float,
  sv (w_axpy_entry_step_1 prod_ce guard_ce a x y)
     (IeeeModel.axpy_entry_step_1 prec emax nan_plus' nan_fma' a x y).
Proof.
intros a x y. rewrite <- axpy_entry_step_1_with_prod.
exact (axpy_entry_step_1_same prod_ce prod' Hmp guard_ce guard' Hgc a a x x y y
         (same_refl prec emax a) (same_refl prec emax x) (same_refl prec emax y)).
Qed.

Theorem axpy_step_1_two_executions :
  forall a x y : float,
  sv (w_axpy_step_1 prod_ce a x y) (IeeeModel.axpy_step_1 prec emax nan_plus' nan_fma' a x y).
Proof.
intros a x y. rewrite <- axpy_step_1_with_prod.
exact (axpy_step_1_same prod_ce prod' Hmp a a x x y y (same_refl prec emax a)
         (same_refl prec emax x) (same_refl prec emax y)).
Qed.

Theorem interval_mid_rad_1_two_executions :
  forall xl xu : float,
  let '(m, r) := w_interval_mid_rad_1 prod_ce xl xu in
  let '(m', r') := IeeeModel.interval_mid_rad_1 prec emax nan_plus' nan_minus' nan_opp' nan_abs'
                     nan_fma' nan_const' xl xu in
  sv m m' /\ sv r r'.
Proof.
intros xl xu. rewrite <- interval_mid_rad_1_with_prod.
exact (interval_mid_rad_1_same prod_ce prod' Hmp xl xl xu xu (same_refl prec emax xl)
         (same_refl prec emax xu)).
Qed.

Theorem interval_to_ball_1_two_executions :
  forall xl xu : float,
  let '(c, r) := w_interval_to_ball_1 prod_ce xl xu in
  let '(c', r') := IeeeModel.interval_to_ball_1 prec emax nan_plus' nan_minus' nan_opp' nan_abs'
                     nan_fma' nan_const' xl xu in
  sv c c' /\ sv r r'.
Proof.
intros xl xu. rewrite <- interval_to_ball_1_with_prod.
exact (interval_to_ball_1_same prod_ce prod' Hmp xl xl xu xu (same_refl prec emax xl)
         (same_refl prec emax xu)).
Qed.

Theorem ball_from_interval_1_two_executions :
  forall lo hi : float,
  let '(c, r) := w_ball_from_interval_1 prod_ce guard_ce lo hi in
  let '(c', r') := IeeeModel.ball_from_interval_1 prec emax nan_plus' nan_minus' nan_opp'
                     nan_abs' nan_fma' nan_const' lo hi in
  sv c c' /\ sv r r'.
Proof.
intros lo hi. rewrite <- ball_from_interval_1_with_prod.
exact (ball_from_interval_1_same prod_ce prod' Hmp guard_ce guard' Hgc lo lo hi hi
         (same_refl prec emax lo) (same_refl prec emax hi)).
Qed.

Theorem ball_from_interval_2_two_executions :
  forall lo hi : float,
  let '(c0, c1, r) := w_ball_from_interval_2 prod_ce guard_ce lo hi in
  let '(c0', c1', r') := IeeeModel.ball_from_interval_2 prec emax nan_plus' nan_minus' nan_opp'
                           nan_abs' nan_fma' nan_const' lo hi in
  sv c0 c0' /\ sv c1 c1' /\ sv r r'.
Proof.
intros lo hi. rewrite <- ball_from_interval_2_with_prod.
exact (ball_from_interval_2_same prod_ce prod' Hmp guard_ce guard' Hgc lo lo hi hi
         (same_refl prec emax lo) (same_refl prec emax hi)).
Qed.

Theorem ball_hull_1_two_executions :
  forall cx rx cy ry : float,
  let '(c, r) := w_ball_hull_1 prod_ce cx rx cy ry in
  let '(c', r') := IeeeModel.ball_hull_1 prec emax nan_plus' nan_minus' nan_opp' nan_abs'
                     nan_fma' nan_const' cx rx cy ry in
  sv c c' /\ sv r r'.
Proof.
intros cx rx cy ry. rewrite <- ball_hull_1_with_prod.
exact (ball_hull_1_same prod_ce prod' Hmp cx cx rx rx cy cy ry ry (same_refl prec emax cx)
         (same_refl prec emax rx) (same_refl prec emax cy) (same_refl prec emax ry)).
Qed.

Theorem ball_intersection_1_two_executions :
  forall cx rx cy ry : float,
  let '(c, r) := w_ball_intersection_1 prod_ce cx rx cy ry in
  let '(c', r') := IeeeModel.ball_intersection_1 prec emax nan_plus' nan_minus' nan_opp'
                     nan_abs' nan_fma' nan_const' cx rx cy ry in
  sv c c' /\ sv r r'.
Proof.
intros cx rx cy ry. rewrite <- ball_intersection_1_with_prod.
exact (ball_intersection_1_same prod_ce prod' Hmp cx cx rx rx cy cy ry ry (same_refl prec emax cx)
         (same_refl prec emax rx) (same_refl prec emax cy) (same_refl prec emax ry)).
Qed.

Theorem bound_dot_1_two_executions :
  forall m : float,
  let '(g, t, ok) := w_bound_dot_1 prod_ce m in
  let '(g', t', ok') := IeeeModel.bound_dot_1 prec emax nan_plus' nan_fma' m in
  sv g g' /\ sv t t' /\ ok = ok'.
Proof.
intros m. rewrite <- bound_dot_1_with_prod.
exact (bound_dot_1_same prod_ce prod' Hmp m m (same_refl prec emax m)).
Qed.

Theorem bound_dot_2_two_executions :
  forall m : float,
  let '(g, t, ok) := w_bound_dot_2 prod_ce m in
  let '(g', t', ok') := IeeeModel.bound_dot_2 prec emax nan_plus' nan_fma' m in
  sv g g' /\ sv t t' /\ ok = ok'.
Proof.
intros m. rewrite <- bound_dot_2_with_prod.
exact (bound_dot_2_same prod_ce prod' Hmp m m (same_refl prec emax m)).
Qed.

Theorem bound_sum_1_two_executions :
  forall m : float,
  let '(g, ok) := w_bound_sum_1 prod_ce m in
  let '(g', ok') := IeeeModel.bound_sum_1 prec emax nan_plus' nan_fma' m in
  sv g g' /\ ok = ok'.
Proof.
intros m. rewrite <- bound_sum_1_with_prod.
exact (bound_sum_1_same prod_ce prod' Hmp m m (same_refl prec emax m)).
Qed.

Theorem bound_sum_2_two_executions :
  forall m : float,
  let '(g, ok) := w_bound_sum_2 prod_ce m in
  let '(g', ok') := IeeeModel.bound_sum_2 prec emax nan_plus' nan_fma' m in
  sv g g' /\ ok = ok'.
Proof.
intros m. rewrite <- bound_sum_2_with_prod.
exact (bound_sum_2_same prod_ce prod' Hmp m m (same_refl prec emax m)).
Qed.

Theorem bv_mul_pow2_radius_two_executions :
  forall (m : float) (ex : bool) (rx c : float),
  sv (w_bv_mul_pow2_radius prod_ce m ex rx c)
     (IeeeModel.bv_mul_pow2_radius prec emax nan_plus' nan_minus' nan_fma' m ex rx c).
Proof.
intros m ex rx c. rewrite <- bv_mul_pow2_radius_with_prod.
exact (bv_mul_pow2_radius_same prod_ce prod' Hmp m m ex rx rx c c (same_refl prec emax m)
         (same_refl prec emax rx) (same_refl prec emax c)).
Qed.

Theorem bv_mul_pow2_step_1_two_executions :
  forall x c : float,
  let '(z, e) := w_bv_mul_pow2_step_1 prod_ce x c in
  let '(z', e') := IeeeModel.bv_mul_pow2_step_1 prec emax nan_abs' nan_fma' x c in
  sv z z' /\ e = e'.
Proof.
intros x c. rewrite <- bv_mul_pow2_step_1_with_prod.
exact (bv_mul_pow2_step_1_same prod_ce prod' Hmp x x c c (same_refl prec emax x)
         (same_refl prec emax c)).
Qed.

Theorem interval_split_1_two_executions :
  forall xl xu : float,
  let '(al, au, bl, bu) := w_interval_split_1 prod_ce xl xu in
  let '(al', au', bl', bu') := IeeeModel.interval_split_1 prec emax nan_plus' nan_minus' nan_opp'
                                 nan_abs' nan_fma' nan_const' xl xu in
  sv al al' /\ sv au au' /\ sv bl bl' /\ sv bu bu'.
Proof.
intros xl xu. rewrite <- interval_split_1_with_prod.
exact (interval_split_1_same prod_ce prod' Hmp xl xl xu xu (same_refl prec emax xl)
         (same_refl prec emax xu)).
Qed.

Theorem mul_pow2_step_1_two_executions :
  forall x c : float,
  sv (w_mul_pow2_step_1 prod_ce x c) (IeeeModel.mul_pow2_step_1 prec emax nan_fma' x c).
Proof.
intros x c. rewrite <- mul_pow2_step_1_with_prod.
exact (mul_pow2_step_1_same prod_ce prod' Hmp x x c c (same_refl prec emax x)
         (same_refl prec emax c)).
Qed.

Theorem rmul_two_executions :
  forall a b : float, sv (w_rmul prod_ce a b) (IeeeModel.rmul prec emax nan_fma' a b).
Proof.
intros a b. rewrite <- rmul_with_prod.
exact (rmul_same prod_ce prod' Hmp a a b b (same_refl prec emax a) (same_refl prec emax b)).
Qed.

Theorem scale_step_1_two_executions :
  forall x a : float,
  sv (w_scale_step_1 prod_ce x a) (IeeeModel.scale_step_1 prec emax nan_fma' x a).
Proof.
intros x a. rewrite <- scale_step_1_with_prod.
exact (scale_step_1_same prod_ce prod' Hmp x x a a (same_refl prec emax x)
         (same_refl prec emax a)).
Qed.

Theorem bv_mul_pow2_step_2_two_executions :
  forall x0 x1 c : float,
  let '(z0, z1, e) := w_bv_mul_pow2_step_2 prod_ce x0 x1 c in
  let '(z0', z1', e') := IeeeModel.bv_mul_pow2_step_2 prec emax nan_plus' nan_minus' nan_abs'
                           nan_fma' x0 x1 c in
  sv z0 z0' /\ sv z1 z1' /\ e = e'.
Proof.
intros x0 x1 c. rewrite <- bv_mul_pow2_step_2_with_prod.
exact (bv_mul_pow2_step_2_same prod_ce prod' Hmp x0 x0 x1 x1 c c (same_refl prec emax x0)
         (same_refl prec emax x1) (same_refl prec emax c)).
Qed.

Theorem interval_split_2_two_executions :
  forall xl0 xl1 xu0 xu1 : float,
  let '(al0, al1, au0, au1, bl0, bl1, bu0, bu1) := w_interval_split_2 prod_ce xl0 xl1 xu0 xu1 in
  let '(al0', al1', au0', au1', bl0', bl1', bu0', bu1') :=
    IeeeModel.interval_split_2 prec emax nan_plus' nan_minus' nan_opp' nan_fma'
      xl0 xl1 xu0 xu1 in
  sv al0 al0' /\ sv al1 al1' /\ sv au0 au0' /\ sv au1 au1' /\
  sv bl0 bl0' /\ sv bl1 bl1' /\ sv bu0 bu0' /\ sv bu1 bu1'.
Proof.
intros xl0 xl1 xu0 xu1. rewrite <- interval_split_2_with_prod.
exact (interval_split_2_same prod_ce prod' Hmp xl0 xl0 xl1 xl1 xu0 xu0 xu1 xu1
         (same_refl prec emax xl0) (same_refl prec emax xl1) (same_refl prec emax xu0)
         (same_refl prec emax xu1)).
Qed.

Theorem mul_pow2_step_2_two_executions :
  forall x0 x1 c : float,
  let '(z0, z1) := w_mul_pow2_step_2 prod_ce x0 x1 c in
  let '(z0', z1') := IeeeModel.mul_pow2_step_2 prec emax nan_plus' nan_minus' nan_fma'
                       x0 x1 c in
  sv z0 z0' /\ sv z1 z1'.
Proof.
intros x0 x1 c. rewrite <- mul_pow2_step_2_with_prod.
exact (mul_pow2_step_2_same prod_ce prod' Hmp x0 x0 x1 x1 c c (same_refl prec emax x0)
         (same_refl prec emax x1) (same_refl prec emax c)).
Qed.

(* The kernels without a product, in the order of IeeeWith.v. *)
Theorem acc_add_1_two_executions :
  forall s a x : float,
  let '(t, b) := w_acc_add_1 guard_ce s a x in
  let '(t', b') := IeeeModel.acc_add_1 prec emax nan_plus' nan_abs' s a x in
  sv t t' /\ sv b b'.
Proof.
intros s a x. rewrite <- acc_add_1_with_prod.
exact (acc_add_1_same guard_ce guard' Hgc s s a a x x (same_refl prec emax s) (same_refl prec emax
       a) (same_refl prec emax x)).
Qed.

Theorem add_down_entry_two_executions :
  forall a b : float,
  sv (w_add_down_entry guard_ce a b)
     (IeeeModel.add_down_entry prec emax nan_plus' nan_minus' nan_abs' a b).
Proof.
intros a b. rewrite <- add_down_entry_with_prod.
exact (add_down_entry_same guard_ce guard' Hgc a a b b (same_refl prec emax a) (same_refl prec emax
       b)).
Qed.

Theorem add_entry_step_1_two_executions :
  forall x y : float,
  sv (w_add_entry_step_1 guard_ce x y)
     (IeeeModel.add_entry_step_1 prec emax nan_plus' x y).
Proof.
intros x y. rewrite <- add_entry_step_1_with_prod.
exact (add_entry_step_1_same guard_ce guard' Hgc x x y y (same_refl prec emax x) (same_refl prec
       emax y)).
Qed.

Theorem add_up_entry_two_executions :
  forall a b : float,
  sv (w_add_up_entry guard_ce a b)
     (IeeeModel.add_up_entry prec emax nan_plus' nan_minus' nan_abs' a b).
Proof.
intros a b. rewrite <- add_up_entry_with_prod.
exact (add_up_entry_same guard_ce guard' Hgc a a b b (same_refl prec emax a) (same_refl prec emax
       b)).
Qed.

Theorem ball_contains_point_1_two_executions :
  forall c r t : float,
  w_ball_contains_point_1 guard_ce c r t
  = IeeeModel.ball_contains_point_1 prec emax nan_plus' nan_minus' nan_opp' nan_abs' c r t.
Proof.
intros c r t. rewrite <- ball_contains_point_1_with_prod.
exact (ball_contains_point_1_same guard_ce guard' Hgc c c r r t t (same_refl prec emax c)
       (same_refl prec emax r) (same_refl prec emax t)).
Qed.

Theorem ball_make_1_two_executions :
  forall c r : float,
  let '(cw, rw) := w_ball_make_1 guard_ce c r in
  let '(cw', rw') := IeeeModel.ball_make_1 prec emax nan_plus' nan_abs' nan_const' c r in
  sv cw cw' /\ sv rw rw'.
Proof.
intros c r. rewrite <- ball_make_1_with_prod.
exact (ball_make_1_same guard_ce guard' Hgc c c r r (same_refl prec emax c) (same_refl prec emax
       r)).
Qed.

Theorem bv_center_entry_1_two_executions :
  forall c : float,
  sv (w_bv_center_entry_1 guard_ce c)
     (IeeeModel.bv_center_entry_1 prec emax nan_plus' c).
Proof.
intros c. rewrite <- bv_center_entry_1_with_prod.
exact (bv_center_entry_1_same guard_ce guard' Hgc c c (same_refl prec emax c)).
Qed.

Theorem bv_make_radius_two_executions :
  forall m r : float,
  sv (w_bv_make_radius guard_ce m r)
     (IeeeModel.bv_make_radius prec emax nan_plus' nan_minus' m r).
Proof.
intros m r. rewrite <- bv_make_radius_with_prod.
exact (bv_make_radius_same guard_ce guard' Hgc m m r r (same_refl prec emax m) (same_refl prec emax
       r)).
Qed.

Theorem fast_two_sum_entry_two_executions :
  forall a b : float,
  let '(s, e) := w_fast_two_sum_entry guard_ce a b in
  let '(s', e') := IeeeModel.fast_two_sum_entry prec emax nan_plus' nan_minus' a b in
  sv s s' /\ sv e e'.
Proof.
intros a b. rewrite <- fast_two_sum_entry_with_prod.
exact (fast_two_sum_entry_same guard_ce guard' Hgc a a b b (same_refl prec emax a) (same_refl prec
       emax b)).
Qed.

Theorem interval_make_1_two_executions :
  forall lo hi : float,
  let '(zl, zu) := w_interval_make_1 guard_ce lo hi in
  let '(zl', zu') := IeeeModel.interval_make_1 prec emax nan_plus' nan_opp' lo hi in
  sv zl zl' /\ sv zu zu'.
Proof.
intros lo hi. rewrite <- interval_make_1_with_prod.
exact (interval_make_1_same guard_ce guard' Hgc lo lo hi hi (same_refl prec emax lo) (same_refl
       prec emax hi)).
Qed.

Theorem make_2_two_executions :
  forall a : float,
  let '(x0, x1) := w_make_2 guard_ce a in
  let '(x0', x1') := IeeeModel.make_2 prec emax nan_plus' a in
  sv x0 x0' /\ sv x1 x1'.
Proof.
intros a. rewrite <- make_2_with_prod.
exact (make_2_same guard_ce guard' Hgc a a (same_refl prec emax a)).
Qed.

Theorem radd_entry_two_executions :
  forall a b : float,
  sv (w_radd_entry guard_ce a b)
     (IeeeModel.radd_entry prec emax nan_plus' a b).
Proof.
intros a b. rewrite <- radd_entry_with_prod.
exact (radd_entry_same guard_ce guard' Hgc a a b b (same_refl prec emax a) (same_refl prec emax
       b)).
Qed.

Theorem sub_down_entry_two_executions :
  forall a b : float,
  sv (w_sub_down_entry guard_ce a b)
     (IeeeModel.sub_down_entry prec emax nan_plus' nan_minus' nan_opp' nan_abs' a b).
Proof.
intros a b. rewrite <- sub_down_entry_with_prod.
exact (sub_down_entry_same guard_ce guard' Hgc a a b b (same_refl prec emax a) (same_refl prec emax
       b)).
Qed.

Theorem sub_entry_step_1_two_executions :
  forall x y : float,
  sv (w_sub_entry_step_1 guard_ce x y)
     (IeeeModel.sub_entry_step_1 prec emax nan_plus' nan_minus' x y).
Proof.
intros x y. rewrite <- sub_entry_step_1_with_prod.
exact (sub_entry_step_1_same guard_ce guard' Hgc x x y y (same_refl prec emax x) (same_refl prec
       emax y)).
Qed.

Theorem sub_up_entry_two_executions :
  forall a b : float,
  sv (w_sub_up_entry guard_ce a b)
     (IeeeModel.sub_up_entry prec emax nan_plus' nan_minus' nan_opp' nan_abs' a b).
Proof.
intros a b. rewrite <- sub_up_entry_with_prod.
exact (sub_up_entry_same guard_ce guard' Hgc a a b b (same_refl prec emax a) (same_refl prec emax
       b)).
Qed.

Theorem sum_entry_step_1_two_executions :
  forall s x : float,
  sv (w_sum_entry_step_1 guard_ce s x)
     (IeeeModel.sum_entry_step_1 prec emax nan_plus' s x).
Proof.
intros s x. rewrite <- sum_entry_step_1_with_prod.
exact (sum_entry_step_1_same guard_ce guard' Hgc s s x x (same_refl prec emax s) (same_refl prec
       emax x)).
Qed.

Theorem two_sum_entry_two_executions :
  forall a b : float,
  let '(s, e) := w_two_sum_entry guard_ce a b in
  let '(s', e') := IeeeModel.two_sum_entry prec emax nan_plus' nan_minus' a b in
  sv s s' /\ sv e e'.
Proof.
intros a b. rewrite <- two_sum_entry_with_prod.
exact (two_sum_entry_same guard_ce guard' Hgc a a b b (same_refl prec emax a) (same_refl prec emax
       b)).
Qed.

Theorem acc_add_2_two_executions :
  forall s0 s1 a x0 x1 : float,
  let '(t0, t1, b) := w_acc_add_2 guard_ce s0 s1 a x0 x1 in
let '(t0', t1', b') := IeeeModel.acc_add_2 prec emax nan_plus' nan_minus' nan_abs' s0 s1 a x0 x1 in
  sv t0 t0' /\ sv t1 t1' /\ sv b b'.
Proof.
intros s0 s1 a x0 x1. rewrite <- acc_add_2_with_prod.
exact (acc_add_2_same guard_ce guard' Hgc s0 s0 s1 s1 a a x0 x0 x1 x1 (same_refl prec emax s0)
       (same_refl prec emax s1) (same_refl prec emax a) (same_refl prec emax x0) (same_refl prec
       emax x1)).
Qed.

Theorem add_2_1_two_executions :
  forall x0 x1 a : float,
  let '(z0, z1) := w_add_2_1 guard_ce x0 x1 a in
  let '(z0', z1') := IeeeModel.add_2_1 prec emax nan_plus' nan_minus' x0 x1 a in
  sv z0 z0' /\ sv z1 z1'.
Proof.
intros x0 x1 a. rewrite <- add_2_1_with_prod.
exact (add_2_1_same guard_ce guard' Hgc x0 x0 x1 x1 a a (same_refl prec emax x0) (same_refl prec
       emax x1) (same_refl prec emax a)).
Qed.

Theorem add_2_1_full_two_executions :
  forall x0 x1 a : float,
  let '(w0, w1) := w_add_2_1_full guard_ce times_inf_ce x0 x1 a in
let '(w0', w1') := IeeeModel.add_2_1_full prec emax nan_plus' nan_minus' nan_abs' nan_mult' x0 x1 a
    in
  sv w0 w0' /\ sv w1 w1'.
Proof.
intros x0 x1 a. rewrite <- add_2_1_full_with_prod.
exact (add_2_1_full_same guard_ce guard' Hgc times_inf_ce times_inf' Htc x0 x0 x1 x1 a a (same_refl
       prec emax x0) (same_refl prec emax x1) (same_refl prec emax a)).
Qed.

Theorem add_2_2_full_two_executions :
  forall x0 x1 y0 y1 : float,
  let '(w0, w1) := w_add_2_2_full times_inf_ce x0 x1 y0 y1 in
let '(w0', w1') := IeeeModel.add_2_2_full prec emax nan_plus' nan_minus' nan_abs' nan_mult' x0 x1
    y0 y1 in
  sv w0 w0' /\ sv w1 w1'.
Proof.
intros x0 x1 y0 y1. rewrite <- add_2_2_full_with_prod.
exact (add_2_2_full_same times_inf_ce times_inf' Htc x0 x0 x1 x1 y0 y0 y1 y1 (same_refl prec emax
       x0) (same_refl prec emax x1) (same_refl prec emax y0) (same_refl prec emax y1)).
Qed.

Theorem add_entry_step_2_two_executions :
  forall x0 x1 y0 y1 : float,
  let '(z0, z1) := w_add_entry_step_2 guard_ce x0 x1 y0 y1 in
  let '(z0', z1') := IeeeModel.add_entry_step_2 prec emax nan_plus' nan_minus' x0 x1 y0 y1 in
  sv z0 z0' /\ sv z1 z1'.
Proof.
intros x0 x1 y0 y1. rewrite <- add_entry_step_2_with_prod.
exact (add_entry_step_2_same guard_ce guard' Hgc x0 x0 x1 x1 y0 y0 y1 y1 (same_refl prec emax x0)
       (same_refl prec emax x1) (same_refl prec emax y0) (same_refl prec emax y1)).
Qed.

Theorem add_fast_2_2_full_two_executions :
  forall x0 x1 y0 y1 : float,
  let '(w0, w1) := w_add_fast_2_2_full times_inf_ce x0 x1 y0 y1 in
let '(w0', w1') := IeeeModel.add_fast_2_2_full prec emax nan_plus' nan_minus' nan_abs' nan_mult' x0
    x1 y0 y1 in
  sv w0 w0' /\ sv w1 w1'.
Proof.
intros x0 x1 y0 y1. rewrite <- add_fast_2_2_full_with_prod.
exact (add_fast_2_2_full_same times_inf_ce times_inf' Htc x0 x0 x1 x1 y0 y0 y1 y1 (same_refl prec
       emax x0) (same_refl prec emax x1) (same_refl prec emax y0) (same_refl prec emax y1)).
Qed.

Theorem ball_make_2_two_executions :
  forall c0 c1 r : float,
  let '(cw0, cw1, rw) := w_ball_make_2 guard_ce c0 c1 r in
let '(cw0', cw1', rw') := IeeeModel.ball_make_2 prec emax nan_plus' nan_abs' nan_const' c0 c1 r in
  sv cw0 cw0' /\ sv cw1 cw1' /\ sv rw rw'.
Proof.
intros c0 c1 r. rewrite <- ball_make_2_with_prod.
exact (ball_make_2_same guard_ce guard' Hgc c0 c0 c1 c1 r r (same_refl prec emax c0) (same_refl
       prec emax c1) (same_refl prec emax r)).
Qed.

Theorem make_2_limbs_two_executions :
  forall h l : float,
  let '(x0, x1) := w_make_2_limbs guard_ce h l in
  let '(x0', x1') := IeeeModel.make_2_limbs prec emax nan_plus' h l in
  sv x0 x0' /\ sv x1 x1'.
Proof.
intros h l. rewrite <- make_2_limbs_with_prod.
exact (make_2_limbs_same guard_ce guard' Hgc h h l l (same_refl prec emax h) (same_refl prec emax
       l)).
Qed.

Theorem sub_1_2_two_executions :
  forall a y0 y1 : float,
  let '(z0, z1) := w_sub_1_2 guard_ce a y0 y1 in
  let '(z0', z1') := IeeeModel.sub_1_2 prec emax nan_plus' nan_minus' nan_opp' a y0 y1 in
  sv z0 z0' /\ sv z1 z1'.
Proof.
intros a y0 y1. rewrite <- sub_1_2_with_prod.
exact (sub_1_2_same guard_ce guard' Hgc a a y0 y0 y1 y1 (same_refl prec emax a) (same_refl prec
       emax y0) (same_refl prec emax y1)).
Qed.

Theorem sub_1_2_full_two_executions :
  forall a y0 y1 : float,
  let '(w0, w1) := w_sub_1_2_full guard_ce times_inf_ce a y0 y1 in
let '(w0', w1') := IeeeModel.sub_1_2_full prec emax nan_plus' nan_minus' nan_opp' nan_abs'
    nan_mult' a y0 y1 in
  sv w0 w0' /\ sv w1 w1'.
Proof.
intros a y0 y1. rewrite <- sub_1_2_full_with_prod.
exact (sub_1_2_full_same guard_ce guard' Hgc times_inf_ce times_inf' Htc a a y0 y0 y1 y1 (same_refl
       prec emax a) (same_refl prec emax y0) (same_refl prec emax y1)).
Qed.

Theorem sub_2_1_two_executions :
  forall x0 x1 a : float,
  let '(z0, z1) := w_sub_2_1 guard_ce x0 x1 a in
  let '(z0', z1') := IeeeModel.sub_2_1 prec emax nan_plus' nan_minus' nan_opp' x0 x1 a in
  sv z0 z0' /\ sv z1 z1'.
Proof.
intros x0 x1 a. rewrite <- sub_2_1_with_prod.
exact (sub_2_1_same guard_ce guard' Hgc x0 x0 x1 x1 a a (same_refl prec emax x0) (same_refl prec
       emax x1) (same_refl prec emax a)).
Qed.

Theorem sub_2_1_full_two_executions :
  forall x0 x1 a : float,
  let '(w0, w1) := w_sub_2_1_full guard_ce times_inf_ce x0 x1 a in
let '(w0', w1') := IeeeModel.sub_2_1_full prec emax nan_plus' nan_minus' nan_opp' nan_abs'
    nan_mult' x0 x1 a in
  sv w0 w0' /\ sv w1 w1'.
Proof.
intros x0 x1 a. rewrite <- sub_2_1_full_with_prod.
exact (sub_2_1_full_same guard_ce guard' Hgc times_inf_ce times_inf' Htc x0 x0 x1 x1 a a (same_refl
       prec emax x0) (same_refl prec emax x1) (same_refl prec emax a)).
Qed.

Theorem sub_2_2_full_two_executions :
  forall x0 x1 y0 y1 : float,
  let '(w0, w1) := w_sub_2_2_full times_inf_ce x0 x1 y0 y1 in
let '(w0', w1') := IeeeModel.sub_2_2_full prec emax nan_plus' nan_minus' nan_opp' nan_abs'
    nan_mult' x0 x1 y0 y1 in
  sv w0 w0' /\ sv w1 w1'.
Proof.
intros x0 x1 y0 y1. rewrite <- sub_2_2_full_with_prod.
exact (sub_2_2_full_same times_inf_ce times_inf' Htc x0 x0 x1 x1 y0 y0 y1 y1 (same_refl prec emax
       x0) (same_refl prec emax x1) (same_refl prec emax y0) (same_refl prec emax y1)).
Qed.

Theorem sub_entry_step_2_two_executions :
  forall x0 x1 y0 y1 : float,
  let '(z0, z1) := w_sub_entry_step_2 guard_ce x0 x1 y0 y1 in
let '(z0', z1') := IeeeModel.sub_entry_step_2 prec emax nan_plus' nan_minus' nan_opp' x0 x1 y0 y1
    in
  sv z0 z0' /\ sv z1 z1'.
Proof.
intros x0 x1 y0 y1. rewrite <- sub_entry_step_2_with_prod.
exact (sub_entry_step_2_same guard_ce guard' Hgc x0 x0 x1 x1 y0 y0 y1 y1 (same_refl prec emax x0)
       (same_refl prec emax x1) (same_refl prec emax y0) (same_refl prec emax y1)).
Qed.

Theorem sum_entry_step_2_two_executions :
  forall s0 s1 x0 x1 : float,
  let '(t0, t1) := w_sum_entry_step_2 guard_ce s0 s1 x0 x1 in
  let '(t0', t1') := IeeeModel.sum_entry_step_2 prec emax nan_plus' nan_minus' s0 s1 x0 x1 in
  sv t0 t0' /\ sv t1 t1'.
Proof.
intros s0 s1 x0 x1. rewrite <- sum_entry_step_2_with_prod.
exact (sum_entry_step_2_same guard_ce guard' Hgc s0 s0 s1 s1 x0 x0 x1 x1 (same_refl prec emax s0)
       (same_refl prec emax s1) (same_refl prec emax x0) (same_refl prec emax x1)).
Qed.

Theorem sum_fast_entry_step_2_two_executions :
  forall s0 s1 x0 x1 : float,
  let '(t0, t1) := w_sum_fast_entry_step_2 guard_ce s0 s1 x0 x1 in
  let '(t0', t1') := IeeeModel.sum_fast_entry_step_2 prec emax nan_plus' nan_minus' s0 s1 x0 x1 in
  sv t0 t0' /\ sv t1 t1'.
Proof.
intros s0 s1 x0 x1. rewrite <- sum_fast_entry_step_2_with_prod.
exact (sum_fast_entry_step_2_same guard_ce guard' Hgc s0 s0 s1 s1 x0 x0 x1 x1 (same_refl prec emax
       s0) (same_refl prec emax s1) (same_refl prec emax x0) (same_refl prec emax x1)).
Qed.

End TwoExecutions.

(** * two_prod: Dekker's product in constant evaluation against TwoProd at run time *)

(* two_prod is constexpr through a constant-evaluation variant, not by the rule of the
   product: in constant evaluation the C++ runs the listing of two_prod_dekker (Veltkamp's
   split and Dekker's product) with plain products, at run time TwoProd with an FMA. These
   are two algorithms, and their error terms are not always the same number: below
   2^(2p-1) eta neither is exact and each is its own rounding of the exact error, within
   eta/2 at run time and 13/8 eta in constant evaluation; and an operation of Dekker's
   product (a split, a partial product) can overflow where TwoProd overflows nowhere, which
   makes its error term infinite or a NaN. What is proved here: when the error term of
   Dekker's product is finite (then so is every value it computes: non-finite in, non-finite
   out), and the product is exact (a b = 0 or |a b| >= 2^(2p-1) eta), the two executions of
   two_prod return the same values. Without the second condition this is false: in binary64,
   a = -0x1.204f8c386bbc4p-102 and b = -0x1.3c5fd414c343cp-911 give the error term
   -0x1.d4p-1068 at run time and -0x1.d8p-1068 in constant evaluation. Without the first, too:
   a = b = 0x1.fffffffffffffp+511 give 0x1p+918 at run time, and +infinity in constant
   evaluation, where Dekker's partial product ah bh overflows (Clang computes it; GCC refuses
   the program, which is no wrong constant). No kernel
   reaches two_prod in constant evaluation: every kernel that calls it has an fms, and no
   variant, so it is not constexpr. *)
Section TwoProdVariant.
Variable prec emax : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Context {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}.

Notation float := (binary_float prec emax).
Notation nan_of := {x : float | is_nan prec emax x = true}.
(* The NaN functions of constant evaluation, and those of run time (primed). *)
Variable nan_plus : float -> float -> nan_of.
Variable nan_minus : float -> float -> nan_of.
Variable nan_opp' : float -> nan_of.
Variable nan_fma' : float -> float -> float -> nan_of.
Variable nan_mult : float -> float -> nan_of.

Notation emin := (3 - emax - prec)%Z.
Notation fexp := (FLT_exp emin prec).
Notation rnd := (round radix2 fexp (Znearest tie_even)).
Notation fin x := (is_finite prec emax x = true).
Notation b2r := (B2R prec emax).
Notation sv := (@same_value prec emax).
Notation add := (IeeeOperations.add prec emax nan_plus).
Notation sub := (IeeeOperations.sub prec emax nan_minus).
Notation prod_ce := (IeeeWith.prod_ce prec emax nan_mult).
Notation prod' := (IeeeOperations.prod prec emax nan_fma').
Notation splitter := (IeeeModel.splitter prec emax).
Notation dekker_ce := (IeeeWith.two_prod_dekker_with prec emax nan_plus nan_minus prod_ce).

Let Hprec : (0 < prec)%Z.
Proof. exact prec_gt_0_. Qed.
Let Hemax : (prec < emax)%Z.
Proof. exact prec_lt_emax_. Qed.

(* The plain product: non-finite in, non-finite out; finite, the rounded product. *)
Lemma prod_ce_finite_inv : forall x y : float, fin (prod_ce x y) -> fin x /\ fin y.
Proof.
intros x y. unfold IeeeWith.prod_ce, Bmult. rewrite is_finite_BSN2B.
destruct x as [sx|sx|sx px Hx|sx mx ex Hx]; destruct y as [sy|sy|sy py Hy|sy my ey Hy];
  try (intros _; split; reflexivity); simpl; try discriminate.
Qed.

Lemma prod_ce_val :
  forall x y : float, fin x -> fin y -> fin (prod_ce x y) ->
  b2r (prod_ce x y) = rnd (b2r x * b2r y + 0).
Proof.
intros x y Fx Fy F.
assert (S : sv (prod_ce x y) (prod' x y)).
{ apply (same_prod_ce prec emax nan_fma' nan_mult); apply same_refl. }
assert (F' : fin (prod' x y)) by (rewrite <- (same_finite prec emax _ _ S); exact F).
rewrite (same_val prec emax _ _ S). unfold IeeeOperations.prod.
destruct (fma_spec prec emax nan_fma' x y (IeeeOperations.pzero prec emax) Fx Fy eq_refl)
  as [_ E].
rewrite (E F'). reflexivity.
Qed.

(* The splitter of the format, 2^s + 1 with s = ceil(prec / 2), is the number of the
   real model. *)
Lemma splitter_val : (4 <= prec)%Z -> fin splitter /\ b2r splitter = Model.splitter prec.
Proof.
intros Hp. unfold IeeeModel.splitter.
assert (Hs : (2 <= Split.split_s prec <= prec - 2)%Z) by (apply Split.split_s_bounds; exact Hp).
assert (P : (2 ^ Split.split_s prec + 1 < 2 ^ prec)%Z).
{ assert (A : (2 ^ Split.split_s prec <= 2 ^ (prec - 2))%Z) by (apply Z.pow_le_mono_r; lia).
  assert (B : (2 ^ prec = 2 ^ (prec - 2) * 2 ^ 2)%Z).
  { rewrite <- Z.pow_add_r by lia. f_equal. lia. }
  assert (C : (0 < 2 ^ (prec - 2))%Z) by (apply Z.pow_pos_nonneg; lia).
  rewrite B. simpl (2 ^ 2)%Z. lia. }
rewrite (Split.splitter_IZR prec) by lia.
apply (const_of_spec prec emax).
- apply generic_format_FLT.
  apply (FLT_spec _ _ _ _ (Float radix2 (2 ^ Split.split_s prec + 1) 0)).
  + unfold F2R. simpl. ring.
  + simpl. rewrite Z.abs_eq by lia. change (Zpower radix2 prec) with (2 ^ prec)%Z. exact P.
  + cbn [Fexp]. lia.
- rewrite Rabs_pos_eq by (apply IZR_le; lia).
  apply Rlt_le_trans with (IZR (2 ^ prec)); [apply IZR_lt; exact P|].
  change (2 ^ prec)%Z with (Zpower radix2 prec).
  rewrite (IZR_Zpower radix2) by lia. apply bpow_le. lia.
Qed.

(* Dekker's product in constant evaluation with a finite error term: every value finite, and
   the values of the real model. *)
Lemma dekker_ce_model :
  (4 <= prec)%Z ->
  forall a b : float, fin a -> fin b ->
  fin (snd (dekker_ce a b)) ->
  fin (fst (dekker_ce a b)) /\
  (b2r (fst (dekker_ce a b)), b2r (snd (dekker_ce a b)))
  = Model.two_prod_dekker emin prec tie_even (b2r a) (b2r b).
Proof.
intros Hp a b Fa Fb.
destruct (splitter_val Hp) as [FS VS].
cbv beta iota zeta delta [IeeeWith.two_prod_dekker_with IeeeWith.split_with Model.two_prod_dekker
  Model.split fst snd].
set (ga := prod_ce splitter a). set (da := sub a ga). set (ah := add ga da).
set (al := sub a ah).
set (gb := prod_ce splitter b). set (db := sub b gb). set (bh := add gb db).
set (bl := sub b bh).
set (p := prod_ce a b). set (q0 := prod_ce ah bh). set (t1 := sub q0 p).
set (q1 := prod_ce ah bl). set (t2 := add t1 q1). set (q2 := prod_ce al bh).
set (t3 := add t2 q2). set (q3 := prod_ce al bl). set (e := add t3 q3).
intros Fe.
destruct (add_finite_inv prec emax nan_plus t3 q3 Fe) as [Ft3 Fq3].
destruct (add_finite_inv prec emax nan_plus t2 q2 Ft3) as [Ft2 Fq2].
destruct (add_finite_inv prec emax nan_plus t1 q1 Ft2) as [Ft1 Fq1].
destruct (sub_finite_inv prec emax nan_minus q0 p Ft1) as [Fq0 Fp].
destruct (prod_ce_finite_inv ah bh Fq0) as [Fah Fbh].
destruct (prod_ce_finite_inv al bl Fq3) as [Fal Fbl].
destruct (add_finite_inv prec emax nan_plus ga da Fah) as [Fga Fda].
destruct (add_finite_inv prec emax nan_plus gb db Fbh) as [Fgb Fdb].
split; [exact Fp|].
assert (Vga : b2r ga = rnd (Model.splitter prec * b2r a + 0)).
{ rewrite <- VS. apply prod_ce_val; assumption. }
assert (Vgb : b2r gb = rnd (Model.splitter prec * b2r b + 0)).
{ rewrite <- VS. apply prod_ce_val; assumption. }
assert (Vda : b2r da = rnd (b2r a - b2r ga)).
{ apply (proj2 (sub_spec prec emax nan_minus a ga Fa Fga)). exact Fda. }
assert (Vdb : b2r db = rnd (b2r b - b2r gb)).
{ apply (proj2 (sub_spec prec emax nan_minus b gb Fb Fgb)). exact Fdb. }
assert (Vah : b2r ah = rnd (b2r ga + b2r da)).
{ apply (proj2 (add_spec prec emax nan_plus ga da Fga Fda)). exact Fah. }
assert (Vbh : b2r bh = rnd (b2r gb + b2r db)).
{ apply (proj2 (add_spec prec emax nan_plus gb db Fgb Fdb)). exact Fbh. }
assert (Val : b2r al = rnd (b2r a - b2r ah)).
{ apply (proj2 (sub_spec prec emax nan_minus a ah Fa Fah)). exact Fal. }
assert (Vbl : b2r bl = rnd (b2r b - b2r bh)).
{ apply (proj2 (sub_spec prec emax nan_minus b bh Fb Fbh)). exact Fbl. }
assert (Vp : b2r p = rnd (b2r a * b2r b + 0)) by (apply prod_ce_val; assumption).
assert (Vq0 : b2r q0 = rnd (b2r ah * b2r bh + 0)) by (apply prod_ce_val; assumption).
assert (Vq1 : b2r q1 = rnd (b2r ah * b2r bl + 0)) by (apply prod_ce_val; assumption).
assert (Vq2 : b2r q2 = rnd (b2r al * b2r bh + 0)) by (apply prod_ce_val; assumption).
assert (Vq3 : b2r q3 = rnd (b2r al * b2r bl + 0)) by (apply prod_ce_val; assumption).
assert (Vt1 : b2r t1 = rnd (b2r q0 - b2r p)).
{ apply (proj2 (sub_spec prec emax nan_minus q0 p Fq0 Fp)). exact Ft1. }
assert (Vt2 : b2r t2 = rnd (b2r t1 + b2r q1)).
{ apply (proj2 (add_spec prec emax nan_plus t1 q1 Ft1 Fq1)). exact Ft2. }
assert (Vt3 : b2r t3 = rnd (b2r t2 + b2r q2)).
{ apply (proj2 (add_spec prec emax nan_plus t2 q2 Ft2 Fq2)). exact Ft3. }
assert (Ve : b2r e = rnd (b2r t3 + b2r q3)).
{ apply (proj2 (add_spec prec emax nan_plus t3 q3 Ft3 Fq3)). exact Fe. }
rewrite Ve, Vt3, Vq3, Vt2, Vq2, Vt1, Vq1, Vq0, Vp, Val, Vbl, Vah, Vbh, Vda, Vdb, Vga, Vgb.
reflexivity.
Qed.

(* The two executions of two_prod: Dekker's product with plain products (constant evaluation)
   and TwoProd with an FMA (run time), on the same finite operands, with any NaN functions on
   either side. When the error term of constant evaluation is finite and the product is
   exact, both pairs have the same values. *)
Theorem two_prod_two_executions_exact :
  (4 <= prec)%Z ->
  forall a b : float, fin a -> fin b ->
  let '(p, e) := dekker_ce a b in
  let '(p', e') := IeeeModel.two_prod prec emax nan_opp' nan_fma' a b in
  fin e ->
  (b2r a * b2r b = 0 \/ bpow radix2 (2 * prec - 1) * bpow radix2 emin <= Rabs (b2r a * b2r b)) ->
  sv p p' /\ sv e e'.
Proof.
intros Hp a b Fa Fb.
assert (Sp : sv (fst (dekker_ce a b)) (fst (IeeeModel.two_prod prec emax nan_opp' nan_fma' a b))).
{ cbv beta iota zeta delta [IeeeWith.two_prod_dekker_with IeeeWith.split_with IeeeModel.two_prod
    fst].
  apply (same_prod_ce prec emax nan_fma' nan_mult); apply same_refl. }
generalize (dekker_ce_model Hp a b Fa Fb).
generalize (IeeeEFT.two_prod_ieee_correct prec emax prec_gt_0_ prec_lt_emax_ nan_opp' nan_fma'
              ltac:(lia) a b Fa Fb).
generalize (TwoProdDekker.two_prod_dekker_correct emin prec Hp (b2r a) (b2r b)
              (b2r_format prec emax a) (b2r_format prec emax b)).
revert Sp.
destruct (Model.two_prod_dekker emin prec tie_even (b2r a) (b2r b)) as [rp re].
destruct (dekker_ce a b) as [p e].
destruct (IeeeModel.two_prod prec emax nan_opp' nan_fma' a b) as [p' e'].
cbn [fst snd]. intros Sp [_ [_ [Erp [_ Xr]]]] Hrun Hce Fe Big.
destruct (Hce Fe) as [Fp E]. injection E as Ep Ee.
assert (Fp' : fin p') by (rewrite <- (same_finite prec emax _ _ Sp); exact Fp).
destruct (Hrun Fp') as [Fe' [Ep' [_ Xrun]]].
split; [exact Sp|].
unfold same_value. rewrite (xval_fin prec emax e Fe), (xval_fin prec emax e' Fe').
f_equal.
assert (Hrp : rp + re = b2r a * b2r b) by (apply Xr; exact Big).
assert (Hrun' : b2r p' + b2r e' = b2r a * b2r b) by (apply Xrun; exact Big).
assert (Epp : b2r p' = rp) by (change (b2r p') with (val p'); rewrite Ep', Erp; reflexivity).
lra.
Qed.

End TwoProdVariant.

(* The statement of two_prod_two_executions_exact, written by hand (two_prod is constexpr
   through a variant, which IeeeWith.v does not list, and the statement has two hypotheses):
   proofs/audit/HandAudit.v checks the theorem against it. *)
Definition two_prod_two_executions_exact_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_opp' : nan1 prec emax)
         (nan_fma' : nan3 prec emax) (nan_mult : nan2 prec emax),
  (4 <= prec)%Z ->
  forall a b : binary_float prec emax, finite a -> finite b ->
  let '(p, e) := IeeeWith.two_prod_dekker_with prec emax nan_plus nan_minus
                   (IeeeWith.prod_ce prec emax nan_mult) a b in
  let '(p', e') := IeeeModel.two_prod prec emax nan_opp' nan_fma' a b in
  finite e ->
  (val a * val b = 0 \/
   bpow radix2 (2 * prec - 1) * eta (ieee_emin prec emax) <= Rabs (val a * val b)) ->
  xval p = xval p' /\ xval e = xval e'.
