(* Single operations of the IEEE model (IeeeDraft.v) on all values: finite numbers,
   infinities and NaN.

   IeeeBridge.v describes add, sub, fma and neg on finite operands. The non-finite layer
   also needs to know what the operations do with the other values, and it uses
   operations for which "a non-finite operand gives a non-finite result" is false:
   comparisons, selections and steps to a neighbor. This file states, for each
   operation, what the proofs of the layer use:

   - the tests of the fix-ups: lt (abs z) inf is true exactly when z is finite;
     lt r inf is true exactly when r is finite or -infinity; eq x x is false exactly
     when x is a NaN;
   - times_inf t, which makes a leading value t canonical: a NaN or a zero t gives a NaN,
     any other t the infinity of its sign;
   - guard: the value and the finiteness of its operand are kept, a zero comes out as
     +0, an infinity is unchanged, a NaN stays a NaN (guard_ieee);
   - comparisons of finite numbers are those of their real values;
   - succ: on a finite x it is the successor of the real model when that is below
     2^emax and +infinity otherwise; succ (+infinity) = +infinity; a NaN stays a NaN;
     and succ never returns -infinity. Hence on a value that is nonnegative,
     +infinity or NaN (nonneg_ext), succ returns such a value, and a finite result
     means a finite operand;
   - add, prod and fma on such values, and so radd and rmul: the result is again
     nonnegative, +infinity or NaN, and when it is finite the operands were finite and
     it is the value of the real model. A radius computation contains no -infinity,
     which is what makes the test lt (rz, inf) of the Ball fix-up mean "finite";
   - abs_2, to_up_2, abs_upper_2 on a finite pair;
   - const_of r is the finite number of value r, for r a number of the format below
     2^emax in magnitude; a nonnegative expression rounded up and bounded by such a
     number is one (const_of_RU). *)
From Stdlib Require Import Reals ZArith List Arith Bool Lia Lra.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements.
From Kairn Require Import Format Normalized Program IeeeBridge
  IeeeStatementsDraft IeeeExtStatementsDraft.
From Kairn Require IeeeDraft.
Open Scope R_scope.

Section IeeeOps.
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

Notation emin := (3 - emax - prec)%Z.
Notation fexp := (FLT_exp emin prec).
Notation format := (generic_format radix2 fexp).
Notation rnd := (round radix2 fexp (Znearest tie_even)).
Notation fin x := (is_finite prec emax x = true).
Notation b2r := (B2R prec emax).
Notation add := (IeeeDraft.add prec emax nan_plus).
Notation sub := (IeeeDraft.sub prec emax nan_minus).
Notation neg := (IeeeDraft.neg prec emax nan_opp).
Notation fabs := (IeeeDraft.abs prec emax nan_abs).
Notation fma := (IeeeDraft.fma prec emax nan_fma).
Notation prod := (IeeeDraft.prod prec emax nan_fma).
Notation times_inf := (IeeeDraft.times_inf prec emax nan_mult).
Notation flt := (IeeeDraft.lt prec emax).
Notation fle := (IeeeDraft.le prec emax).
Notation feq := (IeeeDraft.eq prec emax).
Notation fsucc := (IeeeDraft.succ prec emax).
Notation fpred := (IeeeDraft.pred prec emax).
Notation guard := (IeeeDraft.guard prec emax nan_plus).
Notation pzero := (IeeeDraft.pzero prec emax).
Notation pinf := (IeeeDraft.pinf prec emax).
Notation ninf := (B754_infinity prec emax true).
Notation inrange := (inrange emax).

Let Hprec : (0 < prec)%Z.
Proof. exact prec_gt_0_. Qed.
Let Hemax : (prec < emax)%Z.
Proof. exact prec_lt_emax_. Qed.

(** * The three kinds of values *)

Lemma nan_not_finite : forall x : float, is_nan prec emax x = true -> is_finite prec emax x = false.
Proof. intros [s|s|s pl H|s m e H]; try discriminate; reflexivity. Qed.

Lemma finite_not_nan : forall x : float, fin x -> is_nan prec emax x = false.
Proof. intros [s|s|s pl H|s m e H]; try discriminate; reflexivity. Qed.

Lemma not_finite_cases :
  forall x : float, is_finite prec emax x = false ->
  is_nan prec emax x = true \/ exists s : bool, x = B754_infinity prec emax s.
Proof.
intros [s|s|s pl H|s m e H]; try discriminate; intros _.
- right. now exists s.
- now left.
Qed.

Lemma finite_dec : forall x : float, fin x \/ is_finite prec emax x = false.
Proof. intros x. destruct (is_finite prec emax x); auto. Qed.

(* The sign of a finite number that is not zero is that of its value. *)
Lemma finite_sign_neg :
  forall (m : positive) (e : Z) H, b2r (B754_finite prec emax true m e H) < 0.
Proof. intros m e H. exact (F2R_lt_0 radix2 (Float radix2 (Zneg m) e) eq_refl). Qed.

