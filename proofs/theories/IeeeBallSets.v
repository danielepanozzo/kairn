(* The ball of one limb made from an interval of two numbers of T, and the split of a ball of one
   limb, in the IEEE model, on all values (docs/developer/design/milestone2.md, "One enclosure
   interface": "Midpoint, radius and the conversions" and "Hull, intersection and split of
   balls"; docs/developer/architecture.md, "Claims of the enclosure interface: the set operations
   of a ball" and "the conversions of two limbs"): ball_from_interval_1 and ball_split_1.

   Notation as in IeeeIntervalConvert.v and IeeeBallPredicates.v. From precision 2. The theorems
   K_correct at the end are the generated statements.

   What is proved.

   - ball_from_interval_1, for any two values lo and hi of T (ball_from_interval_1_correct): the
     result is a canonical ball; for lo <= hi finite, a finite ball that contains [lo, hi],
     whose center is in [lo, hi] within u |m| + eta of the midpoint m, and whose radius is the
     smallest number of T with which it contains [lo, hi]; the whole line when lo and hi are
     the bounds of a nonempty interval that is not bounded, when one of them is a NaN, whatever
     the other is, and when both are the same infinity (the owner's decision of 2026-11-20, as
     for interval_make_1 and ball_from_interval_2); and the empty set when the bounds are
     reversed, hi < lo. It is interval_to_ball_1 of the interval of interval_make_1, with the
     special balls selected last (the empty ball where rv = lt(hi, lo), the whole line
     otherwise), and the proof is that of interval_to_ball_1 (interval_to_ball_1_all of
     IeeeIntervalConvert.v) on the guarded bounds.

   - ball_split_1, for a canonical ball (ball_split_1_correct): two canonical balls; the empty
     set twice for the empty set and the whole line twice for the whole line; and for a finite
     ball of center c and radius r, every real number of [c - r, c] is in the first part and
     every one of [c, c + r] in the second. The parts are the point c plus the balls of center
     -h and h and radius q = max(h, r - h), h = RN(r / 2), by ball_add_1_full: r - h is a
     number of the format (it is r / 2 when the halving is exact, and otherwise r and h are
     multiples of eta below 2^(emin + prec)), so that q is at least h and r - h, and the ball
     (+-h, q) contains every number between 0 and +-r. *)
From Stdlib Require Import Reals ZArith Bool Lia Lra Psatz.
From Flocq Require Import Core Binary Plus_error.
From Kairn.Gen Require Import Model Statements IeeeStatements.
From Kairn Require Import Format Normalized EFT IeeeBridge IeeeVocabulary IeeeOps IeeeExt.
From Kairn Require Import IeeeBall IeeeBallFinite IeeeDirected IeeeEntry.
From Kairn Require Import IeeeIntervalVocabulary IeeeInterval1 IeeeBallConvert IeeeIntervalConvert.
From Kairn Require IeeeOperations.
From Kairn.Gen Require IeeeModel.
Open Scope R_scope.

Section IeeeBallSets.
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
Variable nan_const : nan_of.

Notation emin := (3 - emax - prec)%Z.
Notation fexp := (FLT_exp emin prec).
Notation format := (generic_format radix2 fexp).
Notation rnd := (round radix2 fexp (Znearest tie_even)).
Notation fin x := (is_finite prec emax x = true).
Notation b2r := (B2R prec emax).
Notation neg := (IeeeOperations.neg prec emax nan_opp).
Notation sub := (IeeeOperations.sub prec emax nan_minus).
Notation prod := (IeeeOperations.prod prec emax nan_fma).
Notation guard := (IeeeOperations.guard prec emax nan_plus).
Notation flt := (IeeeOperations.lt prec emax).
Notation fle := (IeeeOperations.le prec emax).
Notation feq := (IeeeOperations.eq prec emax).
Notation pzero := (IeeeOperations.pzero prec emax).
Notation pinf := (IeeeOperations.pinf prec emax).
Notation cnan := (IeeeOperations.cnan prec emax nan_const).
Notation ninf := (B754_infinity prec emax true).
Notation xv := (@xval prec emax).
Notation Om := (Omega prec emax).
Notation half := (IeeeModel.up_ball_from_interval_2_0 prec emax).
Notation interval_to_ball_1 :=
  (IeeeModel.interval_to_ball_1 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const).
Notation ball_add_1_full := (IeeeModel.ball_add_1_full prec emax nan_plus nan_abs nan_fma).

(** * ball_from_interval_1 *)

Theorem ball_from_interval_1_all :
  (2 <= prec)%Z ->
  forall lo hi : float,
  let '(cw, rw) :=
    IeeeModel.ball_from_interval_1 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const
      lo hi in
  ball_1 cw rw /\
  (xnonempty (xval lo) (xval hi) -> finite lo -> finite hi ->
   ball_finite_1 cw rw /\
   (forall x : R, val lo <= x <= val hi -> in_ball_1 cw rw x)) /\
  (xnonempty (xval lo) (xval hi) -> finite lo -> finite hi ->
   val lo <= val cw <= val hi /\
   Rabs (val cw - (val lo + val hi) / 2) <= u prec * Rabs ((val lo + val hi) / 2) + eta (ieee_emin prec emax) /\
   val rw = RU (ieee_emin prec emax) prec (Rmax (val cw - val lo) (val hi - val cw))) /\
  (xnonempty (xval lo) (xval hi) -> ~ (finite lo /\ finite hi) -> ball_whole_1 cw rw) /\
  (nan lo \/ nan hi \/ (exists s : bool, xval lo = XInf s /\ xval hi = XInf s) ->
   ball_whole_1 cw rw) /\
  (xlt (xval hi) (xval lo) = true -> ball_empty_1 cw rw).
Proof.
intros Hp lo hi. unfold IeeeModel.ball_from_interval_1. cbv zeta.
assert (Xl : xv (guard lo) = xv lo) by apply (xval_guard prec emax nan_plus).
assert (Xu : xv (guard hi) = xv hi) by apply (xval_guard prec emax nan_plus).
assert (Fl : is_finite prec emax (guard lo) = is_finite prec emax lo)
  by apply (guard_finite prec emax nan_plus).
assert (Fu : is_finite prec emax (guard hi) = is_finite prec emax hi)
  by apply (guard_finite prec emax nan_plus).
assert (Vl : b2r (guard lo) = b2r lo) by apply (guard_val prec emax nan_plus).
assert (Vu : b2r (guard hi) = b2r hi) by apply (guard_val prec emax nan_plus).
rewrite (neg_pinf prec emax nan_opp), (le_xval prec emax), !(lt_xval prec emax), Xl, Xu.
change (xv pinf) with (XInf false). change (xv ninf) with (XInf true).
assert (Wh : ball_whole_1 pzero pinf) by (split; [exists false; reflexivity|reflexivity]).
destruct (andb (andb (xle (xv lo) (xv hi)) (xlt (xv lo) (XInf false))) (xlt (XInf true) (xv hi)))
  eqn:V; cbv beta iota.
- (* the pair describes an interval *)
  apply andb_true_iff in V. destruct V as [V V3]. apply andb_true_iff in V. destruct V as [V1 V2].
  assert (N : xnonempty (xv lo) (xv hi)) by (split; [exact V1|split; [exact V2|exact V3]]).
  assert (I : interval_1 (guard lo) (guard hi)).
  { right. unfold interval_nonempty_1. rewrite Xl, Xu. exact N. }
  destruct (xnonempty_not_nan prec emax lo hi N) as [Nl Nh].
  (* neither a NaN nor the same infinity twice, nor reversed *)
  assert (NW : ~ (nan lo \/ nan hi \/ (exists s : bool, xval lo = XInf s /\ xval hi = XInf s))).
  { unfold nan. intros [K|[K|[s [K1 K2]]]]; [congruence|congruence|].
    rewrite K1, K2 in N. destruct N as [_ [W1 W2]]. destruct s; cbn in W1, W2; discriminate. }
  assert (NR : xlt (xval hi) (xval lo) <> true) by exact (xle_not_xlt _ _ V1).
  generalize (interval_to_ball_1_all prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const
                Hp (guard lo) (guard hi) I).
  destruct (interval_to_ball_1 (guard lo) (guard hi)) as [c r].
  intros [B1 [_ [B3 B4]]].
  assert (NI : interval_nonempty_1 (guard lo) (guard hi)).
  { unfold interval_nonempty_1. rewrite Xl, Xu. exact N. }
  split; [exact B1|].
  split.
  { intros _ Flo Fhi.
    assert (Bd : interval_bounded_1 (guard lo) (guard hi))
      by (split; [unfold finite; rewrite Fl; exact Flo|unfold finite; rewrite Fu; exact Fhi]).
    destruct (B4 Bd) as [BF [_ [_ [Cont _]]]].
    split; [exact BF|]. intros x Hx. right. split; [exact BF|]. apply Cont.
    unfold in_interval_1. unfold finite in Flo, Fhi.
    rewrite Xl, Xu, (xval_fin prec emax lo Flo), (xval_fin prec emax hi Fhi).
    unfold val in Hx. split; cbn; apply Rle_bool_true; lra. }
  split.
  { intros _ Flo Fhi.
    assert (Bd : interval_bounded_1 (guard lo) (guard hi))
      by (split; [unfold finite; rewrite Fl; exact Flo|unfold finite; rewrite Fu; exact Fhi]).
    destruct (B4 Bd) as [_ [Bc [Mc [_ Rr]]]]. unfold val in Bc, Mc, Rr |- *.
    rewrite Vl, Vu in Bc, Mc, Rr. split; [exact Bc|split; [exact Mc|exact Rr]]. }
  split.
  { intros _ NB. apply (B3 NI). intros [K1 K2]. apply NB. unfold finite.
    rewrite <- Fl, <- Fu. split; assumption. }
  split; [intros K; elim (NW K)|].
  intros K. elim (NR K).
- (* it describes none *)
  assert (NN : ~ xnonempty (xv lo) (xv hi)).
  { intros [N1 [N2 N3]]. rewrite N1, N2, N3 in V. discriminate V. }
  destruct (interval_to_ball_1 pzero pzero) as [c r].
  destruct (xlt (xv hi) (xv lo)) eqn:R; cbv beta iota.
  + (* reversed bounds: the empty ball *)
    assert (Em : ball_empty_1 cnan cnan) by (split; exact (proj2_sig nan_const)).
    split; [right; right; exact Em|].
    split; [intros K; elim (NN K)|].
    split; [intros K; elim (NN K)|].
    split; [intros K; elim (NN K)|].
    split; [|intros _; exact Em].
    unfold nan. intros [K|[K|[s [K1 K2]]]].
    * rewrite (xval_nan prec emax lo K) in R. destruct (xv hi) as [|[|]|z]; discriminate R.
    * rewrite (xval_nan prec emax hi K) in R. discriminate R.
    * rewrite K1, K2 in R. destruct s; discriminate R.
  + (* a NaN bound, or the same infinity twice: the whole line *)
    split; [right; left; exact Wh|].
    split; [intros K; elim (NN K)|].
    split; [intros K; elim (NN K)|].
    split; [intros K; elim (NN K)|].
    split; [intros _; exact Wh|].
    intros K. discriminate K.
Qed.

(** * ball_split_1 *)

(* r - RN(r / 2) is a number of the format, for a finite r >= 0. *)
Lemma half_rest_format :
  (2 <= prec)%Z -> forall r : R, format r -> 0 <= r ->
  0 <= rnd (r * / 2 + 0) <= r /\ format (r - rnd (r * / 2 + 0)).
Proof.
intros Hp r Fr Pr.
assert (Lo : 0 <= rnd (r * / 2 + 0)).
{ apply round_ge_generic; auto with typeclass_instances; [apply generic_format_0|lra]. }
assert (Hi : rnd (r * / 2 + 0) <= r).
{ apply round_le_generic; auto with typeclass_instances. lra. }
split; [split; assumption|].
destruct (Req_dec (rnd (r * / 2 + 0) * 2) r) as [E|E].
- replace (r - rnd (r * / 2 + 0)) with (rnd (r * / 2 + 0)) by lra.
  apply generic_format_round; auto with typeclass_instances.
- assert (S := half_inexact_small prec emax r Fr E).
  unfold Rminus. apply FLT_format_plus_small; [exact prec_gt_0_|exact Fr| |].
  + apply generic_format_opp. apply generic_format_round; auto with typeclass_instances.
  + rewrite Rabs_pos_eq by lra. rewrite Rabs_pos_eq in S by exact Pr.
    replace (prec + emin)%Z with (emin + prec)%Z by ring. lra.
Qed.

(* The ball (c, 0) plus the ball (k, q), for a finite c and |k| <= q, contains c + y for every
   y within q of k. *)
Lemma point_plus :
  (2 <= prec)%Z ->
  forall c k q : float, fin c -> fin k -> fin q -> 0 <= b2r q ->
  forall z : R, Rabs (z - b2r c - b2r k) <= b2r q ->
  let '(a0, a1) := ball_add_1_full c pzero k q in ball_1 a0 a1 /\ in_ball_1 a0 a1 z.
Proof.
intros Hp c k q Fc Fk Fq Pq z Hz.
assert (BC : ball_finite_1 c pzero) by (split; [exact Fc|split; [reflexivity|apply Rle_refl]]).
assert (BK : ball_finite_1 k q) by (split; [exact Fk|split; [exact Fq|exact Pq]]).
generalize (ball_add_1_full_correct prec emax prec_gt_0_ prec_lt_emax_ nan_plus nan_abs nan_fma Hp
              c pzero k q (or_introl BC) (or_introl BK)).
destruct (ball_add_1_full c pzero k q) as [a0 a1]. intros [B [_ [_ [_ C]]]].
split; [exact B|].
replace z with (b2r c + (z - b2r c)) by ring. apply C.
- right. split; [exact BC|]. unfold val. rewrite Rminus_diag, Rabs_R0. apply Rle_refl.
- right. split; [exact BK|]. unfold val. exact Hz.
Qed.

Theorem ball_split_1_all :
  (2 <= prec)%Z ->
  forall c r : float, ball_1 c r ->
  let '(ca, ra, cb, rb) :=
    IeeeModel.ball_split_1 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma c r in
  ball_1 ca ra /\
  ball_1 cb rb /\
  (ball_empty_1 c r -> ball_empty_1 ca ra /\ ball_empty_1 cb rb) /\
  (ball_whole_1 c r -> ball_whole_1 ca ra /\ ball_whole_1 cb rb) /\
  (ball_finite_1 c r ->
   (forall z : R, val c - val r <= z <= val c -> in_ball_1 ca ra z) /\
   (forall z : R, val c <= z <= val c + val r -> in_ball_1 cb rb z)).
Proof.
intros Hp c r B. unfold IeeeModel.ball_split_1. cbv zeta.
destruct B as [F|[W|E]].
2: { (* the whole line *)
  assert (Fr : flt r pinf = false) by (destruct W as [_ K]; rewrite K; reflexivity).
  rewrite Fr. cbv beta iota.
  destruct (ball_add_1_full pzero pzero pzero pzero) as [a0 a1]. cbv beta iota.
  split; [right; left; exact W|split; [right; left; exact W|]].
  split; [intros [K _]; destruct W as [[s Z] _]; rewrite Z in K; discriminate K|].
  split; [intros _; split; exact W|].
  intros [_ [K _]]. destruct W as [_ K']. rewrite K' in K. discriminate K. }
2: { (* the empty set *)
  assert (Fr : flt r pinf = false).
  { rewrite (lt_xval prec emax), (xval_nan prec emax r (proj2 E)). reflexivity. }
  rewrite Fr. cbv beta iota.
  destruct (ball_add_1_full pzero pzero pzero pzero) as [a0 a1]. cbv beta iota.
  split; [right; right; exact E|split; [right; right; exact E|]].
  split; [intros _; split; exact E|].
  split; [intros [[s Z] _]; destruct E as [K _]; rewrite Z in K; discriminate K|].
  intros [Fc _]. destruct E as [K _]. unfold nan in K.
  rewrite (finite_not_nan prec emax c Fc) in K. discriminate K. }
(* a finite ball *)
destruct F as [Fc [Fr Pr]]. unfold val in Pr.
rewrite (lt_pinf_finite prec emax r Fr). cbv beta iota.
destruct (prod_half prec emax nan_fma Hp r Fr)
  as [Fh [Eh _]].
assert (Fnr : fin (neg r)) by (rewrite (IeeeExt.neg_finite prec emax nan_opp); exact Fr).
destruct (prod_half prec emax nan_fma Hp (neg r) Fnr)
  as [Fhn [Ehn _]].
rewrite (IeeeExt.neg_value prec emax nan_opp) in Ehn.
assert (Ehn' : b2r (prod (neg r) half) = - b2r (prod r half)).
{ rewrite Ehn, Eh. replace (- b2r r * / 2 + 0) with (- (b2r r * / 2 + 0)) by ring.
  change (rnd (- (b2r r * / 2 + 0))) with (RN emin prec (- (b2r r * / 2 + 0))).
  rewrite RN_opp. reflexivity. }
destruct (half_rest_format Hp (b2r r) (b2r_format prec emax r) Pr) as [[H0 H1] Fg].
rewrite <- Eh in H0, H1, Fg.
assert (G : fin (sub r (prod r half)) /\ b2r (sub r (prod r half)) = b2r r - b2r (prod r half)).
{ destruct (sub_spec prec emax nan_minus r (prod r half) Fr Fh) as [S1 S2].
  assert (R : rnd (b2r r - b2r (prod r half)) = b2r r - b2r (prod r half))
    by (apply round_generic; auto with typeclass_instances).
  assert (I : inrange emax (rnd (b2r r - b2r (prod r half)))).
  { rewrite R. unfold IeeeBridge.inrange.
    generalize (b2r_Omega prec emax r) (Omega_lt_top prec emax). intros A B.
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
assert (PA : forall z : R, b2r c - b2r r <= z <= b2r c ->
             let '(a0, a1) := ball_add_1_full c pzero hn q in ball_1 a0 a1 /\ in_ball_1 a0 a1 z).
{ intros z Hz. apply (point_plus Hp c hn q Fc Fhn Fq Pq z).
  rewrite Ehn'. apply Rabs_le. lra. }
assert (PB : forall z : R, b2r c <= z <= b2r c + b2r r ->
             let '(b0, b1) := ball_add_1_full c pzero h q in ball_1 b0 b1 /\ in_ball_1 b0 b1 z).
{ intros z Hz. apply (point_plus Hp c h q Fc Fh Fq Pq z). apply Rabs_le. lra. }
assert (Bc : in_ball_1 c pzero (b2r c)).
{ right. split; [split; [exact Fc|split; [reflexivity|apply Rle_refl]]|].
  unfold val. rewrite Rminus_diag, Rabs_R0. apply Rle_refl. }
generalize (PA (b2r c)) (PB (b2r c)) PA PB.
destruct (ball_add_1_full c pzero hn q) as [a0 a1].
destruct (ball_add_1_full c pzero h q) as [b0 b1].
intros A B PA' PB'.
destruct (A ltac:(lra)) as [BA _]. destruct (B ltac:(lra)) as [BB _].
split; [exact BA|split; [exact BB|]].
split; [intros [K _]; unfold nan in K; rewrite (finite_not_nan prec emax c Fc) in K; discriminate K|].
split; [intros [_ K]; rewrite K in Fr; discriminate Fr|].
intros _. split.
- intros z Hz. unfold val in Hz. exact (proj2 (PA' z Hz)).
- intros z Hz. unfold val in Hz. exact (proj2 (PB' z Hz)).
Qed.

End IeeeBallSets.

(** * The generated statements *)

Theorem ball_from_interval_1_correct : ball_from_interval_1_spec.
Proof.
intros prec emax Hp0 He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const Hp lo hi.
exact (ball_from_interval_1_all prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const
         Hp lo hi).
Qed.

Theorem ball_split_1_correct : ball_split_1_spec.
Proof.
intros prec emax Hp0 He nan_plus nan_minus nan_opp nan_abs nan_fma Hp c r B.
exact (ball_split_1_all prec emax nan_plus nan_minus nan_opp nan_abs nan_fma Hp c r B).
Qed.
