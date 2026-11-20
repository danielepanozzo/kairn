(* The two executions of a product, in the IEEE model
   (docs/developer/design/milestone2.md, "The two executions of a product").

   The operation `prod a b` of a kernel is fma(a, b, +0) at run time and the plain product
   a * b in constant evaluation, where C++20 has no fused operation. In Flocq's terms the
   first is Bfma on a, b and +0, which is IeeeOperations.prod, and the second is Bmult.
   This file compares the two on all values: finite numbers, signed zeros, infinities and
   NaN. Rounding is to nearest, ties to even; which NaN an operation returns is a
   parameter of each of them (nan_fma, nan_mult), and nothing here depends on it.

   What is proved, for all limbs a and b:
   - mult_prod_xval: the two results are the same extended real number (xval): the same
     real number, the same infinity, or both NaN;
   - mult_prod_nan: one is a NaN exactly when the other is;
   - mult_prod_eq: they are equal as values (the same bits) whenever they are not NaN
     and the product is not an exact zero, that is, unless a and b are finite and
     a b = 0. This covers a product that underflows to zero (the two zeros then have the
     same sign, that of the product), an overflow, and infinite operands;
   - mult_prod_zero: when a and b are finite and a b = 0, both results are zeros: the
     plain product has the sign of the product of the signs, and the fused one is +0. So
     they differ exactly when the signs of a and b differ;
   - mult_prod_same: the three cases in one statement;
   - succ_mult_prod: the successors of the two results are equal whenever they are not
     NaN, the exact zeros included, since the successor of either zero is the smallest
     positive number. This is why `rmul`, which is succ(prod(a, b)), gives the same bits
     in constant evaluation as at run time.

   Why: for finite nonzero operands Flocq's Bmult_correct and Bfma_correct give both
   results the same real value (a b + 0 = a b) and the same sign (that of the real number
   a b, which is not zero), or the same overflow; two finite values with the same real
   value and the same sign are equal (B2R_Bsign_inj). The other cases are computations on
   the constructors. *)
From Stdlib Require Import Reals ZArith Bool Lia Lra Psatz.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements IeeeStatements.
From Kairn Require Import Format IeeeBridge IeeeVocabulary IeeeOps IeeeExt.
From Kairn Require IeeeOperations.
From Kairn.Gen Require IeeeModel.
Open Scope R_scope.

Section TwoExecutions.
Variable prec emax : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Context {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}.

Notation float := (binary_float prec emax).
Notation nan_of := {x : float | is_nan prec emax x = true}.
Variable nan_fma : float -> float -> float -> nan_of.
Variable nan_mult : float -> float -> nan_of.