Lemma finite_sign_pos :
  forall (m : positive) (e : Z) H, 0 < b2r (B754_finite prec emax false m e H).
Proof. intros m e H. exact (F2R_gt_0 radix2 (Float radix2 (Zpos m) e) eq_refl). Qed.

Lemma zero_inv : forall x : float, fin x -> b2r x = 0 -> exists s : bool, x = B754_zero prec emax s.
Proof.
intros [s|s|s pl H|s m e H]; try discriminate; intros _ E.
- now exists s.
- exfalso. destruct s.
  + generalize (finite_sign_neg m e H). lra.
  + generalize (finite_sign_pos m e H). lra.
Qed.

Lemma pos_sign : forall x : float, 0 < b2r x -> Bsign prec emax x = false.
Proof.
intros [s|s|s pl H|s m e H] K; try (simpl in K; lra).
destruct s; trivial.
generalize (finite_sign_neg m e H). lra.
Qed.

Lemma neg_sign : forall x : float, b2r x < 0 -> Bsign prec emax x = true.
Proof.
intros [s|s|s pl H|s m e H] K; try (simpl in K; lra).
destruct s; trivial.
generalize (finite_sign_pos m e H). lra.
Qed.

Lemma B2FF_inf_inv :
  forall (z : float) (s : bool), B2FF prec emax z = F754_infinity s -> z = B754_infinity prec emax s.
Proof. intros [s'|s'|s' pl H|s' m e H] s E; try discriminate E. now inversion E. Qed.

Lemma overflow_NE :
  forall s : bool, binary_overflow prec emax BinarySingleNaN.mode_NE s = F754_infinity s.
Proof. intros s. reflexivity. Qed.

(** * The tests of the fix-ups *)

Lemma lt_abs_pinf : forall z : float, flt (fabs z) pinf = is_finite prec emax z.
Proof. intros [s|s|s pl H|s m e H]; reflexivity. Qed.

Lemma lt_pinf_inv : forall r : float, flt r pinf = true -> fin r \/ r = ninf.
Proof.
intros [s|[|]|s pl H|s m e H] E; try discriminate E.
- left. reflexivity.
- right. reflexivity.
- left. reflexivity.
Qed.

Lemma lt_pinf_finite : forall r : float, fin r -> flt r pinf = true.
Proof. intros [s|s|s pl H|s m e H] E; try discriminate E; reflexivity. Qed.

Lemma eq_self : forall x : float, feq x x = negb (is_nan prec emax x).
Proof.
intros x. unfold IeeeDraft.eq. rewrite <- (is_nan_B2BSN prec emax x).
apply BinarySingleNaN.Beqb_refl.
Qed.

(** * times_inf t: the multiplication by +infinity *)

Lemma times_inf_inf : forall s : bool, times_inf (B754_infinity prec emax s) = B754_infinity prec emax s.
Proof. intros [|]; reflexivity. Qed.

Lemma times_inf_finite :
  forall (s : bool) (m : positive) (e : Z) H,
  times_inf (B754_finite prec emax s m e H) = B754_infinity prec emax s.
Proof. intros [|] m e H; reflexivity. Qed.

Lemma times_inf_zero : forall s : bool, is_nan prec emax (times_inf (B754_zero prec emax s)) = true.
Proof. intros s. reflexivity. Qed.

Lemma times_inf_nan : forall t : float, is_nan prec emax t = true -> is_nan prec emax (times_inf t) = true.
Proof. intros [s|s|s pl H|s m e H]; try discriminate; reflexivity. Qed.

Lemma times_inf_cases :
  forall t : float,
  is_nan prec emax (times_inf t) = true \/ exists s : bool, times_inf t = B754_infinity prec emax s.
Proof.
intros [s|s|s pl H|s m e H].
- left. apply times_inf_zero.
- right. exists s. apply times_inf_inf.
- left. now apply times_inf_nan.
- right. exists s. apply times_inf_finite.
Qed.

(* A finite t that is not zero becomes the infinity of the sign of its value. *)
Lemma times_inf_sign :
  forall t : float, fin t -> b2r t <> 0 ->
  times_inf t = B754_infinity prec emax (Rlt_bool (b2r t) 0).
Proof.
intros [s|s|s pl H|s m e H] F Z; try discriminate F.
- now elim Z.
- rewrite times_inf_finite. f_equal. destruct s.
  + symmetry. apply Rlt_bool_true. apply finite_sign_neg.
  + symmetry. apply Rlt_bool_false. left. apply finite_sign_pos.
Qed.

(** * The guard *)

Lemma guard_finite : forall a : float, is_finite prec emax (guard a) = is_finite prec emax a.
Proof. intros [[|]|s|s pl H|s m e H]; reflexivity. Qed.

Lemma guard_val : forall a : float, b2r (guard a) = b2r a.
Proof. intros [[|]|s|s pl H|s m e H]; reflexivity. Qed.

Lemma guard_zero : forall s : bool, guard (B754_zero prec emax s) = pzero.
Proof. intros [|]; reflexivity. Qed.

