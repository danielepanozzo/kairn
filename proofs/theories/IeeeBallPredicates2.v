(* The signs and the split of a ball with a center of two limbs, in the IEEE model, on all
   values (docs/developer/design/milestone2.md, "One enclosure interface"; docs/developer/
   architecture.md, "Claims of the enclosure interface: predicates and comparisons" and "the set
   operations of a ball"): ball_positive_2, ball_negative_2, ball_zero_2 and ball_split_2.

   Notation as in IeeeBallPredicates.v. A ball of two limbs (c0, c1, r) is canonical: finite
   ((c0, c1) a finite normalized pair, r finite, r >= 0), the whole line ((+-0, +-0, +inf)) or
   the empty set ((NaN, NaN, NaN)), with c = c0 + c1 for a finite ball.

   What is proved, for a canonical ball. The three signs are exact, for every precision: the
   mask is true exactly when the ball is not empty and every member is positive (negative,
   zero). The split, from precision 3: two canonical balls, the empty set twice for the empty
   set and the whole line twice for the whole line, and for a finite ball every real number of
   [c - r, c] in the first part and every one of [c, c + r] in the second (ball_add_2_full of
   the point c and the balls of center -+h and radius max(h, r - h), h = RN(r / 2), as for one
   limb). The theorems K_correct at the end are the generated statements.

   The proofs. A canonical ball of two limbs is the interval of extended real numbers
   [c - r, c + r], [-inf, +inf] or the empty pair (xlo_2, xhi_2, xball_2), and a sign is a
   relation of IeeeIntervalPredicates.v on these bounds; the comparisons of a 2-limb center with
   a limb are those of what they stand for (lt_1_2_ext, lt_2_1_ext, eq_2_1_ext of IeeeExt.v). *)
From Stdlib Require Import Reals ZArith Bool Lia Lra Psatz.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements IeeeStatements.
From Kairn Require Import Format Normalized EFT IeeeBridge IeeeVocabulary IeeeOps IeeeExt.
From Kairn Require Import IeeeBall IeeeBallFinite IeeeDirected IeeeEntry IeeeMake.
From Kairn Require Import IeeeIntervalVocabulary IeeeInterval1 IeeeInterval2.
From Kairn Require Import IeeeBallConvert IeeeIntervalConvert.
From Kairn Require Import IeeeIntervalExact IeeeIntervalPredicates IeeeBallPredicates IeeeBallSets.
From Kairn Require IeeeOperations.
From Kairn.Gen Require IeeeModel.
Open Scope R_scope.

Section BallPredicates2.
Variable prec emax : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Context {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}.

Notation float := (binary_float prec emax).
Notation nan_of := {x : float | is_nan prec emax x = true}.
Variable nan_plus nan_minus : float -> float -> nan_of.
Variable nan_opp nan_abs : float -> nan_of.
Variable nan_fma : float -> float -> float -> nan_of.

Notation emin := (3 - emax - prec)%Z.
Notation fexp := (FLT_exp emin prec).
Notation format := (generic_format radix2 fexp).
Notation rnd := (round radix2 fexp (Znearest tie_even)).
Notation fin x := (is_finite prec emax x = true).
Notation b2r := (B2R prec emax).
Notation neg := (IeeeOperations.neg prec emax nan_opp).
Notation sub := (IeeeOperations.sub prec emax nan_minus).
Notation prod := (IeeeOperations.prod prec emax nan_fma).
Notation flt := (IeeeOperations.lt prec emax).
Notation feq := (IeeeOperations.eq prec emax).
Notation pzero := (IeeeOperations.pzero prec emax).
Notation pinf := (IeeeOperations.pinf prec emax).
Notation xv := (@xval prec emax).
Notation xv2 := (@xval_2 prec emax).
Notation Om := (Omega prec emax).
Notation half := (IeeeModel.up_ball_from_interval_2_0 prec emax).
Notation make_2 := (IeeeModel.make_2 prec emax nan_plus).
Notation ball_add_2_full := (IeeeModel.ball_add_2_full prec emax nan_plus nan_minus nan_abs nan_fma).

Let Hp1 : (1 <= prec)%Z.
Proof. generalize prec_gt_0_. unfold Prec_gt_0. lia. Qed.

(** * A canonical ball of two limbs as an interval of extended real numbers *)

Definition xlo_2 (c0 c1 r : float) : xreal :=
  if is_finite prec emax r then XFin (b2r c0 + b2r c1 - b2r r)
  else if is_nan prec emax r then XInf false else XInf true.

Definition xhi_2 (c0 c1 r : float) : xreal :=
  if is_finite prec emax r then XFin (b2r c0 + b2r c1 + b2r r)
  else if is_nan prec emax r then XInf true else XInf false.

Lemma ball_2_canonical : forall c0 c1 r : float, ball_2 c0 c1 r -> canonical_2 c0 c1.
Proof.
intros c0 c1 r [[F0 [F1 [N _]]]|[[[s Z0] [[t Z1] _]]|[N0 [N1 _]]]].
- left. exact (conj F0 (conj F1 N)).
- left. subst c0 c1. split; [reflexivity|split; [reflexivity|]].
  apply (normalized_2_lead prec emax).
- right; right. split; assumption.
Qed.

Lemma ball_2_states :
  forall c0 c1 r : float, ball_2 c0 c1 r ->
  (ball_finite_2 c0 c1 r /\ ~ ball_whole_2 c0 c1 r /\ ~ ball_empty_2 c0 c1 r) \/
  (ball_whole_2 c0 c1 r /\ ~ ball_finite_2 c0 c1 r /\ ~ ball_empty_2 c0 c1 r) \/
  (ball_empty_2 c0 c1 r /\ ~ ball_finite_2 c0 c1 r /\ ~ ball_whole_2 c0 c1 r).
Proof.
intros c0 c1 r [F|[W|E]].
- left. split; [exact F|split].
  + intros [_ [_ K]]. destruct F as [_ [_ [_ [Fr _]]]]. rewrite K in Fr. discriminate Fr.
  + intros [K _]. destruct F as [F0 _]. unfold nan in K.
    rewrite (finite_not_nan prec emax c0 F0) in K. discriminate K.
- right; left. split; [exact W|split].
  + intros [_ [_ [_ [Fr _]]]]. destruct W as [_ [_ K]]. rewrite K in Fr. discriminate Fr.
  + intros [_ [_ K]]. destruct W as [_ [_ K']]. rewrite K' in K. discriminate K.
- right; right. split; [exact E|split].
  + intros [F0 _]. destruct E as [K _]. unfold nan in K.
    rewrite (finite_not_nan prec emax c0 F0) in K. discriminate K.
  + intros [[s K] _]. destruct E as [K' _]. rewrite K in K'. discriminate K'.
Qed.

Lemma xlohi_2_fin :
  forall c0 c1 r : float, fin r ->
  xlo_2 c0 c1 r = XFin (b2r c0 + b2r c1 - b2r r) /\ xhi_2 c0 c1 r = XFin (b2r c0 + b2r c1 + b2r r).
Proof. intros c0 c1 r F. unfold xlo_2, xhi_2. rewrite F. split; reflexivity. Qed.

Lemma xlohi_2_whole :
  forall c0 c1 : float,
  xlo_2 c0 c1 (infinity prec emax false) = XInf true /\
  xhi_2 c0 c1 (infinity prec emax false) = XInf false.
Proof. intros c0 c1. split; reflexivity. Qed.

Lemma xlohi_2_nan :
  forall c0 c1 r : float, is_nan prec emax r = true ->
  xlo_2 c0 c1 r = XInf false /\ xhi_2 c0 c1 r = XInf true.
Proof.
intros c0 c1 r N. unfold xlo_2, xhi_2. rewrite (nan_not_finite prec emax r N), N.
split; reflexivity.
Qed.

Lemma xball_2 :
  forall c0 c1 r : float, ball_2 c0 c1 r ->
  xinterval (xlo_2 c0 c1 r) (xhi_2 c0 c1 r) /\
  (~ ball_empty_2 c0 c1 r <-> xnonempty (xlo_2 c0 c1 r) (xhi_2 c0 c1 r)) /\
  (forall x : R, in_ball_2 c0 c1 r x <-> xmember (xlo_2 c0 c1 r) (xhi_2 c0 c1 r) x).
Proof.
intros c0 c1 r B. destruct (ball_2_states c0 c1 r B) as [[F [NW NE]]|[[W [NF NE]]|[E [NF NW]]]].
- assert (F' := F). destruct F' as [F0 [F1 [Nn [Fr Pr]]]].
  destruct (xlohi_2_fin c0 c1 r Fr) as [El Eh]. rewrite El, Eh.
  unfold val in Pr.
  assert (N : xnonempty (XFin (b2r c0 + b2r c1 - b2r r)) (XFin (b2r c0 + b2r c1 + b2r r))).
  { split; [cbn; apply Rle_bool_true; lra|split; reflexivity]. }
  split; [right; exact N|split; [split; intros _; [exact N|exact NE]|]].
  intros x. unfold in_ball_2, xmember. cbn [xle]. split.
  + intros [K|[_ K]]; [elim (NW K)|].
    apply Rabs_le_inv in K. unfold val in K. split; apply Rle_bool_true; lra.
  + intros [H K]. apply Rle_bool_inv in H. apply Rle_bool_inv in K. right.
    split; [exact F|]. apply Rabs_le. unfold val. lra.
- destruct W as [Z0 [Z1 Er]]. subst r. destruct (xlohi_2_whole c0 c1) as [El Eh].
  rewrite El, Eh.
  assert (N : xnonempty (XInf true) (XInf false)) by (split; [reflexivity|split; reflexivity]).
  split; [right; exact N|split; [split; intros _; [exact N|exact NE]|]].
  intros x. split; [intros _; split; reflexivity|intros _; left; split; [exact Z0|split; [exact Z1|reflexivity]]].
- destruct E as [N0 [N1 Nr]]. destruct (xlohi_2_nan c0 c1 r Nr) as [El Eh]. rewrite El, Eh.
  split; [left; split; reflexivity|split].
  + split; [intros K; elim (K (conj N0 (conj N1 Nr)))|intros [_ [K _]]; discriminate K].
  + intros x. split; [intros [K|[K _]]; [elim (NW K)|elim (NF K)]|intros K; elim (xmember_empty x K)].
Qed.

(** * The signs *)

Lemma ball_positive_2_bool :
  forall c0 c1 r : float, ball_2 c0 c1 r ->
  IeeeModel.ball_positive_2 prec emax c0 c1 r
  = andb (xlt (XFin 0) (xlo_2 c0 c1 r)) (xlt (xlo_2 c0 c1 r) (XInf false)).
Proof.
intros c0 c1 r B. unfold IeeeModel.ball_positive_2. cbv zeta.
rewrite (lt_1_2_ext prec emax Hp1 r c0 c1 (ball_2_canonical c0 c1 r B)).
destruct (ball_2_states c0 c1 r B) as [[[F0 [F1 [_ [Fr _]]]] _]|[[[[s Z0] [[t Z1] Er]] _]|[[N0 [N1 Nr]] _]]].
- destruct (xlohi_2_fin c0 c1 r Fr) as [El _].
  rewrite El, (xval_fin prec emax r Fr), (xval_2_fin prec emax c0 c1 F0). cbn [xlt]. bools.
- subst c0 c1 r. reflexivity.
- rewrite (xval_nan prec emax r Nr). destruct (xlohi_2_nan c0 c1 r Nr) as [El _]. rewrite El.
  reflexivity.
Qed.

Lemma ball_negative_2_bool :
  forall c0 c1 r : float, ball_2 c0 c1 r ->
  IeeeModel.ball_negative_2 prec emax nan_opp c0 c1 r
  = andb (xlt (xhi_2 c0 c1 r) (XFin 0)) (xlt (XInf true) (xhi_2 c0 c1 r)).
Proof.
intros c0 c1 r B. unfold IeeeModel.ball_negative_2. cbv zeta.
rewrite (lt_2_1_ext prec emax Hp1 c0 c1 (neg r) (ball_2_canonical c0 c1 r B)),
  (xval_neg prec emax nan_opp).
destruct (ball_2_states c0 c1 r B) as [[[F0 [F1 [_ [Fr _]]]] _]|[[[[s Z0] [[t Z1] Er]] _]|[[N0 [N1 Nr]] _]]].
- destruct (xlohi_2_fin c0 c1 r Fr) as [_ Eh].
  rewrite Eh, (xval_fin prec emax r Fr), (xval_2_fin prec emax c0 c1 F0). cbn [xlt xopp]. bools.
- subst c0 c1 r. reflexivity.
- rewrite (xval_2_nan prec emax c0 c1 N0). destruct (xlohi_2_nan c0 c1 r Nr) as [_ Eh].
  rewrite Eh. reflexivity.
Qed.

Lemma ball_zero_2_bool :
  forall c0 c1 r : float, ball_2 c0 c1 r ->
  IeeeModel.ball_zero_2 prec emax c0 c1 r
  = andb (xeq (xlo_2 c0 c1 r) (XFin 0)) (xeq (xhi_2 c0 c1 r) (XFin 0)).
Proof.
intros c0 c1 r B. unfold IeeeModel.ball_zero_2. cbv zeta.
rewrite (eq_2_1_ext prec emax Hp1 c0 c1 pzero (ball_2_canonical c0 c1 r B)), eq_xval.
change (xv pzero) with (XFin 0).
destruct (ball_2_states c0 c1 r B) as [[[F0 [F1 [_ [Fr _]]]] _]|[[[[s Z0] [[t Z1] Er]] _]|[[N0 [N1 Nr]] _]]].
- destruct (xlohi_2_fin c0 c1 r Fr) as [El Eh].
  rewrite El, Eh, (xval_fin prec emax r Fr), (xval_2_fin prec emax c0 c1 F0). cbn [xeq]. bools.
- subst c0 c1 r. rewrite andb_false_r. reflexivity.
- rewrite (xval_2_nan prec emax c0 c1 N0). destruct (xlohi_2_nan c0 c1 r Nr) as [El Eh].
  rewrite El, Eh. reflexivity.
Qed.

(** * ball_split_2 *)

(* The ball (c0, c1, 0) plus the ball (make_2 k, q), for a finite normalized center c and a
   finite k, contains c + y for every y within q of k. *)
Lemma point_plus_2 :
  (3 <= prec)%Z ->
  forall c0 c1 k q : float, fin c0 -> fin c1 -> normalized_2 emin prec (b2r c0) (b2r c1) ->
  fin k -> fin q -> 0 <= b2r q ->
  forall z : R, Rabs (z - (b2r c0 + b2r c1) - b2r k) <= b2r q ->
  let '(n0, n1) := make_2 k in
  let '(a0, a1, ar) := ball_add_2_full c0 c1 pzero n0 n1 q in
  ball_2 a0 a1 ar /\ in_ball_2 a0 a1 ar z.
Proof.
intros Hp c0 c1 k q F0 F1 Nc Fk Fq Pq z Hz.
generalize (make_2_facts prec emax nan_plus k).
destruct (make_2 k) as [n0 n1]. intros [Cn En].
rewrite (xval_fin prec emax k Fk) in En.
destruct (canonical_cases prec emax n0 n1 Cn)
  as [[Fn0 [Fn1 [Nn [_ [_ E2]]]]]|[[s [s' [_ [_ [_ [_ E2]]]]]]|[_ [_ [_ [_ E2]]]]]];
  rewrite E2 in En; try discriminate En.
injection En as En.
assert (BC : ball_finite_2 c0 c1 pzero)
  by (split; [exact F0|split; [exact F1|split; [exact Nc|split; [reflexivity|apply Rle_refl]]]]).
assert (BK : ball_finite_2 n0 n1 q)
  by (split; [exact Fn0|split; [exact Fn1|split; [exact Nn|split; [exact Fq|exact Pq]]]]).
generalize (ball_add_2_full_correct prec emax prec_gt_0_ prec_lt_emax_ nan_plus nan_minus nan_abs
              nan_fma Hp c0 c1 pzero n0 n1 q (or_introl BC) (or_introl BK)).
destruct (ball_add_2_full c0 c1 pzero n0 n1 q) as [[a0 a1] ar]. intros [B [_ [_ [_ C]]]].
split; [exact B|].
replace z with ((b2r c0 + b2r c1) + (z - (b2r c0 + b2r c1))) by ring. apply C.
- right. split; [exact BC|]. unfold val. rewrite Rminus_diag, Rabs_R0. apply Rle_refl.
- right. split; [exact BK|]. unfold val. rewrite En. exact Hz.
Qed.

Theorem ball_split_2_all :
  (3 <= prec)%Z ->
  forall c0 c1 r : float, ball_2 c0 c1 r ->
  let '(ca0, ca1, ra, cb0, cb1, rb) :=
    IeeeModel.ball_split_2 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma c0 c1 r in
  ball_2 ca0 ca1 ra /\
  ball_2 cb0 cb1 rb /\
  (ball_empty_2 c0 c1 r -> ball_empty_2 ca0 ca1 ra /\ ball_empty_2 cb0 cb1 rb) /\
  (ball_whole_2 c0 c1 r -> ball_whole_2 ca0 ca1 ra /\ ball_whole_2 cb0 cb1 rb) /\
  (ball_finite_2 c0 c1 r ->
   (forall z : R, (val c0 + val c1) - val r <= z <= (val c0 + val c1) -> in_ball_2 ca0 ca1 ra z) /\
   (forall z : R, (val c0 + val c1) <= z <= (val c0 + val c1) + val r -> in_ball_2 cb0 cb1 rb z)).
Proof.
intros Hp c0 c1 r B. assert (Hp2 : (2 <= prec)%Z) by lia.
unfold IeeeModel.ball_split_2. cbv zeta.
destruct (ball_2_states c0 c1 r B) as [[F [NW NE]]|[[W [NF NE]]|[E [NF NW]]]].
2: { (* the whole line *)
  assert (Fr : flt r pinf = false) by (destruct W as [_ [_ K]]; rewrite K; reflexivity).
  rewrite Fr. cbv beta iota.
  destruct (make_2 pzero) as [n0 n1].
  destruct (ball_add_2_full pzero pzero pzero n0 n1 pzero) as [[a0 a1] ar]. cbv beta iota.
  split; [right; left; exact W|split; [right; left; exact W|]].
  split; [intros K; elim (NE K)|].
  split; [intros _; split; exact W|].
  intros K. elim (NF K). }
2: { (* the empty set *)
  assert (Fr : flt r pinf = false).
  { rewrite (lt_xval prec emax), (xval_nan prec emax r (proj2 (proj2 E))). reflexivity. }
  rewrite Fr. cbv beta iota.
  destruct (make_2 pzero) as [n0 n1].
  destruct (ball_add_2_full pzero pzero pzero n0 n1 pzero) as [[a0 a1] ar]. cbv beta iota.
  split; [right; right; exact E|split; [right; right; exact E|]].
  split; [intros _; split; exact E|].
  split; [intros K; elim (NW K)|].
  intros K. elim (NF K). }
(* a finite ball *)
assert (F' := F). destruct F' as [F0 [F1 [Nc [Fr Pr]]]]. unfold val in Pr.
rewrite (lt_pinf_finite prec emax r Fr). cbv beta iota.
destruct (prod_half prec emax nan_fma Hp2 r Fr) as [Fh [Eh _]].
assert (Fnr : fin (neg r)) by (rewrite (IeeeExt.neg_finite prec emax nan_opp); exact Fr).
destruct (prod_half prec emax nan_fma Hp2 (neg r) Fnr) as [Fhn [Ehn _]].
rewrite (IeeeExt.neg_value prec emax nan_opp) in Ehn.
assert (Ehn' : b2r (prod (neg r) half) = - b2r (prod r half)).
{ rewrite Ehn, Eh. replace (- b2r r * / 2 + 0) with (- (b2r r * / 2 + 0)) by ring.
  change (rnd (- (b2r r * / 2 + 0))) with (RN emin prec (- (b2r r * / 2 + 0))).
  rewrite RN_opp. reflexivity. }
destruct (half_rest_format prec emax Hp2 (b2r r) (b2r_format prec emax r) Pr) as [[H0 H1] Fg].
rewrite <- Eh in H0, H1, Fg.
assert (G : fin (sub r (prod r half)) /\ b2r (sub r (prod r half)) = b2r r - b2r (prod r half)).
{ destruct (sub_spec prec emax nan_minus r (prod r half) Fr Fh) as [S1 S2].
  assert (R : rnd (b2r r - b2r (prod r half)) = b2r r - b2r (prod r half))
    by (apply round_generic; auto with typeclass_instances).
  assert (I : inrange emax (rnd (b2r r - b2r (prod r half)))).
  { rewrite R. unfold IeeeBridge.inrange.
    generalize (b2r_Omega prec emax r) (Omega_lt_top prec emax). intros A B'.
    rewrite Rabs_pos_eq by lra. lra. }
  assert (Fs := proj2 S1 I). split; [exact Fs|]. rewrite (S2 Fs). exact R. }
destruct G as [Fg' Eg].
set (h := prod r half) in *. set (g := sub r h) in *. set (hn := prod (neg r) half) in *.
assert (Q : fin (if flt h g then g else h) /\
            b2r (if flt h g then g else h) = Rmax (b2r h) (b2r g)).
{ rewrite (lt_finite prec emax h g Fh Fg').
  destruct (Rlt_bool_spec (b2r h) (b2r g)) as [K|K].
  - split; [exact Fg'|]. rewrite Rmax_right by lra. reflexivity.
  - split; [exact Fh|]. rewrite Rmax_left by lra. reflexivity. }
destruct Q as [Fq Eq]. set (q := if flt h g then g else h) in *.
assert (Pq : 0 <= b2r q) by (rewrite Eq; apply Rle_trans with (2 := Rmax_l _ _); exact H0).
assert (Qh : b2r h <= b2r q) by (rewrite Eq; apply Rmax_l).
assert (Qg : b2r r - b2r h <= b2r q) by (rewrite Eq, <- Eg; apply Rmax_r).
assert (PA : forall z : R, b2r c0 + b2r c1 - b2r r <= z <= b2r c0 + b2r c1 ->
             let '(n0, n1) := make_2 hn in
             let '(a0, a1, ar) := ball_add_2_full c0 c1 pzero n0 n1 q in
             ball_2 a0 a1 ar /\ in_ball_2 a0 a1 ar z).
{ intros z Hz. apply (point_plus_2 Hp c0 c1 hn q F0 F1 Nc Fhn Fq Pq z).
  rewrite Ehn'. apply Rabs_le. lra. }
assert (PB : forall z : R, b2r c0 + b2r c1 <= z <= b2r c0 + b2r c1 + b2r r ->
             let '(p0, p1) := make_2 h in
             let '(b0, b1, br) := ball_add_2_full c0 c1 pzero p0 p1 q in
             ball_2 b0 b1 br /\ in_ball_2 b0 b1 br z).
{ intros z Hz. apply (point_plus_2 Hp c0 c1 h q F0 F1 Nc Fh Fq Pq z). apply Rabs_le. lra. }
generalize (PA (b2r c0 + b2r c1)) (PB (b2r c0 + b2r c1)) PA PB.
destruct (make_2 hn) as [n0 n1]. destruct (make_2 h) as [p0 p1].
destruct (ball_add_2_full c0 c1 pzero n0 n1 q) as [[a0 a1] ar].
destruct (ball_add_2_full c0 c1 pzero p0 p1 q) as [[b0 b1] br].
intros A B' PA' PB'.
destruct (A ltac:(lra)) as [BA _]. destruct (B' ltac:(lra)) as [BB _].
split; [exact BA|split; [exact BB|]].
split; [intros K; elim (NE K)|].
split; [intros K; elim (NW K)|].
intros _. split.
- intros z Hz. unfold val in Hz. exact (proj2 (PA' z Hz)).
- intros z Hz. unfold val in Hz. exact (proj2 (PB' z Hz)).
Qed.

End BallPredicates2.

(** * The generated statements *)

Theorem ball_positive_2_correct : ball_positive_2_spec.
Proof.
intros prec emax Hp0 He c0 c1 r B. cbv zeta.
destruct (xball_2 prec emax c0 c1 r B) as [I [NE M]].
rewrite (ball_positive_2_bool prec emax c0 c1 r B), NE. setoid_rewrite M. exact (xpositive _ _ I).
Qed.

Theorem ball_negative_2_correct : ball_negative_2_spec.
Proof.
intros prec emax Hp0 He nan_opp c0 c1 r B. cbv zeta.
destruct (xball_2 prec emax c0 c1 r B) as [I [NE M]].
rewrite (ball_negative_2_bool prec emax nan_opp c0 c1 r B), NE. setoid_rewrite M.
exact (xnegative _ _ I).
Qed.

Theorem ball_zero_2_correct : ball_zero_2_spec.
Proof.
intros prec emax Hp0 He c0 c1 r B. cbv zeta.
destruct (xball_2 prec emax c0 c1 r B) as [I [NE M]].
rewrite (ball_zero_2_bool prec emax c0 c1 r B), NE. setoid_rewrite M. exact (xzero _ _).
Qed.

Theorem ball_split_2_correct : ball_split_2_spec.
Proof.
intros prec emax Hp0 He nan_plus nan_minus nan_opp nan_abs nan_fma Hp c0 c1 r B.
exact (ball_split_2_all prec emax nan_plus nan_minus nan_opp nan_abs nan_fma Hp c0 c1 r B).
Qed.
