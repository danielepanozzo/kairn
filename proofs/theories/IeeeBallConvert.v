(* The conversions of a ball, in the IEEE model, on all values: the bounds of a ball as
   numbers of T (ball_lower_as_1, ball_upper_as_1, ball_lower_as_2, ball_upper_as_2), the
   ball of one limb that contains a ball of two limbs (ball_narrow_2_1), and the ball of
   two limbs made from an interval of two values of T (ball_from_interval_2)
   (docs/developer/design/milestone2.md, "One enclosure interface": the row of lower_as
   and upper_as, "Midpoint, radius and the conversions" and "The empty set and the whole
   line").

   Notation as in IeeeInterval1.v: T is the IEEE format; Omega is its largest number; eta
   its smallest positive one; xval a is the extended real number a limb stands for; xrd
   and xru are the roundings down and up in the format with overflow; a ball, its states
   and its members are those of IeeeVocabulary.v, and the bounds of a set of real numbers
   those of IeeeIntervalVocabulary.v (range_lower, range_upper). c is the center of a
   ball (c0 + c1 for two limbs) and r its radius. The six kernels are the generated
   models of proofs/gen/IeeeModel.v, and the theorems K_correct at the end of the file
   establish their generated statements (proofs/gen/IeeeStatements.v).

   What is proved, from precision 2, for a canonical ball.

   - ball_lower_as_1 and ball_upper_as_1 (ball_lower_as_1_ieee, ball_upper_as_1_ieee): the
     empty ball gives +infinity and -infinity; otherwise the lower output is the lower
     bound of the set of the members rounded down in the format with overflow, and the
     upper output its upper bound rounded up: RD(c - r) and RU(c + r) for a finite ball,
     -infinity and +infinity for the whole line. These are the largest number of T that
     is at most every member, and the smallest that is at least every member.

   - ball_lower_as_2 and ball_upper_as_2 (ball_lower_as_2_ieee, ball_upper_as_2_ieee): the
     empty ball gives +infinity and -infinity; otherwise the lower output is at most the
     lower bound of the set of the members (-infinity for the whole line), and the upper
     output at least its upper bound; and for a finite ball and a finite output l,
     |l - (c - r)| <= 5 u (|c| + r) + 3 eta, and the same for the upper output and c + r.
     The output is RD(RD(c) - r): each rounding is within the gap of the format at its
     argument, at most max(eta, 2 u |t|) (rd_gap, ru_gap of Directed2.v), and the argument
     of the second is at most |c| + r plus the first gap. No number of steps from the
     rounding of c - r is claimed.

   - ball_narrow_2_1 (ball_narrow_2_1_ieee): the result is a canonical ball of one limb;
     it is empty exactly when the operand is; if it is finite then the operand is, and
     every x within r of c is within the new radius of c0; it is finite when the operand
     is finite and |c| + r <= 2^(emax - 2); and it contains every member of the operand
     in every case (the whole line for the whole line, and when the new radius
     overflows). The new radius is radd(r, |c1|), at least r + |c1|.

   - ball_from_interval_2, for any two values lo and hi of T (ball_from_interval_2_ieee):
     the result is a canonical ball of two limbs; for lo <= hi both finite it is a finite
     ball that contains [lo, hi], and when lo / 2 and hi / 2 are numbers of T its center is
     (lo + hi) / 2 exactly and its radius RU((hi - lo) / 2); for lo <= hi with an infinite
     bound it is the whole line; when a bound is a NaN it is the whole line, whatever the
     other bound is; otherwise it is the empty ball.
     The finite case (ball_from_interval_2_finite). The halves hl = RN(lo / 2) and
     hu = RN(hi / 2) are within eta / 2 of lo / 2 and hi / 2 (scale_error of MulPow2.v), and
     at most Omega / 2 in magnitude, so their exact sum by two_sum_ord does not overflow.
     The listing computes -hl as the product of the negated bound by 1/2, which is the
     same number (rounding to nearest is symmetric), so d = RU(hu - hl). Doubling a half
     back is exact, so the two tests say exactly whether the halvings were exact. If they
     were, the center is the midpoint and [lo, hi] is within hu - hl <= d of it. If not,
     [lo, hi] is within hu - hl + eta of the center, and the radius is the number after
     d, at least d + eta; that number is finite, because a bound whose halving is not
     exact is below 2^(emin + prec) in magnitude, so that d is at most 2^(emax - 1).

   What is not proved: for ball_from_interval_2, that the radius is the smallest of T for
   its center when a halving is not exact (it is not claimed); for the bounds of a ball of
   two limbs, anything about a number of steps. *)
From Stdlib Require Import Reals ZArith Bool Lia Lra Psatz.
From Flocq Require Import Core Binary Mult_error.
From Kairn.Gen Require Import Model Statements IeeeStatements.
From Kairn Require Import Format Normalized EFT Convert DirectedSum MulPow2 Directed2.
From Kairn Require Import IeeeBridge IeeeVocabulary IeeeEFT IeeeOps IeeeExt.
From Kairn Require Import IeeeBall IeeeBallFinite.
From Kairn Require Import Rectangle IeeeDirected IeeeEntry.
From Kairn Require Import IeeeIntervalVocabulary IeeeInterval1.
From Kairn Require Ball2 IeeeOperations.
From Kairn.Gen Require IeeeModel.
Open Scope R_scope.

(** * The bounds of a segment and of the whole line *)

(* The set of the real numbers within r of m has the bounds m - r and m + r. *)
Lemma range_segment_lower :
  forall (A : R -> Prop) (m r : R), 0 <= r ->
  (forall x : R, A x <-> Rabs (x - m) <= r) -> range_lower A (XFin (m - r)).
Proof.
intros A m r Hr E. split.
- intros z Hz. apply E in Hz. apply Rabs_le_inv in Hz. cbn [xle]. apply Rle_bool_true. lra.
- intros t Ht. cbn [xlt] in Ht. apply Rlt_bool_inv in Ht. exists (m - r). split; [|exact Ht].
  apply E. replace (m - r - m) with (- r) by ring.
  rewrite Rabs_Ropp, Rabs_pos_eq by exact Hr. apply Rle_refl.
Qed.

Lemma range_segment_upper :
  forall (A : R -> Prop) (m r : R), 0 <= r ->
  (forall x : R, A x <-> Rabs (x - m) <= r) -> range_upper A (XFin (m + r)).
Proof.
intros A m r Hr E. split.
- intros z Hz. apply E in Hz. apply Rabs_le_inv in Hz. cbn [xle]. apply Rle_bool_true. lra.
- intros t Ht. cbn [xlt] in Ht. apply Rlt_bool_inv in Ht. exists (m + r). split; [|exact Ht].
  apply E. replace (m + r - m) with r by ring.
  rewrite Rabs_pos_eq by exact Hr. apply Rle_refl.
Qed.

(* The set of all real numbers has the bounds -infinity and +infinity. *)
Lemma range_line_lower :
  forall A : R -> Prop, (forall x : R, A x) -> range_lower A (XInf true).
Proof.
intros A H. split.
- intros z _. reflexivity.
- intros t _. exists (t - 1). split; [apply H|lra].
Qed.

Lemma range_line_upper :
  forall A : R -> Prop, (forall x : R, A x) -> range_upper A (XInf false).
Proof.
intros A H. split.
- intros z _. reflexivity.
- intros t _. exists (t + 1). split; [apply H|lra].
Qed.

Section IeeeBallConvert.
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
Notation inrange := (IeeeBridge.inrange emax).
Notation neg := (IeeeOperations.neg prec emax nan_opp).
Notation fabs := (IeeeOperations.abs prec emax nan_abs).
Notation add := (IeeeOperations.add prec emax nan_plus).
Notation prod := (IeeeOperations.prod prec emax nan_fma).
Notation flt := (IeeeOperations.lt prec emax).
Notation fle := (IeeeOperations.le prec emax).
Notation feq := (IeeeOperations.eq prec emax).
Notation fsucc := (IeeeOperations.succ prec emax).
Notation guard := (IeeeOperations.guard prec emax nan_plus).
Notation pzero := (IeeeOperations.pzero prec emax).
Notation pinf := (IeeeOperations.pinf prec emax).
Notation cnan := (IeeeOperations.cnan prec emax nan_const).
Notation ninf := (B754_infinity prec emax true).
Notation xv := (@xval prec emax).
Notation Om := (Omega prec emax).
Notation two_sum_ord := (IeeeModel.two_sum_ord prec emax nan_plus nan_minus nan_abs).
Notation add_up_1 := (IeeeModel.add_up_1 prec emax nan_plus nan_minus nan_abs).
Notation sub_down_1 := (IeeeModel.sub_down_1 prec emax nan_plus nan_minus nan_opp nan_abs).
Notation to_down_2 := (IeeeModel.to_down_2 prec emax).
Notation to_up_2 := (IeeeModel.to_up_2 prec emax).
Notation radd := (IeeeModel.radd prec emax nan_plus).
Notation half := (IeeeModel.up_ball_from_interval_2_0 prec emax).
Notation two := (IeeeModel.up_ball_from_interval_2_1 prec emax).
Notation ball_lower_as_1 :=
  (IeeeModel.ball_lower_as_1 prec emax nan_plus nan_minus nan_opp nan_abs).
Notation ball_upper_as_1 :=
  (IeeeModel.ball_upper_as_1 prec emax nan_plus nan_minus nan_opp nan_abs).
Notation ball_lower_as_2 :=
  (IeeeModel.ball_lower_as_2 prec emax nan_plus nan_minus nan_opp nan_abs).
Notation ball_upper_as_2 :=
  (IeeeModel.ball_upper_as_2 prec emax nan_plus nan_minus nan_opp nan_abs).
Notation ball_narrow_2_1 := (IeeeModel.ball_narrow_2_1 prec emax nan_plus nan_abs).
Notation ball_from_interval_2 :=
  (IeeeModel.ball_from_interval_2 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const).

Let Hprec : (0 < prec)%Z.
Proof. exact prec_gt_0_. Qed.
Let Hemax : (prec < emax)%Z.
Proof. exact prec_lt_emax_. Qed.

(** * The members of a ball *)

(* The members of a finite ball are the real numbers within the radius of the center. *)
Lemma ball_1_members :
  forall c r : float, ball_finite_1 c r ->
  forall x : R, in_ball_1 c r x <-> Rabs (x - b2r c) <= b2r r.
Proof.
intros c r F x. split.
- intros H. exact (in_ball_1_finite prec emax c r x H F).
- intros H. right. split; assumption.
Qed.

Lemma ball_2_members :
  forall c0 c1 r : float, ball_finite_2 c0 c1 r ->
  forall x : R, in_ball_2 c0 c1 r x <-> Rabs (x - (b2r c0 + b2r c1)) <= b2r r.
Proof.
intros c0 c1 r F x. split.
- intros H. exact (in_ball_2_finite prec emax c0 c1 r x H F).
- intros H. right. split; assumption.
Qed.

(* The radius of a ball that is not empty is not a NaN. *)
Lemma ball_1_not_nan :
  forall c r : float, ball_1 c r -> ~ ball_empty_1 c r -> is_nan prec emax r = false.
Proof.
intros c r B NE. destruct (is_nan prec emax r) eqn:N; [|reflexivity].
elim NE. exact (proj1 (ball_1_empty prec emax c r B) N).
Qed.

Lemma ball_2_not_nan :
  forall c0 c1 r : float, ball_2 c0 c1 r -> ~ ball_empty_2 c0 c1 r ->
  is_nan prec emax r = false.
Proof.
intros c0 c1 r B NE. destruct (is_nan prec emax r) eqn:N; [|reflexivity].
elim NE. exact (proj1 (ball_2_empty prec emax c0 c1 r B) N).
Qed.

(** * ball_lower_as_1 and ball_upper_as_1 *)

(* ball_lower_as_1, for a canonical ball, from precision 2: the empty ball gives
   +infinity; otherwise the output is the lower bound of the set of the members rounded
   down in the format with overflow. *)
Theorem ball_lower_as_1_ieee :
  (2 <= prec)%Z -> forall c r : float, ball_1 c r ->
  let l := ball_lower_as_1 c r in
  (ball_empty_1 c r -> l = infinity prec emax false) /\
  (~ ball_empty_1 c r ->
   forall lo : xreal, range_lower (in_ball_1 c r) lo -> xval l = xrd prec emax lo).
Proof.
intros Hp c r B. unfold IeeeModel.ball_lower_as_1. cbv zeta. rewrite (eq_self prec emax r).
split.
- intros [_ Nr]. unfold nan in Nr. rewrite Nr. reflexivity.
- intros NE lo Hlo. rewrite (ball_1_not_nan c r B NE). cbn [negb].
  rewrite (sub_down_1_ieee prec emax nan_plus nan_minus nan_opp nan_abs Hp c r). f_equal.
  destruct B as [F|[Wh|E]]; [| |elim (NE E)].
  + assert (F' := F). destruct F' as [Fc [Fr Pr]].
    rewrite (xval_fin prec emax c Fc), (xval_fin prec emax r Fr). cbn [xopp xadd].
    assert (Ex : exists z : R, in_ball_1 c r z).
    { exists (b2r c). apply (ball_1_members c r F).
      unfold Rminus. rewrite Rplus_opp_r, Rabs_R0. exact Pr. }
    exact (range_lower_unique _ _ _ Ex
             (range_segment_lower _ _ _ Pr (ball_1_members c r F)) Hlo).
  + assert (All : forall x : R, in_ball_1 c r x) by (intros x; left; exact Wh).
    rewrite <- (range_lower_unique _ _ _ (ex_intro _ 0 (All 0)) (range_line_lower _ All) Hlo).
    destruct Wh as [[s Ec] Er]. rewrite Ec, Er. reflexivity.
Qed.

(* ball_upper_as_1, likewise: -infinity for the empty ball, and otherwise the upper bound
   of the set of the members rounded up. *)
Theorem ball_upper_as_1_ieee :
  (2 <= prec)%Z -> forall c r : float, ball_1 c r ->
  let h := ball_upper_as_1 c r in
  (ball_empty_1 c r -> h = infinity prec emax true) /\
  (~ ball_empty_1 c r ->
   forall hi : xreal, range_upper (in_ball_1 c r) hi -> xval h = xru prec emax hi).
Proof.
intros Hp c r B. unfold IeeeModel.ball_upper_as_1. cbv zeta. rewrite (eq_self prec emax r).
split.
- intros [_ Nr]. unfold nan in Nr. rewrite Nr. reflexivity.
- intros NE hi Hhi. rewrite (ball_1_not_nan c r B NE). cbn [negb].
  rewrite (add_up_1_ieee prec emax nan_plus nan_minus nan_abs Hp c r). f_equal.
  destruct B as [F|[Wh|E]]; [| |elim (NE E)].
  + assert (F' := F). destruct F' as [Fc [Fr Pr]].
    rewrite (xval_fin prec emax c Fc), (xval_fin prec emax r Fr). cbn [xadd].
    assert (Ex : exists z : R, in_ball_1 c r z).
    { exists (b2r c). apply (ball_1_members c r F).
      unfold Rminus. rewrite Rplus_opp_r, Rabs_R0. exact Pr. }
    exact (range_upper_unique _ _ _ Ex
             (range_segment_upper _ _ _ Pr (ball_1_members c r F)) Hhi).
  + assert (All : forall x : R, in_ball_1 c r x) by (intros x; left; exact Wh).
    rewrite <- (range_upper_unique _ _ _ (ex_intro _ 0 (All 0)) (range_line_upper _ All) Hhi).
    destruct Wh as [[s Ec] Er]. rewrite Ec, Er. reflexivity.
Qed.

(** * The center of a ball of two limbs, rounded down and up *)

(* The value of a finite normalized pair is below 2^emax in magnitude. *)
Lemma normalized_inrange :
  forall c0 c1 : float, normalized_2 emin prec (b2r c0) (b2r c1) ->
  Rabs (b2r c0 + b2r c1) < bpow radix2 emax.
Proof.
intros c0 c1 [_ [_ E]]. apply Rnot_le_lt. intros K.
generalize (Format.round_abs_ge emin prec tie_even (b2r c0 + b2r c1) (bpow radix2 emax)
              (format_top prec emax) K).
unfold RN in E. rewrite <- E.
generalize (b2r_inrange prec emax c0). unfold IeeeBridge.inrange. lra.
Qed.

(* to_down_2 of a finite normalized pair is at most its value, as an extended real number
   (it is -infinity when the rounding down is beyond the format), and when it is finite it
   is the rounding down of the value. *)
Lemma to_down_2_le :
  forall c0 c1 : float, fin c0 -> fin c1 -> normalized_2 emin prec (b2r c0) (b2r c1) ->
  xle (xv (to_down_2 c0 c1)) (XFin (b2r c0 + b2r c1)) = true /\
  (fin (to_down_2 c0 c1) -> b2r (to_down_2 c0 c1) = RD emin prec (b2r c0 + b2r c1)).
Proof.
intros c0 c1 F0 F1 N.
assert (C : canonical_2 c0 c1) by (left; split; [exact F0|split; [exact F1|exact N]]).
assert (Hp1 : (1 <= prec)%Z) by lia.
assert (E := to_down_2_ext prec emax Hp1 c0 c1 C).
unfold xval_2 in E. rewrite F0 in E. cbn [xround] in E. unfold overflow_of, val in E.
assert (R := normalized_inrange c0 c1 N). apply Rabs_lt_inv in R.
assert (L : RD emin prec (b2r c0 + b2r c1) <= b2r c0 + b2r c1).
{ unfold RD. destruct (round_DN_pt radix2 fexp (b2r c0 + b2r c1)) as [_ [L _]]. exact L. }
revert E.
destruct (Rlt_bool_spec (Rabs (RD emin prec (b2r c0 + b2r c1))) (bpow radix2 emax)) as [K|K];
  intros E.
- split.
  + rewrite E. cbn [xle]. apply Rle_bool_true. exact L.
  + intros Fa. rewrite (xval_fin prec emax _ Fa) in E. injection E as E. exact E.
- split.
  + rewrite E.
    destruct (Rlt_bool_spec (RD emin prec (b2r c0 + b2r c1)) 0) as [Q|Q]; [reflexivity|].
    exfalso. rewrite Rabs_pos_eq in K by exact Q. lra.
  + intros Fa. rewrite (xval_fin prec emax _ Fa) in E. discriminate E.
Qed.

Lemma to_up_2_ge :
  forall c0 c1 : float, fin c0 -> fin c1 -> normalized_2 emin prec (b2r c0) (b2r c1) ->
  xle (XFin (b2r c0 + b2r c1)) (xv (to_up_2 c0 c1)) = true /\
  (fin (to_up_2 c0 c1) -> b2r (to_up_2 c0 c1) = RU emin prec (b2r c0 + b2r c1)).
Proof.
intros c0 c1 F0 F1 N.
assert (C : canonical_2 c0 c1) by (left; split; [exact F0|split; [exact F1|exact N]]).
assert (Hp1 : (1 <= prec)%Z) by lia.
assert (E := to_up_2_ext prec emax Hp1 c0 c1 C).
unfold xval_2 in E. rewrite F0 in E. cbn [xround] in E. unfold overflow_of, val in E.
assert (R := normalized_inrange c0 c1 N). apply Rabs_lt_inv in R.
assert (L : b2r c0 + b2r c1 <= RU emin prec (b2r c0 + b2r c1)).
{ unfold RU. destruct (round_UP_pt radix2 fexp (b2r c0 + b2r c1)) as [_ [L _]]. exact L. }
revert E.
destruct (Rlt_bool_spec (Rabs (RU emin prec (b2r c0 + b2r c1))) (bpow radix2 emax)) as [K|K];
  intros E.
- split.
  + rewrite E. cbn [xle]. apply Rle_bool_true. exact L.
  + intros Fa. rewrite (xval_fin prec emax _ Fa) in E. injection E as E. exact E.
- split.
  + rewrite E.
    destruct (Rlt_bool_spec (RU emin prec (b2r c0 + b2r c1)) 0) as [Q|Q]; [|reflexivity].
    exfalso. rewrite Rabs_left in K by exact Q. lra.
  + intros Fa. rewrite (xval_fin prec emax _ Fa) in E. discriminate E.
Qed.

(** * ball_lower_as_2 and ball_upper_as_2 *)

(* Two roundings, each within the gap of the format at its argument: with g1 the gap at c
   and g2 the gap at x, where |x| <= |c| + g1 + r, the two gaps together are at most
   5 u (|c| + r) + 3 eta. From precision 2. *)
Lemma two_gaps :
  (2 <= prec)%Z -> forall c x r g1 g2 : R, 0 <= r ->
  0 <= g1 <= Rmax (eta emin) (2 * u prec * Rabs c) ->
  0 <= g2 <= Rmax (eta emin) (2 * u prec * Rabs x) ->
  Rabs x <= Rabs c + g1 + r ->
  g1 + g2 <= 5 * u prec * (Rabs c + r) + 3 * eta emin.
Proof.
intros Hp c x r g1 g2 Pr [G10 G11] [G20 G21] AX.
assert (Ht : 0 < u prec <= / 4) by exact (Ball2.u_bounds prec 2 Hp). destruct Ht as [U0 U1].
assert (e0 : 0 < eta emin) by apply bpow_gt_0.
set (U := u prec) in *. set (e := eta emin) in *.
assert (C0 := Rabs_pos c). assert (X0 := Rabs_pos x).
assert (P1 : 0 <= U * Rabs c) by (apply Rmult_le_pos; lra).
assert (P2 : 0 <= U * Rabs x) by (apply Rmult_le_pos; lra).
assert (P3 : 0 <= U * r) by (apply Rmult_le_pos; lra).
assert (M1 : Rmax e (2 * U * Rabs c) <= e + 2 * U * Rabs c) by (apply Rmax_lub; lra).
assert (M2 : Rmax e (2 * U * Rabs x) <= e + 2 * U * Rabs x) by (apply Rmax_lub; lra).
assert (K1 : U * Rabs x <= U * (Rabs c + g1 + r)) by (apply Rmult_le_compat_l; lra).
assert (K2 : U * g1 <= U * (e + 2 * U * Rabs c)) by (apply Rmult_le_compat_l; lra).
assert (K3 : U * e <= / 4 * e) by (apply Rmult_le_compat_r; lra).
assert (K4 : U * (U * Rabs c) <= / 4 * (U * Rabs c)) by (apply Rmult_le_compat_r; lra).
lra.
Qed.

(* ball_lower_as_2, for a canonical ball, from precision 2: the empty ball gives
   +infinity; otherwise the output is at most the lower bound of the set of the members;
   and for a finite ball and a finite output l, |l - (c - r)| <= 5 u (|c| + r) + 3 eta. *)
Theorem ball_lower_as_2_ieee :
  (2 <= prec)%Z -> forall c0 c1 r : float, ball_2 c0 c1 r ->
  let l := ball_lower_as_2 c0 c1 r in
  (ball_empty_2 c0 c1 r -> l = infinity prec emax false) /\
  (~ ball_empty_2 c0 c1 r ->
   forall lo : xreal, range_lower (in_ball_2 c0 c1 r) lo -> xle (xval l) lo = true) /\
  (finite c0 /\ finite c1 /\ finite r -> finite l ->
   Rabs (val l - ((val c0 + val c1) - val r))
   <= 5 * u prec ^ 1 * (Rabs (val c0 + val c1) + Rabs (val r)) + 3 * eta emin).
Proof.
intros Hp c0 c1 r B. unfold IeeeModel.ball_lower_as_2. cbv zeta. rewrite (eq_self prec emax r).
split; [|split].
- intros [_ [_ Nr]]. unfold nan in Nr. rewrite Nr. reflexivity.
- intros NE lo Hlo. assert (Nr := ball_2_not_nan c0 c1 r B NE). rewrite Nr. cbn [negb].
  destruct (ball_2_center prec emax c0 c1 r B Nr) as [F0 [F1 Nc]].
  destruct (to_down_2_le c0 c1 F0 F1 Nc) as [K _].
  rewrite (sub_down_1_ieee prec emax nan_plus nan_minus nan_opp nan_abs Hp (to_down_2 c0 c1) r).
  destruct B as [F|[Wh|E]]; [| |elim (NE E)].
  + assert (F' := F). destruct F' as [_ [_ [_ [Fr Pr]]]].
    assert (Ex : exists z : R, in_ball_2 c0 c1 r z).
    { exists (b2r c0 + b2r c1). apply (ball_2_members c0 c1 r F).
      unfold Rminus. rewrite Rplus_opp_r, Rabs_R0. exact Pr. }
    rewrite <- (range_lower_unique _ _ _ Ex
                  (range_segment_lower _ _ _ Pr (ball_2_members c0 c1 r F)) Hlo).
    rewrite (xval_fin prec emax r Fr). cbn [xopp]. apply (xrd_below prec emax). unfold val.
    revert K. destruct (xv (to_down_2 c0 c1)) as [|[|]|ra]; cbn [xle xadd]; intros K;
      try discriminate K.
    * reflexivity.
    * apply Rle_bool_inv in K. apply Rle_bool_true. lra.
  + assert (All : forall x : R, in_ball_2 c0 c1 r x) by (intros x; left; exact Wh).
    rewrite <- (range_lower_unique _ _ _ (ex_intro _ 0 (All 0)) (range_line_lower _ All) Hlo).
    destruct Wh as [_ [_ Er]]. rewrite Er.
    revert K. destruct (xv (to_down_2 c0 c1)) as [|[|]|ra]; cbn [xle]; intros K;
      try discriminate K; reflexivity.
- intros [F0 [F1 Fr]] Fl. unfold finite in F0, F1, Fr, Fl.
  rewrite (finite_not_nan prec emax r Fr) in Fl |- *. cbn [negb] in Fl |- *.
  destruct (ball_2_finite prec emax c0 c1 r B Fr) as [_ [_ [Nc [_ Pr]]]]. unfold val in Nc, Pr.
  destruct (to_down_2_le c0 c1 F0 F1 Nc) as [_ Va].
  assert (E := sub_down_1_ieee prec emax nan_plus nan_minus nan_opp nan_abs Hp (to_down_2 c0 c1) r).
  rewrite (xval_fin prec emax _ Fl), (xval_fin prec emax r Fr) in E. cbn [xopp] in E.
  assert (Fa : fin (to_down_2 c0 c1)).
  { destruct (xval_cases prec emax (to_down_2 c0 c1)) as [[Fa _]|[[s Ea]|Ea]]; [exact Fa| |];
      rewrite Ea in E; cbn in E; discriminate E. }
  rewrite (xval_fin prec emax _ Fa), (Va Fa) in E. cbn [xadd] in E.
  rewrite (xrd_real prec emax) in E.
  assert (Ba := b2r_Omega prec emax (to_down_2 c0 c1)). rewrite (Va Fa) in Ba.
  revert E.
  destruct (Rlt_bool_spec (RD emin prec (b2r c0 + b2r c1) + - b2r r) (- Om)) as [C|C];
    [intros E; discriminate E|].
  rewrite Rlt_bool_false by lra. intros E.
  assert (E' : b2r (sub_down_1 (to_down_2 c0 c1) r)
               = RD emin prec (RD emin prec (b2r c0 + b2r c1) + - b2r r))
    by (injection E as E; exact E).
  unfold val. rewrite E'. rewrite pow_1, (Rabs_pos_eq (b2r r)) by exact Pr.
  assert (G1 := rd_gap emin prec (b2r c0 + b2r c1)).
  assert (G2 := rd_gap emin prec (RD emin prec (b2r c0 + b2r c1) + - b2r r)).
  assert (AX : Rabs (RD emin prec (b2r c0 + b2r c1) + - b2r r)
               <= Rabs (b2r c0 + b2r c1)
                  + (b2r c0 + b2r c1 - RD emin prec (b2r c0 + b2r c1)) + b2r r).
  { unfold Rabs. destruct (Rcase_abs _), (Rcase_abs _); lra. }
  assert (T := two_gaps Hp _ _ _ _ _ Pr G1 G2 AX).
  apply Rabs_le. lra.
Qed.

(* ball_upper_as_2, likewise, with the center rounded up and the radius added, rounded
   up. *)
Theorem ball_upper_as_2_ieee :
  (2 <= prec)%Z -> forall c0 c1 r : float, ball_2 c0 c1 r ->
  let h := ball_upper_as_2 c0 c1 r in
  (ball_empty_2 c0 c1 r -> h = infinity prec emax true) /\
  (~ ball_empty_2 c0 c1 r ->
   forall hi : xreal, range_upper (in_ball_2 c0 c1 r) hi -> xle hi (xval h) = true) /\
  (finite c0 /\ finite c1 /\ finite r -> finite h ->
   Rabs (val h - ((val c0 + val c1) + val r))
   <= 5 * u prec ^ 1 * (Rabs (val c0 + val c1) + Rabs (val r)) + 3 * eta emin).
Proof.
intros Hp c0 c1 r B. unfold IeeeModel.ball_upper_as_2. cbv zeta. rewrite (eq_self prec emax r).
split; [|split].
- intros [_ [_ Nr]]. unfold nan in Nr. rewrite Nr. reflexivity.
- intros NE hi Hhi. assert (Nr := ball_2_not_nan c0 c1 r B NE). rewrite Nr. cbn [negb].
  destruct (ball_2_center prec emax c0 c1 r B Nr) as [F0 [F1 Nc]].
  destruct (to_up_2_ge c0 c1 F0 F1 Nc) as [K _].
  rewrite (add_up_1_ieee prec emax nan_plus nan_minus nan_abs Hp (to_up_2 c0 c1) r).
  destruct B as [F|[Wh|E]]; [| |elim (NE E)].
  + assert (F' := F). destruct F' as [_ [_ [_ [Fr Pr]]]].
    assert (Ex : exists z : R, in_ball_2 c0 c1 r z).
    { exists (b2r c0 + b2r c1). apply (ball_2_members c0 c1 r F).
      unfold Rminus. rewrite Rplus_opp_r, Rabs_R0. exact Pr. }
    rewrite <- (range_upper_unique _ _ _ Ex
                  (range_segment_upper _ _ _ Pr (ball_2_members c0 c1 r F)) Hhi).
    rewrite (xval_fin prec emax r Fr). apply (xru_above prec emax). unfold val.
    revert K. destruct (xv (to_up_2 c0 c1)) as [|[|]|ra]; cbn [xle xadd]; intros K;
      try discriminate K.
    * reflexivity.
    * apply Rle_bool_inv in K. apply Rle_bool_true. lra.
  + assert (All : forall x : R, in_ball_2 c0 c1 r x) by (intros x; left; exact Wh).
    rewrite <- (range_upper_unique _ _ _ (ex_intro _ 0 (All 0)) (range_line_upper _ All) Hhi).
    destruct Wh as [_ [_ Er]]. rewrite Er.
    revert K. destruct (xv (to_up_2 c0 c1)) as [|[|]|ra]; cbn [xle]; intros K;
      try discriminate K; reflexivity.
- intros [F0 [F1 Fr]] Fh. unfold finite in F0, F1, Fr, Fh.
  rewrite (finite_not_nan prec emax r Fr) in Fh |- *. cbn [negb] in Fh |- *.
  destruct (ball_2_finite prec emax c0 c1 r B Fr) as [_ [_ [Nc [_ Pr]]]]. unfold val in Nc, Pr.
  destruct (to_up_2_ge c0 c1 F0 F1 Nc) as [_ Va].
  assert (E := add_up_1_ieee prec emax nan_plus nan_minus nan_abs Hp (to_up_2 c0 c1) r).
  rewrite (xval_fin prec emax _ Fh), (xval_fin prec emax r Fr) in E.
  assert (Fa : fin (to_up_2 c0 c1)).
  { destruct (xval_cases prec emax (to_up_2 c0 c1)) as [[Fa _]|[[s Ea]|Ea]]; [exact Fa| |];
      rewrite Ea in E; cbn in E; discriminate E. }
  rewrite (xval_fin prec emax _ Fa), (Va Fa) in E. cbn [xadd] in E.
  rewrite (xru_real prec emax) in E.
  assert (Ba := b2r_Omega prec emax (to_up_2 c0 c1)). rewrite (Va Fa) in Ba.
  revert E.
  destruct (Rlt_bool_spec Om (RU emin prec (b2r c0 + b2r c1) + b2r r)) as [C|C];
    [intros E; discriminate E|].
  rewrite Rlt_bool_false by lra. intros E.
  assert (E' : b2r (add_up_1 (to_up_2 c0 c1) r)
               = RU emin prec (RU emin prec (b2r c0 + b2r c1) + b2r r))
    by (injection E as E; exact E).
  unfold val. rewrite E'. rewrite pow_1, (Rabs_pos_eq (b2r r)) by exact Pr.
  assert (G1 := ru_gap emin prec (b2r c0 + b2r c1)).
  assert (G2 := ru_gap emin prec (RU emin prec (b2r c0 + b2r c1) + b2r r)).
  assert (AX : Rabs (RU emin prec (b2r c0 + b2r c1) + b2r r)
               <= Rabs (b2r c0 + b2r c1)
                  + (RU emin prec (b2r c0 + b2r c1) - (b2r c0 + b2r c1)) + b2r r).
  { unfold Rabs. destruct (Rcase_abs _), (Rcase_abs _); lra. }
  assert (T := two_gaps Hp _ _ _ _ _ Pr G1 G2 AX).
  apply Rabs_le. lra.
Qed.

(** * ball_narrow_2_1 *)

(* The sum of two finite numbers, stepped up, is not a NaN. *)
Lemma radd_not_nan :
  forall a b : float, fin a -> fin b -> is_nan prec emax (radd a b) = false.
Proof.
intros a b Fa Fb. unfold IeeeModel.radd. cbv zeta. rewrite (succ_nan prec emax).
destruct (add_finite_cases prec emax nan_plus a b Fa Fb) as [[F _]|[E _]].
- exact (finite_not_nan prec emax _ F).
- rewrite E. reflexivity.
Qed.

(* It is finite when the exact sum of two nonnegative numbers is at most 2^(emax - 2). *)
Lemma radd_small :
  (2 <= prec)%Z -> forall a b : float, fin a -> fin b -> 0 <= b2r a -> 0 <= b2r b ->
  b2r a + b2r b <= bpow radix2 (emax - 2) -> fin (radd a b).
Proof.
intros Hp a b Fa Fb Pa Pb H. unfold IeeeModel.radd. cbv zeta.
assert (FT : format (bpow radix2 (emax - 2)))
  by (apply (IeeeBallFinite.format_bpow prec emax); lia).
assert (LT : bpow radix2 (emax - 2) < bpow radix2 (emax - 1)) by (apply bpow_lt; lia).
assert (LT' : bpow radix2 (emax - 1) < bpow radix2 emax) by (apply bpow_lt; lia).
assert (I : inrange (rnd (b2r a + b2r b))).
{ apply (IeeeBallFinite.inrange_le prec emax) with (bpow radix2 (emax - 2)); [exact FT|lra|lra]. }
destruct (add_fin prec emax nan_plus a b Fa Fb I) as [Fs Es].
assert (S1 : b2r (add a b) <= bpow radix2 (emax - 2)).
{ rewrite Es. apply (rnd_le_format prec emax); assumption. }
destruct (succ_finite prec emax (add a b) Fs) as [[F _]|[_ Top]]; [exact F|].
exfalso.
assert (succ radix2 fexp (b2r (add a b)) <= bpow radix2 (emax - 1)).
{ apply succ_le_lt; auto with typeclass_instances.
  - apply b2r_format.
  - apply (IeeeBallFinite.format_bpow prec emax). lia.
  - lra. }
lra.
Qed.

(* ball_narrow_2_1, for a canonical ball of two limbs, from precision 2: the result is a
   canonical ball of one limb; it is empty exactly when the operand is; a finite result
   has a finite operand, and every x within r of c is within the new radius of c0; the
   result is finite when the operand is and |c| + r <= 2^(emax - 2); and every member of
   the operand is a member of the result. *)
Theorem ball_narrow_2_1_ieee :
  (2 <= prec)%Z -> forall c0 c1 r : float, ball_2 c0 c1 r ->
  let '(cz, rz) := ball_narrow_2_1 c0 c1 r in
  ball_1 cz rz /\
  (ball_empty_1 cz rz <-> ball_empty_2 c0 c1 r) /\
  (ball_finite_1 cz rz ->
   ball_finite_2 c0 c1 r /\
   (forall x : R, Rabs (x - (val c0 + val c1)) <= val r -> Rabs (x - val cz) <= val rz)) /\
  (ball_finite_2 c0 c1 r ->
   Rabs ((Rabs (val c0 + val c1)) + val r) <= bpow radix2 (emax - 2) ->
   ball_finite_1 cz rz) /\
  (forall x : R, in_ball_2 c0 c1 r x -> in_ball_1 cz rz x).
Proof.
intros Hp c0 c1 r B. unfold IeeeModel.ball_narrow_2_1. cbv zeta.
assert (Whole : ball_whole_1 pzero pinf) by (split; [exists false; reflexivity|reflexivity]).
destruct B as [F|[Wh|E]].
- (* a finite ball *)
  assert (F' := F). destruct F' as [F0 [F1 [Nc [Fr Pr]]]]. unfold val in Nc, Pr.
  assert (Fa : fin (fabs c1)) by (rewrite (abs_finite prec emax nan_abs); exact F1).
  assert (Ea : b2r (fabs c1) = Rabs (b2r c1)) by apply (abs_val prec emax nan_abs).
  assert (Pa : 0 <= b2r (fabs c1)) by (rewrite Ea; apply Rabs_pos).
  assert (NE2 : ~ ball_empty_2 c0 c1 r).
  { intros [_ [_ K]]. unfold nan in K. rewrite (finite_not_nan prec emax r Fr) in K.
    discriminate K. }
  destruct (radd_ext prec emax nan_plus Hp r (fabs c1)
              (nonneg_ext_finite prec emax r Fr Pr) (abs_nonneg prec emax nan_abs c1))
    as [Nn Fin].
  assert (NN := radd_not_nan r (fabs c1) Fr Fa).
  assert (Small := radd_small Hp r (fabs c1) Fr Fa Pr Pa).
  revert Nn Fin NN Small. generalize (radd r (fabs c1)). intros rz Nn Fin NN Small.
  destruct Nn as [K|[Inf|[Frz Prz]]]; [unfold nan in K; congruence| |].
  + (* the new radius overflows: the whole line *)
    rewrite Inf. change (feq (infinity prec emax false) pinf) with true. cbv beta iota.
    split; [right; left; exact Whole|].
    split; [split; [intros [K _]; unfold nan in K; discriminate K|intros K; elim (NE2 K)]|].
    split; [intros [_ [K _]]; unfold finite in K; discriminate K|].
    split; [|intros x _; left; exact Whole].
    intros _ Hb. exfalso.
    assert (Ht : 0 < u prec <= / 4) by exact (Ball2.u_bounds prec 2 Hp).
    assert (Tl := normalized_2_tail_rel emin prec _ _ Nc).
    assert (Ld := lead_le prec emax Hp _ _ Nc).
    assert (A0 := Rabs_pos (b2r c0)).
    assert (L1 : u prec * Rabs (b2r c0) <= / 4 * Rabs (b2r c0))
      by (apply Rmult_le_compat_r; lra).
    assert (Hb' := Rle_trans _ _ _ (Rle_abs _) Hb). unfold val in Hb'.
    assert (Frz : fin rz) by (apply Small; rewrite Ea; lra).
    rewrite Inf in Frz. discriminate Frz.
  + (* a finite radius: the leading limb is the center *)
    assert (Wf : feq rz pinf = false).
    { rewrite (eq_xval prec emax), (xval_fin prec emax rz Frz). reflexivity. }
    rewrite Wf. cbv beta iota.
    destruct (Fin Frz) as [_ [_ [Sum _]]]. rewrite Ea in Sum.
    assert (BF : ball_finite_1 c0 rz) by (split; [exact F0|split; [exact Frz|exact Prz]]).
    assert (Near : forall x : R, Rabs (x - (b2r c0 + b2r c1)) <= b2r r ->
                   Rabs (x - b2r c0) <= b2r rz).
    { intros x Hx. replace (x - b2r c0) with ((x - (b2r c0 + b2r c1)) + b2r c1) by ring.
      apply Rle_trans with (1 := Rabs_triang _ _). lra. }
    split; [left; exact BF|].
    split.
    { split; [|intros K; elim (NE2 K)].
      intros [K _]. unfold nan in K. rewrite (finite_not_nan prec emax c0 F0) in K.
      discriminate K. }
    split; [intros _; split; [exact F|exact Near]|].
    split; [intros _ _; exact BF|].
    intros x Hx. right. split; [exact BF|].
    exact (Near x (in_ball_2_finite prec emax c0 c1 r x Hx F)).
- (* the whole line *)
  assert (Wh' := Wh). destruct Wh' as [[s0 E0] [[s1 E1] Er]].
  assert (Erz : radd r (fabs c1) = pinf).
  { unfold IeeeModel.radd. cbv zeta. rewrite Er, E1.
    change (add (infinity prec emax false) (fabs (B754_zero prec emax s1))) with pinf.
    apply (succ_pinf prec emax). }
  rewrite Erz. change (feq pinf pinf) with true. cbv beta iota.
  assert (NE2 : ~ ball_empty_2 c0 c1 r).
  { intros [_ [_ K]]. rewrite Er in K. unfold nan in K. discriminate K. }
  split; [right; left; exact Whole|].
  split; [split; [intros [K _]; unfold nan in K; discriminate K|intros K; elim (NE2 K)]|].
  split; [intros [_ [K _]]; unfold finite in K; discriminate K|].
  split; [intros [_ [_ [_ [K _]]]]; rewrite Er in K; unfold finite in K; discriminate K|].
  intros x _. left. exact Whole.
- (* the empty ball *)
  assert (E' := E). destruct E' as [N0 [N1 Nr]].
  assert (Nrz : is_nan prec emax (radd r (fabs c1)) = true).
  { unfold IeeeModel.radd. cbv zeta. rewrite (succ_nan prec emax).
    apply (add_nan_l prec emax nan_plus). exact Nr. }
  revert Nrz. generalize (radd r (fabs c1)). intros rz Nrz.
  assert (Wf : feq rz pinf = false).
  { rewrite (eq_xval prec emax), (xval_nan prec emax rz Nrz). reflexivity. }
  rewrite Wf. cbv beta iota.
  assert (Em : ball_empty_1 c0 rz) by (split; [exact N0|exact Nrz]).
  split; [right; right; exact Em|].
  split; [split; intros _; [exact E|exact Em]|].
  split.
  { intros [_ [K _]]. unfold finite in K. rewrite (nan_not_finite prec emax rz Nrz) in K.
    discriminate K. }
  split.
  { intros [_ [_ [_ [K _]]]]. unfold finite in K. rewrite (nan_not_finite prec emax r Nr) in K.
    discriminate K. }
  intros x Hx. elim (in_ball_2_not_empty prec emax c0 c1 r x Hx E).
Qed.

(** * ball_from_interval_2 *)

(* The two constants of the listing: 1/2 and 2. *)
Lemma half_spec : (2 <= prec)%Z -> fin half /\ b2r half = / 2.
Proof.
intros Hp. unfold IeeeModel.up_ball_from_interval_2_0.
assert (FH : format (/ 2)) by exact (IeeeBallFinite.format_half prec emax Hp).
assert (LT : / 2 < bpow radix2 emax).
{ apply Rlt_le_trans with (bpow radix2 0); [simpl; lra|apply bpow_le; lia]. }
replace (1 / 2) with (/ 2) by field.
destruct (const_of_RU prec emax (/ 2) (/ 2) ltac:(lra) (Rle_refl _) FH LT) as [F [E _]].
split; [exact F|]. rewrite E. apply round_generic; auto with typeclass_instances.
Qed.

Lemma two_spec : (2 <= prec)%Z -> fin two /\ b2r two = 2.
Proof.
intros Hp. unfold IeeeModel.up_ball_from_interval_2_1.
assert (F2 : format (bpow radix2 1)) by (apply (IeeeBallFinite.format_bpow prec emax); lia).
assert (LT : bpow radix2 1 < bpow radix2 emax) by (apply bpow_lt; lia).
change (bpow radix2 1) with 2 in F2, LT.
destruct (const_of_RU prec emax 2 2 ltac:(lra) (Rle_refl _) F2 LT) as [F [E _]].
split; [exact F|]. rewrite E. apply round_generic; auto with typeclass_instances.
Qed.

(* Halving a number of the format: the rounded half is within eta / 2 of the half, and it
   is the half unless the number is below 2^(emin + prec) in magnitude. Doubling a number
   of the format is exact. *)
Lemma half_error :
  forall x : R, format x -> Rabs (rnd (x * / 2 + 0) - x * / 2) <= / 2 * eta emin.
Proof.
intros x Fx. rewrite Rplus_0_r.
replace (x * / 2) with (x * bpow radix2 (-1)) by (rewrite pow2_m1; reflexivity).
exact (scale_error emin prec x (-1) Fx).
Qed.

Lemma half_inexact_small :
  forall x : R, format x -> rnd (x * / 2 + 0) * 2 <> x -> Rabs x < bpow radix2 (emin + prec).
Proof.
intros x Fx H. apply Rnot_le_lt. intros K. apply H.
assert (Fh : format (x * / 2)).
{ rewrite <- pow2_m1. apply (mult_bpow_exact_FLT radix2 emin prec x (-1) Fx).
  assert (emin + prec + 1 <= mag radix2 x)%Z.
  { apply mag_ge_bpow. replace (emin + prec + 1 - 1)%Z with (emin + prec)%Z by ring. exact K. }
  lia. }
rewrite Rplus_0_r, (round_generic radix2 fexp (Znearest tie_even) _ Fh). field.
Qed.

Lemma format_double : forall x : R, format x -> format (x * 2).
Proof.
intros x Fx.
destruct (FLT_format_generic radix2 emin prec x Fx) as [[m e] Ex Hm He].
apply generic_format_FLT. exists (Float radix2 m (e + 1)).
- rewrite Ex. unfold F2R. cbn [Fnum Fexp]. rewrite bpow_plus.
  change (bpow radix2 1) with 2. ring.
- exact Hm.
- cbn [Fexp] in He |- *. lia.
Qed.

(* One step up from a nonnegative number of the format adds at least eta. *)
Lemma succ_ge_plus_eta :
  forall x : R, 0 <= x -> x + eta emin <= succ radix2 fexp x.
Proof.
intros x Hx. rewrite succ_eq_pos by exact Hx. apply Rplus_le_compat_l.
unfold eta. rewrite <- (ulp_FLT_0 radix2 emin prec).
apply ulp_ge_ulp_0; auto with typeclass_instances.
Qed.

(* A finite bound, guarded, and its half: both are finite; the half is the rounded half,
   at most Omega / 2 in magnitude and within eta / 2 of the exact half; and doubling it
   back is exact. *)
Lemma half_of_bound :
  (2 <= prec)%Z -> forall x : float, fin x ->
  fin (guard x) /\ b2r (guard x) = b2r x /\
  fin (prod (guard x) half) /\ b2r (prod (guard x) half) = rnd (b2r x * / 2 + 0) /\
  Rabs (b2r (prod (guard x) half)) <= Om / 2 /\
  Rabs (b2r (prod (guard x) half) - b2r x * / 2) <= / 2 * eta emin /\
  fin (prod (prod (guard x) half) two) /\
  b2r (prod (prod (guard x) half) two) = b2r (prod (guard x) half) * 2.
Proof.
intros Hp x Fx.
destruct (half_spec Hp) as [Fhalf Ehalf]. destruct (two_spec Hp) as [Ftwo Etwo].
assert (Fg : fin (guard x)) by (rewrite (guard_finite prec emax nan_plus); exact Fx).
assert (Eg : b2r (guard x) = b2r x) by apply (guard_val prec emax nan_plus).
assert (Bx := b2r_le_Omega prec emax x).
assert (LT := Omega_lt_top prec emax).
assert (O0 := Omega_gt_0 prec emax).
assert (R1 : Rabs (rnd (b2r x * / 2 + 0)) <= Om / 2).
{ apply (Format.round_abs_le emin prec tie_even); [exact (format_half_Omega prec emax)|].
  rewrite Rplus_0_r, Rabs_mult, (Rabs_pos_eq (/ 2)) by lra. lra. }
assert (I1 : inrange (rnd (b2r (guard x) * b2r half + 0))).
{ rewrite Eg, Ehalf. unfold IeeeBridge.inrange. lra. }
destruct (prod_fin prec emax nan_fma (guard x) half Fg Fhalf I1) as [Fh Eh].
rewrite Eg, Ehalf in Eh.
assert (Ed : rnd (b2r (prod (guard x) half) * b2r two + 0) = b2r (prod (guard x) half) * 2).
{ rewrite Etwo, Rplus_0_r. apply round_generic; auto with typeclass_instances.
  apply format_double. apply b2r_format. }
assert (I2 : inrange (rnd (b2r (prod (guard x) half) * b2r two + 0))).
{ rewrite Ed, Eh. unfold IeeeBridge.inrange.
  rewrite Rabs_mult, (Rabs_pos_eq 2) by lra. lra. }
destruct (prod_fin prec emax nan_fma _ two Fh Ftwo I2) as [Fb Eb]. rewrite Ed in Eb.
split; [exact Fg|split; [exact Eg|split; [exact Fh|split; [exact Eh|]]]].
split; [rewrite Eh; exact R1|].
split; [rewrite Eh; apply half_error; apply b2r_format|].
split; [exact Fb|exact Eb].
Qed.

(* The center and the radius that the listing computes for a bounded interval: the exact
   sum of the halves, and the difference of the halves rounded up, stepped up when a
   halving was not exact. *)
Definition bfi_center (lo hi : float) : float * float :=
  two_sum_ord (prod (guard lo) half) (prod (guard hi) half).

Definition bfi_radius (lo hi : float) : float :=
  if andb (feq (prod (prod (guard lo) half) two) (guard lo))
          (feq (prod (prod (guard hi) half) two) (guard hi))
  then add_up_1 (prod (guard hi) half) (prod (neg (guard lo)) half)
  else fsucc (add_up_1 (prod (guard hi) half) (prod (neg (guard lo)) half)).

(* What the listing returns: for a pair that describes an interval, the center and the
   radius above when both bounds are finite and the whole line otherwise; for a pair that
   describes none, the empty ball, or the whole line when a bound is a NaN. *)
Lemma ball_from_interval_2_eq :
  forall lo hi : float,
  ball_from_interval_2 lo hi
  = (let v := andb (andb (fle (guard lo) (guard hi)) (flt (guard lo) pinf))
                   (flt (neg pinf) (guard hi)) in
     let f := andb (flt (neg pinf) (guard lo)) (flt (guard hi) pinf) in
     let nn := andb (feq (guard lo) (guard lo)) (feq (guard hi) (guard hi)) in
     (if v then (if f then fst (bfi_center lo hi) else pzero) else (if nn then cnan else pzero),
      if v then (if f then snd (bfi_center lo hi) else pzero) else (if nn then cnan else pzero),
      if v then (if f then bfi_radius lo hi else pinf) else (if nn then cnan else pinf))).
Proof.
intros lo hi. unfold IeeeModel.ball_from_interval_2, bfi_center, bfi_radius.
destruct (two_sum_ord (prod (guard lo) half) (prod (guard hi) half)) as [c0 c1].
reflexivity.
Qed.

(* A bounded interval lo <= hi of two finite values of T: the ball is finite, it contains
   [lo, hi], and when lo / 2 and hi / 2 are numbers of the format its center is the
   midpoint and its radius the half-width rounded up. From precision 2. *)
Lemma ball_from_interval_2_finite :
  (2 <= prec)%Z -> forall lo hi : float, fin lo -> fin hi -> b2r lo <= b2r hi ->
  ball_finite_2 (fst (bfi_center lo hi)) (snd (bfi_center lo hi)) (bfi_radius lo hi) /\
  (forall x : R, b2r lo <= x <= b2r hi ->
   Rabs (x - (b2r (fst (bfi_center lo hi)) + b2r (snd (bfi_center lo hi))))
   <= b2r (bfi_radius lo hi)) /\
  (format (b2r lo / 2) -> format (b2r hi / 2) ->
   b2r (fst (bfi_center lo hi)) + b2r (snd (bfi_center lo hi)) = (b2r lo + b2r hi) / 2 /\
   b2r (bfi_radius lo hi) = RU emin prec ((b2r hi - b2r lo) / 2)).
Proof.
intros Hp lo hi Flo Fhi Hle.
generalize (half_of_bound Hp lo Flo) (half_of_bound Hp hi Fhi).
unfold bfi_center, bfi_radius.
set (gl := guard lo). set (gu := guard hi).
set (hl := prod gl half). set (hu := prod gu half).
intros [Fgl [Egl [Fhl [Ehl [Bhl [Dhl [Fbl Ebl]]]]]]] [Fgu [Egu [Fhu [Ehu [Bhu [Dhu [Fbu Ebu]]]]]]].
assert (O0 := Omega_gt_0 prec emax).
assert (e0 : 0 < eta emin) by apply bpow_gt_0.
(* the center: the exact sum of the halves *)
assert (Sum : Rabs (b2r hl + b2r hu) <= Om).
{ apply Rle_trans with (1 := Rabs_triang _ _). lra. }
generalize (two_sum_ord_ieee_finite prec emax nan_plus nan_minus nan_abs Hp hl hu Fhl Fhu)
           (two_sum_ord_facts emin prec Hp (b2r hl) (b2r hu)
              (b2r_format prec emax hl) (b2r_format prec emax hu)).
destruct (two_sum_ord hl hu) as [c0 c1]. cbn [fst snd].
intros [TF NF] [_ [Es Nc]].
assert (Fc0 : fin c0).
{ destruct (finite_dec prec emax c0) as [F|F]; [exact F|].
  exfalso. destruct (NF F) as [sg [_ [_ K]]]. apply Rabs_le_inv in Sum. destruct sg; lra. }
destruct (TF Fc0) as [Fc1 Ec]. rewrite <- Ec in Es, Nc. cbn [fst snd] in Es, Nc.
(* minus the lower half *)
set (hn := prod (neg gl) half).
assert (Hn : fin hn /\ b2r hn = - b2r hl).
{ destruct (half_spec Hp) as [Fhalf Ehalf].
  assert (Fn : fin (neg gl)) by (rewrite (IeeeExt.neg_finite prec emax nan_opp); exact Fgl).
  assert (V : rnd (b2r (neg gl) * b2r half + 0) = - b2r hl).
  { rewrite (IeeeExt.neg_value prec emax nan_opp), Egl, Ehalf, Ehl.
    replace (- b2r lo * / 2 + 0) with (- (b2r lo * / 2 + 0)) by ring.
    exact (EFT.RN_opp emin prec (b2r lo * / 2 + 0)). }
  assert (I : inrange (rnd (b2r (neg gl) * b2r half + 0))).
  { rewrite V. unfold IeeeBridge.inrange. rewrite Rabs_Ropp.
    generalize (Omega_lt_top prec emax). lra. }
  destruct (prod_fin prec emax nan_fma (neg gl) half Fn Fhalf I) as [F E].
  rewrite V in E. split; assumption. }
destruct Hn as [Fhn Ehn].
(* the difference of the halves, rounded up *)
set (d := add_up_1 hu hn).
assert (Mono : b2r hl <= b2r hu).
{ rewrite Ehl, Ehu. apply round_le; auto with typeclass_instances. lra. }
assert (Rg : 0 <= b2r hu - b2r hl <= Om).
{ apply Rabs_le_inv in Bhl. apply Rabs_le_inv in Bhu. lra. }
assert (Hd : fin d /\ b2r d = RU emin prec (b2r hu - b2r hl)).
{ assert (E := add_up_1_ieee prec emax nan_plus nan_minus nan_abs Hp hu hn).
  rewrite (xval_fin prec emax hu Fhu), (xval_fin prec emax hn Fhn), Ehn in E. cbn [xadd] in E.
  rewrite (xru_in prec emax) in E by (unfold Rminus in Rg; lra).
  assert (F : fin (add_up_1 hu hn)) by exact (xval_fin_inv prec emax _ _ E).
  rewrite (xval_fin prec emax _ F) in E. injection E as E.
  split; [exact F|exact E]. }
destruct Hd as [Fd Ed].
assert (RUge : b2r hu - b2r hl <= b2r d).
{ rewrite Ed. unfold RU. destruct (round_UP_pt radix2 fexp (b2r hu - b2r hl)) as [_ [L _]].
  exact L. }
assert (D0 : 0 <= b2r d) by lra.
(* the tests of an exact halving *)
rewrite (eq_finite prec emax _ gl Fbl Fgl), (eq_finite prec emax _ gu Fbu Fgu).
rewrite Ebl, Ebu, Egl, Egu.
assert (ExactL : format (b2r lo / 2) -> b2r hl * 2 = b2r lo).
{ intros FL. unfold Rdiv in FL.
  rewrite Ehl, Rplus_0_r, (round_generic radix2 fexp (Znearest tie_even) _ FL). field. }
assert (ExactU : format (b2r hi / 2) -> b2r hu * 2 = b2r hi).
{ intros FH. unfold Rdiv in FH.
  rewrite Ehu, Rplus_0_r, (round_generic radix2 fexp (Znearest tie_even) _ FH). field. }
(* the step, when a halving was not exact *)
assert (Succ : b2r hl * 2 <> b2r lo \/ b2r hu * 2 <> b2r hi ->
               fin (fsucc d) /\ b2r d + eta emin <= b2r (fsucc d)).
{ intros Inexact.
  assert (FS : format (bpow radix2 (emin + prec - 1)))
    by (apply (IeeeBallFinite.format_bpow prec emax); lia).
  assert (HB : bpow radix2 (emin + prec) = 2 * bpow radix2 (emin + prec - 1)).
  { rewrite <- two_bpow. f_equal. lia. }
  assert (Tiny : forall (x : float) (h : R), h = rnd (b2r x * / 2 + 0) ->
                 h * 2 <> b2r x -> Rabs h <= bpow radix2 (emin + prec - 1)).
  { intros x h Eh Hx. rewrite Eh in Hx |- *.
    assert (Sm := half_inexact_small (b2r x) (b2r_format prec emax x) Hx).
    apply (Format.round_abs_le emin prec tie_even); [exact FS|].
    rewrite Rplus_0_r, Rabs_mult, (Rabs_pos_eq (/ 2)) by lra. lra. }
  assert (T1 : bpow radix2 (emin + prec - 1) <= bpow radix2 (emax - prec - 1))
    by (apply bpow_le; lia).
  assert (T2 : bpow radix2 emax = 2 * bpow radix2 (emax - 1)).
  { rewrite <- two_bpow. f_equal. lia. }
  assert (T3 : bpow radix2 (emax - prec) = 2 * bpow radix2 (emax - prec - 1)).
  { rewrite <- two_bpow. f_equal. lia. }
  assert (T4 : bpow radix2 (emax - prec) < bpow radix2 (emax - 1)) by (apply bpow_lt; lia).
  assert (OmE : Om = bpow radix2 emax - bpow radix2 (emax - prec)) by reflexivity.
  assert (Small : b2r hu - b2r hl <= bpow radix2 (emax - 1)).
  { apply Rabs_le_inv in Bhl. apply Rabs_le_inv in Bhu.
    destruct Inexact as [I|I].
    - assert (K := Tiny lo (b2r hl) Ehl I). apply Rabs_le_inv in K. lra.
    - assert (K := Tiny hi (b2r hu) Ehu I). apply Rabs_le_inv in K. lra. }
  assert (Dle : b2r d <= bpow radix2 (emax - 1)).
  { rewrite Ed. apply (RU_le prec emax); [|exact Small].
    apply (IeeeBallFinite.format_bpow prec emax). lia. }
  destruct (succ_finite prec emax d Fd) as [[Fs [Esd _]]|[_ Top]].
  - split; [exact Fs|]. rewrite Esd. apply succ_ge_plus_eta. exact D0.
  - exfalso.
    assert (succ radix2 fexp (b2r d) <= Om).
    { apply succ_le_lt; auto with typeclass_instances.
      - apply b2r_format.
      - apply (format_Omega prec emax).
      - lra. }
    generalize (Omega_lt_top prec emax). lra. }
(* a halving that was not exact *)
assert (Inex : b2r hl * 2 <> b2r lo \/ b2r hu * 2 <> b2r hi ->
  ball_finite_2 c0 c1 (fsucc d) /\
  (forall x : R, b2r lo <= x <= b2r hi -> Rabs (x - (b2r c0 + b2r c1)) <= b2r (fsucc d)) /\
  (format (b2r lo / 2) -> format (b2r hi / 2) ->
   b2r c0 + b2r c1 = (b2r lo + b2r hi) / 2 /\
   b2r (fsucc d) = RU emin prec ((b2r hi - b2r lo) / 2))).
{ intros I. destruct (Succ I) as [Fs Ge]. split; [|split].
  - split; [exact Fc0|split; [exact Fc1|split; [exact Nc|split; [exact Fs|unfold val; lra]]]].
  - intros x Hx. rewrite Es. apply Rabs_le_inv in Dhl. apply Rabs_le_inv in Dhu.
    apply Rabs_le. lra.
  - intros FL FH. exfalso. destruct I as [I|I]; apply I; [exact (ExactL FL)|exact (ExactU FH)]. }
destruct (Req_bool_spec (b2r hl * 2) (b2r lo)) as [XL|XL];
  destruct (Req_bool_spec (b2r hu * 2) (b2r hi)) as [XU|XU]; cbn [andb]; cbv beta iota.
- (* both halvings exact: the midpoint and the smallest radius *)
  split; [|split].
  + split; [exact Fc0|split; [exact Fc1|split; [exact Nc|split; [exact Fd|exact D0]]]].
  + intros x Hx. rewrite Es. apply Rabs_le. lra.
  + intros _ _. split; [rewrite Es; lra|]. rewrite Ed. f_equal. lra.
- exact (Inex (or_intror XU)).
- exact (Inex (or_introl XL)).
- exact (Inex (or_introl XL)).
Qed.

(* ball_from_interval_2, for any two values lo and hi of T, from precision 2: the result
   is a canonical ball; a finite ball that contains [lo, hi] when lo <= hi are finite, with
   the midpoint for its center and the half-width rounded up for its radius when both
   halvings are exact; the whole line when lo <= hi and a bound is infinite, and when a
   bound is a NaN; the empty ball otherwise. *)
Theorem ball_from_interval_2_ieee :
  (2 <= prec)%Z -> forall lo hi : float,
  let '(cw0, cw1, rw) := ball_from_interval_2 lo hi in
  ball_2 cw0 cw1 rw /\
  (xnonempty (xval lo) (xval hi) -> finite lo -> finite hi ->
   ball_finite_2 cw0 cw1 rw /\
   (forall x : R, val lo <= x <= val hi -> in_ball_2 cw0 cw1 rw x)) /\
  (xnonempty (xval lo) (xval hi) -> finite lo -> finite hi ->
   fmt emin prec (val lo / 2) -> fmt emin prec (val hi / 2) ->
   (val cw0 + val cw1) = (val lo + val hi) / 2 /\
   val rw = RU emin prec ((val hi - val lo) / 2)) /\
  (xnonempty (xval lo) (xval hi) -> ~ (finite lo /\ finite hi) -> ball_whole_2 cw0 cw1 rw) /\
  (nan lo \/ nan hi -> ball_whole_2 cw0 cw1 rw) /\
  (~ nan lo -> ~ nan hi -> ~ xnonempty (xval lo) (xval hi) -> ball_empty_2 cw0 cw1 rw).
Proof.
intros Hp lo hi. rewrite ball_from_interval_2_eq. cbv zeta.
rewrite (le_xval prec emax), !(lt_xval prec emax), !(eq_self prec emax).
rewrite !(guard_nan prec emax nan_plus), !(xval_guard prec emax nan_plus).
rewrite (neg_pinf prec emax nan_opp).
change (xv pinf) with (XInf false). change (xv ninf) with (XInf true).
assert (Wh : ball_whole_2 pzero pzero pinf).
{ split; [exists false; reflexivity|split; [exists false; reflexivity|reflexivity]]. }
destruct (andb (andb (xle (xv lo) (xv hi)) (xlt (xv lo) (XInf false)))
               (xlt (XInf true) (xv hi))) eqn:V.
- (* the pair describes an interval *)
  apply andb_true_iff in V. destruct V as [V V3]. apply andb_true_iff in V.
  destruct V as [V1 V2].
  assert (N : xnonempty (xv lo) (xv hi)) by (split; [exact V1|split; [exact V2|exact V3]]).
  destruct (xnonempty_not_nan prec emax lo hi N) as [N1 N2].
  destruct (andb (xlt (XInf true) (xv lo)) (xlt (xv hi) (XInf false))) eqn:Ff; cbv beta iota.
  + (* a bounded one *)
    apply andb_true_iff in Ff. destruct Ff as [W1 W2].
    assert (Flo : fin lo).
    { destruct (xval_cases prec emax lo) as [[F _]|[[s E]|E]]; [exact F| |]; rewrite E in V2, W1.
      - destruct s; [discriminate W1|discriminate V2].
      - discriminate V2. }
    assert (Fhi : fin hi).
    { destruct (xval_cases prec emax hi) as [[F _]|[[s E]|E]]; [exact F| |]; rewrite E in V3, W2.
      - destruct s; [discriminate V3|discriminate W2].
      - discriminate V3. }
    assert (Hle : b2r lo <= b2r hi).
    { rewrite (xval_fin prec emax lo Flo), (xval_fin prec emax hi Fhi) in V1.
      cbn [xle] in V1. exact (Rle_bool_inv _ _ V1). }
    destruct (ball_from_interval_2_finite Hp lo hi Flo Fhi Hle) as [BF [Cont Mid]].
    split; [left; exact BF|].
    split.
    { intros _ _ _. split; [exact BF|]. intros x Hx. right. split; [exact BF|exact (Cont x Hx)]. }
    split; [intros _ _ _ FL FH; exact (Mid FL FH)|].
    split; [intros _ K; elim K; split; assumption|].
    split; [intros [K|K]; unfold nan in K; congruence|].
    intros _ _ K. elim (K N).
  + (* a bound is infinite: the whole line *)
    assert (NotBoth : ~ (fin lo /\ fin hi)).
    { intros [Flo Fhi].
      rewrite (xval_fin prec emax lo Flo), (xval_fin prec emax hi Fhi) in Ff. discriminate Ff. }
    split; [right; left; exact Wh|].
    split; [intros _ Flo Fhi; elim NotBoth; split; assumption|].
    split; [intros _ Flo Fhi; elim NotBoth; split; assumption|].
    split; [intros _ _; exact Wh|].
    split; [intros _; exact Wh|].
    intros _ _ K. elim (K N).
- (* it describes none *)
  assert (NN : ~ xnonempty (xv lo) (xv hi)).
  { intros [N1 [N2 N3]]. rewrite N1, N2, N3 in V. discriminate V. }
  destruct (is_nan prec emax lo) eqn:N1; [|destruct (is_nan prec emax hi) eqn:N2];
    cbn [andb negb]; cbv beta iota.
  + split; [right; left; exact Wh|].
    split; [intros K; elim (NN K)|].
    split; [intros K; elim (NN K)|].
    split; [intros K; elim (NN K)|].
    split; [intros _; exact Wh|].
    intros K. elim K. exact N1.
  + split; [right; left; exact Wh|].
    split; [intros K; elim (NN K)|].
    split; [intros K; elim (NN K)|].
    split; [intros K; elim (NN K)|].
    split; [intros _; exact Wh|].
    intros _ K. elim K. exact N2.
  + assert (Em : ball_empty_2 cnan cnan cnan).
    { split; [|split]; exact (proj2_sig nan_const). }
    split; [right; right; exact Em|].
    split; [intros K; elim (NN K)|].
    split; [intros K; elim (NN K)|].
    split; [intros K; elim (NN K)|].
    split; [intros [K|K]; unfold nan in K; congruence|].
    intros _ _ _. exact Em.
Qed.

End IeeeBallConvert.

(** * The generated statements *)

Theorem ball_lower_as_1_correct : ball_lower_as_1_spec.
Proof.
intros prec emax Hp0 He nan_plus nan_minus nan_opp nan_abs Hp c r B.
exact (ball_lower_as_1_ieee prec emax nan_plus nan_minus nan_opp nan_abs Hp c r B).
Qed.

Theorem ball_upper_as_1_correct : ball_upper_as_1_spec.
Proof.
intros prec emax Hp0 He nan_plus nan_minus nan_opp nan_abs Hp c r B.
exact (ball_upper_as_1_ieee prec emax nan_plus nan_minus nan_opp nan_abs Hp c r B).
Qed.

Theorem ball_lower_as_2_correct : ball_lower_as_2_spec.
Proof.
intros prec emax Hp0 He nan_plus nan_minus nan_opp nan_abs Hp c0 c1 r B.
exact (ball_lower_as_2_ieee prec emax nan_plus nan_minus nan_opp nan_abs Hp c0 c1 r B).
Qed.

Theorem ball_upper_as_2_correct : ball_upper_as_2_spec.
Proof.
intros prec emax Hp0 He nan_plus nan_minus nan_opp nan_abs Hp c0 c1 r B.
exact (ball_upper_as_2_ieee prec emax nan_plus nan_minus nan_opp nan_abs Hp c0 c1 r B).
Qed.

Theorem ball_narrow_2_1_correct : ball_narrow_2_1_spec.
Proof.
intros prec emax Hp0 He nan_plus nan_abs Hp c0 c1 r B.
exact (ball_narrow_2_1_ieee prec emax nan_plus nan_abs Hp c0 c1 r B).
Qed.

Theorem ball_from_interval_2_correct : ball_from_interval_2_spec.
Proof.
intros prec emax Hp0 He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const Hp lo hi.
exact (ball_from_interval_2_ieee prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const
         Hp lo hi).
Qed.