Lemma guard_inf : forall s : bool, guard (B754_infinity prec emax s) = B754_infinity prec emax s.
Proof. intros s. reflexivity. Qed.

Lemma guard_nan : forall a : float, is_nan prec emax (guard a) = is_nan prec emax a.
Proof. intros [[|]|s|s pl H|s m e H]; reflexivity. Qed.

Lemma guard_finite_nonzero :
  forall (s : bool) (m : positive) (e : Z) H,
  guard (B754_finite prec emax s m e H) = B754_finite prec emax s m e H.
Proof. intros s m e H. reflexivity. Qed.

(** * Operations with an operand that is not finite *)

Lemma add_not_finite :
  forall x y : float, is_finite prec emax x = false \/ is_finite prec emax y = false ->
  is_finite prec emax (add x y) = false.
Proof.
intros x y H. destruct (is_finite prec emax (add x y)) eqn:E; trivial.
apply (add_finite_inv prec emax nan_plus) in E. destruct E as [E1 E2].
destruct H as [H|H]; congruence.
Qed.

Lemma sub_not_finite :
  forall x y : float, is_finite prec emax x = false \/ is_finite prec emax y = false ->
  is_finite prec emax (sub x y) = false.
Proof.
intros x y H. destruct (is_finite prec emax (sub x y)) eqn:E; trivial.
apply (sub_finite_inv prec emax nan_minus) in E. destruct E as [E1 E2].
destruct H as [H|H]; congruence.
Qed.

Lemma prod_not_finite :
  forall x y : float, is_finite prec emax x = false \/ is_finite prec emax y = false ->
  is_finite prec emax (prod x y) = false.
Proof.
intros x y H. destruct (is_finite prec emax (prod x y)) eqn:E; trivial.
unfold IeeeDraft.prod in E. apply (fma_finite_inv prec emax nan_fma) in E.
destruct E as [E1 [E2 _]]. destruct H as [H|H]; congruence.
Qed.

Lemma add_nan_l : forall x y : float, is_nan prec emax x = true -> is_nan prec emax (add x y) = true.
Proof.
intros [s|s|s pl H|s m e H] y; try discriminate; intros _.
destruct y; reflexivity.
Qed.

Lemma add_nan_r : forall x y : float, is_nan prec emax y = true -> is_nan prec emax (add x y) = true.
Proof.
intros x [s|s|s pl H|s m e H]; try discriminate; intros _.
destruct x; reflexivity.
Qed.

(** * Comparisons of finite numbers *)

Lemma lt_finite : forall a b : float, fin a -> fin b -> flt a b = Rlt_bool (b2r a) (b2r b).
Proof.
intros a b Fa Fb. unfold IeeeDraft.lt.
rewrite <- (B2R_B2BSN prec emax a), <- (B2R_B2BSN prec emax b).
apply BinarySingleNaN.Bltb_correct; now rewrite is_finite_B2BSN.
Qed.

Lemma le_finite : forall a b : float, fin a -> fin b -> fle a b = Rle_bool (b2r a) (b2r b).
Proof.
intros a b Fa Fb. unfold IeeeDraft.le.
rewrite <- (B2R_B2BSN prec emax a), <- (B2R_B2BSN prec emax b).
apply BinarySingleNaN.Bleb_correct; now rewrite is_finite_B2BSN.
Qed.

Lemma eq_finite : forall a b : float, fin a -> fin b -> feq a b = Req_bool (b2r a) (b2r b).
Proof.
intros a b Fa Fb. unfold IeeeDraft.eq.
rewrite <- (B2R_B2BSN prec emax a), <- (B2R_B2BSN prec emax b).
apply BinarySingleNaN.Beqb_correct; now rewrite is_finite_B2BSN.
Qed.

(** * succ and pred *)

Lemma B2BSN_succ :
  forall x : float, B2BSN prec emax (fsucc x) = BinarySingleNaN.Bsucc (B2BSN prec emax x).
Proof. intros x. unfold IeeeDraft.succ, Bsucc. apply B2BSN_lift. Qed.

Lemma succ_nan : forall x : float, is_nan prec emax (fsucc x) = is_nan prec emax x.
Proof.
intros x. rewrite <- (is_nan_B2BSN prec emax (fsucc x)), B2BSN_succ.
rewrite BinarySingleNaN.is_nan_Bsucc. apply is_nan_B2BSN.
Qed.

Lemma B2BSN_inf_inv :
  forall (z : float) (s : bool),
  B2BSN prec emax z = @BinarySingleNaN.B754_infinity prec emax s -> z = B754_infinity prec emax s.
Proof. intros [s'|s'|s' pl H|s' m e H] s E; try discriminate E. now inversion E. Qed.

Lemma succ_pinf : fsucc pinf = pinf.
Proof. apply B2BSN_inf_inv. rewrite B2BSN_succ. reflexivity. Qed.