Notation fin x := (is_finite prec emax x = true).
Notation b2r := (B2R prec emax).
Notation pzero := (IeeeOperations.pzero prec emax).
Notation fsucc := (IeeeOperations.succ prec emax).
Notation xv := (@xval prec emax).
(* The fused execution: Bfma on a, b and +0. *)
Notation prod := (IeeeOperations.prod prec emax nan_fma).
(* The plain execution: Flocq's multiplication of the format. *)
Notation mult := (Bmult prec emax prec_gt_0_ prec_lt_emax_ nan_mult BinarySingleNaN.mode_NE).

(* Two finite operands that are not zero: the two executions return the same value, which
   is not a NaN, and the exact product is not zero. *)
Lemma mult_prod_finite :
  forall (sa : bool) (ma : positive) (ea : Z) Ha (sb : bool) (mb : positive) (eb : Z) Hb,
  let a := B754_finite prec emax sa ma ea Ha in
  let b := B754_finite prec emax sb mb eb Hb in
  mult a b = prod a b /\ is_nan prec emax (mult a b) = false /\ b2r a * b2r b <> 0.
Proof.
intros sa ma ea Ha sb mb eb Hb a b.
assert (Fa : fin a) by reflexivity.
assert (Fb : fin b) by reflexivity.
(* the sign of the real product is the product of the signs *)
assert (Sx : Rlt_bool (b2r a * b2r b) 0 = xorb sa sb /\ b2r a * b2r b <> 0).
{ unfold a, b. destruct sa, sb.
  - generalize (finite_sign_neg prec emax ma ea Ha) (finite_sign_neg prec emax mb eb Hb).
    intros A B. split; [apply Rlt_bool_false|]; nra.
  - generalize (finite_sign_neg prec emax ma ea Ha) (finite_sign_pos prec emax mb eb Hb).
    intros A B. split; [apply Rlt_bool_true|]; nra.
  - generalize (finite_sign_pos prec emax ma ea Ha) (finite_sign_neg prec emax mb eb Hb).
    intros A B. split; [apply Rlt_bool_true|]; nra.
  - generalize (finite_sign_pos prec emax ma ea Ha) (finite_sign_pos prec emax mb eb Hb).
    intros A B. split; [apply Rlt_bool_false|]; nra. }
destruct Sx as [Sx Nx].
generalize (Bmult_correct prec emax prec_gt_0_ prec_lt_emax_ nan_mult BinarySingleNaN.mode_NE a b).
generalize (Bfma_correct prec emax prec_gt_0_ prec_lt_emax_ nan_fma BinarySingleNaN.mode_NE
              a b pzero Fa Fb eq_refl).
cbv zeta. change (b2r pzero) with 0. rewrite Rplus_0_r.
change (Bfma prec emax prec_gt_0_ prec_lt_emax_ nan_fma BinarySingleNaN.mode_NE a b pzero)
  with (prod a b).
destruct (Rlt_bool (Rabs (round radix2 (SpecFloat.fexp prec emax)
            (BinarySingleNaN.round_mode BinarySingleNaN.mode_NE) (b2r a * b2r b)))
            (bpow radix2 emax)).
- (* no overflow: the same real value and the same sign *)
  intros [E2 [F2 S2]] [E1 [F1 S1]].
  assert (F1' : fin (mult a b)) by (rewrite F1; reflexivity).
  assert (N1 : is_nan prec emax (mult a b) = false) by now apply finite_not_nan.
  split; [|split; [exact N1|exact Nx]].
  apply B2R_Bsign_inj; trivial.
  + now rewrite E1, E2.
  + rewrite (S1 N1), S2.
    change (xorb (Bsign prec emax a) (Bsign prec emax b)) with (xorb sa sb).
    rewrite <- Sx.
    destruct (Rcompare_spec (b2r a * b2r b) 0) as [C|C|C].
    * now apply Rlt_bool_true.
    * now elim Nx.
    * apply Rlt_bool_false. lra.
- (* overflow: the same infinity *)
  intros E2 E1.
  assert (E : mult a b = prod a b).
  { apply B2FF_inj. rewrite E1, E2. f_equal. symmetry. exact Sx. }
  split; [exact E|split; [|exact Nx]].
  rewrite overflow_NE in E1. apply B2FF_inf_inv in E1. now rewrite E1.
Qed.

(* The three cases. Either both results are NaN; or they are equal, not NaN, and the
   product is not an exact zero; or a and b are finite with a b = 0, the plain product is
   the zero with the product of the signs, and the fused one is +0. *)
Lemma mult_prod_cases :
  forall a b : float,
  (is_nan prec emax (mult a b) = true /\ is_nan prec emax (prod a b) = true) \/
  (mult a b = prod a b /\ is_nan prec emax (mult a b) = false /\
   ~ (fin a /\ fin b /\ b2r a * b2r b = 0)) \/
  (fin a /\ fin b /\ b2r a * b2r b = 0 /\
   mult a b = B754_zero prec emax (xorb (Bsign prec emax a) (Bsign prec emax b)) /\
   prod a b = pzero).
Proof.
intros [sa|sa|sa pa Ha|sa ma ea Ha] [sb|sb|sb pb Hb|sb mb eb Hb];
  try (left; split; reflexivity).
- (* zero, zero *)
  right. right. repeat split; try reflexivity.
  + simpl. ring.
  + destruct sa, sb; reflexivity.
- (* zero, finite *)
  right. right. repeat split; try reflexivity.
  + simpl. ring.
  + destruct sa, sb; reflexivity.
- (* infinity, infinity *)
  right. left. repeat split; try reflexivity. intros [F _]. discriminate F.
- (* infinity, finite *)
  right. left. repeat split; try reflexivity. intros [F _]. discriminate F.
- (* finite, zero *)
  right. right. repeat split; try reflexivity.
  + simpl. ring.
  + destruct sa, sb; reflexivity.
- (* finite, infinity *)
  right. left. repeat split; try reflexivity. intros [_ [F _]]. discriminate F.
- (* finite, finite *)
  right. left. destruct (mult_prod_finite sa ma ea Ha sb mb eb Hb) as [E [N Z]].
  split; [exact E|split; [exact N|]]. intros [_ [_ K]]. now apply Z.
Qed.

(* The plain product and the fused product with a zero addend are the same extended real
   number, for all operands. *)
Theorem mult_prod_xval : forall a b : float, xv (mult a b) = xv (prod a b).
Proof.
intros a b. destruct (mult_prod_cases a b) as [[N1 N2]|[[E _]|[_ [_ [_ [E1 E2]]]]]].
- now rewrite (xval_nan prec emax _ N1), (xval_nan prec emax _ N2).
- now rewrite E.
- rewrite E1, E2. reflexivity.
Qed.

(* One is a NaN exactly when the other is. *)
Theorem mult_prod_nan :
  forall a b : float, is_nan prec emax (mult a b) = is_nan prec emax (prod a b).
Proof.
intros a b. destruct (mult_prod_cases a b) as [[N1 N2]|[[E _]|[_ [_ [_ [E1 E2]]]]]].
- now rewrite N1, N2.
- now rewrite E.
- rewrite E1, E2. reflexivity.
Qed.

(* They are equal as values whenever they are not NaN and the product is not an exact
   zero. *)
Theorem mult_prod_eq :
  forall a b : float,
  is_nan prec emax (mult a b) = false ->
  ~ (fin a /\ fin b /\ b2r a * b2r b = 0) ->
  mult a b = prod a b.
Proof.
intros a b N Z. destruct (mult_prod_cases a b) as [[N1 _]|[[E _]|[Fa [Fb [K _]]]]].
- congruence.
- exact E.
- elim Z. auto.
Qed.

(* An exact zero: both results are zeros; the plain product has the sign of the product
   of the signs of a and b, and the fused one is +0. *)
Theorem mult_prod_zero :
  forall a b : float,
  fin a -> fin b -> b2r a * b2r b = 0 ->
  mult a b = B754_zero prec emax (xorb (Bsign prec emax a) (Bsign prec emax b)) /\
  prod a b = pzero.
Proof.
intros a b Fa Fb K. destruct (mult_prod_cases a b) as [[N1 _]|[[_ [_ Z]]|[_ [_ [_ E]]]]].
- exfalso.
  generalize (Bmult_correct prec emax prec_gt_0_ prec_lt_emax_ nan_mult BinarySingleNaN.mode_NE a b).
  rewrite K, round_0, Rabs_R0, Rlt_bool_true by (auto with typeclass_instances; apply bpow_gt_0).
  rewrite Fa, Fb. intros [_ [F _]]. apply nan_not_finite in N1. cbn in F. congruence.
- elim Z. auto.
- exact E.
Qed.

(* The whole comparison in one statement: both NaN, or equal, or zeros of an exact zero
   product. *)
Theorem mult_prod_same :
  forall a b : float,
  (is_nan prec emax (mult a b) = true /\ is_nan prec emax (prod a b) = true) \/
  mult a b = prod a b \/
  (fin a /\ fin b /\ b2r a * b2r b = 0 /\ zero (mult a b) /\ prod a b = pzero).
Proof.
intros a b. destruct (mult_prod_cases a b) as [H|[[E _]|[Fa [Fb [K [E1 E2]]]]]].
- now left.
- right. now left.
- right. right. repeat split; trivial. eexists. exact E1.
Qed.

(* The successors of the two results are equal whenever they are not NaN: the successor
   of either zero is the smallest positive number. Hence succ(a * b) is rmul(a, b), bit
   for bit, whenever the product is not a NaN. *)
Theorem succ_mult_prod :
  forall a b : float,
  is_nan prec emax (mult a b) = false -> fsucc (mult a b) = fsucc (prod a b).
Proof.
intros a b N. destruct (mult_prod_cases a b) as [[N1 _]|[[E _]|[_ [_ [_ [E1 E2]]]]]].
- congruence.
- now rewrite E.
- rewrite E1, E2. destruct (xorb (Bsign prec emax a) (Bsign prec emax b)); reflexivity.
Qed.

Corollary rmul_two_executions :
  forall a b : float,
  is_nan prec emax (mult a b) = false ->
  fsucc (mult a b) = IeeeModel.rmul prec emax nan_fma a b.
Proof. intros a b N. unfold IeeeModel.rmul. cbv zeta. now apply succ_mult_prod. Qed.

End TwoExecutions.
