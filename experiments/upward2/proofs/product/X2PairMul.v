(* EXPERIMENTAL proof probe. Statement 2 of the product: pair_mul (upward2.hpp lines 366-372)
   returns an upper pair of the exact product for all inputs, and an upper-normalized pair for
   operands that are upper-normalized pairs or negations of such pairs (the product passes both:
   mul_case negates the lanes of Q where its flags s are set), underflow included, from
   precision 7. Model and definitions: X2Defs.v.

   Main theorems (Print Assumptions at the end of the file):
   - fast2sum_up_exact: for numbers a, b of the format with |b| <= |a|, a - RU(a + b) is a number
     of the format (the first two operations of Fast2Sum are exact when rounding up). Every
     precision, gradual underflow included, no overflow. This is the fact the header takes from
     Boldo, Graillat and Muller (2017); it is proved here (Sterbenz's lemma and one case below
     2^(emin + prec)), not assumed.
   - fast_two_sum_upper: s + t >= a + b, for all real a, b;
   - fast_two_sum_normalized: when a - RU(a + b) is a number of the format (by
     fast2sum_up_exact: when |b| <= |a|), t = RU(a + b - s) and (s, t) is upper-normalized;
   - pair_mul_upper: zh + zl >= (Ph + Pl) (Qh + Ql), for all real inputs;
   - pair_mul_normalized: (zh, zl) is upper-normalized, for numbers of the format with
     |Pl| <= 2 u |Ph| and |Ql| <= 2 u |Qh| (small_tail), from precision 7;
   - small_tail_upper_normalized: an upper-normalized pair and its negation have small tails;
   - pair_mul_correct: the two together for operands that are upper-normalized pairs or
     negations of upper-normalized pairs, from precision 7.

   What makes p - zh exact is EITHER |w| <= |p| (then fast2sum_up_exact) OR
   |p + w| <= 2^(emin + prec) (then p + w is itself a number of the format, zh = p + w and
   zl = 0). The proof bounds, with Y = u |Ph Qh| and eta = 2^emin: |w| <= 7 Y + 6 eta and
   |p| >= |Ph Qh| - 2 Y - eta (lemma pair_mul_exact_step); so |w| > |p| forces |Ph Qh| < 8 eta
   and then |p + w| < 14 eta, below 2^(emin + prec). Precision 7 is what keeps these constants
   simple (u <= 1/128). *)
From Stdlib Require Import Reals ZArith Lia Lra Psatz Bool.
From Flocq Require Import Core Plus_error Mult_error Sterbenz.
From Kairn.Gen Require Import Statements.
From Kairn Require Import Format Directed2.
From KairnX2P Require Import X2Defs X2Order.
Open Scope R_scope.

(* A second limb small against the first: |l| <= 2 u |h| (for an upper-normalized pair,
   |l| < ulp(h) <= 2 u |h|, or l = 0 below the normal range). *)
Definition small_tail (prec : Z) (h l : R) : Prop := Rabs l <= 2 * u prec * Rabs h.

Section PairMul.
Variable emin prec : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.

Notation fexp := (FLT_exp emin prec).
Notation format := (generic_format radix2 fexp).
Notation ru := (RU emin prec).