(* On a finite x: the successor of the real model, or +infinity when that is 2^emax. *)
Lemma succ_finite :
  forall x : float, fin x ->
  (fin (fsucc x) /\ b2r (fsucc x) = Ulp.succ radix2 fexp (b2r x) /\
   Ulp.succ radix2 fexp (b2r x) < bpow radix2 emax) \/
  (fsucc x = pinf /\ bpow radix2 emax <= Ulp.succ radix2 fexp (b2r x)).
Proof.
intros x Fx.
generalize (Bsucc_correct prec emax prec_gt_0_ prec_lt_emax_ x Fx).
change (Bsucc prec emax prec_gt_0_ prec_lt_emax_ x) with (fsucc x).
change (SpecFloat.fexp prec emax) with fexp.
destruct (Rlt_bool_spec (Ulp.succ radix2 fexp (b2r x)) (bpow radix2 emax)) as [H|H].
- intros [E [F _]]. left. auto.
- intros E. right. split; trivial. now apply B2FF_inf_inv.
Qed.

(* succ never returns -infinity. *)
Lemma succ_not_ninf : forall x : float, fsucc x <> ninf.
Proof.
intros x E.
assert (K : B2BSN prec emax (fsucc x) = @BinarySingleNaN.B754_infinity prec emax true)
  by now rewrite E.
rewrite B2BSN_succ in K.
destruct x as [s|[|]|s pl H|s m e H]; try discriminate K.
assert (F : fin (B754_finite prec emax s m e H)) by reflexivity.
destruct (succ_finite _ F) as [[F' _]|[E' _]]; rewrite E in *; discriminate.
Qed.

(* On a finite x: the predecessor of the real model, or -infinity when that is -2^emax. *)
Lemma pred_finite :
  forall x : float, fin x ->
  (fin (fpred x) /\ b2r (fpred x) = Ulp.pred radix2 fexp (b2r x) /\
   - bpow radix2 emax < Ulp.pred radix2 fexp (b2r x)) \/
  (fpred x = ninf /\ Ulp.pred radix2 fexp (b2r x) <= - bpow radix2 emax).
Proof.
intros x Fx.
generalize (Bpred_correct prec emax prec_gt_0_ prec_lt_emax_ x Fx).
change (Bpred prec emax prec_gt_0_ prec_lt_emax_ x) with (fpred x).
change (SpecFloat.fexp prec emax) with fexp.
destruct (Rlt_bool_spec (- bpow radix2 emax) (Ulp.pred radix2 fexp (b2r x))) as [H|H].
- intros [E [F _]]. left. auto.
- intros E. right. split; trivial. now apply B2FF_inf_inv.
Qed.

(** * Values that are nonnegative, +infinity or NaN *)

Lemma nonneg_ext_finite : forall x : float, fin x -> 0 <= b2r x -> nonneg_ext x.
Proof. intros x F P. right. right. split; assumption. Qed.

Lemma nonneg_ext_pinf : nonneg_ext pinf.
Proof. right. left. reflexivity. Qed.

Lemma nonneg_ext_nan : forall x : float, is_nan prec emax x = true -> nonneg_ext x.
Proof. intros x N. left. exact N. Qed.

Lemma nonneg_ext_fin : forall x : float, nonneg_ext x -> fin x -> 0 <= b2r x.
Proof.
intros x [N|[I|[_ P]]] F; trivial.
- apply nan_not_finite in N. congruence.
- rewrite I in F. discriminate F.
Qed.

Lemma nonneg_ext_not_ninf : forall x : float, nonneg_ext x -> x <> ninf.
Proof.
intros x [N|[I|[F _]]] E; rewrite E in *; discriminate.
Qed.

(* A value of this kind that passes the test lt r inf is finite. *)
Lemma nonneg_ext_lt_pinf : forall r : float, nonneg_ext r -> flt r pinf = true -> fin r.
Proof.
intros r Hr L. destruct (lt_pinf_inv r L) as [F|E]; trivial.
now elim (nonneg_ext_not_ninf r Hr).
Qed.

Lemma succ_nonneg :
  forall x : float, nonneg_ext x ->
  nonneg_ext (fsucc x) /\
  (fin (fsucc x) -> fin x /\ b2r (fsucc x) = Ulp.succ radix2 fexp (b2r x)).
