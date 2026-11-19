(* The constructor kernels in the IEEE model (docs/developer/design/milestone1.md, "Values
   that enter from the program"): make_2, make_2_limbs, ball_make_1, ball_make_2.

   A constructor takes values of T from the program, which may be anything: a NaN, an
   infinity, a zero of either sign. Its result is a canonical object. Every limb that
   comes from the program passes through guard (an addition of +0), which keeps the value
   and what kind of number it is; the proofs are case analyses on the operands.

     make_2(a)            canonical, with the value of a (as an extended real number).
     make_2_limbs(h, l)   requires (h, l) canonical; canonical, with the same value, and
                          with limbs of the same values when h is finite.
     ball_make_1(c, r)    a canonical ball: empty when r is a NaN or negative (-infinity
     ball_make_2(c, r)    included); else the whole line when r is +infinity or the center
                          is not finite; else the ball of center c and radius r.

   The statements are in proofs/gen/IeeeStatements.v. *)
From Stdlib Require Import Reals ZArith Bool Lia Lra.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements IeeeStatements.
From Kairn Require Import Format Normalized IeeeBridge IeeeVocabulary
  IeeeOps.
From Kairn Require IeeeOperations.
From Kairn.Gen Require IeeeModel.
Open Scope R_scope.

Section IeeeMake.
Variable prec emax : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Context {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}.

Notation float := (binary_float prec emax).
Notation nan_of := {x : float | is_nan prec emax x = true}.
Variable nan_plus : float -> float -> nan_of.
Variable nan_abs : float -> nan_of.
Variable nan_const : nan_of.

Notation emin := (3 - emax - prec)%Z.
Notation fexp := (FLT_exp emin prec).
Notation format := (generic_format radix2 fexp).
Notation fin x := (is_finite prec emax x = true).
Notation b2r := (B2R prec emax).
Notation guard := (IeeeOperations.guard prec emax nan_plus).
Notation fabs := (IeeeOperations.abs prec emax nan_abs).
Notation flt := (IeeeOperations.lt prec emax).
Notation fle := (IeeeOperations.le prec emax).
Notation feq := (IeeeOperations.eq prec emax).
Notation pzero := (IeeeOperations.pzero prec emax).
Notation pinf := (IeeeOperations.pinf prec emax).
Notation cnan := (IeeeOperations.cnan prec emax nan_const).
Notation ninf := (B754_infinity prec emax true).

(* A number of the format followed by zero is normalized. *)
Lemma normalized_2_lead : forall x : float, normalized_2 emin prec (b2r x) 0.
Proof.
intros x. split; [apply (b2r_format prec emax)|split; [apply generic_format_0|]].
unfold RN. rewrite Rplus_0_r. symmetry.
apply round_generic; auto with typeclass_instances. apply (b2r_format prec emax).
Qed.

(** * make_2 *)

Lemma make_2_facts :
  forall a : float,
  let '(x0, x1) := IeeeModel.make_2 prec emax nan_plus a in
  canonical_2 x0 x1 /\ xval_2 x0 x1 = xval a.
Proof.
intros a. unfold IeeeModel.make_2. cbv beta iota zeta.
rewrite (eq_self prec emax), (guard_nan prec emax nan_plus).
unfold xval_2, xval.
rewrite (guard_finite prec emax nan_plus), (guard_nan prec emax nan_plus).
destruct (finite_dec prec emax a) as [Fa|Fa].
- rewrite (finite_not_nan prec emax a Fa), Fa. cbn [negb].
  unfold finite, val. rewrite (guard_val prec emax nan_plus).
  split.
  + left. unfold finite, val.
    rewrite (guard_finite prec emax nan_plus), (guard_val prec emax nan_plus).
    split; [exact Fa|split; [reflexivity|apply normalized_2_lead]].
  + change (B2R prec emax pzero) with 0. now rewrite Rplus_0_r.
- rewrite Fa. destruct (not_finite_cases prec emax a Fa) as [Na|[s Ea]].
  + rewrite Na. cbn [negb]. split; [|reflexivity].
    right. right. unfold nan. rewrite (guard_nan prec emax nan_plus). now split.
  + subst a. cbn [is_nan negb]. rewrite (guard_inf prec emax nan_plus). split; [|reflexivity].
    right. left. split; [now exists s|now exists false].
Qed.

(** * make_2_limbs *)

Lemma make_2_limbs_facts :
  forall h l : float, canonical_2 h l ->
  let '(x0, x1) := IeeeModel.make_2_limbs prec emax nan_plus h l in
  canonical_2 x0 x1 /\ xval_2 x0 x1 = xval_2 h l /\
  (fin h -> b2r x0 = b2r h /\ b2r x1 = b2r l).
Proof.
intros h l C. unfold IeeeModel.make_2_limbs. cbv beta iota zeta.
unfold xval_2. rewrite (guard_finite prec emax nan_plus), (guard_nan prec emax nan_plus).
split; [|split].
- destruct C as [[Fh [Fl N]]|[[[s E] [s' E']]|[Nh Nl]]].
  + left. unfold finite, val in *.
    rewrite 2!(guard_finite prec emax nan_plus), 2!(guard_val prec emax nan_plus). auto.
  + subst h l. rewrite (guard_inf prec emax nan_plus), (guard_zero prec emax nan_plus).
    right. left. split; [now exists s|now exists false].
  + right. right. unfold nan in *. rewrite 2!(guard_nan prec emax nan_plus). now split.
- destruct (is_finite prec emax h) eqn:Fh.
  + unfold val. now rewrite 2!(guard_val prec emax nan_plus).
  + destruct (not_finite_cases prec emax h Fh) as [Nh|[s Eh]].
    * now rewrite Nh.
    * subst h. now rewrite (guard_inf prec emax nan_plus).
- intros _. split; apply (guard_val prec emax nan_plus).
Qed.

(** * ball_make_1 and ball_make_2 *)

(* The radii that give the empty set: a NaN, -infinity, a negative number. *)
Definition r_empty (r : float) : Prop :=
  is_nan prec emax r = true \/ r = ninf \/ (fin r /\ b2r r < 0).

Lemma r_empty_not_nonneg : forall r : float, r_empty r -> fin r -> 0 <= b2r r -> False.
Proof.
intros r [N|[E|[_ L]]] F P.
- rewrite (nan_not_finite prec emax r N) in F. discriminate F.
- subst r. discriminate F.
- lra.
Qed.

Lemma r_empty_not_pinf : forall r : float, r_empty r -> r = pinf -> False.
Proof. intros r [N|[E|[F _]]] K; subst r; discriminate. Qed.

(* The two tests on the guarded radius, in the three cases. *)
Lemma radius_tests :
  forall r : float,
  (r_empty r /\ fle pzero (guard r) = false) \/
  (fin r /\ 0 <= b2r r /\ fle pzero (guard r) = true /\ flt (guard r) pinf = true) \/
  (r = pinf /\ fle pzero (guard r) = true /\ flt (guard r) pinf = false).
Proof.
intros r. destruct (finite_dec prec emax r) as [F|F].
- assert (Fg : fin (guard r)) by now rewrite (guard_finite prec emax nan_plus).
  assert (Fz : fin pzero) by reflexivity.
  assert (E : fle pzero (guard r) = Rle_bool 0 (b2r r)).
  { rewrite (le_finite prec emax pzero (guard r) Fz Fg), (guard_val prec emax nan_plus).
    reflexivity. }
  destruct (Rle_or_lt 0 (b2r r)) as [P|P].
  + right. left. rewrite (Rle_bool_true _ _ P) in E.
    split; [exact F|split; [exact P|split; [exact E|]]].
    now apply (lt_pinf_finite prec emax).
  + left. rewrite (Rle_bool_false _ _ P) in E. split; [right; right; now split|exact E].
- destruct (not_finite_cases prec emax r F) as [N|[[|] E]].
  + left. split; [now left|].
    destruct r as [s|s|s pl H|s m e H]; try discriminate N. reflexivity.
  + subst r. left. split; [right; now left|reflexivity].
  + subst r. right. right. split; [reflexivity|split; reflexivity].
Qed.

Lemma ball_make_1_facts :
  forall c r : float,
  let '(cw, rw) := IeeeModel.ball_make_1 prec emax nan_plus nan_abs nan_const c r in
  ball_1 cw rw /\
  (r_empty r -> ball_empty_1 cw rw) /\
  (fin r -> 0 <= b2r r -> fin c ->
   ball_finite_1 cw rw /\ b2r cw = b2r c /\ b2r rw = b2r r) /\
  (r = pinf \/ (fin r /\ 0 <= b2r r /\ ~ fin c) -> ball_whole_1 cw rw).
Proof.
intros c r. unfold IeeeModel.ball_make_1. cbv beta iota zeta.
rewrite (lt_abs_pinf prec emax nan_abs), (guard_finite prec emax nan_plus).
assert (Ne : ball_empty_1 cnan cnan) by (split; exact (proj2_sig nan_const)).
assert (Nw : ball_whole_1 pzero pinf) by (split; [now exists false|reflexivity]).
destruct (radius_tests r) as [[HE Ee]|[[Fr [Pr [Ee Ef]]]|[Er [Ee Ef]]]]; rewrite Ee.
- (* the empty set *)
  split; [right; right; exact Ne|split; [intros _; exact Ne|split]].
  + intros F P _. elim (r_empty_not_nonneg r HE F P).
  + intros [K|[F [P _]]]; [elim (r_empty_not_pinf r HE K)|elim (r_empty_not_nonneg r HE F P)].
- rewrite Ef. destruct (is_finite prec emax c) eqn:Fc; cbn [andb].
  + (* the ball itself *)
    assert (B : ball_finite_1 (guard c) (guard r)).
    { unfold ball_finite_1, finite, val.
      rewrite 2!(guard_finite prec emax nan_plus), (guard_val prec emax nan_plus).
      split; [exact Fc|split; [exact Fr|exact Pr]]. }
    split; [left; exact B|split; [|split]].
    * intros HE. elim (r_empty_not_nonneg r HE Fr Pr).
    * intros _ _ _. split; [exact B|split; apply (guard_val prec emax nan_plus)].
    * intros [K|[_ [_ K]]]; [subst r; discriminate Fr|now elim K].
  + (* the center is not finite: the whole line *)
    split; [right; left; exact Nw|split; [|split]].
    * intros HE. elim (r_empty_not_nonneg r HE Fr Pr).
    * intros _ _ K. discriminate K.
    * intros _. exact Nw.
- (* the radius is +infinity: the whole line *)
  rewrite Ef, andb_false_r.
  split; [right; left; exact Nw|split; [|split]].
  + intros HE. elim (r_empty_not_pinf r HE Er).
  + intros F _ _. subst r. discriminate F.
  + intros _. exact Nw.
Qed.

Lemma ball_make_2_facts :
  forall c0 c1 r : float, canonical_2 c0 c1 ->
  let '(cw0, cw1, rw) := IeeeModel.ball_make_2 prec emax nan_plus nan_abs nan_const c0 c1 r in
  ball_2 cw0 cw1 rw /\
  (r_empty r -> ball_empty_2 cw0 cw1 rw) /\
  (fin r -> 0 <= b2r r -> fin c0 ->
   ball_finite_2 cw0 cw1 rw /\ cw0 = c0 /\ cw1 = c1 /\ b2r rw = b2r r) /\
  (r = pinf \/ (fin r /\ 0 <= b2r r /\ ~ fin c0) -> ball_whole_2 cw0 cw1 rw).
Proof.
intros c0 c1 r C. unfold IeeeModel.ball_make_2. cbv beta iota zeta.
rewrite (lt_abs_pinf prec emax nan_abs).
assert (Ne : ball_empty_2 cnan cnan cnan) by (repeat split; exact (proj2_sig nan_const)).
assert (Nw : ball_whole_2 pzero pzero pinf)
  by (split; [now exists false|split; [now exists false|reflexivity]]).
destruct (radius_tests r) as [[HE Ee]|[[Fr [Pr [Ee Ef]]]|[Er [Ee Ef]]]]; rewrite Ee.
- (* the empty set *)
  split; [right; right; exact Ne|split; [intros _; exact Ne|split]].
  + intros F P _. elim (r_empty_not_nonneg r HE F P).
  + intros [K|[F [P _]]]; [elim (r_empty_not_pinf r HE K)|elim (r_empty_not_nonneg r HE F P)].
- rewrite Ef. destruct (is_finite prec emax c0) eqn:Fc; cbn [andb].
  + (* the ball itself *)
    assert (B : ball_finite_2 c0 c1 (guard r)).
    { destruct C as [[_ [F1 N]]|[[[s E] _]|[N0 _]]].
      - unfold ball_finite_2, finite, val in *.
        rewrite (guard_finite prec emax nan_plus), (guard_val prec emax nan_plus).
        split; [exact Fc|split; [exact F1|split; [exact N|split; [exact Fr|exact Pr]]]].
      - subst c0. discriminate Fc.
      - unfold nan in N0. rewrite (nan_not_finite prec emax c0 N0) in Fc. discriminate Fc. }
    split; [left; exact B|split; [|split]].
    * intros HE. elim (r_empty_not_nonneg r HE Fr Pr).
    * intros _ _ _.
      split; [exact B|split; [reflexivity|split; [reflexivity|apply (guard_val prec emax nan_plus)]]].
    * intros [K|[_ [_ K]]]; [subst r; discriminate Fr|now elim K].
  + (* the center is not finite: the whole line *)
    split; [right; left; exact Nw|split; [|split]].
    * intros HE. elim (r_empty_not_nonneg r HE Fr Pr).
    * intros _ _ K. discriminate K.
    * intros _. exact Nw.
- (* the radius is +infinity: the whole line *)
  rewrite Ef, andb_false_r.
  split; [right; left; exact Nw|split; [|split]].
  + intros HE. elim (r_empty_not_pinf r HE Er).
  + intros F _ _. subst r. discriminate F.
  + intros _. exact Nw.
Qed.

End IeeeMake.

Theorem make_2_correct : make_2_spec.
Proof. intros prec emax Hp He nan_plus a. exact (make_2_facts prec emax nan_plus a). Qed.

Theorem make_2_limbs_correct : make_2_limbs_spec.
Proof.
intros prec emax Hp He nan_plus h l C. exact (make_2_limbs_facts prec emax nan_plus h l C).
Qed.

Theorem ball_make_1_correct : ball_make_1_spec.
Proof.
intros prec emax Hp He nan_plus nan_abs nan_const c r.
exact (ball_make_1_facts prec emax nan_plus nan_abs nan_const c r).
Qed.

Theorem ball_make_2_correct : ball_make_2_spec.
Proof.
intros prec emax Hp He nan_plus nan_abs nan_const c0 c1 r C.
exact (ball_make_2_facts prec emax nan_plus nan_abs nan_const c0 c1 r C).
Qed.
