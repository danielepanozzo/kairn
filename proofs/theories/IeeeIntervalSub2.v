(* The difference of two intervals with bounds of two limbs, in the IEEE model, on all values:
   interval_sub_2 (docs/developer/design/milestone2.md, "Interval kernels": "Bounds of two
   limbs" and "Two limbs").

   Notation as in IeeeInterval2.v. X, Y are the operands and Z the result; A and B are the
   constants of the closed form of the directed sums (add_outward_rel, add_outward_abs of
   Directed2.v). The kernel is the generated model of proofs/gen/IeeeModel.v.

   What is proved, from precision 3: interval_sub_2, for canonical operands
   (interval_sub_2_correct, the generated statement, from interval_sub_2_all), with the same
   five parts as the sum:
     I1  Z is canonical;
     I2  Z is empty exactly when an operand is;
     I3  x - y is a member of Z for all members x of X and y of Y, unbounded operands
         included;
     I4  for bounded operands, with lo and hi the bounds of the exact range of x - y: if Z
         is bounded, lo - zl <= A |lo| + B and zu - hi <= A |hi| + B; a difference
         xl - yu that is exactly zero gives the lower bound lo (which is zero), and
         xu - yl = 0 the upper bound hi; and for nonempty operands a bound of the exact
         range that is infinite is that bound of Z;
     I5  for bounded operands, Z is bounded when every member of the exact range is at most
         2^(emax - 2) in magnitude.

   The proof: the listing is interval_add_2 on X and on the negated interval
   -Y = [-yu, -yl] (interval_sub_2_as_add). Its cores are sub_down_2_2(xl, yu), which is
   add_down_2_2 on xl and neg_2(yu), and sub_up_2_2(xu, yl), which is add_up_2_2 on xu and
   neg_2(yl); and its test of an empty operand, lt(yl0, inf), is the test lt(-yu0, inf) of
   the sum, for every canonical Y: both are true for a nonempty Y and false for the empty
   set ((+inf, 0), (-inf, 0)) (sub_test). The negated interval is canonical, empty, nonempty
   and bounded exactly when Y is, and its members are the opposites of Y's
   (interval_neg_2_facts of IeeeIntervalExact.v), so the exact range of x + y' over X and -Y
   is the exact range of x - y over X and Y (range_sub_2_as_add), with the same bounds; and
   the theorem of the sum (interval_add_2_all of IeeeInterval2.v) says the rest. *)
From Stdlib Require Import Reals ZArith Bool Lia Lra Psatz.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements IeeeStatements.
From Kairn Require Import Format Normalized Directed2 IeeeBridge IeeeVocabulary IeeeOps IeeeExt.
From Kairn Require Import IeeeDirected IeeeIntervalVocabulary IeeeInterval1 IeeeInterval2.
From Kairn Require Import IeeeIntervalExact.
From Kairn Require IeeeOperations.
From Kairn.Gen Require IeeeModel.
Open Scope R_scope.

Section IeeeIntervalSub2.
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

Notation emin := (3 - emax - prec)%Z.
Notation b2r := (B2R prec emax).
Notation neg := (IeeeOperations.neg prec emax nan_opp).
Notation flt := (IeeeOperations.lt prec emax).
Notation pinf := (IeeeOperations.pinf prec emax).
Notation xv := (@xval prec emax).
Notation xv2 := (@xval_2 prec emax).
Notation add_down_2_2 :=
  (IeeeModel.add_down_2_2 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma).
Notation add_up_2_2 := (IeeeModel.add_up_2_2 prec emax nan_plus nan_minus nan_abs nan_fma).
Notation sub_down_2_2 :=
  (IeeeModel.sub_down_2_2 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma).
Notation sub_up_2_2 :=
  (IeeeModel.sub_up_2_2 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma).
Notation interval_add_2 :=
  (IeeeModel.interval_add_2 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma).
Notation interval_sub_2 :=
  (IeeeModel.interval_sub_2 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma).

(** * The listing is the sum with the negated operand *)

Lemma sub_down_2_2_as_add :
  forall x0 x1 y0 y1 : float, sub_down_2_2 x0 x1 y0 y1 = add_down_2_2 x0 x1 (neg y0) (neg y1).
Proof.
intros x0 x1 y0 y1. unfold IeeeModel.sub_down_2_2, IeeeModel.neg_2. cbv beta iota zeta.
destruct (add_down_2_2 x0 x1 (neg y0) (neg y1)). reflexivity.
Qed.

Lemma sub_up_2_2_as_add :
  forall x0 x1 y0 y1 : float, sub_up_2_2 x0 x1 y0 y1 = add_up_2_2 x0 x1 (neg y0) (neg y1).
Proof.
intros x0 x1 y0 y1. unfold IeeeModel.sub_up_2_2, IeeeModel.neg_2. cbv beta iota zeta.
destruct (add_up_2_2 x0 x1 (neg y0) (neg y1)). reflexivity.
Qed.

(* The test of an empty operand: lt(yl0, inf) is lt(-yu0, inf) for a canonical Y. *)
Lemma sub_test :
  forall yl0 yl1 yu0 yu1 : float, interval_2 yl0 yl1 yu0 yu1 ->
  flt yl0 pinf = flt (neg yu0) pinf.
Proof.
intros yl0 yl1 yu0 yu1 CY.
rewrite (lt_xval prec emax yl0 pinf), (lt_xval prec emax (neg yu0) pinf).
rewrite (xval_neg prec emax nan_opp). change (xv pinf) with (XInf false).
rewrite xlt_opp_pinf.
rewrite <- (xlt_xval_2_pinf prec emax yl0 yl1), <- (xlt_ninf_xval_2 prec emax yu0 yu1).
destruct CY as [[E0 [_ [E2 _]]]|[_ [_ [_ [N1 N2]]]]].
- subst yl0 yu0. reflexivity.
- rewrite N1, N2. reflexivity.
Qed.

Lemma interval_sub_2_as_add :
  forall xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 : float,
  interval_2 yl0 yl1 yu0 yu1 ->
  interval_sub_2 xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1
  = interval_add_2 xl0 xl1 xu0 xu1 (neg yu0) (neg yu1) (neg yl0) (neg yl1).
Proof.
intros xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 CY.
unfold IeeeModel.interval_sub_2, IeeeModel.interval_add_2.
rewrite sub_down_2_2_as_add, sub_up_2_2_as_add, (sub_test yl0 yl1 yu0 yu1 CY).
reflexivity.
Qed.

(* The exact range of x + y' over X and -Y is the exact range of x - y over X and Y. *)
Lemma range_sub_2_as_add :
  forall (xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 : float) (z : R),
  range_2 (fun x y : R => x + y) (in_interval_2 xl0 xl1 xu0 xu1)
    (in_interval_2 (neg yu0) (neg yu1) (neg yl0) (neg yl1)) z <->
  range_2 (fun x y : R => x - y) (in_interval_2 xl0 xl1 xu0 xu1)
    (in_interval_2 yl0 yl1 yu0 yu1) z.
Proof.
intros xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 z. unfold range_2, in_interval_2.
rewrite 2!(xval_2_neg prec emax nan_opp).
exact (range_sub_add (xv2 xl0 xl1) (xv2 xu0 xu1) (xv2 yl0 yl1) (xv2 yu0 yu1) z).
Qed.

(** * interval_sub_2 *)

(* interval_sub_2, for canonical operands X and Y, from precision 3: I1 to I5 as the
   generated statement has them, with the constants of the closed form by name. *)
Theorem interval_sub_2_all :
  (3 <= prec)%Z ->
  forall xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 : float,
  interval_2 xl0 xl1 xu0 xu1 -> interval_2 yl0 yl1 yu0 yu1 ->
  let '(zl0, zl1, zu0, zu1) := interval_sub_2 xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 in
  interval_2 zl0 zl1 zu0 zu1 /\
  (interval_empty_2 zl0 zl1 zu0 zu1 <->
   interval_empty_2 xl0 xl1 xu0 xu1 \/ interval_empty_2 yl0 yl1 yu0 yu1) /\
  (forall x y : R, in_interval_2 xl0 xl1 xu0 xu1 x -> in_interval_2 yl0 yl1 yu0 yu1 y ->
   in_interval_2 zl0 zl1 zu0 zu1 (x - y)) /\
  (interval_bounded_2 xl0 xl1 xu0 xu1 -> interval_bounded_2 yl0 yl1 yu0 yu1 ->
   forall lo hi : R,
   range_lower (range_2 (fun x y : R => x - y) (in_interval_2 xl0 xl1 xu0 xu1)
                  (in_interval_2 yl0 yl1 yu0 yu1)) (XFin lo) ->
   range_upper (range_2 (fun x y : R => x - y) (in_interval_2 xl0 xl1 xu0 xu1)
                  (in_interval_2 yl0 yl1 yu0 yu1)) (XFin hi) ->
   (interval_bounded_2 zl0 zl1 zu0 zu1 ->
    lo - (b2r zl0 + b2r zl1) <= add_outward_rel emin prec * Rabs lo + add_outward_abs emin prec /\
    (b2r zu0 + b2r zu1) - hi <= add_outward_rel emin prec * Rabs hi + add_outward_abs emin prec) /\
   (((b2r xl0 + b2r xl1) - (b2r yu0 + b2r yu1)) = 0 -> xval_2 zl0 zl1 = XFin lo) /\
   (((b2r xu0 + b2r xu1) - (b2r yl0 + b2r yl1)) = 0 -> xval_2 zu0 zu1 = XFin hi)) /\
  (interval_nonempty_2 xl0 xl1 xu0 xu1 -> interval_nonempty_2 yl0 yl1 yu0 yu1 ->
   (range_lower (range_2 (fun x y : R => x - y) (in_interval_2 xl0 xl1 xu0 xu1)
                   (in_interval_2 yl0 yl1 yu0 yu1)) (XInf true) ->
    xval_2 zl0 zl1 = XInf true) /\
   (range_upper (range_2 (fun x y : R => x - y) (in_interval_2 xl0 xl1 xu0 xu1)
                   (in_interval_2 yl0 yl1 yu0 yu1)) (XInf false) ->
    xval_2 zu0 zu1 = XInf false)) /\
  (interval_bounded_2 xl0 xl1 xu0 xu1 -> interval_bounded_2 yl0 yl1 yu0 yu1 ->
   (forall z : R,
    range_2 (fun x y : R => x - y) (in_interval_2 xl0 xl1 xu0 xu1)
      (in_interval_2 yl0 yl1 yu0 yu1) z ->
    Rabs z <= bpow radix2 (emax - 2)) ->
   interval_bounded_2 zl0 zl1 zu0 zu1).
Proof.
intros Hp xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 CX CY.
destruct (interval_neg_2_facts prec emax nan_opp yl0 yl1 yu0 yu1 CY)
  as [CY' [EY' [NY' [BY' [MY' _]]]]].
rewrite (interval_sub_2_as_add xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 CY).
generalize (interval_add_2_all prec emax nan_plus nan_minus nan_opp nan_abs nan_fma Hp
              xl0 xl1 xu0 xu1 (neg yu0) (neg yu1) (neg yl0) (neg yl1) CX CY').
destruct (interval_add_2 xl0 xl1 xu0 xu1 (neg yu0) (neg yu1) (neg yl0) (neg yl1))
  as [[[zl0 zl1] zu0] zu1].
intros [I1 [I2 [I3 [I4 [I4' I5]]]]].
assert (Rs := range_sub_2_as_add xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1).
assert (Rs' : forall z : R,
             range_2 (fun x y : R => x - y) (in_interval_2 xl0 xl1 xu0 xu1)
               (in_interval_2 yl0 yl1 yu0 yu1) z <->
             range_2 (fun x y : R => x + y) (in_interval_2 xl0 xl1 xu0 xu1)
               (in_interval_2 (neg yu0) (neg yu1) (neg yl0) (neg yl1)) z)
  by (intros z; apply iff_sym; apply Rs).
split; [exact I1|].
split; [rewrite I2, EY'; reflexivity|].
split.
{ intros x y Hx Hy. replace (x - y) with (x + - y) by ring. exact (I3 x (- y) Hx (MY' y Hy)). }
split.
{ intros BX BY lo hi Hlo Hhi.
  destruct (I4 BX (proj2 BY' BY) lo hi (range_lower_ext _ _ _ Rs' Hlo)
              (range_upper_ext _ _ _ Rs' Hhi)) as [T [Zl Zu]].
  rewrite 2!(IeeeExt.neg_value prec emax nan_opp) in Zl, Zu.
  split; [exact T|split].
  - intros V. apply Zl. lra.
  - intros V. apply Zu. lra. }
split.
{ intros NX NY. destruct (I4' NX (NY' NY)) as [L U]. split.
  - intros Hlo. apply L. exact (range_lower_ext _ _ _ Rs' Hlo).
  - intros Hhi. apply U. exact (range_upper_ext _ _ _ Rs' Hhi). }
intros BX BY W. apply (I5 BX (proj2 BY' BY)). intros z Hz. apply W. now apply Rs.
Qed.

End IeeeIntervalSub2.

(** * The generated statement *)

(* interval_sub_2: the generated statement, which prints the constants A and B of the
   closed form unfolded, is interval_sub_2_all. *)
Theorem interval_sub_2_correct : interval_sub_2_spec.
Proof.
intros prec emax Hp0 He nan_plus nan_minus nan_opp nan_abs nan_fma Hp
       xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 CX CY.
exact (interval_sub_2_all prec emax nan_plus nan_minus nan_opp nan_abs nan_fma Hp
         xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 CX CY).
Qed.