Proof.
intros x [N|[I|[F P]]].
- assert (N' : is_nan prec emax (fsucc x) = true) by now rewrite succ_nan.
  split. now left. intros F. apply nan_not_finite in N'. congruence.
- rewrite I. change (infinity prec emax false) with pinf. rewrite succ_pinf.
  split. apply nonneg_ext_pinf. discriminate.
- destruct (succ_finite x F) as [[F' [E L]]|[E L]].
  + split.
    * apply nonneg_ext_finite; trivial. rewrite E.
      apply Rle_trans with (1 := P). apply succ_ge_id.
    * intros _. split; assumption.
  + rewrite E. split. apply nonneg_ext_pinf. discriminate.
Qed.

Lemma add_nonneg :
  forall a b : float, nonneg_ext a -> nonneg_ext b ->
  nonneg_ext (add a b) /\
  (fin (add a b) -> fin a /\ fin b /\ b2r (add a b) = rnd (b2r a + b2r b)) /\
  (is_nan prec emax (add a b) = true <-> is_nan prec emax a = true \/ is_nan prec emax b = true).
Proof.
intros a b Ha Hb.
assert (Second : fin (add a b) -> fin a /\ fin b /\ b2r (add a b) = rnd (b2r a + b2r b)).
{ intros F. destruct (add_finite_inv prec emax nan_plus a b F) as [Fa Fb].
  split; [exact Fa|split; [exact Fb|]].
  now apply (add_spec prec emax nan_plus a b Fa Fb). }
(* the sum, when neither operand is a NaN: +infinity or a nonnegative number *)
assert (Main : is_nan prec emax a = false -> is_nan prec emax b = false ->
               add a b = pinf \/ (fin (add a b) /\ 0 <= b2r (add a b))).
{ intros Na Nb.
  destruct Ha as [N|[I|[Fa Pa]]]; [unfold nan in N; congruence| |];
  destruct Hb as [N|[I'|[Fb Pb]]]; try (unfold nan in N; congruence).
  - left. rewrite I, I'. reflexivity.
  - left. rewrite I. destruct b as [s|s|s pl H|s m e H]; try discriminate Fb; reflexivity.
  - left. rewrite I'. destruct a as [s|s|s pl H|s m e H]; try discriminate Fa; reflexivity.
  - generalize (Bplus_correct prec emax prec_gt_0_ prec_lt_emax_ nan_plus
                  BinarySingleNaN.mode_NE a b Fa Fb).
    fold (add a b).
    change (round radix2 (SpecFloat.fexp prec emax)
              (BinarySingleNaN.round_mode BinarySingleNaN.mode_NE) (b2r a + b2r b))
      with (rnd (b2r a + b2r b)).
    destruct (Rlt_bool_spec (Rabs (rnd (b2r a + b2r b))) (bpow radix2 emax)) as [H|H].
    + intros [E [F _]]. right. split; trivial. rewrite E.
      apply round_ge_generic; auto with typeclass_instances. apply generic_format_0.
      unfold val in *. lra.
    + intros [E S]. left. apply B2FF_inf_inv. rewrite E, overflow_NE. f_equal.
      (* one of the operands is positive, and they have the same sign *)
      assert (Z : b2r a + b2r b <> 0).
      { intros Z. rewrite Z, round_0, Rabs_R0 in H; auto with typeclass_instances.
        generalize (bpow_gt_0 radix2 emax). lra. }
      unfold val in *.
      destruct (Rle_lt_or_eq_dec 0 (b2r a) Pa) as [Q|Q].
      * now apply pos_sign.
      * rewrite S. apply pos_sign. lra. }
split; [|split; [exact Second|]].
- destruct (is_nan prec emax a) eqn:Na.
  { left. now apply add_nan_l. }
  destruct (is_nan prec emax b) eqn:Nb.
  { left. now apply add_nan_r. }
  destruct (Main eq_refl eq_refl) as [E|[F P]].
  + rewrite E. apply nonneg_ext_pinf.
  + now apply nonneg_ext_finite.
- split.
  + intros N. destruct (is_nan prec emax a) eqn:Na; [now left|].
    destruct (is_nan prec emax b) eqn:Nb; [now right|].
    destruct (Main eq_refl eq_refl) as [E|[F P]].
    * rewrite E in N. discriminate N.
    * apply finite_not_nan in F. congruence.
  + intros [N|N]. now apply add_nan_l. now apply add_nan_r.
Qed.

Lemma prod_nonneg :
  forall a b : float, nonneg_ext a -> nonneg_ext b ->
  nonneg_ext (prod a b) /\
  (fin (prod a b) -> fin a /\ fin b /\ b2r (prod a b) = rnd (b2r a * b2r b + 0)).
Proof.
intros a b Ha Hb.
split.
- destruct (is_nan prec emax (prod a b)) eqn:Np.
  { now left. }
  destruct Ha as [N|[I|[Fa Pa]]].
  { exfalso. unfold nan in N. destruct a as [s|s|s pl H|s m e H]; try discriminate N.
    destruct b; discriminate Np. }
  + (* a = +infinity *)
    rewrite I in Np |- *. destruct Hb as [N|[I'|[Fb Pb]]].
    * exfalso. unfold nan in N. destruct b as [s|s|s pl H|s m e H]; try discriminate N.
      discriminate Np.
    * rewrite I'. apply nonneg_ext_pinf.
    * destruct b as [s|s|s pl H|s m e H]; try discriminate Fb; try discriminate Np.
      destruct s.
      -- exfalso. generalize (finite_sign_neg m e H). unfold val in Pb. lra.
      -- apply nonneg_ext_pinf.
  + destruct Hb as [N|[I'|[Fb Pb]]].
    * exfalso. unfold nan in N. destruct b as [s|s|s pl H|s m e H]; try discriminate N.
      destruct a; discriminate Np.
    * (* b = +infinity *)
      rewrite I' in Np |- *.
      destruct a as [s|s|s pl H|s m e H]; try discriminate Fa; try discriminate Np.
      destruct s.
      -- exfalso. generalize (finite_sign_neg m e H). unfold val in Pa. lra.
      -- apply nonneg_ext_pinf.
    * (* both finite *)
      assert (P : 0 <= b2r a * b2r b + b2r pzero).
      { change (b2r pzero) with 0. rewrite Rplus_0_r. now apply Rmult_le_pos. }
      generalize (Bfma_correct prec emax prec_gt_0_ prec_lt_emax_ nan_fma
                    BinarySingleNaN.mode_NE a b pzero Fa Fb eq_refl).
      cbv zeta. fold (fma a b pzero). fold (prod a b).
      change (round radix2 (SpecFloat.fexp prec emax)
                (BinarySingleNaN.round_mode BinarySingleNaN.mode_NE) (b2r a * b2r b + b2r pzero))
        with (rnd (b2r a * b2r b + b2r pzero)).
      destruct (Rlt_bool_spec (Rabs (rnd (b2r a * b2r b + b2r pzero))) (bpow radix2 emax)) as [H|H].
      -- intros [E [F _]]. apply nonneg_ext_finite; trivial. rewrite E.
         apply round_ge_generic; auto with typeclass_instances. apply generic_format_0.
      -- intros E. rewrite Rlt_bool_false in E by exact P.
         rewrite overflow_NE in E. apply B2FF_inf_inv in E. rewrite E. apply nonneg_ext_pinf.
- intros F. unfold IeeeDraft.prod in F.
  destruct (fma_finite_inv prec emax nan_fma a b pzero F) as [Fa [Fb _]].
  split; [exact Fa|split; [exact Fb|]].
  change (rnd (b2r a * b2r b + 0)) with (rnd (b2r a * b2r b + b2r pzero)).
  now apply (fma_spec prec emax nan_fma a b pzero Fa Fb eq_refl).
Qed.

(** * radd and rmul *)

Notation radd := (IeeeDraft.radd prec emax nan_plus).
Notation rmul := (IeeeDraft.rmul prec emax nan_fma).

Lemma radd_nonneg :
  forall a b : float, nonneg_ext a -> nonneg_ext b ->
  nonneg_ext (radd a b) /\
  (fin (radd a b) ->
   fin a /\ fin b /\ b2r (radd a b) = Model.radd emin prec tie_even (b2r a) (b2r b)).
Proof.
intros a b Ha Hb. unfold IeeeDraft.radd. cbv zeta.
destruct (add_nonneg a b Ha Hb) as [Hs [Fs _]].
destruct (succ_nonneg (add a b) Hs) as [Hr Fr].
split. exact Hr.
intros F. destruct (Fr F) as [F1 E]. destruct (Fs F1) as [Fa [Fb E1]].
split; [exact Fa|split; [exact Fb|]]. rewrite E, E1. reflexivity.
Qed.

Lemma rmul_nonneg :
  forall a b : float, nonneg_ext a -> nonneg_ext b ->
  nonneg_ext (rmul a b) /\
  (fin (rmul a b) ->
   fin a /\ fin b /\ b2r (rmul a b) = Model.rmul emin prec tie_even (b2r a) (b2r b)).
Proof.
intros a b Ha Hb. unfold IeeeDraft.rmul. cbv zeta.
destruct (prod_nonneg a b Ha Hb) as [Hs Fs].
destruct (succ_nonneg (prod a b) Hs) as [Hr Fr].
split. exact Hr.
intros F. destruct (Fr F) as [F1 E]. destruct (Fs F1) as [Fa [Fb E1]].
split; [exact Fa|split; [exact Fb|]]. rewrite E, E1. reflexivity.
Qed.

(** * The absolute value of one limb *)

Lemma abs_nonneg : forall a : float, nonneg_ext (fabs a).
Proof.
intros [s|s|s pl H|s m e H].
- apply nonneg_ext_finite. reflexivity. unfold val. simpl. lra.
- apply nonneg_ext_pinf.
- apply nonneg_ext_nan. reflexivity.
- apply nonneg_ext_finite. reflexivity.
  left. exact (finite_sign_pos m e H).
Qed.

Lemma abs_finite : forall a : float, is_finite prec emax (fabs a) = is_finite prec emax a.
Proof. intros a. apply is_finite_Babs. Qed.

Lemma abs_val : forall a : float, b2r (fabs a) = Rabs (b2r a).
Proof. intros a. apply B2R_Babs. Qed.

(** * abs_2, to_up_2 and abs_upper_2 on a finite pair *)

Notation abs_upper_2 := (IeeeDraft.abs_upper_2 prec emax nan_opp).

Lemma abs_upper_2_nonneg :
  forall x0 x1 : float, fin x0 -> fin x1 ->
  nonneg_ext (abs_upper_2 x0 x1) /\
  (fin (abs_upper_2 x0 x1) ->
   b2r (abs_upper_2 x0 x1) = Model.abs_upper_2 emin prec (b2r x0) (b2r x1)).
Proof.
intros x0 x1 F0 F1.
unfold IeeeDraft.abs_upper_2, IeeeDraft.abs_2, IeeeDraft.to_up_2,
       Model.abs_upper_2, Model.abs_2, Model.to_up_2.
cbv beta iota zeta.
rewrite (lt_finite x0 pzero F0 eq_refl). change (b2r pzero) with 0.
assert (Fn0 : fin (neg x0)) by (unfold IeeeDraft.neg; now rewrite is_finite_Bopp).
assert (Fn1 : fin (neg x1)) by (unfold IeeeDraft.neg; now rewrite is_finite_Bopp).
assert (En0 : b2r (neg x0) = - b2r x0) by apply B2R_Bopp.
assert (En1 : b2r (neg x1) = - b2r x1) by apply B2R_Bopp.
destruct (Rlt_bool_spec (b2r x0) 0) as [M|M].
- rewrite (lt_finite pzero (neg x1) eq_refl Fn1). change (b2r pzero) with 0. rewrite En1.
  assert (Ha : nonneg_ext (neg x0)) by (apply nonneg_ext_finite; trivial; rewrite En0; lra).
  destruct (Rlt_bool 0 (- b2r x1)).
  + destruct (succ_nonneg (neg x0) Ha) as [Hr Fr]. split. exact Hr.
    intros F. destruct (Fr F) as [_ E]. now rewrite E, En0.
  + split. exact Ha. intros _. exact En0.
- rewrite (lt_finite pzero x1 eq_refl F1). change (b2r pzero) with 0.
  assert (Ha : nonneg_ext x0) by (apply nonneg_ext_finite; trivial).
  destruct (Rlt_bool 0 (b2r x1)).
  + destruct (succ_nonneg x0 Ha) as [Hr Fr]. split. exact Hr.
    intros F. destruct (Fr F) as [_ E]. exact E.
  + split. exact Ha. intros _. reflexivity.
Qed.

(** * Constants *)

Notation const_of := (IeeeDraft.const_of prec emax).

(* const_of r is the finite number of value r, when there is one. *)
Lemma const_of_spec :
  forall r : R, format r -> Rabs r < bpow radix2 emax ->
  fin (const_of r) /\ b2r (const_of r) = r.
Proof.
intros r Fr Hr. unfold IeeeDraft.const_of.
generalize (binary_normalize_correct prec emax prec_gt_0_ prec_lt_emax_ BinarySingleNaN.mode_NE
              (Ztrunc (scaled_mantissa radix2 fexp r)) (cexp radix2 fexp r) false).
assert (E : F2R (Float radix2 (Ztrunc (scaled_mantissa radix2 fexp r)) (cexp radix2 fexp r)) = r)
  by (symmetry; exact Fr).
rewrite E.
change (round radix2 (SpecFloat.fexp prec emax)
          (BinarySingleNaN.round_mode BinarySingleNaN.mode_NE) r) with (rnd r).
rewrite round_generic by (auto with typeclass_instances).
rewrite Rlt_bool_true by exact Hr.
intros [E1 [F1 _]]. split; assumption.
Qed.

(* A nonnegative number of the format that is at most 1 is below 2^emax. *)
Lemma le_1_inrange : forall r : R, 0 <= r <= 1 -> Rabs r < bpow radix2 emax.
Proof.
intros r [H0 H1]. rewrite Rabs_pos_eq by exact H0.
apply Rle_lt_trans with (1 := H1). change 1 with (bpow radix2 0). apply bpow_lt. lia.
Qed.

Lemma format_1 : format 1.
Proof.
change 1 with (bpow radix2 0). apply generic_format_bpow. unfold FLT_exp. lia.
Qed.

(* A nonnegative expression t rounded up, when it is at most a number B of the format
   that is below 2^emax: const_of gives the finite number of that value. This is how
   the constants of the Ball kernels enter the IEEE model. *)
Lemma const_of_RU :
  forall t B : R, 0 <= t -> t <= B -> format B -> B < bpow radix2 emax ->
  fin (const_of (round radix2 fexp Zceil t)) /\
  b2r (const_of (round radix2 fexp Zceil t)) = round radix2 fexp Zceil t /\
  nonneg_ext (const_of (round radix2 fexp Zceil t)).
Proof.
intros t B Ht HB FB LB.
assert (P : 0 <= round radix2 fexp Zceil t).
{ apply round_ge_generic; auto with typeclass_instances. apply generic_format_0. }
assert (L : round radix2 fexp Zceil t <= B).
{ apply round_le_generic; auto with typeclass_instances. }
destruct (const_of_spec (round radix2 fexp Zceil t)) as [F E].
{ apply generic_format_round; auto with typeclass_instances. }
{ rewrite Rabs_pos_eq by exact P. lra. }
split; [exact F|split; [exact E|]].
apply nonneg_ext_finite; trivial. unfold val. now rewrite E.
Qed.

(** * fma on values that are nonnegative, +infinity or NaN *)

Lemma fma_nan :
  forall a b c : float,
  is_nan prec emax a = true \/ is_nan prec emax b = true \/ is_nan prec emax c = true ->
  is_nan prec emax (fma a b c) = true.
Proof.
intros [sa|sa|sa pa Ha|sa ma ea Ha] [sb|sb|sb pb Hb|sb mb eb Hb] [sc|sc|sc pc Hc|sc mc ec Hc]
  [K|[K|K]]; try discriminate K; reflexivity.
Qed.

Lemma nonneg_ext_cases :
  forall x : float, nonneg_ext x ->
  is_nan prec emax x = true \/ x = pinf \/
  ((exists s : bool, x = B754_zero prec emax s) \/
   (exists m e H, x = B754_finite prec emax false m e H)).
Proof.
intros x [N|[I|[F P]]].
- now left.
- right. now left.
- right. right. destruct x as [s|s|s pl H|s m e H]; try discriminate F.
  + left. now exists s.
  + right. destruct s.
    * exfalso. generalize (finite_sign_neg m e H). unfold val in P. lra.
    * now exists m, e, H.
Qed.

(* The result is again nonnegative, +infinity or NaN: with nonnegative operands a fused
   operation cannot return -infinity. And, as for every operands, a finite result means
   finite operands and is the rounded real result. *)
Lemma fma_nonneg :
  forall a b c : float, nonneg_ext a -> nonneg_ext b -> nonneg_ext c ->
  nonneg_ext (fma a b c) /\
  (fin (fma a b c) ->
   fin a /\ fin b /\ fin c /\ b2r (fma a b c) = rnd (b2r a * b2r b + b2r c)).
Proof.
intros a b c Ha Hb Hc. split.
- destruct (finite_dec a) as [Fa|Fa]; destruct (finite_dec b) as [Fb|Fb];
    destruct (finite_dec c) as [Fc|Fc].
  1: { generalize (nonneg_ext_fin a Ha Fa) (nonneg_ext_fin b Hb Fb) (nonneg_ext_fin c Hc Fc).
       intros Pa Pb Pc.
       assert (P : 0 <= b2r a * b2r b + b2r c) by (generalize (Rmult_le_pos _ _ Pa Pb); lra).
       generalize (Bfma_correct prec emax prec_gt_0_ prec_lt_emax_ nan_fma
                     BinarySingleNaN.mode_NE a b c Fa Fb Fc).
       cbv zeta. fold (fma a b c).
       change (round radix2 (SpecFloat.fexp prec emax)
                 (BinarySingleNaN.round_mode BinarySingleNaN.mode_NE) (b2r a * b2r b + b2r c))
         with (rnd (b2r a * b2r b + b2r c)).
       destruct (Rlt_bool_spec (Rabs (rnd (b2r a * b2r b + b2r c))) (bpow radix2 emax)) as [H|H].
       - intros [E [F _]]. apply nonneg_ext_finite; trivial. rewrite E.
         apply round_ge_generic; auto with typeclass_instances. apply generic_format_0.
       - intros E. rewrite Rlt_bool_false in E by exact P.
         rewrite overflow_NE in E. apply B2FF_inf_inv in E. rewrite E. apply nonneg_ext_pinf. }
  all: (destruct (nonneg_ext_cases a Ha) as [Na|[Ia|Ka]]; [left; apply fma_nan; auto| |]);
       (destruct (nonneg_ext_cases b Hb) as [Nb|[Ib|Kb]]; [left; apply fma_nan; auto| |]);
       (destruct (nonneg_ext_cases c Hc) as [Nc|[Ic|Kc]]; [left; apply fma_nan; auto| |]);
       repeat match goal with
       | K : (exists s : bool, _ = B754_zero _ _ s) \/ _ |- _ =>
           destruct K as [[? K]|[? [? [? K]]]]
       end;
       subst;
       first [discriminate | left; reflexivity | right; left; reflexivity].
- intros F. destruct (fma_finite_inv prec emax nan_fma a b c F) as [Fa [Fb Fc]].
  split; [exact Fa|split; [exact Fb|split; [exact Fc|]]].
  now apply (fma_spec prec emax nan_fma a b c Fa Fb Fc).
Qed.

End IeeeOps.

(** * The statement of IeeeExtStatementsDraft.v *)

Theorem guard_ieee : guard_ieee_spec.
Proof.
intros prec emax Hp He nan_plus a g. unfold g. clear g.
unfold finite, val, zero, nan, infinity, pos_zero.
split; [|split; [|split; [|split]]].
- now rewrite (guard_finite prec emax nan_plus).
- apply guard_val.
- intros [s E]. rewrite E. apply guard_zero.
- intros s E. rewrite E. apply guard_inf.
- now rewrite (guard_nan prec emax nan_plus).
Qed.