(** * Fast2Sum's first two operations rounded up are exact *)

Lemma format_double : forall a, format a -> format (2 * a).
Proof.
intros a Fa. replace (2 * a) with (a * pow2 1) by (rewrite pow2_1; ring).
apply mult_bpow_pos_exact_FLT; [exact Fa | lia].
Qed.

(* Either a / 2 is a number of the format, or |a| is below 2^(emin + prec). *)
Lemma format_half_or_small : forall a, format a -> format (a / 2) \/ Rabs a < pow2 (emin + prec).
Proof.
intros a Fa.
assert (P0 : (0 < prec)%Z) by exact prec_gt_0_.
assert (FF : FLT_format radix2 emin prec a) by (apply FLT_format_generic; trivial).
destruct FF as [[m e] Ha Hm He]. cbn [Fnum Fexp] in Hm, He.
destruct (Z.eq_dec e emin) as [E|E].
- right. rewrite Ha, <- F2R_Zabs. unfold F2R. cbn [Fnum Fexp]. rewrite E.
  rewrite Z.add_comm, bpow_plus.
  apply Rmult_lt_compat_r; [apply bpow_gt_0|].
  rewrite <- IZR_Zpower by lia. apply IZR_lt. exact Hm.
- left. apply generic_format_FLT. exists (Float radix2 m (e - 1)); cbn [Fnum Fexp].
  + rewrite Ha. unfold F2R. cbn [Fnum Fexp].
    assert (H2 : pow2 e = pow2 (e - 1) * pow2 1) by (rewrite <- bpow_plus; f_equal; ring).
    rewrite H2, pow2_1. field.
  + exact Hm.
  + lia.
Qed.

Lemma sterb : forall x y, format x -> format y -> y / 2 <= x <= 2 * y -> format (x - y).
Proof. intros x y Fx Fy H. apply sterbenz; auto with typeclass_instances. Qed.

Theorem fast2sum_up_exact :
  forall a b, format a -> format b -> Rabs b <= Rabs a -> format (a - ru (a + b)).
Proof.
intros a b Fa Fb Hab.
assert (Fs : format (ru (a + b))) by apply (ru_format emin prec).
assert (G1 : a + b <= ru (a + b)) by apply (ru_ge emin prec).
(* when a + b is a number of the format, a - RU(a + b) = -b *)
assert (Ex : format (a + b) -> format (a - ru (a + b))).
{ intros F. rewrite (ru_id emin prec (a + b)) by exact F. replace (a - (a + b)) with (- b) by ring.
  now apply generic_format_opp. }
destruct (Rtotal_order a 0) as [Ha|[Ha|Ha]].
- (* a < 0 *)
  rewrite (Rabs_left a) in Hab by exact Ha.
  destruct (Rle_or_lt b 0) as [Hb|Hb].
  + (* b <= 0: a + b in [2 a, a], and RU(a + b) too *)
    rewrite (Rabs_left1 b) in Hab by exact Hb.
    assert (L : 2 * a <= ru (a + b)) by (apply (ru_ge_format emin prec); [now apply format_double | lra]).
    assert (U : ru (a + b) <= a) by (apply (ru_le_format emin prec); [exact Fa | lra]).
    replace (a - ru (a + b)) with (- ru (a + b) - - a) by ring.
    apply sterb; try (now apply generic_format_opp). lra.
  + rewrite (Rabs_pos_eq b) in Hab by lra.
    destruct (Rle_or_lt (- a / 2) b) as [Hb2|Hb2].
    * (* -a / 2 <= b <= -a: a + b is exact (Sterbenz) *)
      apply Ex. replace (a + b) with (- (- a - b)) by ring. apply generic_format_opp.
      apply sterb; [now apply generic_format_opp | exact Fb | lra].
    * (* 0 < b < -a / 2: a + b in (a, a / 2) *)
      destruct (format_half_or_small a Fa) as [Fh|Sm].
      -- assert (U : ru (a + b) <= a / 2) by (apply (ru_le_format emin prec); [exact Fh | lra]).
         replace (a - ru (a + b)) with (- ru (a + b) - - a) by ring.
         apply sterb; try (now apply generic_format_opp). lra.
      -- apply Ex. apply FLT_format_plus_small; trivial.
         rewrite (Rabs_left a) in Sm by exact Ha. rewrite Rabs_left by lra.
         rewrite Z.add_comm. lra.
- (* a = 0, so b = 0 *)
  subst a. rewrite Rabs_R0 in Hab.
  assert (Bz : b = 0) by (generalize (Rle_abs b) (Rle_abs (- b)); rewrite Rabs_Ropp; lra).
  subst b. rewrite Rplus_0_l, (ru_0 emin prec), Rminus_0_r. apply generic_format_0.
- (* a > 0 *)
  rewrite (Rabs_pos_eq a) in Hab by lra.
  destruct (Rle_or_lt 0 b) as [Hb|Hb].
  + (* b >= 0: a + b in [a, 2 a] *)
    rewrite (Rabs_pos_eq b) in Hab by exact Hb.
    assert (L : a <= ru (a + b)) by (apply (ru_ge_format emin prec); [exact Fa | lra]).
    assert (U : ru (a + b) <= 2 * a) by (apply (ru_le_format emin prec); [now apply format_double | lra]).
    replace (a - ru (a + b)) with (- (ru (a + b) - a)) by ring. apply generic_format_opp.
    apply sterb; trivial. lra.
  + rewrite (Rabs_left b) in Hab by exact Hb.
    destruct (Rle_or_lt (a / 2) (- b)) as [Hb2|Hb2].
    * (* a / 2 <= -b <= a: a + b is exact *)
      apply Ex. replace (a + b) with (a - - b) by ring.
      apply sterb; [exact Fa | now apply generic_format_opp | lra].
    * (* -a / 2 < b < 0: a + b in (a / 2, a) *)
      assert (U : ru (a + b) <= a) by (apply (ru_le_format emin prec); [exact Fa | lra]).
      replace (a - ru (a + b)) with (- (ru (a + b) - a)) by ring. apply generic_format_opp.
      apply sterb; trivial. lra.
Qed.

(** * fast_two_sum *)

Theorem fast_two_sum_upper :
  forall a b, let st := fast_two_sum emin prec a b in a + b <= fst st + snd st.
Proof.
intros a b. unfold fast_two_sum, add_up, sub_up. cbv zeta. cbn [fst snd].
generalize (ru_ge emin prec (a - ru (a + b))) (ru_ge emin prec (ru (a - ru (a + b)) + b)). lra.
Qed.

Theorem fast_two_sum_normalized :
  forall a b, format (a - ru (a + b)) ->
  let st := fast_two_sum emin prec a b in
  snd st = ru (a + b - fst st) /\ upper_normalized emin prec (fst st) (snd st).
Proof.
intros a b Fd. unfold fast_two_sum, add_up, sub_up. cbv zeta. cbn [fst snd].
assert (Fs : format (ru (a + b))) by apply (ru_format emin prec).
assert (T : ru (ru (a - ru (a + b)) + b) = ru (a + b - ru (a + b))).
{ rewrite (ru_id emin prec (a - ru (a + b))) by exact Fd. f_equal. ring. }
rewrite T. split; [reflexivity|].
unfold upper_normalized, fmt. split; [exact Fs | split; [apply (ru_format emin prec)|]].
apply (proj2 (ru_eq_iff emin prec _ _ Fs)).
assert (H1 : a + b <= ru (a + b)) by apply (ru_ge emin prec).
assert (H2 : pred radix2 fexp (ru (a + b)) < a + b) by apply (pred_ru_lt emin prec).
assert (H3 : a + b - ru (a + b) <= ru (a + b - ru (a + b))) by apply (ru_ge emin prec).
assert (H4 : ru (a + b - ru (a + b)) <= 0) by (apply (ru_nonpos emin prec); lra).
lra.
Qed.

(** * Small tails *)

Theorem small_tail_upper_normalized :
  forall h l, upper_normalized emin prec h l ->
  small_tail prec h l /\ small_tail prec (- h) (- l).
Proof.
intros h l N.
assert (S : small_tail prec h l).
{ unfold small_tail.
  assert (P : 0 <= 2 * u prec * Rabs h).
  { apply Rmult_le_pos; [apply Rmult_le_pos; [lra | apply bpow_ge_0] | apply Rabs_pos]. }
  destruct N as [Fh [Fl Eh]].
  destruct (Req_dec (h + l) 0) as [Z0|Z0].
  - rewrite Z0, (ru_0 emin prec) in Eh. subst h.
    replace l with 0 by lra. rewrite Rabs_R0. lra.
  - assert (E : Rabs (ru (h + l) - (h + l)) < ulp radix2 fexp (ru (h + l))).
    { unfold RU. apply error_lt_ulp_round; try exact Z0; auto with typeclass_instances. }
    rewrite Eh in E.
    replace (h - (h + l)) with (- l) in E by ring. rewrite Rabs_Ropp in E.
    generalize (ulp_le_max emin prec h). intros M.
    unfold Rmax in M. destruct (Rle_dec (eta emin) (2 * u prec * Rabs h)) as [D|D].
    + lra.
    + rewrite (format_small_zero emin prec l Fl) by lra. rewrite Rabs_R0. exact P. }
split; [exact S|]. unfold small_tail in *. now rewrite 2!Rabs_Ropp.
Qed.

(** * One rounding up, from above *)

Lemma u_le_128 : (7 <= prec)%Z -> u prec <= / 128.
Proof.
intros Hp. unfold u. change (/ 128) with (bpow radix2 (-7)). apply bpow_le. lia.
Qed.

Lemma ru_abs_le : (7 <= prec)%Z -> forall y, Rabs (ru y) <= (1 + / 64) * Rabs y + eta emin.
Proof.
intros Hp y.
generalize (ru_gap emin prec y) (u_le_128 Hp) (Rabs_pos y). intros [G1 G2] U A.
assert (K : 2 * u prec * Rabs y <= / 64 * Rabs y).
{ apply Rmult_le_compat_r; [exact A | lra]. }
assert (E : 0 < eta emin) by apply bpow_gt_0.
assert (Hm : Rmax (eta emin) (2 * u prec * Rabs y) <= eta emin + / 64 * Rabs y).
{ unfold Rmax. destruct (Rle_dec (eta emin) (2 * u prec * Rabs y)); lra. }
replace (ru y) with (y + (ru y - y)) by ring.
apply Rle_trans with (1 := Rabs_triang _ _).
rewrite (Rabs_pos_eq (ru y - y)) by exact G1.
lra.
Qed.

(** * Statement 2: pair_mul *)

Theorem pair_mul_upper :
  forall ph pl qh ql,
  let r := pair_mul emin prec ph pl qh ql in
  (ph + pl) * (qh + ql) <= fst (snd r) + snd (snd r).
Proof.
intros ph pl qh ql. unfold pair_mul, mul_up, fma_up, add_up, neg. cbv zeta. cbn [fst snd].
set (p := ru (ph * qh)).
set (r1 := ru (pl * ql)). set (r2 := ru (pl * qh + r1)). set (c := ru (ph * ql + r2)).
set (e := ru (ph * qh + - p)). set (w := ru (e + c)).
assert (Z := fast_two_sum_upper p w). cbv zeta in Z.
assert (H1 : pl * ql <= r1) by (unfold r1; apply (ru_ge emin prec)).
assert (H2 : pl * qh + r1 <= r2) by (unfold r2; apply (ru_ge emin prec)).
assert (H3 : ph * ql + r2 <= c) by (unfold c; apply (ru_ge emin prec)).
assert (H4 : ph * qh + - p <= e) by (unfold e; apply (ru_ge emin prec)).
assert (H5 : e + c <= w) by (unfold w; apply (ru_ge emin prec)).
replace ((ph + pl) * (qh + ql)) with (ph * qh + ph * ql + pl * qh + pl * ql) by ring.
lra.
Qed.

(* The step the header argues informally: p - RU(p + w) is a number of the format. *)
Lemma pair_mul_exact_step :
  (7 <= prec)%Z ->
  forall ph pl qh ql, format ph -> format pl -> format qh -> format ql ->
  small_tail prec ph pl -> small_tail prec qh ql ->
  forall p e r1 r2 c w,
  p = ru (ph * qh) -> e = ru (ph * qh + - p) ->
  r1 = ru (pl * ql) -> r2 = ru (pl * qh + r1) -> c = ru (ph * ql + r2) -> w = ru (e + c) ->
  format (p - ru (p + w)).
Proof.
intros Hp ph pl qh ql Fph Fpl Fqh Fql Tp Tq p e r1 r2 c w Ep Ee E1 E2 Ec Ew.
unfold small_tail in Tp, Tq.
assert (Fp : format p) by (rewrite Ep; apply (ru_format emin prec)).
assert (Fw : format w) by (rewrite Ew; apply (ru_format emin prec)).
assert (U := u_le_128 Hp).
assert (U0 : 0 < u prec) by apply bpow_gt_0.
assert (E0 : 0 < eta emin) by apply bpow_gt_0.
assert (AX : Rabs (ph * qh) = Rabs ph * Rabs qh) by apply Rabs_mult.
assert (X0 : 0 <= Rabs (ph * qh)) by apply Rabs_pos.
assert (Ah : 0 <= Rabs ph) by apply Rabs_pos.
assert (Aq : 0 <= Rabs qh) by apply Rabs_pos.
assert (Y0 : 0 <= u prec * Rabs (ph * qh)) by (apply Rmult_le_pos; lra).
assert (YX : u prec * Rabs (ph * qh) <= / 128 * Rabs (ph * qh))
  by (apply Rmult_le_compat_r; lra).
(* the three cross products, against Y = u |Ph Qh| *)
assert (C1 : Rabs (pl * qh) <= 2 * (u prec * Rabs (ph * qh))).
{ rewrite (Rabs_mult pl qh), AX.
  apply Rle_trans with (2 * u prec * Rabs ph * Rabs qh); [|right; ring].
  apply Rmult_le_compat_r; [exact Aq | exact Tp]. }
assert (C2 : Rabs (ph * ql) <= 2 * (u prec * Rabs (ph * qh))).
{ rewrite (Rabs_mult ph ql), AX.
  apply Rle_trans with (Rabs ph * (2 * u prec * Rabs qh)); [|right; ring].
  apply Rmult_le_compat_l; [exact Ah | exact Tq]. }
assert (C3 : Rabs (pl * ql) <= / 32 * (u prec * Rabs (ph * qh))).
{ rewrite (Rabs_mult pl ql), AX.
  apply Rle_trans with ((2 * u prec * Rabs ph) * (2 * u prec * Rabs qh)).
  { apply Rmult_le_compat; trivial; apply Rabs_pos. }
  replace (2 * u prec * Rabs ph * (2 * u prec * Rabs qh))
    with ((4 * u prec) * (u prec * (Rabs ph * Rabs qh))) by ring.
  apply Rmult_le_compat_r; [|lra].
  apply Rmult_le_pos; [lra | now apply Rmult_le_pos]. }
(* the leading product and its error *)
assert (Gp : 0 <= p - ph * qh <= eta emin + 2 * (u prec * Rabs (ph * qh))).
{ generalize (ru_gap emin prec (ph * qh)). rewrite <- Ep. intros [G1 G2]. split; [exact G1|].
  apply Rle_trans with (1 := G2). unfold Rmax.
  destruct (Rle_dec (eta emin) (2 * u prec * Rabs (ph * qh))); lra. }
assert (He : Rabs e <= eta emin + 2 * (u prec * Rabs (ph * qh))).
{ assert (L : ph * qh + - p <= e) by (rewrite Ee; apply (ru_ge emin prec)).
  assert (R0 : e <= 0) by (rewrite Ee; apply (ru_nonpos emin prec); lra).
  rewrite (Rabs_left1 e) by exact R0. lra. }
assert (Hpx : Rabs (ph * qh) - eta emin - 2 * (u prec * Rabs (ph * qh)) <= Rabs p).
{ assert (T : Rabs (ph * qh) <= Rabs p + Rabs (ph * qh - p)).
  { generalize (Rabs_triang p (ph * qh - p)).
    replace (p + (ph * qh - p)) with (ph * qh) by ring. auto. }
  rewrite (Rabs_minus_sym (ph * qh) p), (Rabs_pos_eq (p - ph * qh)) in T by lra. lra. }
(* the cross terms and w *)
assert (B1 := ru_abs_le Hp (pl * ql)). rewrite <- E1 in B1.
assert (B2 := ru_abs_le Hp (pl * qh + r1)). rewrite <- E2 in B2.
assert (T2 := Rabs_triang (pl * qh) r1).
assert (B3 := ru_abs_le Hp (ph * ql + r2)). rewrite <- Ec in B3.
assert (T3 := Rabs_triang (ph * ql) r2).
assert (B4 := ru_abs_le Hp (e + c)). rewrite <- Ew in B4.
assert (T4 := Rabs_triang e c).
assert (Hw : Rabs w <= 7 * (u prec * Rabs (ph * qh)) + 6 * eta emin) by lra.
destruct (Rle_or_lt (Rabs w) (Rabs p)) as [O|O].
- (* |w| <= |p|: Fast2Sum's order *)
  now apply fast2sum_up_exact.
- (* |w| > |p|: then the product is tiny, and p + w is a number of the format *)
  assert (Xs : Rabs (ph * qh) < 8 * eta emin) by lra.
  assert (Ws : Rabs w <= 7 * eta emin) by lra.
  assert (Sm : Rabs (p + w) <= pow2 (prec + emin)).
  { apply Rle_trans with (1 := Rabs_triang p w).
    assert (P7 : pow2 7 <= pow2 prec) by (apply bpow_le; lia).
    change (pow2 7) with 128 in P7.
    rewrite bpow_plus. fold (eta emin).
    apply Rle_trans with (128 * eta emin); [lra|].
    apply Rmult_le_compat_r; lra. }
  assert (F : format (p + w)) by (apply FLT_format_plus_small; trivial).
  rewrite (ru_id emin prec (p + w)) by exact F.
  replace (p - (p + w)) with (- w) by ring. now apply generic_format_opp.
Qed.

Theorem pair_mul_normalized :
  (7 <= prec)%Z ->
  forall ph pl qh ql, format ph -> format pl -> format qh -> format ql ->
  small_tail prec ph pl -> small_tail prec qh ql ->
  let r := pair_mul emin prec ph pl qh ql in
  upper_normalized emin prec (fst (snd r)) (snd (snd r)).
Proof.
intros Hp ph pl qh ql Fph Fpl Fqh Fql Tp Tq r.
assert (D := pair_mul_exact_step Hp ph pl qh ql Fph Fpl Fqh Fql Tp Tq _ _ _ _ _ _
               eq_refl eq_refl eq_refl eq_refl eq_refl eq_refl).
exact (proj2 (fast_two_sum_normalized _ _ D)).
Qed.

(* The operands the product passes: each one an upper-normalized pair or the negation of one. *)
Definition up_or_neg (h l : R) : Prop :=
  upper_normalized emin prec h l \/ upper_normalized emin prec (- h) (- l).

Lemma up_or_neg_facts :
  forall h l, up_or_neg h l -> format h /\ format l /\ small_tail prec h l.
Proof.
intros h l [N|N].
- pose proof N as [F1 [F2 _]].
  split; [exact F1 | split; [exact F2 |]]. apply (small_tail_upper_normalized h l N).
- pose proof N as [F1 [F2 _]].
  split; [|split].
  + rewrite <- (Ropp_involutive h). now apply generic_format_opp.
  + rewrite <- (Ropp_involutive l). now apply generic_format_opp.
  + generalize (proj2 (small_tail_upper_normalized (- h) (- l) N)).
    now rewrite 2!Ropp_involutive.
Qed.

Theorem pair_mul_correct :
  (7 <= prec)%Z ->
  forall ph pl qh ql, up_or_neg ph pl -> up_or_neg qh ql ->
  let r := pair_mul emin prec ph pl qh ql in
  upper_pair (fst (snd r)) (snd (snd r)) ((ph + pl) * (qh + ql)) /\
  upper_normalized emin prec (fst (snd r)) (snd (snd r)).
Proof.
intros Hp ph pl qh ql P Q r.
destruct (up_or_neg_facts ph pl P) as [Fph [Fpl Tp]].
destruct (up_or_neg_facts qh ql Q) as [Fqh [Fql Tq]].
split.
- exact (pair_mul_upper ph pl qh ql).
- exact (pair_mul_normalized Hp ph pl qh ql Fph Fpl Fqh Fql Tp Tq).
Qed.

End PairMul.

Print Assumptions fast2sum_up_exact.
Print Assumptions fast_two_sum_upper.
Print Assumptions fast_two_sum_normalized.
Print Assumptions pair_mul_upper.
Print Assumptions pair_mul_normalized.
Print Assumptions pair_mul_correct.
