(* The interval of a ball of two limbs, in the IEEE model, on all values
   (docs/developer/design/milestone2.md, "Midpoint, radius and the conversions";
   docs/developer/architecture.md, "Claims of the enclosure interface: the conversions of two
   limbs"): ball_to_interval_2.

   Notation as in IeeeInterval2.v and IeeeBallPredicates2.v. From precision 3.

   What is proved (ball_to_interval_2_correct, the generated statement): for a canonical ball
   (c, r) of two limbs, the result Z is a canonical interval of two limbs, empty exactly when
   the ball is, containing every member of the ball; for a finite ball, a bounded Z has its
   lower bound within A |c - r| + B below c - r and its upper bound within A |c + r| + B above
   c + r, with the constants A and B of the sum of two intervals of two limbs, and a bound of
   the ball that is zero is returned exactly; the whole line gives [-inf, +inf]; and a finite
   ball whose members are at most 2^(emax - 2) in magnitude gives a bounded Z.

   The proof. The listing is interval_add_2 of [c, c] and [-r, r], the radius made a 2-limb
   value by make_2 (ball_to_interval_2_as_add): the directed sums are the same, and the test
   eq(r, r) is the test of emptiness of interval_add_2 on these operands. The members of the
   ball are the exact range of the sum (ball_range_2), and the statement is that of
   interval_add_2 (interval_add_2_all of IeeeInterval2.v). *)
From Stdlib Require Import Reals ZArith Bool Lia Lra Psatz.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements IeeeStatements.
From Kairn Require Import Format Normalized Directed2 IeeeBridge IeeeVocabulary IeeeOps IeeeExt.
From Kairn Require Import IeeeDirected IeeeEntry IeeeMake.
From Kairn Require Import IeeeIntervalVocabulary IeeeInterval1 IeeeInterval2.
From Kairn Require Import IeeeBallConvert IeeeIntervalConvert.
From Kairn Require Import IeeeIntervalExact IeeeIntervalPredicates IeeeBallPredicates.
From Kairn Require Import IeeeBallPredicates2.
From Kairn Require IeeeOperations.
From Kairn.Gen Require IeeeModel.
Open Scope R_scope.

Section BallConvert2.
Variable prec emax : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Context {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}.

Notation float := (binary_float prec emax).
Notation nan_of := {x : float | is_nan prec emax x = true}.
Variable nan_plus nan_minus : float -> float -> nan_of.
Variable nan_opp nan_abs : float -> nan_of.
Variable nan_fma : float -> float -> float -> nan_of.

Notation emin := (3 - emax - prec)%Z.
Notation fin x := (is_finite prec emax x = true).
Notation b2r := (B2R prec emax).
Notation neg := (IeeeOperations.neg prec emax nan_opp).
Notation guard := (IeeeOperations.guard prec emax nan_plus).
Notation flt := (IeeeOperations.lt prec emax).
Notation feq := (IeeeOperations.eq prec emax).
Notation pzero := (IeeeOperations.pzero prec emax).
Notation pinf := (IeeeOperations.pinf prec emax).
Notation ninf := (B754_infinity prec emax true).
Notation xv := (@xval prec emax).
Notation xv2 := (@xval_2 prec emax).
Notation make_2 := (IeeeModel.make_2 prec emax nan_plus).
Notation interval_add_2 :=
  (IeeeModel.interval_add_2 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma).
Notation ball_to_interval_2 :=
  (IeeeModel.ball_to_interval_2 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma).

(* ball_to_interval_2 is interval_add_2 of [c, c] and [-r, r]. *)
Lemma ball_to_interval_2_as_add :
  forall c0 c1 r : float, ball_2 c0 c1 r ->
  ball_to_interval_2 c0 c1 r =
  (let '(n0, n1) := make_2 (neg r) in let '(p0, p1) := make_2 r in
   interval_add_2 c0 c1 c0 c1 n0 n1 p0 p1).
Proof.
intros c0 c1 r B.
unfold IeeeModel.ball_to_interval_2, IeeeModel.interval_add_2. cbv zeta.
destruct (make_2 (neg r)) as [n0 n1] eqn:EN.
assert (G : n0 = guard (neg r)).
{ unfold IeeeModel.make_2 in EN. cbv zeta in EN. injection EN as E _. symmetry. exact E. }
destruct (make_2 r) as [p0 p1].
destruct (IeeeModel.add_down_2_2 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma c0 c1 n0 n1)
  as [l0 l1].
destruct (IeeeModel.add_up_2_2 prec emax nan_plus nan_minus nan_abs nan_fma c0 c1 p0 p1) as [h0 h1].
assert (Ne : feq r r = andb (flt c0 pinf) (flt n0 pinf)).
{ rewrite G, (eq_self prec emax), 2!(lt_xval prec emax), (xval_guard prec emax nan_plus),
    (xval_neg prec emax nan_opp).
  destruct (ball_2_states prec emax c0 c1 r B)
    as [[[F0 [_ [_ [Fr _]]]] _]|[[[[s Z0] [_ Er]] _]|[[N0 [_ Nr]] _]]].
  - rewrite (finite_not_nan prec emax r Fr), (xval_fin prec emax c0 F0), (xval_fin prec emax r Fr).
    reflexivity.
  - subst c0 r. reflexivity.
  - rewrite Nr, (xval_nan prec emax c0 N0). reflexivity. }
rewrite Ne. reflexivity.
Qed.

End BallConvert2.

(** * The generated statement *)

Theorem ball_to_interval_2_correct : ball_to_interval_2_spec.
Proof.
intros prec emax Hp0 He nan_plus nan_minus nan_opp nan_abs nan_fma Hp c0 c1 r B.
assert (Hp1 : (1 <= prec)%Z) by lia.
rewrite (ball_to_interval_2_as_add prec emax nan_plus nan_minus nan_opp nan_abs nan_fma c0 c1 r B).
generalize (make_2_facts prec emax nan_plus (IeeeOperations.neg prec emax nan_opp r)).
generalize (make_2_facts prec emax nan_plus r).
destruct (IeeeModel.make_2 prec emax nan_plus (IeeeOperations.neg prec emax nan_opp r)) as [n0 n1].
destruct (IeeeModel.make_2 prec emax nan_plus r) as [p0 p1].
intros [Cp Ep] [Cn En].
rewrite (xval_neg prec emax nan_opp) in En.
destruct (ball_2_states prec emax c0 c1 r B) as [[F [NW NE]]|[[W [NF NE]]|[E [NF NW]]]].
3: { (* the empty set: the empty interval *)
  destruct E as [N0 [N1 Nr]].
  rewrite (interval_add_2_eq prec emax nan_plus nan_minus nan_opp nan_abs nan_fma). cbv zeta.
  rewrite (lt_xval prec emax c0), (xval_nan prec emax c0 N0). cbn [xlt andb]. cbv beta iota.
  assert (EZ : interval_empty_2 (IeeeOperations.pinf prec emax) (IeeeOperations.pzero prec emax)
                 (IeeeOperations.neg prec emax nan_opp (IeeeOperations.pinf prec emax))
                 (IeeeOperations.pzero prec emax)).
  { split; [reflexivity|split; [exists false; reflexivity|split; [reflexivity|exists false; reflexivity]]]. }
  split; [left; exact EZ|].
  split; [split; intros _; [exact (conj N0 (conj N1 Nr))|exact EZ]|].
  split; [intros x [K|[K _]]; [elim (NW K)|elim (NF K)]|].
  split; [intros K; elim (NF K)|].
  split; [intros K; elim (K (conj N0 (conj N1 Nr)))|].
  intros K; elim (NF K). }
(* a ball that is not empty: interval_add_2 of [c, c] and [-r, r] *)
- (* a finite ball *)
  assert (F' := F). destruct F' as [F0 [F1 [Nc [Fr Pr]]]]. unfold val in Pr.
  assert (C : canonical_2 c0 c1) by (left; exact (conj F0 (conj F1 Nc))).
  rewrite (xval_fin prec emax r Fr) in Ep, En. cbn [xopp] in En.
  assert (Fn0 := xval_2_lead_fin prec emax n0 n1 _ En).
  assert (Fp0 := xval_2_lead_fin prec emax p0 p1 _ Ep).
  rewrite (xval_2_fin prec emax n0 n1 Fn0) in En. injection En as En.
  rewrite (xval_2_fin prec emax p0 p1 Fp0) in Ep. injection Ep as Ep.
  assert (Vc := xval_2_fin prec emax c0 c1 F0).
  assert (NX : interval_nonempty_2 c0 c1 c0 c1).
  { split; [exact C|split; [exact C|]]. rewrite Vc. apply xnonempty_fin. lra. }
  assert (NY : interval_nonempty_2 n0 n1 p0 p1).
  { split; [exact Cn|split; [exact Cp|]].
    rewrite (xval_2_fin prec emax n0 n1 Fn0), (xval_2_fin prec emax p0 p1 Fp0), En, Ep.
    apply xnonempty_fin. lra. }
  assert (R : forall z : R,
              range_2 (fun x y : R => x + y) (in_interval_2 c0 c1 c0 c1) (in_interval_2 n0 n1 p0 p1) z
              <-> in_ball_2 c0 c1 r z).
  { intros z. unfold in_interval_2, in_ball_2.
    rewrite Vc, (xval_2_fin prec emax n0 n1 Fn0), (xval_2_fin prec emax p0 p1 Fp0), En, Ep.
    split.
    - intros [x [y [[Hx Kx] [[Hy Ky] E]]]]. cbn [xle] in Hx, Kx, Hy, Ky.
      apply Rle_bool_inv in Hx. apply Rle_bool_inv in Kx.
      apply Rle_bool_inv in Hy. apply Rle_bool_inv in Ky. cbv beta in E.
      right. split; [exact F|]. unfold val. apply Rabs_le. lra.
    - intros [K|[_ K]]; [elim (NW K)|]. unfold val in K. apply Rabs_le_inv in K.
      exists (B2R prec emax c0 + B2R prec emax c1), (z - (B2R prec emax c0 + B2R prec emax c1)).
      split; [split; cbn; apply Rle_bool_true; lra|].
      split; [split; cbn; apply Rle_bool_true; lra|]. cbv beta. ring. }
  generalize (interval_add_2_all prec emax nan_plus nan_minus nan_opp nan_abs nan_fma Hp
                c0 c1 c0 c1 n0 n1 p0 p1 (or_intror NX) (or_intror NY)).
  destruct (IeeeModel.interval_add_2 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma
              c0 c1 c0 c1 n0 n1 p0 p1) as [[[zl0 zl1] zu0] zu1].
  intros [I1 [I2 [I3 [I4 [I4' I5]]]]].
  assert (BX : interval_bounded_2 c0 c1 c0 c1) by (split; exact F0).
  assert (BY : interval_bounded_2 n0 n1 p0 p1) by (split; [exact Fn0|exact Fp0]).
  split; [exact I1|].
  split.
  { rewrite I2. split; [|intros K; elim (NE K)].
    intros [K|K]; exfalso; destruct K as [K _]; [rewrite K in F0|rewrite K in Fn0]; discriminate. }
  split.
  { intros x Hx. apply R in Hx. destruct Hx as [a [b [Ha [Hb E]]]]. rewrite E. exact (I3 a b Ha Hb). }
  split.
  { intros _ lo hi Hlo Hhi.
    assert (Hlo' := range_lower_ext _ _ _ (fun z => iff_sym (R z)) Hlo).
    assert (Hhi' := range_upper_ext _ _ _ (fun z => iff_sym (R z)) Hhi).
    destruct (I4 BX BY lo hi Hlo' Hhi') as [A [Bl Bu]].
    split; [exact A|split].
    - intros K. apply Bl. unfold val in K. rewrite En. lra.
    - intros K. apply Bu. unfold val in K. rewrite Ep. lra. }
  split.
  { intros _. destruct (I4' NX NY) as [L U]. split; intros K.
    - apply L. exact (range_lower_ext _ _ _ (fun z => iff_sym (R z)) K).
    - apply U. exact (range_upper_ext _ _ _ (fun z => iff_sym (R z)) K). }
  intros _ Hz. apply (I5 BX BY). intros z Hz'. apply Hz. apply R. exact Hz'.
- (* the whole line *)
  assert (W' := W). destruct W' as [[s Z0] [[t Z1] Er]].
  assert (C : canonical_2 c0 c1)
    by exact (ball_2_canonical prec emax c0 c1 r (or_intror (or_introl W))).
  assert (F0 : is_finite prec emax c0 = true) by (rewrite Z0; reflexivity).
  rewrite Er in Ep, En. change (xval (infinity prec emax false)) with (XInf false) in Ep, En.
  cbn [xopp negb] in En.
  assert (Vc := xval_2_fin prec emax c0 c1 F0).
  assert (NX : interval_nonempty_2 c0 c1 c0 c1).
  { split; [exact C|split; [exact C|]]. rewrite Vc. apply xnonempty_fin. lra. }
  assert (NY : interval_nonempty_2 n0 n1 p0 p1).
  { split; [exact Cn|split; [exact Cp|]]. rewrite En, Ep. split; [reflexivity|split; reflexivity]. }
  assert (R : forall z : R,
              range_2 (fun x y : R => x + y) (in_interval_2 c0 c1 c0 c1) (in_interval_2 n0 n1 p0 p1) z
              <-> in_ball_2 c0 c1 r z).
  { intros z. split; [intros _; left; exact W|intros _].
    unfold in_interval_2. rewrite Vc, En, Ep.
    exists (B2R prec emax c0 + B2R prec emax c1), (z - (B2R prec emax c0 + B2R prec emax c1)).
    split; [split; cbn; apply Rle_bool_true; lra|].
    split; [split; reflexivity|]. cbv beta. ring. }
  generalize (interval_add_2_all prec emax nan_plus nan_minus nan_opp nan_abs nan_fma Hp
                c0 c1 c0 c1 n0 n1 p0 p1 (or_intror NX) (or_intror NY)).
  destruct (IeeeModel.interval_add_2 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma
              c0 c1 c0 c1 n0 n1 p0 p1) as [[[zl0 zl1] zu0] zu1].
  intros [I1 [I2 [I3 [I4 [I4' I5]]]]].
  split; [exact I1|].
  split.
  { rewrite I2. split; [|intros K; elim (NE K)].
    intros [K|K]; exfalso; destruct K as [K _].
    - rewrite K in F0. discriminate F0.
    - rewrite K in En. discriminate En. }
  split.
  { intros x Hx. apply R in Hx. destruct Hx as [a [b [Ha [Hb E]]]]. rewrite E. exact (I3 a b Ha Hb). }
  split; [intros K; elim (NF K)|].
  split.
  { intros _. destruct (I4' NX NY) as [L U]. split; intros K.
    - apply L. exact (range_lower_ext _ _ _ (fun z => iff_sym (R z)) K).
    - apply U. exact (range_upper_ext _ _ _ (fun z => iff_sym (R z)) K). }
  intros K. elim (NF K).
Qed.
