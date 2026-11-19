(* The full Ball kernels in the IEEE model: what does not depend on how a core computes
   its radius.

   A canonical ball is a finite ball, the whole line, or the empty set
   (IeeeExtStatementsDraft.v). A full Ball kernel is a finite core followed by a fix-up
   that tests three things: whether an operand is the empty set (q is a NaN), and
   whether the center and the radius of the core are finite. This file contains:

   - the three states: what a canonical ball that is not empty looks like (its center is
     finite and, for two limbs, normalized: the center of the whole line is zero; its
     radius is nonnegative or +infinity), and what membership of a real number says;
   - the fix-up, as one function per number of center limbs, and one lemma each
     (ball_template_1, ball_template_2) that gives B1 to B3 of milestone1.md ("Ball
     kernels") from two facts about a core:
       1. q is a NaN exactly when an operand is empty;
       2. when no operand is empty and the leading limb of the center is finite: the
          radius is nonnegative, +infinity or NaN (so that the test lt (rz, inf) means
          "finite"), and a finite radius gives finite operands, a normalized center,
          and the containment statement of the core;
   - containment in every case from B1 to B3 (the lemmas every_case): a real number in each
     operand gives a real number in the result, the whole line included.

   An operand that is the whole line, or a scalar that is not finite, must make the
   center or the radius of the core not finite, whatever the other operand is: the
   result is then the whole line, not the empty set. That is fact 2, read backwards.

   The cores themselves, and the statements of the full kernels, are in IeeeBallCores.v. *)
From Stdlib Require Import Reals ZArith List Arith Bool Lia Lra Psatz.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements.
From Kairn Require Import Format Normalized Program IeeeBridge IeeeStatementsDraft
  IeeeExtStatementsDraft IeeeOps.
From Kairn Require IeeeDraft.
Import ListNotations.
Open Scope R_scope.

Section IeeeBall.
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
Notation fexp := (FLT_exp emin prec).
Notation format := (generic_format radix2 fexp).
Notation rnd := (round radix2 fexp (Znearest tie_even)).
Notation fin x := (is_finite prec emax x = true).
Notation b2r := (B2R prec emax).
Notation add := (IeeeDraft.add prec emax nan_plus).
Notation fabs := (IeeeDraft.abs prec emax nan_abs).
Notation flt := (IeeeDraft.lt prec emax).
Notation feq := (IeeeDraft.eq prec emax).
Notation pzero := (IeeeDraft.pzero prec emax).
Notation pinf := (IeeeDraft.pinf prec emax).

Let Hprec : (0 < prec)%Z.
Proof. exact prec_gt_0_. Qed.
Let Hemax : (prec < emax)%Z.
Proof. exact prec_lt_emax_. Qed.

(** * Canonical balls *)

Lemma normalized_2_0 : normalized_2 emin prec 0 0.
Proof.
split; [apply generic_format_0|split; [apply generic_format_0|]].
unfold RN. rewrite Rplus_0_r. symmetry. apply round_0; auto with typeclass_instances.
Qed.

Lemma ball_2_radius : forall c0 c1 r : float, ball_2 c0 c1 r -> nonneg_ext r.
Proof.
intros c0 c1 r [[_ [_ [_ [F P]]]]|[[_ [_ E]]|[_ [_ N]]]].
- right. right. split; assumption.
- right. left. exact E.
- left. exact N.
Qed.

Lemma ball_2_center :
  forall c0 c1 r : float, ball_2 c0 c1 r -> is_nan prec emax r = false ->
  fin c0 /\ fin c1 /\ normalized_2 emin prec (b2r c0) (b2r c1).
Proof.
intros c0 c1 r [[F0 [F1 [N _]]]|[[[s0 E0] [[s1 E1] _]]|[_ [_ N]]]] Nr.
- split; [exact F0|split; [exact F1|exact N]].
- rewrite E0, E1. split; [reflexivity|split; [reflexivity|exact normalized_2_0]].
- unfold nan in N. congruence.
Qed.

Lemma ball_2_empty :
  forall c0 c1 r : float, ball_2 c0 c1 r ->
  (is_nan prec emax r = true <-> ball_empty_2 c0 c1 r).
Proof.
intros c0 c1 r B. split.
- intros N. destruct B as [[_ [_ [_ [F _]]]]|[[_ [_ E]]|B]]; trivial.
  + apply (finite_not_nan prec emax) in F. congruence.
  + rewrite E in N. discriminate N.
- intros [_ [_ N]]. exact N.
Qed.

Lemma ball_2_finite :
  forall c0 c1 r : float, ball_2 c0 c1 r -> fin r -> ball_finite_2 c0 c1 r.
Proof.
intros c0 c1 r [B|[[_ [_ E]]|[_ [_ N]]]] F; trivial.
- rewrite E in F. discriminate F.
- apply (nan_not_finite prec emax) in N. congruence.
Qed.

Lemma ball_1_radius : forall c r : float, ball_1 c r -> nonneg_ext r.
Proof.
intros c r [[_ [F P]]|[[_ E]|[_ N]]].
- right. right. split; assumption.
- right. left. exact E.
- left. exact N.
Qed.

Lemma ball_1_center :
  forall c r : float, ball_1 c r -> is_nan prec emax r = false -> fin c.
Proof.
intros c r [[F0 _]|[[[s0 E0] _]|[_ N]]] Nr.
- exact F0.
- rewrite E0. reflexivity.
- unfold nan in N. congruence.
Qed.

Lemma ball_1_empty :
  forall c r : float, ball_1 c r -> (is_nan prec emax r = true <-> ball_empty_1 c r).
Proof.
intros c r B. split.
- intros N. destruct B as [[_ [F _]]|[[_ E]|B]]; trivial.
  + apply (finite_not_nan prec emax) in F. congruence.
  + rewrite E in N. discriminate N.
- intros [_ N]. exact N.
Qed.

Lemma ball_1_finite : forall c r : float, ball_1 c r -> fin r -> ball_finite_1 c r.
Proof.
intros c r [B|[[_ E]|[_ N]]] F; trivial.
- rewrite E in F. discriminate F.
- apply (nan_not_finite prec emax) in N. congruence.
Qed.

(* A real number in a ball: the ball is not empty, and a finite ball bounds it. *)
Lemma in_ball_2_not_empty :
  forall (c0 c1 r : float) (x : R), in_ball_2 c0 c1 r x -> ~ ball_empty_2 c0 c1 r.
Proof.
intros c0 c1 r x [[_ [_ E]]|[[_ [_ [_ [F _]]]] _]] [_ [_ N]].
- rewrite E in N. discriminate N.
- apply (nan_not_finite prec emax) in N. unfold finite in F. congruence.
Qed.

Lemma in_ball_2_finite :
  forall (c0 c1 r : float) (x : R), in_ball_2 c0 c1 r x -> ball_finite_2 c0 c1 r ->
  Rabs (x - (b2r c0 + b2r c1)) <= b2r r.
Proof.
intros c0 c1 r x [[_ [_ E]]|[_ Hx]] [_ [_ [_ [F _]]]].
- rewrite E in F. discriminate F.
- exact Hx.
Qed.

Lemma in_ball_1_not_empty :
  forall (c r : float) (x : R), in_ball_1 c r x -> ~ ball_empty_1 c r.
Proof.
intros c r x [[_ E]|[[_ [F _]] _]] [_ N].
- rewrite E in N. discriminate N.
- apply (nan_not_finite prec emax) in N. unfold finite in F. congruence.
Qed.

Lemma in_ball_1_finite :
  forall (c r : float) (x : R), in_ball_1 c r x -> ball_finite_1 c r -> Rabs (x - b2r c) <= b2r r.
Proof.
intros c r x [[_ E]|[_ Hx]] [_ [F _]].
- rewrite E in F. discriminate F.
- exact Hx.
Qed.

(* Containment in every case, from B1 to B3: two ball operands. *)
Lemma every_case_2 :
  forall (g : R -> R -> R) (cx0 cx1 rx cy0 cy1 ry cw0 cw1 rw : float),
  ball_2 cw0 cw1 rw ->
  (ball_empty_2 cw0 cw1 rw <-> ball_empty_2 cx0 cx1 rx \/ ball_empty_2 cy0 cy1 ry) ->
  (ball_finite_2 cw0 cw1 rw ->
   (ball_finite_2 cx0 cx1 rx /\ ball_finite_2 cy0 cy1 ry) /\
   (forall x y : R, Rabs (x - (b2r cx0 + b2r cx1)) <= b2r rx ->
    Rabs (y - (b2r cy0 + b2r cy1)) <= b2r ry -> Rabs (g x y - (b2r cw0 + b2r cw1)) <= b2r rw)) ->
  forall x y : R, in_ball_2 cx0 cx1 rx x -> in_ball_2 cy0 cy1 ry y -> in_ball_2 cw0 cw1 rw (g x y).
Proof.
intros g cx0 cx1 rx cy0 cy1 ry cw0 cw1 rw B1 B2 B3 x y Hx Hy.
destruct B1 as [Fw|[Ww|Ew]].
- right. split. exact Fw. destruct (B3 Fw) as [[Fx Fy] C].
  apply C; now apply in_ball_2_finite.
- left. exact Ww.
- exfalso. destruct (proj1 B2 Ew) as [E|E].
  + exact (in_ball_2_not_empty _ _ _ _ Hx E).
  + exact (in_ball_2_not_empty _ _ _ _ Hy E).
Qed.

Lemma every_case_1 :
  forall (g : R -> R -> R) (cx rx cy ry cw rw : float),
  ball_1 cw rw ->
  (ball_empty_1 cw rw <-> ball_empty_1 cx rx \/ ball_empty_1 cy ry) ->
  (ball_finite_1 cw rw ->
   (ball_finite_1 cx rx /\ ball_finite_1 cy ry) /\
   (forall x y : R, Rabs (x - b2r cx) <= b2r rx -> Rabs (y - b2r cy) <= b2r ry ->
    Rabs (g x y - b2r cw) <= b2r rw)) ->
  forall x y : R, in_ball_1 cx rx x -> in_ball_1 cy ry y -> in_ball_1 cw rw (g x y).
Proof.
intros g cx rx cy ry cw rw B1 B2 B3 x y Hx Hy.
destruct B1 as [Fw|[Ww|Ew]].
- right. split. exact Fw. destruct (B3 Fw) as [[Fx Fy] C].
  apply C; now apply in_ball_1_finite.
- left. exact Ww.
- exfalso. destruct (proj1 B2 Ew) as [E|E].
  + exact (in_ball_1_not_empty _ _ _ Hx E).
  + exact (in_ball_1_not_empty _ _ _ Hy E).
Qed.

(* The same for one ball operand: g is the function of the real number in it. *)
Lemma every_case_scale_2 :
  forall (g : R -> R) (cx0 cx1 rx cw0 cw1 rw : float),
  ball_2 cw0 cw1 rw ->
  (ball_empty_2 cw0 cw1 rw <-> ball_empty_2 cx0 cx1 rx) ->
  (ball_finite_2 cw0 cw1 rw ->
   ball_finite_2 cx0 cx1 rx /\
   (forall x : R, Rabs (x - (b2r cx0 + b2r cx1)) <= b2r rx ->
    Rabs (g x - (b2r cw0 + b2r cw1)) <= b2r rw)) ->
  forall x : R, in_ball_2 cx0 cx1 rx x -> in_ball_2 cw0 cw1 rw (g x).
Proof.
intros g cx0 cx1 rx cw0 cw1 rw B1 B2 B3 x Hx.
destruct B1 as [Fw|[Ww|Ew]].
- right. split. exact Fw. destruct (B3 Fw) as [Fx C].
  apply C. now apply in_ball_2_finite.
- left. exact Ww.
- exfalso. exact (in_ball_2_not_empty _ _ _ _ Hx (proj1 B2 Ew)).
Qed.

Lemma every_case_scale_1 :
  forall (g : R -> R) (cx rx cw rw : float),
  ball_1 cw rw ->
  (ball_empty_1 cw rw <-> ball_empty_1 cx rx) ->
  (ball_finite_1 cw rw ->
   ball_finite_1 cx rx /\
   (forall x : R, Rabs (x - b2r cx) <= b2r rx -> Rabs (g x - b2r cw) <= b2r rw)) ->
  forall x : R, in_ball_1 cx rx x -> in_ball_1 cw rw (g x).
Proof.
intros g cx rx cw rw B1 B2 B3 x Hx.
destruct B1 as [Fw|[Ww|Ew]].
- right. split. exact Fw. destruct (B3 Fw) as [Fx C].
  apply C. now apply in_ball_1_finite.
- left. exact Ww.
- exfalso. exact (in_ball_1_not_empty _ _ _ Hx (proj1 B2 Ew)).
Qed.

(** * The fix-up *)

Definition ball_fixup_2 (cz0 cz1 rz q : float) : float * float * float :=
  let e := feq q q in
  let a := fabs cz0 in
  let f1 := flt a pinf in
  let f2 := flt rz pinf in
  let f := andb f1 f2 in
  let c0 := if f then cz0 else pzero in
  let c1 := if f then cz1 else pzero in
  let r := if f then rz else pinf in
  let cw0 := if e then c0 else q in
  let cw1 := if e then c1 else q in
  let rw := if e then r else q in
  (cw0, cw1, rw).

Definition ball_fixup_1 (cz rz q : float) : float * float :=
  let e := feq q q in
  let a := fabs cz in
  let f1 := flt a pinf in
  let f2 := flt rz pinf in
  let f := andb f1 f2 in
  let c0 := if f then cz else pzero in
  let r := if f then rz else pinf in
  let cw := if e then c0 else q in
  let rw := if e then r else q in
  (cw, rw).

(* B1 to B3 for a center of two limbs, from two facts: q is a NaN exactly when an operand
   is empty; and, when no operand is empty and the leading limb of the center of the core
   is finite, the radius is nonnegative, +infinity or NaN, and a finite radius gives
   finite operands, a normalized center and the containment C. *)
Lemma ball_template_2 :
  forall (cz0 cz1 rz q : float) (anyempty allfinite : Prop) (C : float -> float -> float -> Prop),
  (is_nan prec emax q = true <-> anyempty) ->
  (~ anyempty -> fin cz0 ->
   nonneg_ext rz /\
   (fin rz -> allfinite /\ fin cz1 /\ normalized_2 emin prec (b2r cz0) (b2r cz1) /\ C cz0 cz1 rz)) ->
  let '(cw0, cw1, rw) := ball_fixup_2 cz0 cz1 rz q in
  ball_2 cw0 cw1 rw /\
  (ball_empty_2 cw0 cw1 rw <-> anyempty) /\
  (ball_finite_2 cw0 cw1 rw -> allfinite /\ C cw0 cw1 rw).
Proof.
intros cz0 cz1 rz q anyempty allfinite C Hq Hcore.
unfold ball_fixup_2. cbv zeta. rewrite eq_self, lt_abs_pinf.
destruct (is_nan prec emax q) eqn:Nq.
- (* an operand is empty *)
  cbn [negb]. split; [|split].
  + right. right. split; [exact Nq|split; exact Nq].
  + split. intros _. now apply Hq. intros _. split; [exact Nq|split; exact Nq].
  + intros [F _]. apply (nan_not_finite prec emax) in Nq. unfold finite in F. congruence.
- assert (NE : ~ anyempty).
  { intros E. apply Hq in E. discriminate E. }
  cbn [negb].
  destruct (is_finite prec emax cz0) eqn:Fz; [destruct (flt rz pinf) eqn:Lr|]; cbn [andb].
  + (* the core returned a finite ball *)
    destruct (Hcore NE eq_refl) as [Hrz K].
    assert (Frz : fin rz) by now apply (nonneg_ext_lt_pinf prec emax).
    destruct (K Frz) as [A [Fz1 [N Cz]]].
    split; [|split].
    * left. split; [exact Fz|split; [exact Fz1|split; [exact N|split; [exact Frz|]]]].
      now apply (nonneg_ext_fin prec emax).
    * split. intros [E _]. apply (nan_not_finite prec emax) in E. congruence.
      intros E. now elim NE.
    * intros _. split; assumption.
  + (* the radius is not finite: the whole line *)
    split; [|split].
    * right. left. split; [now exists false|split; [now exists false|reflexivity]].
    * split. intros [E _]. discriminate E. intros E. now elim NE.
    * intros [_ [_ [_ [F _]]]]. discriminate F.
  + (* the center is not finite: the whole line *)
    split; [|split].
    * right. left. split; [now exists false|split; [now exists false|reflexivity]].
    * split. intros [E _]. discriminate E. intros E. now elim NE.
    * intros [_ [_ [_ [F _]]]]. discriminate F.
Qed.

(* The same for a center of one limb. *)
Lemma ball_template_1 :
  forall (cz rz q : float) (anyempty allfinite : Prop) (C : float -> float -> Prop),
  (is_nan prec emax q = true <-> anyempty) ->
  (~ anyempty -> fin cz -> nonneg_ext rz /\ (fin rz -> allfinite /\ C cz rz)) ->
  let '(cw, rw) := ball_fixup_1 cz rz q in
  ball_1 cw rw /\
  (ball_empty_1 cw rw <-> anyempty) /\
  (ball_finite_1 cw rw -> allfinite /\ C cw rw).
Proof.
intros cz rz q anyempty allfinite C Hq Hcore.
unfold ball_fixup_1. cbv zeta. rewrite eq_self, lt_abs_pinf.
destruct (is_nan prec emax q) eqn:Nq.
- cbn [negb]. split; [|split].
  + right. right. split; exact Nq.
  + split. intros _. now apply Hq. intros _. split; exact Nq.
  + intros [F _]. apply (nan_not_finite prec emax) in Nq. unfold finite in F. congruence.
- assert (NE : ~ anyempty).
  { intros E. apply Hq in E. discriminate E. }
  cbn [negb].
  destruct (is_finite prec emax cz) eqn:Fz; [destruct (flt rz pinf) eqn:Lr|]; cbn [andb].
  + destruct (Hcore NE eq_refl) as [Hrz K].
    assert (Frz : fin rz) by now apply (nonneg_ext_lt_pinf prec emax).
    destruct (K Frz) as [A Cz].
    split; [|split].
    * left. split; [exact Fz|split; [exact Frz|]]. now apply (nonneg_ext_fin prec emax).
    * split. intros [E _]. apply (nan_not_finite prec emax) in E. congruence.
      intros E. now elim NE.
    * intros _. split; assumption.
  + split; [|split].
    * right. left. split; [now exists false|reflexivity].
    * split. intros [E _]. discriminate E. intros E. now elim NE.
    * intros [_ [F _]]. discriminate F.
  + split; [|split].
    * right. left. split; [now exists false|reflexivity].
    * split. intros [E _]. discriminate E. intros E. now elim NE.
    * intros [_ [F _]]. discriminate F.
Qed.

(* q = add (rx, ry) is a NaN exactly when one of two canonical balls is empty. *)
Lemma q_empty_2 :
  forall cx0 cx1 rx cy0 cy1 ry : float, ball_2 cx0 cx1 rx -> ball_2 cy0 cy1 ry ->
  (is_nan prec emax (add rx ry) = true <-> ball_empty_2 cx0 cx1 rx \/ ball_empty_2 cy0 cy1 ry).
Proof.
intros cx0 cx1 rx cy0 cy1 ry Bx By.
destruct (add_nonneg prec emax nan_plus rx ry (ball_2_radius _ _ _ Bx) (ball_2_radius _ _ _ By))
  as [_ [_ K]].
split.
- intros N. destruct (proj1 K N) as [Nx|Ny].
  + left. now apply (proj1 (ball_2_empty _ _ _ Bx)).
  + right. now apply (proj1 (ball_2_empty _ _ _ By)).
- intros [E|E]; apply (proj2 K).
  + left. now apply (proj2 (ball_2_empty _ _ _ Bx)).
  + right. now apply (proj2 (ball_2_empty _ _ _ By)).
Qed.

Lemma q_empty_1 :
  forall cx rx cy ry : float, ball_1 cx rx -> ball_1 cy ry ->
  (is_nan prec emax (add rx ry) = true <-> ball_empty_1 cx rx \/ ball_empty_1 cy ry).
Proof.
intros cx rx cy ry Bx By.
destruct (add_nonneg prec emax nan_plus rx ry (ball_1_radius _ _ Bx) (ball_1_radius _ _ By))
  as [_ [_ K]].
split.
- intros N. destruct (proj1 K N) as [Nx|Ny].
  + left. now apply (proj1 (ball_1_empty _ _ Bx)).
  + right. now apply (proj1 (ball_1_empty _ _ By)).
- intros [E|E]; apply (proj2 K).
  + left. now apply (proj2 (ball_1_empty _ _ Bx)).
  + right. now apply (proj2 (ball_1_empty _ _ By)).
Qed.

(* The same for one ball operand, whose radius is q itself. *)
Lemma q_empty_scale_2 :
  forall cx0 cx1 rx : float, ball_2 cx0 cx1 rx ->
  (is_nan prec emax rx = true <-> ball_empty_2 cx0 cx1 rx).
Proof. intros cx0 cx1 rx Bx. now apply ball_2_empty. Qed.

Lemma q_empty_scale_1 :
  forall cx rx : float, ball_1 cx rx -> (is_nan prec emax rx = true <-> ball_empty_1 cx rx).
Proof. intros cx rx Bx. now apply ball_1_empty. Qed.

End IeeeBall.
