(* The conversions between an interval of one limb and a ball of one limb, the midpoint and the
   radius of an interval, and its split at the midpoint, in the IEEE model, on all values:
   ball_to_interval_1, interval_mid_rad_1, interval_to_ball_1 and interval_split_1
   (docs/developer/design/milestone2.md, "One enclosure interface": "Midpoint, radius and the
   conversions", the row of split() and "The empty set and the whole line").

   Notation as in IeeeInterval1.v and IeeeBallConvert.v: T is the IEEE format, Omega its
   largest number, eta its smallest positive one, u = 2^-prec; xval a is the extended real
   number a limb stands for, xrd and xru the roundings down and up in the format with
   overflow; an interval, a ball, their states and members, and the bounds of a set are those
   of IeeeVocabulary.v and IeeeIntervalVocabulary.v. [xl, xu] is the interval, mid its exact
   midpoint (xl + xu) / 2, and (m, r) the midpoint and the radius computed. The four kernels
   are the generated models of proofs/gen/IeeeModel.v, and the theorems K_correct at the end
   establish their generated statements (proofs/gen/IeeeStatements.v). From precision 2.

   What is proved.

   - ball_to_interval_1, for a canonical ball (ball_to_interval_1_correct): the result is a
     canonical interval, empty exactly when the ball is, containing every member of the ball,
     and for a ball that is not empty its bounds are the bounds of the set of the members
     rounded down and up in the format with overflow (RD(c - r) and RU(c + r) for a finite
     ball, -infinity and +infinity for the whole line). The two outputs are ball_lower_as_1
     and ball_upper_as_1 (IeeeBallConvert.v).

   - interval_mid_rad_1, for a canonical interval (interval_mid_rad_1_correct): the empty set
     gives two NaN; the whole line the midpoint 0 and the radius +infinity; a half-line the
     midpoint +-Omega on its side and the radius +infinity; and a bounded interval a finite m
     in [xl, xu] with |m - mid| <= u |mid| + eta, and the finite radius
     r = RU(max(m - xl, xu - m)), so that every member of [xl, xu] is within r of m and r is
     the smallest number of T with that property for the center m.

   - interval_to_ball_1 (interval_to_ball_1_correct): the ball of the midpoint and the radius,
     with the whole line for an unbounded interval: a canonical ball, empty exactly when the
     interval is, the whole line for an unbounded nonempty interval, and for a bounded one the
     finite ball of the midpoint above.

   - interval_split_1 (interval_split_1_correct): [xl, m] and [m, xu], both canonical, both
     empty for the empty set, both nonempty for a nonempty interval, with the bounds xl, m, m,
     xu.

   The proofs. The midpoint of a bounded interval is the sum of the halves rounded, moved
   into [xl, xu] by two selects (clamp_facts); moving it into an interval that contains mid
   does not move it away from mid. The rounded sum of the halves is within u |mid| + eta of
   mid (mid_error): each halving is exact, or is of a number below 2^(emin + prec) in
   magnitude and within eta / 2 (half_error, half_inexact_small of IeeeBallConvert.v); a sum
   of the halves at most 2^(prec + emin) in magnitude is a number of the format
   (FLT_format_plus_small of Flocq), and a larger one is rounded within u of itself, with at
   most one halving not exact. The radius is finite: m - xl and xu - m are at most Omega,
   because the sum of the halves rounded is at least xu - Omega and at most xl + Omega
   (mid_above, mid_below: below Omega / 2 in magnitude by a bound on the halves, and above,
   where xu - Omega and xl + Omega are numbers of the format (Sterbenz) and the halving is
   exact, by monotonicity). The larger of RU(m - xl) and RU(xu - m) is RU of the larger
   (RU_max). *)
From Stdlib Require Import Reals ZArith Bool Lia Lra Psatz.
From Flocq Require Import Core Binary Relative Sterbenz Plus_error.
From Kairn.Gen Require Import Model Statements IeeeStatements.
From Kairn Require Import Format Normalized IeeeBridge IeeeVocabulary IeeeEFT IeeeOps IeeeExt.
From Kairn Require Import IeeeBall IeeeBallFinite IeeeDirected IeeeEntry.
From Kairn Require Import IeeeIntervalVocabulary IeeeInterval1 IeeeBallConvert.
From Kairn Require Ball2 IeeeOperations.
From Kairn.Gen Require IeeeModel.
Open Scope R_scope.

Section IeeeIntervalConvert.
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
Notation add := (IeeeOperations.add prec emax nan_plus).
Notation prod := (IeeeOperations.prod prec emax nan_fma).
Notation flt := (IeeeOperations.lt prec emax).
Notation feq := (IeeeOperations.eq prec emax).
Notation fpred := (IeeeOperations.pred prec emax).
Notation pzero := (IeeeOperations.pzero prec emax).
Notation pinf := (IeeeOperations.pinf prec emax).
Notation cnan := (IeeeOperations.cnan prec emax nan_const).
Notation ninf := (B754_infinity prec emax true).
Notation xv := (@xval prec emax).
Notation Om := (Omega prec emax).
Notation half := (IeeeModel.up_ball_from_interval_2_0 prec emax).
Notation sub_up_1 := (IeeeModel.sub_up_1 prec emax nan_plus nan_minus nan_opp nan_abs).
Notation interval_mid_rad_1 :=
  (IeeeModel.interval_mid_rad_1 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const).
Notation interval_to_ball_1 :=
  (IeeeModel.interval_to_ball_1 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const).
Notation interval_split_1 :=
  (IeeeModel.interval_split_1 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const).
Notation ball_to_interval_1 :=
  (IeeeModel.ball_to_interval_1 prec emax nan_plus nan_minus nan_opp nan_abs).
Notation ball_lower_as_1 :=
  (IeeeModel.ball_lower_as_1 prec emax nan_plus nan_minus nan_opp nan_abs).
Notation ball_upper_as_1 :=
  (IeeeModel.ball_upper_as_1 prec emax nan_plus nan_minus nan_opp nan_abs).

Let Hprec : (0 < prec)%Z.
Proof. exact prec_gt_0_. Qed.
Let Hemax : (prec < emax)%Z.
Proof. exact prec_lt_emax_. Qed.

(** * The cases of a canonical interval of one limb *)

Lemma interval_1_cases :
  forall xl xu : float, interval_1 xl xu ->
  interval_empty_1 xl xu \/
  (xv xl = XInf true /\ xv xu = XInf false) \/
  (fin xl /\ xv xu = XInf false) \/
  (xv xl = XInf true /\ fin xu) \/
  (fin xl /\ fin xu /\ b2r xl <= b2r xu).
Proof.
intros xl xu [E|[H1 [H2 H3]]]; [now left|right].
destruct (xval_cases prec emax xl) as [[Fl El]|[[s El]|El]];
  destruct (xval_cases prec emax xu) as [[Fu Eu]|[[t Eu]|Eu]];
  rewrite El in H1, H2; rewrite Eu in H1, H3; cbn in H1, H2, H3; try discriminate H1.
- right; right; right. split; [exact Fl|split; [exact Fu|now apply Rle_bool_inv]].
- destruct t; cbn in H3; [discriminate H3|]. right; left. split; [exact Fl|exact Eu].
- destruct s; cbn in H2; [|discriminate H2]. right; right; left. split; [exact El|exact Fu].
- destruct s; cbn in H2; [|discriminate H2]. destruct t; cbn in H3; [discriminate H3|].
  left. split; [exact El|exact Eu].
Qed.

Lemma xnonempty_fin : forall a b : R, a <= b -> xnonempty (XFin a) (XFin b).
Proof. intros a b H. split; [cbn; now apply Rle_bool_true|split; reflexivity]. Qed.

(** * ball_to_interval_1 *)

(* The bounds of the set of the members of a ball that is not empty, and a member. *)
Lemma ball_1_bounds :
  forall c r : float, ball_1 c r -> ~ ball_empty_1 c r ->
  exists lo hi : xreal, range_lower (in_ball_1 c r) lo /\ range_upper (in_ball_1 c r) hi /\
  exists m : R, in_ball_1 c r m.
Proof.
intros c r B NE. destruct B as [F|[Wh|E]]; [| |elim (NE E)].
- assert (F' := F). destruct F' as [Fc [Fr Pr]].
  exists (XFin (b2r c - b2r r)), (XFin (b2r c + b2r r)).
  split; [exact (range_segment_lower _ _ _ Pr (ball_1_members prec emax c r F))|].
  split; [exact (range_segment_upper _ _ _ Pr (ball_1_members prec emax c r F))|].
  exists (b2r c). apply (ball_1_members prec emax c r F).
  unfold Rminus. rewrite Rplus_opp_r, Rabs_R0. exact Pr.
- assert (All : forall x : R, in_ball_1 c r x) by (intros x; left; exact Wh).
  exists (XInf true), (XInf false).
  split; [exact (range_line_lower _ All)|split; [exact (range_line_upper _ All)|]].
  exists 0. apply All.
Qed.

(* ball_to_interval_1, for a canonical ball, from precision 2: its outputs are those of
   ball_lower_as_1 and ball_upper_as_1. *)
Theorem ball_to_interval_1_all :
  (2 <= prec)%Z -> forall c r : float, ball_1 c r ->
  let '(zl, zu) := ball_to_interval_1 c r in
  interval_1 zl zu /\
  (interval_empty_1 zl zu <-> ball_empty_1 c r) /\
  (forall x : R, in_ball_1 c r x -> in_interval_1 zl zu x) /\
  (~ (ball_empty_1 c r) ->
   forall lo hi : xreal,
   range_lower (in_ball_1 c r) lo ->
   range_upper (in_ball_1 c r) hi ->
   xval zl = xrd prec emax lo /\ xval zu = xru prec emax hi).
Proof.
intros Hp c r B.
assert (Eq : ball_to_interval_1 c r = (ball_lower_as_1 c r, ball_upper_as_1 c r)) by reflexivity.
rewrite Eq.
destruct (ball_lower_as_1_ieee prec emax nan_plus nan_minus nan_opp nan_abs Hp c r B) as [LE LN].
destruct (ball_upper_as_1_ieee prec emax nan_plus nan_minus nan_opp nan_abs Hp c r B) as [UE UN].
assert (I4 : ~ ball_empty_1 c r -> forall lo hi : xreal,
             range_lower (in_ball_1 c r) lo -> range_upper (in_ball_1 c r) hi ->
             xv (ball_lower_as_1 c r) = xrd prec emax lo /\
             xv (ball_upper_as_1 c r) = xru prec emax hi).
{ intros NE lo hi Hlo Hhi. split; [exact (LN NE lo Hlo)|exact (UN NE hi Hhi)]. }
destruct (is_nan prec emax r) eqn:Nr.
- assert (E := proj1 (ball_1_empty prec emax c r B) Nr).
  rewrite (LE E), (UE E).
  split; [left; split; reflexivity|].
  split; [split; intros _; [exact E|split; reflexivity]|].
  split; [intros x Hx; elim (in_ball_1_not_empty prec emax c r x Hx E)|].
  intros NE. elim (NE E).
- assert (NE : ~ ball_empty_1 c r) by (intros [_ K]; unfold nan in K; congruence).
  destruct (ball_1_bounds c r B NE) as [lo [hi [Hlo [Hhi [m Hm]]]]].
  destruct (I4 NE lo hi Hlo Hhi) as [El Eu].
  assert (I3 : forall x : R, in_ball_1 c r x ->
               in_interval_1 (ball_lower_as_1 c r) (ball_upper_as_1 c r) x).
  { intros x Hx. split.
    - rewrite El. apply (xrd_below prec emax). exact (proj1 Hlo x Hx).
    - rewrite Eu. apply (xru_above prec emax). exact (proj1 Hhi x Hx). }
  split; [right; exact (member_interval prec emax _ _ m (I3 m Hm))|].
  split; [split; [intros K; elim (empty_no_member prec emax _ _ m K (I3 m Hm))|intros K; elim (NE K)]|].
  split; [exact I3|exact I4].
Qed.

(** * The midpoint of a bounded interval, over the real numbers *)

(* Above Omega / 2 in magnitude, every halving is exact. *)
Lemma half_exact_large :
  (2 <= prec)%Z -> forall x : R, format x -> Om / 2 <= Rabs x -> rnd (x * / 2 + 0) = x / 2.
Proof.
intros Hp x Fx H.
destruct (Req_dec (rnd (x * / 2 + 0) * 2) x) as [E|E]; [lra|].
exfalso. assert (S := half_inexact_small prec emax x Fx E).
assert (A : bpow radix2 (emin + prec) <= bpow radix2 (emax - 3)) by (apply bpow_le; lia).
assert (B : bpow radix2 (emax - prec) <= bpow radix2 (emax - 2)) by (apply bpow_le; lia).
assert (C : bpow radix2 emax = 8 * bpow radix2 (emax - 3)) by apply top_8.
assert (D : bpow radix2 (emax - 2) = 2 * bpow radix2 (emax - 3)).
{ rewrite <- two_bpow. f_equal. lia. }
assert (P : 0 < bpow radix2 (emax - 3)) by apply bpow_gt_0.
assert (OmE : Om = bpow radix2 emax - bpow radix2 (emax - prec)) by reflexivity.
lra.
Qed.

(* The sum of the halves, rounded, is within u |mid| + eta of mid. *)
Lemma mid_error :
  (2 <= prec)%Z -> forall a b : R, format a -> format b ->
  Rabs (rnd (rnd (a * / 2 + 0) + rnd (b * / 2 + 0)) - (a + b) / 2)
  <= u prec * Rabs ((a + b) / 2) + eta emin.
Proof.
intros Hp a b Fa Fb.
assert (Ea := half_error prec emax a Fa). assert (Eb := half_error prec emax b Fb).
set (hl := rnd (a * / 2 + 0)) in *. set (hu := rnd (b * / 2 + 0)) in *.
assert (Fhl : format hl) by (apply generic_format_round; auto with typeclass_instances).
assert (Fhu : format hu) by (apply generic_format_round; auto with typeclass_instances).
assert (E0 : 0 < eta emin) by apply bpow_gt_0.
assert (Ut : 0 < u prec <= / 4) by exact (Ball2.u_bounds prec 2 Hp). destruct Ut as [U0 U1].
assert (M0 := Rabs_pos ((a + b) / 2)).
assert (UM : 0 <= u prec * Rabs ((a + b) / 2)) by (apply Rmult_le_pos; lra).
apply Rabs_le_inv in Ea. apply Rabs_le_inv in Eb.
destruct (Rle_or_lt (Rabs (hl + hu)) (bpow radix2 (prec + emin))) as [Small|Large].
- (* the sum of the halves is a number of the format *)
  assert (Fs : format (hl + hu)) by (apply FLT_format_plus_small; assumption).
  rewrite (round_generic radix2 fexp (Znearest tie_even) _ Fs).
  apply Rabs_le. lra.
- (* at most one halving is not exact, and the sum is rounded within u of itself *)
  replace (prec + emin)%Z with (emin + prec)%Z in Large by ring.
  assert (FS : format (bpow radix2 (emin + prec - 1)))
    by (apply (IeeeBallFinite.format_bpow prec emax); lia).
  assert (HB : bpow radix2 (emin + prec) = 2 * bpow radix2 (emin + prec - 1)).
  { rewrite <- two_bpow. f_equal. lia. }
  assert (P1 : 0 < bpow radix2 (emin + prec - 1)) by apply bpow_gt_0.
  assert (Tiny : forall x : R, format x -> rnd (x * / 2 + 0) * 2 <> x ->
                 Rabs (rnd (x * / 2 + 0)) <= bpow radix2 (emin + prec - 1)).
  { intros x Fx Hx. assert (Sm := half_inexact_small prec emax x Fx Hx).
    apply (Format.round_abs_le emin prec tie_even); [exact FS|].
    rewrite Rplus_0_r, Rabs_mult, (Rabs_pos_eq (/ 2)) by lra. lra. }
  assert (One : hl = a / 2 \/ hu = b / 2).
  { destruct (Req_dec (hl * 2) a) as [X|X]; [left; lra|].
    destruct (Req_dec (hu * 2) b) as [Y|Y]; [right; lra|].
    exfalso. assert (K1 := Tiny a Fa X). assert (K2 := Tiny b Fb Y).
    fold hl in K1. fold hu in K2.
    generalize (Rabs_triang hl hu). lra. }
  assert (D : Rabs (hl + hu - (a + b) / 2) <= / 2 * eta emin).
  { apply Rabs_le. destruct One as [X|X]; lra. }
  assert (Rel : Rabs (rnd (hl + hu) - (hl + hu)) <= u prec * Rabs (hl + hu)).
  { assert (Hx : bpow radix2 (emin + prec - 1) <= Rabs (hl + hu)) by lra.
    generalize (relative_error_N_FLT radix2 emin prec prec_gt_0_ tie_even (hl + hu) Hx).
    replace (/ 2 * bpow radix2 (- prec + 1)) with (u prec); [trivial|].
    unfold u. replace (- prec + 1)%Z with (1 + - prec)%Z by ring. rewrite bpow_plus.
    change (bpow radix2 1) with 2. field. }
  assert (S1 : Rabs (hl + hu) <= Rabs ((a + b) / 2) + / 2 * eta emin).
  { generalize (Rabs_triang (hl + hu - (a + b) / 2) ((a + b) / 2)).
    replace (hl + hu - (a + b) / 2 + (a + b) / 2) with (hl + hu) by ring. lra. }
  assert (S2 : u prec * Rabs (hl + hu)
               <= u prec * Rabs ((a + b) / 2) + u prec * (/ 2 * eta emin)).
  { rewrite <- Rmult_plus_distr_l. apply Rmult_le_compat_l; lra. }
  assert (S3 : u prec * (/ 2 * eta emin) <= / 2 * eta emin).
  { assert (Q : 0 <= / 2 * eta emin) by (clear - E0; lra).
    assert (K : u prec * (/ 2 * eta emin) <= 1 * (/ 2 * eta emin))
      by (apply Rmult_le_compat_r; [exact Q|clear - U1; lra]).
    clear - K. lra. }
  generalize (Rabs_triang (rnd (hl + hu) - (hl + hu)) (hl + hu - (a + b) / 2)).
  replace (rnd (hl + hu) - (hl + hu) + (hl + hu - (a + b) / 2))
    with (rnd (hl + hu) - (a + b) / 2) by ring.
  lra.
Qed.

Lemma rnd_mono : forall x y : R, x <= y -> rnd x <= rnd y.
Proof. intros x y H. apply round_le; auto with typeclass_instances. Qed.

Lemma rnd_fix : forall x : R, format x -> rnd x = x.
Proof. intros x H. apply round_generic; auto with typeclass_instances. Qed.

(* The sum of the halves, rounded, is at least xu - Omega and at most xl + Omega. *)
Lemma mid_above :
  (2 <= prec)%Z -> forall a b : R, format a -> format b -> - Om <= a -> a <= b -> b <= Om ->
  b - Om <= rnd (rnd (a * / 2 + 0) + rnd (b * / 2 + 0)).
Proof.
intros Hp a b Fa Fb H1 H2 H3.
assert (O0 := Omega_gt_0 prec emax).
assert (FO2 := format_half_Omega prec emax).
assert (FmO2 : format (- (Om / 2))) by now apply generic_format_opp.
assert (FO : format Om) by exact (format_Omega prec emax).
assert (FmO : format (- Om)) by now apply generic_format_opp.
assert (Hl : - (Om / 2) <= rnd (a * / 2 + 0)) by (rewrite <- (rnd_fix _ FmO2); apply rnd_mono; lra).
assert (Hu : - (Om / 2) <= rnd (b * / 2 + 0)) by (rewrite <- (rnd_fix _ FmO2); apply rnd_mono; lra).
destruct (Rle_or_lt b 0) as [B0|B0].
- apply Rle_trans with (- Om); [lra|]. rewrite <- (rnd_fix _ FmO). apply rnd_mono. lra.
- destruct (Rlt_or_le b (Om / 2)) as [B1|B1].
  + assert (Hu0 : 0 <= rnd (b * / 2 + 0)).
    { apply (rnd_pos prec emax). lra. }
    apply Rle_trans with (- (Om / 2)); [lra|]. rewrite <- (rnd_fix _ FmO2). apply rnd_mono. lra.
  + assert (Fd : format (b - Om)) by (apply sterbenz; try typeclasses eauto; [exact Fb|exact FO|split; lra]).
    assert (Eu : rnd (b * / 2 + 0) = b / 2).
    { apply (half_exact_large Hp b Fb). rewrite Rabs_pos_eq; lra. }
    rewrite <- (rnd_fix _ Fd). apply rnd_mono. lra.
Qed.

Lemma mid_below :
  (2 <= prec)%Z -> forall a b : R, format a -> format b -> - Om <= a -> a <= b -> b <= Om ->
  rnd (rnd (a * / 2 + 0) + rnd (b * / 2 + 0)) <= a + Om.
Proof.
intros Hp a b Fa Fb H1 H2 H3.
assert (O0 := Omega_gt_0 prec emax).
assert (FO2 := format_half_Omega prec emax).
assert (FO : format Om) by exact (format_Omega prec emax).
assert (Hl : rnd (a * / 2 + 0) <= Om / 2) by (rewrite <- (rnd_fix _ FO2); apply rnd_mono; lra).
assert (Hu : rnd (b * / 2 + 0) <= Om / 2) by (rewrite <- (rnd_fix _ FO2); apply rnd_mono; lra).
destruct (Rle_or_lt 0 a) as [A0|A0].
- apply Rle_trans with Om; [|lra]. rewrite <- (rnd_fix _ FO). apply rnd_mono. lra.
- destruct (Rlt_or_le (- (Om / 2)) a) as [A1|A1].
  + assert (Hl0 : rnd (a * / 2 + 0) <= 0).
    { assert (K := rnd_mono (a * / 2 + 0) 0 ltac:(lra)).
      rewrite (round_0 radix2 fexp (Znearest tie_even)) in K. exact K. }
    apply Rle_trans with (Om / 2); [|lra]. rewrite <- (rnd_fix _ FO2). apply rnd_mono. lra.
  + assert (Fd : format (Om - - a)).
    { apply sterbenz; try typeclasses eauto; [exact FO|now apply generic_format_opp|split; lra]. }
    replace (Om - - a) with (a + Om) in Fd by ring.
    assert (El : rnd (a * / 2 + 0) = a / 2).
    { apply (half_exact_large Hp a Fa). rewrite Rabs_left1; lra. }
    rewrite <- (rnd_fix _ Fd). apply rnd_mono. lra.
Qed.

(* The larger of two roundings up is the rounding up of the larger. *)
Lemma RU_max :
  forall x y : R,
  (if Rlt_bool (RU emin prec x) (RU emin prec y) then RU emin prec y else RU emin prec x)
  = RU emin prec (Rmax x y).
Proof.
intros x y. unfold Rmax.
assert (M : forall s t : R, s <= t -> RU emin prec s <= RU emin prec t)
  by (intros s t H; unfold RU; apply round_le; auto with typeclass_instances).
destruct (Rlt_bool_spec (RU emin prec x) (RU emin prec y)) as [A|A];
  destruct (Rle_dec x y) as [B|B]; trivial.
- exfalso. assert (K := M y x ltac:(lra)). lra.
- apply Rle_antisym; [exact (M x y B)|exact A].
Qed.

(** * The midpoint and the radius of a bounded interval, on limbs *)

(* The two selects that move the sum of the halves into [l, h]. *)
Definition clamp (l h a : float) : float :=
  let mb := if flt a l then l else a in if flt h mb then h else mb.

Definition mid_core (l h : float) : float := clamp l h (add (prod l half) (prod h half)).

Definition rad_core (l h : float) : float :=
  let mc := mid_core l h in
  let ra := sub_up_1 mc l in
  let rb := sub_up_1 h mc in
  if flt ra rb then rb else ra.

Lemma clamp_facts :
  forall l h a : float, fin l -> fin h -> fin a -> b2r l <= b2r h ->
  fin (clamp l h a) /\ b2r l <= b2r (clamp l h a) <= b2r h /\
  (forall t : R, b2r l <= t <= b2r h -> Rabs (b2r (clamp l h a) - t) <= Rabs (b2r a - t)) /\
  b2r h - b2r (clamp l h a) <= Rmax 0 (b2r h - b2r a) /\
  b2r (clamp l h a) - b2r l <= Rmax 0 (b2r a - b2r l).
Proof.
intros l h a Fl Fh Fa Hlh. unfold clamp. cbv zeta.
rewrite (lt_finite prec emax a l Fa Fl).
destruct (Rlt_bool_spec (b2r a) (b2r l)) as [A|A].
- rewrite (lt_finite prec emax h l Fh Fl), (Rlt_bool_false (b2r h) (b2r l)) by lra.
  split; [exact Fl|split; [lra|split]].
  + intros t Ht. rewrite (Rabs_left1 (b2r l - t)) by lra.
    rewrite (Rabs_left1 (b2r a - t)) by lra. lra.
  + split; [apply Rle_trans with (2 := Rmax_r _ _); lra|apply Rle_trans with (2 := Rmax_l _ _); lra].
- rewrite (lt_finite prec emax h a Fh Fa).
  destruct (Rlt_bool_spec (b2r h) (b2r a)) as [B|B].
  + split; [exact Fh|split; [lra|split]].
    * intros t Ht. rewrite (Rabs_pos_eq (b2r h - t)) by lra.
      rewrite (Rabs_pos_eq (b2r a - t)) by lra. lra.
    * split; [apply Rle_trans with (2 := Rmax_l _ _); lra|apply Rle_trans with (2 := Rmax_r _ _); lra].
  + split; [exact Fa|split; [lra|split]].
    * intros t _. apply Rle_refl.
    * split; apply Rmax_r.
Qed.

(* Half of a finite number: finite, the rounded half, at most Omega / 2 in magnitude. *)
Lemma prod_half :
  (2 <= prec)%Z -> forall x : float, fin x ->
  fin (prod x half) /\ b2r (prod x half) = rnd (b2r x * / 2 + 0) /\
  Rabs (b2r (prod x half)) <= Om / 2.
Proof.
intros Hp x Fx. destruct (half_spec prec emax Hp) as [Fh Eh].
assert (Bx := b2r_le_Omega prec emax x).
assert (LT := Omega_lt_top prec emax). assert (O0 := Omega_gt_0 prec emax).
assert (R1 : Rabs (rnd (b2r x * / 2 + 0)) <= Om / 2).
{ apply (Format.round_abs_le emin prec tie_even); [exact (format_half_Omega prec emax)|].
  rewrite Rplus_0_r, Rabs_mult, (Rabs_pos_eq (/ 2)) by lra. lra. }
assert (I1 : IeeeBridge.inrange emax (rnd (b2r x * b2r half + 0))).
{ rewrite Eh. unfold IeeeBridge.inrange. lra. }
destruct (prod_fin prec emax nan_fma x half Fx Fh I1) as [F E]. rewrite Eh in E.
split; [exact F|split; [exact E|rewrite E; exact R1]].
Qed.

(* A directed difference of two finite numbers between 0 and Omega apart. *)
Lemma sub_up_value :
  (2 <= prec)%Z -> forall a b : float, fin a -> fin b -> 0 <= b2r a - b2r b <= Om ->
  fin (sub_up_1 a b) /\ b2r (sub_up_1 a b) = RU emin prec (b2r a - b2r b).
Proof.
intros Hp a b Fa Fb H.
assert (E := sub_up_1_ieee prec emax nan_plus nan_minus nan_opp nan_abs Hp a b).
rewrite (xval_fin prec emax a Fa), (xval_fin prec emax b Fb) in E. cbn [xopp xadd] in E.
rewrite (xru_in prec emax) in E by lra.
assert (F : fin (sub_up_1 a b)) by exact (xval_fin_inv prec emax _ _ E).
rewrite (xval_fin prec emax _ F) in E. injection E as E.
split; [exact F|]. rewrite E. reflexivity.
Qed.

(* The midpoint and the radius of a bounded interval [xl, xu]. *)
Lemma mid_rad_bounded :
  (2 <= prec)%Z -> forall xl xu : float, fin xl -> fin xu -> b2r xl <= b2r xu ->
  fin (mid_core xl xu) /\ fin (rad_core xl xu) /\
  b2r xl <= b2r (mid_core xl xu) <= b2r xu /\
  Rabs (b2r (mid_core xl xu) - (b2r xl + b2r xu) / 2)
  <= u prec * Rabs ((b2r xl + b2r xu) / 2) + eta emin /\
  (forall z : R, b2r xl <= z <= b2r xu -> Rabs (z - b2r (mid_core xl xu)) <= b2r (rad_core xl xu)) /\
  b2r (rad_core xl xu)
  = RU emin prec (Rmax (b2r (mid_core xl xu) - b2r xl) (b2r xu - b2r (mid_core xl xu))).
Proof.
intros Hp xl xu Fl Fu Hle.
assert (Bl := b2r_Omega prec emax xl). assert (Bu := b2r_Omega prec emax xu).
assert (Fxl := b2r_format prec emax xl). assert (Fxu := b2r_format prec emax xu).
assert (O0 := Omega_gt_0 prec emax). assert (LT := Omega_lt_top prec emax).
destruct (prod_half Hp xl Fl) as [Fhl [Ehl Bhl]].
destruct (prod_half Hp xu Fu) as [Fhu [Ehu Bhu]].
assert (I : IeeeBridge.inrange emax (rnd (b2r (prod xl half) + b2r (prod xu half)))).
{ unfold IeeeBridge.inrange.
  assert (K : Rabs (rnd (b2r (prod xl half) + b2r (prod xu half))) <= Om).
  { apply (Format.round_abs_le emin prec tie_even); [exact (format_Omega prec emax)|].
    apply Rle_trans with (1 := Rabs_triang _ _). lra. }
  lra. }
destruct (add_fin prec emax nan_plus _ _ Fhl Fhu I) as [Fa Ea].
rewrite Ehl, Ehu in Ea.
assert (Cl := clamp_facts xl xu (add (prod xl half) (prod xu half)) Fl Fu Fa Hle).
change (clamp xl xu (add (prod xl half) (prod xu half))) with (mid_core xl xu) in Cl.
rewrite Ea in Cl.
destruct Cl as [Fm [Bm [Cm [D1 D2]]]].
assert (P1 := mid_above Hp _ _ Fxl Fxu (proj1 Bl) Hle (proj2 Bu)).
assert (P2 := mid_below Hp _ _ Fxl Fxu (proj1 Bl) Hle (proj2 Bu)).
assert (Err := mid_error Hp _ _ Fxl Fxu).
assert (R1 : b2r (mid_core xl xu) - b2r xl <= Om)
  by (apply Rle_trans with (1 := D2); apply Rmax_lub; lra).
assert (R2 : b2r xu - b2r (mid_core xl xu) <= Om)
  by (apply Rle_trans with (1 := D1); apply Rmax_lub; lra).
destruct (sub_up_value Hp (mid_core xl xu) xl Fm Fl ltac:(lra)) as [Fra Era].
destruct (sub_up_value Hp xu (mid_core xl xu) Fu Fm ltac:(lra)) as [Frb Erb].
assert (Rad : fin (rad_core xl xu) /\
              b2r (rad_core xl xu)
              = RU emin prec (Rmax (b2r (mid_core xl xu) - b2r xl) (b2r xu - b2r (mid_core xl xu)))).
{ unfold rad_core. cbv zeta.
  rewrite (lt_finite prec emax _ _ Fra Frb), Era, Erb, <- RU_max.
  destruct (Rlt_bool (RU emin prec (b2r (mid_core xl xu) - b2r xl))
                     (RU emin prec (b2r xu - b2r (mid_core xl xu)))); split; assumption. }
destruct Rad as [Fr Er].
split; [exact Fm|split; [exact Fr|split; [exact Bm|split]]].
- apply Rle_trans with (2 := Err). apply Cm. lra.
- split; [|exact Er].
  intros z Hz. rewrite Er.
  apply Rle_trans with (Rmax (b2r (mid_core xl xu) - b2r xl) (b2r xu - b2r (mid_core xl xu))).
  + generalize (Rmax_l (b2r (mid_core xl xu) - b2r xl) (b2r xu - b2r (mid_core xl xu)))
               (Rmax_r (b2r (mid_core xl xu) - b2r xl) (b2r xu - b2r (mid_core xl xu))).
    intros M1 M2. apply Rabs_le. lra.
  + unfold RU. destruct (round_UP_pt radix2 fexp (Rmax (b2r (mid_core xl xu) - b2r xl)
                                                    (b2r xu - b2r (mid_core xl xu)))) as [_ [L _]].
    exact L.
Qed.

(** * interval_mid_rad_1 *)

Lemma om_facts :
  fin (fpred pinf) /\ b2r (fpred pinf) = Om /\
  fin (neg (fpred pinf)) /\ b2r (neg (fpred pinf)) = - Om.
Proof.
destruct (pred_pinf prec emax) as [F E].
split; [exact F|split; [exact E|split]].
- now rewrite (IeeeExt.neg_finite prec emax nan_opp).
- rewrite (IeeeExt.neg_value prec emax nan_opp), E. reflexivity.
Qed.

(* What the listing returns, with the cores named. *)
Lemma interval_mid_rad_1_eq :
  forall xl xu : float,
  interval_mid_rad_1 xl xu =
  (if flt xl pinf
   then (if andb (flt xl (neg (fpred pinf))) (flt (fpred pinf) xu) then pzero
         else if flt (fpred pinf) xu then fpred pinf
         else if flt xl (neg (fpred pinf)) then neg (fpred pinf)
         else mid_core (if flt xl (neg (fpred pinf)) then neg (fpred pinf) else xl)
                       (if flt (fpred pinf) xu then fpred pinf else xu))
   else cnan,
   if flt xl pinf
   then (if orb (flt xl (neg (fpred pinf))) (flt (fpred pinf) xu) then pinf
         else rad_core (if flt xl (neg (fpred pinf)) then neg (fpred pinf) else xl)
                       (if flt (fpred pinf) xu then fpred pinf else xu))
   else cnan).
Proof. intros xl xu. reflexivity. Qed.

(* interval_mid_rad_1, for a canonical interval, from precision 2: the generated statement. *)
Theorem interval_mid_rad_1_all :
  (2 <= prec)%Z ->
  forall xl xu : float, interval_1 xl xu ->
  let '(m, r) := interval_mid_rad_1 xl xu in
  (interval_empty_1 xl xu -> nan m /\ nan r) /\
  (xval xl = XInf true -> xval xu = XInf false -> zero m /\ r = infinity prec emax false) /\
  (finite xl -> xval xu = XInf false ->
   xval m = XFin (omega prec emax) /\ r = infinity prec emax false) /\
  (xval xl = XInf true -> finite xu ->
   xval m = XFin (- omega prec emax) /\ r = infinity prec emax false) /\
  (interval_bounded_1 xl xu ->
   finite m /\ finite r /\
   val xl <= val m <= val xu /\
   Rabs (val m - (val xl + val xu) / 2)
   <= u prec * Rabs ((val xl + val xu) / 2) + eta (ieee_emin prec emax) /\
   (forall z : R, in_interval_1 xl xu z -> Rabs (z - val m) <= val r) /\
   val r = RU (ieee_emin prec emax) prec (Rmax (val m - val xl) (val xu - val m))).
Proof.
intros Hp xl xu CX.
rewrite interval_mid_rad_1_eq.
destruct om_facts as [Fom [Eom [Fmo Emo]]].
rewrite (lt_xval prec emax xl pinf), (lt_xval prec emax xl (neg (fpred pinf))),
        (lt_xval prec emax (fpred pinf) xu).
rewrite (xval_fin prec emax _ Fmo), (xval_fin prec emax _ Fom), Emo, Eom.
change (xv pinf) with (XInf false). change (omega prec emax) with Om.
assert (Ncnan : nan cnan) by exact (proj2_sig nan_const).
assert (O0 := Omega_gt_0 prec emax).
destruct (interval_1_cases xl xu CX) as [E|[[Wl Wu]|[[Fl Lu]|[[Ul Fu]|[Fl [Fu Hle]]]]]].
- (* the empty set *)
  assert (Exl : xv xl = XInf false) by exact (proj1 (proj1 (interval_empty_1_xval prec emax xl xu) E)).
  rewrite Exl. cbn [xlt andb orb negb].
  split; [intros _; split; exact Ncnan|].
  split; [intros K; discriminate K|].
  split; [intros K; rewrite (xval_fin prec emax xl K) in Exl; discriminate Exl|].
  split; [intros K; discriminate K|].
  intros [K _]. rewrite (xval_fin prec emax xl K) in Exl. discriminate Exl.
- (* the whole line *)
  rewrite Wl, Wu. cbn [xlt andb orb negb].
  split; [intros K; apply (interval_empty_1_xval prec emax) in K; rewrite Wl in K;
          destruct K as [K _]; discriminate K|].
  split; [intros _ _; split; [exists false; reflexivity|reflexivity]|].
  split; [intros K; rewrite (xval_fin prec emax xl K) in Wl; discriminate Wl|].
  split; [intros _ K; rewrite (xval_fin prec emax xu K) in Wu; discriminate Wu|].
  intros [K _]. rewrite (xval_fin prec emax xl K) in Wl. discriminate Wl.
- (* [xl, +infinity] *)
  rewrite (xval_fin prec emax xl Fl), Lu. cbn [xlt andb orb negb].
  rewrite (Rlt_bool_false (b2r xl) (- Om)) by (generalize (b2r_Omega prec emax xl); lra).
  cbn [andb orb].
  split; [intros [K _]; rewrite K in Fl; discriminate Fl|].
  split; [intros K; discriminate K|].
  split; [intros _ _; split; [rewrite (xval_fin prec emax _ Fom), Eom; reflexivity|reflexivity]|].
  split; [intros K; discriminate K|].
  intros [_ K]. rewrite (xval_fin prec emax xu K) in Lu. discriminate Lu.
- (* [-infinity, xu] *)
  rewrite Ul, (xval_fin prec emax xu Fu). cbn [xlt andb orb negb].
  rewrite (Rlt_bool_false Om (b2r xu)) by (generalize (b2r_Omega prec emax xu); lra).
  cbn [andb orb].
  split; [intros K; apply (interval_empty_1_xval prec emax) in K; rewrite Ul in K;
          destruct K as [K _]; discriminate K|].
  split; [intros _ K; discriminate K|].
  split; [intros K; rewrite (xval_fin prec emax xl K) in Ul; discriminate Ul|].
  split; [intros _ _; split; [rewrite (xval_fin prec emax _ Fmo), Emo; reflexivity|reflexivity]|].
  intros [K _]. rewrite (xval_fin prec emax xl K) in Ul. discriminate Ul.
- (* a bounded interval *)
  rewrite (xval_fin prec emax xl Fl), (xval_fin prec emax xu Fu). cbn [xlt andb orb negb].
  rewrite (Rlt_bool_false (b2r xl) (- Om)) by (generalize (b2r_Omega prec emax xl); lra).
  rewrite (Rlt_bool_false Om (b2r xu)) by (generalize (b2r_Omega prec emax xu); lra).
  cbn [andb orb].
  destruct (mid_rad_bounded Hp xl xu Fl Fu Hle) as [Fm [Fr [Bm [Er [Cn Rr]]]]].
  split; [intros [K _]; rewrite K in Fl; discriminate Fl|].
  split; [intros K; discriminate K|].
  split; [intros _ K; discriminate K|].
  split; [intros K; discriminate K|].
  intros _. split; [exact Fm|split; [exact Fr|split; [exact Bm|split; [exact Er|split; [|exact Rr]]]]].
  intros z [H K]. rewrite (xval_fin prec emax xl Fl) in H. rewrite (xval_fin prec emax xu Fu) in K.
  cbn [xle] in H, K. apply Rle_bool_inv in H. apply Rle_bool_inv in K. apply Cn. lra.
Qed.

(** * interval_to_ball_1 and interval_split_1 *)

Theorem interval_to_ball_1_all :
  (2 <= prec)%Z ->
  forall xl xu : float, interval_1 xl xu ->
  let '(c, r) := interval_to_ball_1 xl xu in
  ball_1 c r /\
  (ball_empty_1 c r <-> interval_empty_1 xl xu) /\
  (interval_nonempty_1 xl xu -> ~ interval_bounded_1 xl xu -> ball_whole_1 c r) /\
  (interval_bounded_1 xl xu ->
   ball_finite_1 c r /\
   val xl <= val c <= val xu /\
   Rabs (val c - (val xl + val xu) / 2)
   <= u prec * Rabs ((val xl + val xu) / 2) + eta (ieee_emin prec emax) /\
   (forall z : R, in_interval_1 xl xu z -> Rabs (z - val c) <= val r) /\
   val r = RU (ieee_emin prec emax) prec (Rmax (val c - val xl) (val xu - val c))).
Proof.
intros Hp xl xu CX.
assert (Eq : interval_to_ball_1 xl xu
             = (if feq (snd (interval_mid_rad_1 xl xu)) pinf then pzero
                else fst (interval_mid_rad_1 xl xu),
                snd (interval_mid_rad_1 xl xu))).
{ unfold IeeeModel.interval_to_ball_1. destruct (interval_mid_rad_1 xl xu). reflexivity. }
rewrite Eq.
generalize (interval_mid_rad_1_all Hp xl xu CX).
destruct (interval_mid_rad_1 xl xu) as [m r]. cbn [fst snd].
intros [M1 [M2 [M3 [M4 M5]]]].
rewrite (eq_xval prec emax r pinf). change (xv pinf) with (XInf false).
assert (WholeZ : ball_1 pzero (infinity prec emax false) /\
                 ~ ball_empty_1 pzero (infinity prec emax false) /\
                 ball_whole_1 pzero (infinity prec emax false)).
{ assert (W : ball_whole_1 pzero (infinity prec emax false))
    by (split; [exists false; reflexivity|reflexivity]).
  split; [right; left; exact W|split; [intros [K _]; discriminate K|exact W]]. }
destruct WholeZ as [WB [WN WW]].
assert (Inf : xeq (xv (infinity prec emax false)) (XInf false) = true) by reflexivity.
destruct (interval_1_cases xl xu CX) as [E|[[Wl Wu]|[[Fl Lu]|[[Ul Fu]|[Fl [Fu Hle]]]]]].
- (* the empty set: the empty ball *)
  destruct (M1 E) as [Nm Nr]. rewrite (xval_nan prec emax r Nr). cbn [xeq].
  assert (BE : ball_empty_1 m r) by exact (conj Nm Nr).
  split; [right; right; exact BE|].
  split; [split; intros _; [exact E|exact BE]|].
  split; [intros N _; elim (nonempty_not_empty prec emax xl xu N E)|].
  intros [K _]. destruct E as [E _]. rewrite E in K. discriminate K.
- (* the whole line *)
  destruct (M2 Wl Wu) as [_ Er]. subst r. rewrite Inf.
  split; [exact WB|].
  split; [split; [intros K; elim (WN K)|intros K; apply (interval_empty_1_xval prec emax) in K;
                                          rewrite Wl in K; destruct K as [K _]; discriminate K]|].
  split; [intros _ _; exact WW|].
  intros [K _]. rewrite (xval_fin prec emax xl K) in Wl. discriminate Wl.
- (* [xl, +infinity] *)
  destruct (M3 Fl Lu) as [_ Er]. subst r. rewrite Inf.
  split; [exact WB|].
  split; [split; [intros K; elim (WN K)|intros [K _]; rewrite K in Fl; discriminate Fl]|].
  split; [intros _ _; exact WW|].
  intros [_ K]. rewrite (xval_fin prec emax xu K) in Lu. discriminate Lu.
- (* [-infinity, xu] *)
  destruct (M4 Ul Fu) as [_ Er]. subst r. rewrite Inf.
  split; [exact WB|].
  split; [split; [intros K; elim (WN K)|intros K; apply (interval_empty_1_xval prec emax) in K;
                                          rewrite Ul in K; destruct K as [K _]; discriminate K]|].
  split; [intros _ _; exact WW|].
  intros [K _]. rewrite (xval_fin prec emax xl K) in Ul. discriminate Ul.
- (* a bounded interval: the finite ball of the midpoint and the radius *)
  destruct (M5 (conj Fl Fu)) as [Fm [Fr [Bm [Er [Cn Rr]]]]].
  rewrite (xval_fin prec emax r Fr). cbn [xeq].
  assert (R0 : 0 <= val r).
  { rewrite Rr. apply Rle_trans with (Rmax (val m - val xl) (val xu - val m)).
    - apply Rle_trans with (2 := Rmax_l _ _). lra.
    - unfold RU. destruct (round_UP_pt radix2 fexp (Rmax (val m - val xl) (val xu - val m)))
        as [_ [L _]]. exact L. }
  assert (BF : ball_finite_1 m r) by (split; [exact Fm|split; [exact Fr|exact R0]]).
  split; [left; exact BF|].
  split; [split; [intros [K _]; unfold nan in K; rewrite (finite_not_nan prec emax m Fm) in K;
                  discriminate K|intros [K _]; rewrite K in Fl; discriminate Fl]|].
  split; [intros _ K; elim (K (conj Fl Fu))|].
  intros _. exact (conj BF (conj Bm (conj Er (conj Cn Rr)))).
Qed.

Theorem interval_split_1_all :
  (2 <= prec)%Z ->
  forall xl xu : float, interval_1 xl xu ->
  let '(al, au, bl, bu) := interval_split_1 xl xu in
  interval_1 al au /\
  interval_1 bl bu /\
  (interval_empty_1 xl xu -> interval_empty_1 al au /\ interval_empty_1 bl bu) /\
  (interval_nonempty_1 xl xu ->
   interval_nonempty_1 al au /\ interval_nonempty_1 bl bu /\
   xval al = xval xl /\ xval bu = xval xu /\ xval au = xval bl).
Proof.
intros Hp xl xu CX.
assert (Eq : interval_split_1 xl xu
             = (xl,
                if feq (snd (interval_mid_rad_1 xl xu)) (snd (interval_mid_rad_1 xl xu))
                then fst (interval_mid_rad_1 xl xu) else neg pinf,
                if feq (snd (interval_mid_rad_1 xl xu)) (snd (interval_mid_rad_1 xl xu))
                then fst (interval_mid_rad_1 xl xu) else pinf,
                xu)).
{ unfold IeeeModel.interval_split_1. destruct (interval_mid_rad_1 xl xu). reflexivity. }
rewrite Eq.
generalize (interval_mid_rad_1_all Hp xl xu CX).
destruct (interval_mid_rad_1 xl xu) as [m r]. cbn [fst snd].
intros [M1 [M2 [M3 [M4 M5]]]].
rewrite (eq_self prec emax r), (neg_pinf prec emax nan_opp).
assert (O0 := Omega_gt_0 prec emax).
(* For a nonempty interval the radius is not a NaN, and the two parts are [xl, m] and
   [m, xu]: they are nonempty when xl <= m <= xu as extended real numbers. *)
assert (Parts : interval_nonempty_1 xl xu -> is_nan prec emax r = false ->
                xnonempty (xv xl) (xv m) -> xnonempty (xv m) (xv xu) ->
                interval_1 xl m /\ interval_1 m xu /\
                (interval_empty_1 xl xu -> interval_empty_1 xl m /\ interval_empty_1 m xu) /\
                (interval_nonempty_1 xl xu ->
                 interval_nonempty_1 xl m /\ interval_nonempty_1 m xu /\
                 xv xl = xv xl /\ xv xu = xv xu /\ xv m = xv m)).
{ intros N _ A B. split; [right; exact A|split; [right; exact B|split]].
  - intros K. elim (nonempty_not_empty prec emax xl xu N K).
  - intros _. split; [exact A|split; [exact B|split; [reflexivity|split; reflexivity]]]. }
destruct (interval_1_cases xl xu CX) as [E|[[Wl Wu]|[[Fl Lu]|[[Ul Fu]|[Fl [Fu Hle]]]]]].
- (* the empty set: the empty set twice *)
  destruct (M1 E) as [_ Nr]. unfold nan in Nr. rewrite Nr. cbn [negb].
  destruct E as [El Eu].
  split; [left; split; [exact El|reflexivity]|].
  split; [left; split; [reflexivity|exact Eu]|].
  split; [intros _; split; split; first [exact El|exact Eu|reflexivity]|].
  intros N. elim (nonempty_not_empty prec emax xl xu N (conj El Eu)).
- (* the whole line: [-infinity, 0] and [0, +infinity] *)
  destruct (M2 Wl Wu) as [[s Em] Er]. subst m r.
  change (is_nan prec emax (infinity prec emax false)) with false. cbn [negb].
  assert (N : interval_nonempty_1 xl xu).
  { unfold interval_nonempty_1. rewrite Wl, Wu. split; [reflexivity|split; reflexivity]. }
  apply (Parts N eq_refl); rewrite ?Wl, ?Wu; split; first [reflexivity|split; reflexivity].
- (* [xl, +infinity]: [xl, Omega] and [Omega, +infinity] *)
  destruct (M3 Fl Lu) as [Xm Er]. subst r. change (omega prec emax) with Om in Xm.
  change (is_nan prec emax (infinity prec emax false)) with false. cbn [negb].
  assert (Bl := b2r_Omega prec emax xl).
  assert (N : interval_nonempty_1 xl xu).
  { unfold interval_nonempty_1. rewrite (xval_fin prec emax xl Fl), Lu.
    split; [reflexivity|split; reflexivity]. }
  apply (Parts N eq_refl).
  + rewrite (xval_fin prec emax xl Fl), Xm. apply xnonempty_fin. lra.
  + rewrite Xm, Lu. split; [reflexivity|split; reflexivity].
- (* [-infinity, xu]: [-infinity, -Omega] and [-Omega, xu] *)
  destruct (M4 Ul Fu) as [Xm Er]. subst r. change (omega prec emax) with Om in Xm.
  change (is_nan prec emax (infinity prec emax false)) with false. cbn [negb].
  assert (Bu := b2r_Omega prec emax xu).
  assert (N : interval_nonempty_1 xl xu).
  { unfold interval_nonempty_1. rewrite Ul, (xval_fin prec emax xu Fu).
    split; [reflexivity|split; reflexivity]. }
  apply (Parts N eq_refl).
  + rewrite Ul, Xm. split; [reflexivity|split; reflexivity].
  + rewrite Xm, (xval_fin prec emax xu Fu). apply xnonempty_fin. lra.
- (* a bounded interval: [xl, m] and [m, xu] *)
  destruct (M5 (conj Fl Fu)) as [Fm [Fr [Bm _]]].
  rewrite (finite_not_nan prec emax r Fr). cbn [negb].
  assert (N : interval_nonempty_1 xl xu).
  { unfold interval_nonempty_1. rewrite (xval_fin prec emax xl Fl), (xval_fin prec emax xu Fu).
    now apply xnonempty_fin. }
  apply (Parts N (finite_not_nan prec emax r Fr)).
  + rewrite (xval_fin prec emax xl Fl), (xval_fin prec emax m Fm). apply xnonempty_fin.
    unfold val in Bm. lra.
  + rewrite (xval_fin prec emax m Fm), (xval_fin prec emax xu Fu). apply xnonempty_fin.
    unfold val in Bm. lra.
Qed.

End IeeeIntervalConvert.

(** * The generated statements *)

Theorem ball_to_interval_1_correct : ball_to_interval_1_spec.
Proof.
intros prec emax Hp0 He nan_plus nan_minus nan_opp nan_abs Hp c r B.
exact (ball_to_interval_1_all prec emax nan_plus nan_minus nan_opp nan_abs Hp c r B).
Qed.

Theorem interval_mid_rad_1_correct : interval_mid_rad_1_spec.
Proof.
intros prec emax Hp0 He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const Hp xl xu CX.
exact (interval_mid_rad_1_all prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const
         Hp xl xu CX).
Qed.

Theorem interval_to_ball_1_correct : interval_to_ball_1_spec.
Proof.
intros prec emax Hp0 He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const Hp xl xu CX.
exact (interval_to_ball_1_all prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const
         Hp xl xu CX).
Qed.

Theorem interval_split_1_correct : interval_split_1_spec.
Proof.
intros prec emax Hp0 He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const Hp xl xu CX.
exact (interval_split_1_all prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const
         Hp xl xu CX).
Qed.
