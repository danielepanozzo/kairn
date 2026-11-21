(* The midpoint and a radius of an interval with bounds of two limbs, the ball made of them,
   and its split at the midpoint, in the IEEE model, on all values: interval_mid_rad_2,
   interval_to_ball_2 and interval_split_2 (docs/developer/design/milestone2.md, "One enclosure
   interface": "Midpoint, radius and the conversions", the row of split() and "The empty set
   and the whole line"; docs/developer/architecture.md, "Claims of the enclosure interface: the
   conversions of two limbs").

   Notation as in IeeeIntervalConvert.v, which proves the same kernels on bounds of one limb:
   T is the IEEE format, Omega its largest number, eta its smallest positive one, u = 2^-prec,
   U = 2^(emax - prec) the gap of the largest numbers; xval_2 is the extended real number a
   canonical 2-limb value stands for. [l, h] is the interval, mid = (l + h) / 2 its exact
   midpoint, and (m, r) the midpoint and the radius computed. rel2 = 3 u^2 / (1 - 4 u) is the
   bound of add_2_2. The theorems K_correct at the end establish the generated statements
   (proofs/gen/IeeeStatements.v). From precision 3.

   What is proved.

   - interval_mid_rad_2, for a canonical interval (interval_mid_rad_2_correct): the empty set
     gives three NaN; the whole line the midpoint 0 and the radius +infinity; a half-line the
     midpoint +-Omega on its side and the radius +infinity; and a bounded interval a finite m
     with l <= m <= h and |m - mid| <= rel2 |mid| + 2 eta, and a radius that is +infinity or a
     finite number with which every member of [l, h] is within r of m; the radius is finite
     when both bounds are at most 2^(emax - 2) in magnitude. And for every canonical interval
     the midpoint is a canonical 2-limb value, the invariant of the type of the midpoint: two
     NaN, a zero twice, (+-Omega, +0), or a normalized pair.

   - interval_to_ball_2 (interval_to_ball_2_correct): a canonical ball, empty exactly when the
     interval is, the whole line for an unbounded nonempty interval, a ball that contains a
     bounded interval, and, when both bounds are at most 2^(emax - 2) in magnitude, the finite
     ball of the midpoint and the radius above.

   - interval_split_2 (interval_split_2_correct): [l, p] and [p, h], both canonical, both
     empty for the empty set, both nonempty for a nonempty interval, p the midpoint moved
     into [l, h].

   The proofs.

   - The midpoint of a bounded interval is finite, which is where the threshold of add_2_2 at
     half the range is needed (IeeeAdd22Top.v). Each bound is halved by mul_pow2_2
     (halve_facts): the half is finite and normalized, within eta / 2 of the exact half (a
     halving is exact unless the limb is below 2^(emin + prec), and then the pair has no second
     limb: halve_real), and its leading limb is at most Omega / 2 in magnitude. That last fact
     is not immediate at a bound whose leading limb is +-Omega: the tail of such a bound is
     strictly below U/2 (tail_Omega_strict, by the tie rule), so that the sum of the two
     rounded halves stays strictly below the midpoint of Omega / 2 and the next number. Then
     add_2_2 of the two halves does not overflow (add_2_2_values_finite_half), and is within
     rel2 of their sum (add_2_2_values_correct): within rel2 |mid| + (1 + rel2) eta of mid.
     The two selects by lt_2_2 move it into [l, h] and do not move it away from mid
     (clamp2_facts).

   - A side of the radius is radd(to_up_2(z), e), (z, e) = add_ball_2_2 of a difference a - b
     that is not negative, made +infinity when it is not below +infinity (side_facts): e is
     nonnegative, +infinity or a NaN; when it is finite, z is finite, within e of a - b and not
     negative (dist_2_rel, which is IeeeBallCompare2.dist_2 with the relative bound of
     add_2_2 kept), so that to_up_2(z) is at least z and radd at least their sum; and when e
     is not finite, radd is +infinity or a NaN (radd_not_lt_pinf), never a finite number or
     -infinity. So a side is +infinity or a finite number that is at least a - b. It is finite
     when both operands are at most 2^(emax - 2) and the difference at most 9/8 of that
     (side_small): add_2_2 is finite there (add_2_2_values_finite), z is at most 45/32, the
     radius e at most 1 and to_up_2(z) at most 3/2 of 2^(emax - 2), and their sum, rounded, at
     most 3/4 of 2^emax, which is below Omega. The distance of the midpoint to a bound is at
     most half the width plus rel2 |mid| + 2 eta, which is at most 9/8 of 2^(emax - 2).

   - The split point is the midpoint selected for the kind of interval (0, +-Omega, or the
     midpoint above), a canonical value with a finite leading limb, moved into [l, h] by two
     selects of lt_2_2: whatever that value is, the result is a canonical finite value between
     the bounds (split_point, from xsplit_point on extended real numbers). *)
From Stdlib Require Import Reals ZArith Bool Lia Lra Psatz.
From Flocq Require Import Core Binary Relative Sterbenz Plus_error.
From Kairn.Gen Require Import Model Statements IeeeStatements.
From Kairn Require Import Format Normalized EFT MulPow2 Add22 Directed2.
From Kairn Require Import IeeeBridge IeeeVocabulary IeeeEFT IeeeOps IeeeExt IeeeAdd22 IeeeSub.
From Kairn Require Import IeeeFinite IeeeRange IeeeAdd22Top IeeeFull.
From Kairn Require Import IeeeBall IeeeBallCores IeeeBallFinite IeeeDirected IeeeEntry.
From Kairn Require Import IeeeIntervalVocabulary IeeeInterval1 IeeeInterval2 IeeeBallConvert.
From Kairn Require Import IeeeIntervalExact IeeeIntervalConvert.
From Kairn Require Import IeeeBallPredicates IeeeBallPredicates2 IeeeBallCompare2.
From Kairn Require Ball2 IeeeOperations.
From Kairn.Gen Require IeeeModel.
Open Scope R_scope.

Section IeeeIntervalConvert2.
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
Notation fabs := (IeeeOperations.abs prec emax nan_abs).
Notation add := (IeeeOperations.add prec emax nan_plus).
Notation prod := (IeeeOperations.prod prec emax nan_fma).
Notation fma := (IeeeOperations.fma prec emax nan_fma).
Notation flt := (IeeeOperations.lt prec emax).
Notation feq := (IeeeOperations.eq prec emax).
Notation fpred := (IeeeOperations.pred prec emax).
Notation fsucc := (IeeeOperations.succ prec emax).
Notation pzero := (IeeeOperations.pzero prec emax).
Notation pinf := (IeeeOperations.pinf prec emax).
Notation cnan := (IeeeOperations.cnan prec emax nan_const).
Notation xv := (@xval prec emax).
Notation xv2 := (@xval_2 prec emax).
Notation Om := (Omega prec emax).
Notation QT := (bpow radix2 (emax - 2)).
Notation U := (bpow radix2 (emax - prec)).
Notation half := (IeeeModel.up_ball_from_interval_2_0 prec emax).
Notation lt_2_2 := (IeeeModel.lt_2_2 prec emax).
Notation radd := (IeeeModel.radd prec emax nan_plus).
Notation to_up_2 := (IeeeModel.to_up_2 prec emax).
Notation mul_pow2_2 := (IeeeModel.mul_pow2_2 prec emax nan_plus nan_minus nan_fma).
Notation add_2_2 := (IeeeModel.add_2_2 prec emax nan_plus nan_minus).
Notation add_ball_2_2 := (IeeeModel.add_ball_2_2 prec emax nan_plus nan_minus nan_abs nan_fma).
Notation interval_mid_rad_2 :=
  (IeeeModel.interval_mid_rad_2 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const).
Notation interval_to_ball_2 :=
  (IeeeModel.interval_to_ball_2 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const).
Notation interval_split_2 :=
  (IeeeModel.interval_split_2 prec emax nan_plus nan_minus nan_opp nan_fma).
Notation rel2 := (3 / (1 - 4 * u prec) * u prec ^ 2).

Let Hprec : (0 < prec)%Z.
Proof. exact prec_gt_0_. Qed.
Let Hemax : (prec < emax)%Z.
Proof. exact prec_lt_emax_. Qed.

(** * Constants *)

(* The relative bound of add_2_2 is at most 3/32 from precision 3 on. *)
Lemma rel2_le : (3 <= prec)%Z -> 0 <= rel2 <= 3 / 32.
Proof.
intros Hp. assert (Ht : 0 < u prec <= / 8) by exact (Ball2.u_bounds prec 3 Hp).
destruct Ht as [T0 T8]. assert (D : 0 < 1 - 4 * u prec) by lra.
split.
- apply Rmult_le_pos; [apply Rlt_le, Rdiv_lt_0_compat; lra|nra].
- apply Rmult_le_reg_r with (1 - 4 * u prec); [exact D|].
  replace (3 / (1 - 4 * u prec) * u prec ^ 2 * (1 - 4 * u prec)) with (3 * u prec ^ 2)
    by (field; lra).
  nra.
Qed.

(* Twice the smallest positive number is at most 1/32 of 2^(emax - 2). *)
Lemma two_eta_le : (3 <= prec)%Z -> 2 * eta emin <= / 32 * QT.
Proof.
intros Hp. unfold eta.
assert (A : bpow radix2 (emin + 1) <= bpow radix2 (emax - 7)) by (apply bpow_le; lia).
rewrite two_bpow in A.
replace (emax - 7)%Z with (-5 + (emax - 2))%Z in A by ring. rewrite bpow_plus in A.
exact A.
Qed.

(** * Canonical values *)

Lemma normalized_single : forall x : R, format x -> normalized_2 emin prec x 0.
Proof.
intros x Fx. split; [exact Fx|split; [apply generic_format_0|]].
unfold RN. rewrite Rplus_0_r. symmetry. apply round_generic; auto with typeclass_instances.
Qed.

Lemma canonical_single : forall x : float, fin x -> canonical_2 x pzero.
Proof.
intros x Fx. left. split; [exact Fx|split; [reflexivity|]].
exact (normalized_single (b2r x) (b2r_format prec emax x)).
Qed.

Lemma canonical_fin :
  forall x0 x1 : float, fin x0 -> fin x1 -> normalized_2 emin prec (b2r x0) (b2r x1) ->
  canonical_2 x0 x1.
Proof. intros x0 x1 F0 F1 N. left. split; [exact F0|split; [exact F1|exact N]]. Qed.

(** * The cases of a canonical interval of two limbs *)

Lemma empty_2_xval :
  forall xl0 xl1 xu0 xu1 : float, interval_empty_2 xl0 xl1 xu0 xu1 ->
  xv2 xl0 xl1 = XInf false /\ xv2 xu0 xu1 = XInf true /\ xv xl0 = XInf false.
Proof. intros xl0 xl1 xu0 xu1 [E0 [_ [E2 _]]]. subst xl0 xu0. repeat split; reflexivity. Qed.

Lemma nonempty_not_empty_2 :
  forall xl0 xl1 xu0 xu1 : float, interval_nonempty_2 xl0 xl1 xu0 xu1 ->
  ~ interval_empty_2 xl0 xl1 xu0 xu1.
Proof.
intros xl0 xl1 xu0 xu1 [_ [_ [_ [K _]]]] E. destruct (empty_2_xval _ _ _ _ E) as [E0 _].
rewrite E0 in K. discriminate K.
Qed.

Lemma interval_2_cases :
  forall xl0 xl1 xu0 xu1 : float, interval_2 xl0 xl1 xu0 xu1 ->
  interval_empty_2 xl0 xl1 xu0 xu1 \/
  (interval_nonempty_2 xl0 xl1 xu0 xu1 /\
   ((xv2 xl0 xl1 = XInf true /\ xv2 xu0 xu1 = XInf false /\
     xv xl0 = XInf true /\ xv xu0 = XInf false) \/
    (fin xl0 /\ fin xl1 /\ normalized_2 emin prec (b2r xl0) (b2r xl1) /\
     xv2 xu0 xu1 = XInf false /\ xv xu0 = XInf false) \/
    (xv2 xl0 xl1 = XInf true /\ xv xl0 = XInf true /\
     fin xu0 /\ fin xu1 /\ normalized_2 emin prec (b2r xu0) (b2r xu1)) \/
    (fin xl0 /\ fin xl1 /\ normalized_2 emin prec (b2r xl0) (b2r xl1) /\
     fin xu0 /\ fin xu1 /\ normalized_2 emin prec (b2r xu0) (b2r xu1) /\
     b2r xl0 + b2r xl1 <= b2r xu0 + b2r xu1))).
Proof.
intros xl0 xl1 xu0 xu1 [E|N]; [now left|right]. split; [exact N|].
destruct N as [Cl [Ch [H1 [H2 H3]]]].
destruct (canonical_cases prec emax xl0 xl1 Cl)
  as [[Fl0 [Fl1 [Nl [El0 [El1 El]]]]]|[[s [s' [_ [_ [El0 [El1 El]]]]]]|[_ [_ [El0 [El1 El]]]]]];
destruct (canonical_cases prec emax xu0 xu1 Ch)
  as [[Fu0 [Fu1 [Nu [Eu0 [Eu1 Eu]]]]]|[[t [t' [_ [_ [Eu0 [Eu1 Eu]]]]]]|[_ [_ [Eu0 [Eu1 Eu]]]]]];
  rewrite El in H1, H2; rewrite Eu in H1, H3; cbn in H1, H2, H3; try discriminate H1.
- right; right; right. apply Rle_bool_inv in H1.
  exact (conj Fl0 (conj Fl1 (conj Nl (conj Fu0 (conj Fu1 (conj Nu H1)))))).
- destruct t; cbn in H3; [discriminate H3|]. right; left.
  exact (conj Fl0 (conj Fl1 (conj Nl (conj Eu Eu0)))).
- destruct s; cbn in H2; [|discriminate H2]. right; right; left.
  exact (conj El (conj El0 (conj Fu0 (conj Fu1 Nu)))).
- destruct s; cbn in H2; [|discriminate H2]. destruct t; cbn in H3; [discriminate H3|].
  left. exact (conj El (conj Eu (conj El0 Eu0))).
Qed.

(* The three tests of the listings, on the extended real numbers the leading limbs stand
   for. *)
Lemma tests_2 :
  forall xl0 xu0 : float,
  flt xl0 pinf = xlt (xv xl0) (XInf false) /\
  flt xl0 (neg (fpred pinf)) = xlt (xv xl0) (XFin (- Om)) /\
  flt (fpred pinf) xu0 = xlt (XFin Om) (xv xu0).
Proof.
intros xl0 xu0. destruct (om_facts prec emax nan_opp) as [Fom [Eom [Fmo Emo]]].
rewrite 3!(lt_xval prec emax), (xval_fin prec emax _ Fmo), (xval_fin prec emax _ Fom), Emo, Eom.
repeat split; reflexivity.
Qed.

(** * Half of a 2-limb number *)

(* Over the real numbers: mul_pow2_2 by 1/2 of a normalized pair whose leading limb is at
   most Omega in magnitude. *)
Lemma halve_real :
  (3 <= prec)%Z -> forall X0 X1 : R, normalized_2 emin prec X0 X1 -> Rabs X0 <= Om ->
  let '(z0, z1) := Model.mul_pow2_2 emin prec tie_even X0 X1 (/ 2) in
  normalized_2 emin prec z0 z1 /\ Rabs z0 <= Om / 2 /\
  Rabs ((z0 + z1) - (X0 + X1) / 2) <= / 2 * eta emin.
Proof.
intros Hp X0 X1 Hn HX0. assert (Hp2 : (2 <= prec)%Z) by lia.
assert (F0 : format X0) by apply Hn. assert (F1 : format X1) by apply Hn.
generalize (mul_pow2_2_facts emin prec Hp2 X0 X1 (-1) Hn). cbv zeta.
unfold Model.mul_pow2_2. cbv zeta. rewrite !Rplus_0_r, pow2_m1. unfold RN.
set (h := rnd (X0 * / 2)). set (l := rnd (X1 * / 2)).
assert (Fst : fst (Model.fast_two_sum emin prec tie_even h l) = rnd (h + l)) by reflexivity.
destruct (Model.fast_two_sum emin prec tie_even h l) as [z0 z1]. cbn [fst snd] in *.
intros [Nz [Hs _]].
assert (E0 := scale_error emin prec X0 (-1) F0). rewrite pow2_m1 in E0. unfold RN in E0. fold h in E0.
assert (E1 := scale_error emin prec X1 (-1) F1). rewrite pow2_m1 in E1. unfold RN in E1. fold l in E1.
assert (Eta0 : 0 < bpow radix2 emin) by apply bpow_gt_0.
assert (U0 : 0 < U) by apply bpow_gt_0.
assert (EO := Omega_eq prec emax).
assert (T3 : 4 * U <= bpow radix2 (emax - 1)).
{ replace (emax - 1)%Z with (2 + (emax - 3))%Z by ring. rewrite bpow_plus, pow2_2.
  apply Rmult_le_compat_l. lra. apply bpow_le. lia. }
assert (Q4 : bpow radix2 (emax - prec - 2) = / 4 * U).
{ replace (emax - prec - 2)%Z with (-2 + (emax - prec))%Z by ring. rewrite bpow_plus. reflexivity. }
assert (Q8 : bpow radix2 (emax - prec - 3) = / 8 * U).
{ replace (emax - prec - 3)%Z with (-3 + (emax - prec))%Z by ring. rewrite bpow_plus. reflexivity. }
(* a halving is exact when the limb is at least 2^(emin + prec) in magnitude *)
assert (Exact : forall x : R, format x -> bpow radix2 (emin + prec) <= Rabs x ->
                rnd (x * / 2) = x * / 2).
{ intros x Fx Big. rewrite <- pow2_m1. apply (scale_exact emin prec x (-1) Fx). right.
  rewrite Rabs_mult, pow2_m1, (Rabs_pos_eq (/ 2)) by lra.
  replace (emin + prec - 1)%Z with (-1 + (emin + prec))%Z by ring.
  rewrite bpow_plus, pow2_m1. lra. }
assert (Err : Rabs (h + l - (X0 + X1) / 2) <= / 2 * bpow radix2 emin).
{ destruct (Rle_or_lt (bpow radix2 (emin + prec)) (Rabs X0)) as [Big|Small].
  - assert (Eh : h = X0 * / 2) by exact (Exact X0 F0 Big).
    rewrite Eh. replace (X0 * / 2 + l - (X0 + X1) / 2) with (l - X1 * / 2) by field. exact E1.
  - assert (Z1 : X1 = 0) by exact (normalized_2_small emin prec X0 X1 Hn Small).
    assert (El : l = 0).
    { unfold l. rewrite Z1, Rmult_0_l. apply round_0; auto with typeclass_instances. }
    rewrite El, Z1. replace (h + 0 - (X0 + 0) / 2) with (h - X0 * / 2) by field. exact E0. }
assert (HX1 : Rabs X1 <= / 2 * U).
{ apply Rle_trans with (1 := normalized_2_tail_ulp emin prec X0 X1 Hn).
  apply Rmult_le_compat_l. lra. apply (ulp_le_top prec emax).
  unfold IeeeBridge.inrange. generalize (Omega_lt_top prec emax). lra. }
assert (Bz0 : Rabs z0 <= Om / 2).
{ rewrite Fst. destruct (Req_dec (Rabs X0) Om) as [Top|NTop].
  - (* the leading limb is +-Omega: its half is exact and the tail strictly below U/2 *)
    assert (S1 := tail_Omega_strict prec emax Hp2 X0 X1 Hn Top).
    assert (Big : bpow radix2 (emin + prec) <= Rabs X0).
    { rewrite Top. apply Rle_trans with (bpow radix2 (emax - 1)); [apply bpow_le; lia|lra]. }
    assert (Eh : h = X0 * / 2) by exact (Exact X0 F0 Big).
    assert (Bl : Rabs l < / 4 * U).
    { destruct (Rle_or_lt (Rabs X1) (/ 4 * U)) as [Sm|Lg].
      - apply Rle_lt_trans with (/ 8 * U); [|lra]. rewrite <- Q8.
        apply (RN_abs_le_bpow emin prec). rewrite Q8, Rabs_mult, (Rabs_pos_eq (/ 2)) by lra. lra.
      - assert (El : l = X1 * / 2).
        { apply (Exact X1 F1). apply Rle_trans with (/ 4 * U); [|lra]. rewrite <- Q4.
          apply bpow_le. lia. }
        rewrite El, Rabs_mult, (Rabs_pos_eq (/ 2)) by lra. lra. }
    apply (rnd_below_half_mid prec emax).
    apply Rle_lt_trans with (1 := Rabs_triang _ _).
    rewrite Eh, Rabs_mult, (Rabs_pos_eq (/ 2)) by lra. lra.
  - (* otherwise the leading limb is at most Omega - U *)
    assert (B := below_Omega prec emax Hp2 X0 F0 HX0 NTop).
    assert (Bh : Rabs h <= Om / 2 - / 2 * U + / 2 * bpow radix2 emin).
    { generalize (Rabs_triang (h - X0 * / 2) (X0 * / 2)).
      replace (h - X0 * / 2 + X0 * / 2) with h by ring.
      rewrite (Rabs_mult X0), (Rabs_pos_eq (/ 2)) by lra. lra. }
    assert (Bl : Rabs l <= / 4 * U).
    { rewrite <- Q4. apply (RN_abs_le_bpow emin prec).
      rewrite Q4, Rabs_mult, (Rabs_pos_eq (/ 2)) by lra. lra. }
    assert (EtaU : bpow radix2 emin <= / 4 * U) by (rewrite <- Q4; apply bpow_le; lia).
    apply (Format.round_abs_le emin prec tie_even). apply (format_half_Omega prec emax).
    apply Rle_trans with (1 := Rabs_triang _ _). lra. }
split; [exact Nz|split; [exact Bz0|]]. rewrite Hs. unfold eta. exact Err.
Qed.

(* In the IEEE model: half of a finite normalized pair is finite and normalized, its leading
   limb is at most Omega / 2 in magnitude, and it is within eta / 2 of the exact half. *)
Lemma halve_facts :
  (3 <= prec)%Z -> forall x0 x1 : float, fin x0 -> fin x1 ->
  normalized_2 emin prec (b2r x0) (b2r x1) ->
  let '(z0, z1) := mul_pow2_2 x0 x1 half in
  fin z0 /\ fin z1 /\ normalized_2 emin prec (b2r z0) (b2r z1) /\
  Rabs (b2r z0) <= Om / 2 /\
  Rabs ((b2r z0 + b2r z1) - (b2r x0 + b2r x1) / 2) <= / 2 * eta emin.
Proof.
intros Hp x0 x1 F0 F1 N. assert (Hp2 : (2 <= prec)%Z) by lia.
destruct (half_spec prec emax Hp2) as [Fh Eh].
assert (B0 := b2r_le_Omega prec emax x0).
assert (B1 := tail_le_half_U prec emax x0 x1 N).
assert (Hs : Rabs ((b2r x0 + b2r x1) * b2r half) <= bpow radix2 (emax - 1)).
{ rewrite Eh, Rabs_mult, (Rabs_pos_eq (/ 2)) by lra.
  generalize (Rabs_triang (b2r x0) (b2r x1)) (Omega_eq prec emax)
             (bpow_gt_0 radix2 (emax - prec)). lra. }
assert (Pc : exists n : Z, b2r half = bpow radix2 n).
{ exists (-1)%Z. rewrite Eh, pow2_m1. reflexivity. }
generalize (mul_pow2_2_ieee_finite_any prec emax prec_gt_0_ prec_lt_emax_
              nan_plus nan_minus nan_opp nan_fma Hp2 x0 x1 half F0 F1 Fh N Hs)
           (mul_pow2_2_values prec emax nan_plus nan_minus nan_opp nan_fma Hp2
              x0 x1 half F0 F1 Fh N Pc)
           (halve_real Hp (b2r x0) (b2r x1) N B0).
rewrite Eh.
destruct (mul_pow2_2 x0 x1 half) as [z0 z1].
intros [_ [Fz0 Fz1]] V. destruct (V Fz0) as [_ E]. rewrite <- E. intros [Nz [Bz Ez]].
exact (conj Fz0 (conj Fz1 (conj Nz (conj Bz Ez)))).
Qed.

(** * The midpoint of a bounded interval *)

(* The two selects that move a finite 2-limb value into [l, h]. *)
Lemma clamp2_facts :
  forall l0 l1 h0 h1 a0 a1 : float,
  fin l0 -> fin l1 -> normalized_2 emin prec (b2r l0) (b2r l1) ->
  fin h0 -> fin h1 -> normalized_2 emin prec (b2r h0) (b2r h1) ->
  fin a0 -> fin a1 -> normalized_2 emin prec (b2r a0) (b2r a1) ->
  b2r l0 + b2r l1 <= b2r h0 + b2r h1 ->
  let ca := lt_2_2 a0 a1 l0 l1 in
  let mb0 := if ca then l0 else a0 in
  let mb1 := if ca then l1 else a1 in
  let cb := lt_2_2 h0 h1 mb0 mb1 in
  let m0 := if cb then h0 else mb0 in
  let m1 := if cb then h1 else mb1 in
  fin m0 /\ fin m1 /\ normalized_2 emin prec (b2r m0) (b2r m1) /\
  b2r l0 + b2r l1 <= b2r m0 + b2r m1 <= b2r h0 + b2r h1 /\
  (forall t : R, b2r l0 + b2r l1 <= t <= b2r h0 + b2r h1 ->
   Rabs (b2r m0 + b2r m1 - t) <= Rabs (b2r a0 + b2r a1 - t)).
Proof.
intros l0 l1 h0 h1 a0 a1 Fl0 Fl1 Nl Fh0 Fh1 Nh Fa0 Fa1 Na Hlh. cbv zeta.
assert (Hp1 : (1 <= prec)%Z) by (generalize prec_gt_0_; unfold Prec_gt_0; lia).
assert (Cl := canonical_fin l0 l1 Fl0 Fl1 Nl).
assert (Ch := canonical_fin h0 h1 Fh0 Fh1 Nh).
assert (Ca := canonical_fin a0 a1 Fa0 Fa1 Na).
rewrite (lt_2_2_ext prec emax Hp1 a0 a1 l0 l1 Ca Cl).
rewrite (xval_2_fin prec emax a0 a1 Fa0), (xval_2_fin prec emax l0 l1 Fl0). cbn [xlt].
destruct (Rlt_bool_spec (b2r a0 + b2r a1) (b2r l0 + b2r l1)) as [A|A]; cbv beta iota.
- rewrite (lt_2_2_ext prec emax Hp1 h0 h1 l0 l1 Ch Cl).
  rewrite (xval_2_fin prec emax h0 h1 Fh0), (xval_2_fin prec emax l0 l1 Fl0). cbn [xlt].
  rewrite Rlt_bool_false by lra.
  split; [exact Fl0|split; [exact Fl1|split; [exact Nl|split; [lra|]]]].
  intros t Ht. rewrite (Rabs_left1 (b2r l0 + b2r l1 - t)) by lra.
  rewrite (Rabs_left1 (b2r a0 + b2r a1 - t)) by lra. lra.
- rewrite (lt_2_2_ext prec emax Hp1 h0 h1 a0 a1 Ch Ca).
  rewrite (xval_2_fin prec emax h0 h1 Fh0), (xval_2_fin prec emax a0 a1 Fa0). cbn [xlt].
  destruct (Rlt_bool_spec (b2r h0 + b2r h1) (b2r a0 + b2r a1)) as [B|B]; cbv beta iota.
  + split; [exact Fh0|split; [exact Fh1|split; [exact Nh|split; [lra|]]]].
    intros t Ht. rewrite (Rabs_pos_eq (b2r h0 + b2r h1 - t)) by lra.
    rewrite (Rabs_pos_eq (b2r a0 + b2r a1 - t)) by lra. lra.
  + split; [exact Fa0|split; [exact Fa1|split; [exact Na|split; [lra|]]]].
    intros t _. apply Rle_refl.
Qed.

(* The sum of the halves, moved into [l, h]. *)
Definition mid_core2 (l0 l1 h0 h1 : float) : float * float :=
  let '(hl0, hl1) := mul_pow2_2 l0 l1 half in
  let '(hu0, hu1) := mul_pow2_2 h0 h1 half in
  let '(ma0, ma1) := add_2_2 hl0 hl1 hu0 hu1 in
  let ca := lt_2_2 ma0 ma1 l0 l1 in
  let mb0 := if ca then l0 else ma0 in
  let mb1 := if ca then l1 else ma1 in
  let cb := lt_2_2 h0 h1 mb0 mb1 in
  (if cb then h0 else mb0, if cb then h1 else mb1).

(* The midpoint of a bounded interval [l, h]: finite, normalized, in the interval, and
   within rel2 |mid| + 2 eta of the exact midpoint. *)
Lemma mid_core2_bounded :
  (3 <= prec)%Z -> forall l0 l1 h0 h1 : float,
  fin l0 -> fin l1 -> normalized_2 emin prec (b2r l0) (b2r l1) ->
  fin h0 -> fin h1 -> normalized_2 emin prec (b2r h0) (b2r h1) ->
  b2r l0 + b2r l1 <= b2r h0 + b2r h1 ->
  let '(m0, m1) := mid_core2 l0 l1 h0 h1 in
  fin m0 /\ fin m1 /\ normalized_2 emin prec (b2r m0) (b2r m1) /\
  b2r l0 + b2r l1 <= b2r m0 + b2r m1 <= b2r h0 + b2r h1 /\
  Rabs ((b2r m0 + b2r m1) - ((b2r l0 + b2r l1) + (b2r h0 + b2r h1)) / 2)
  <= rel2 * Rabs (((b2r l0 + b2r l1) + (b2r h0 + b2r h1)) / 2) + 2 * eta emin.
Proof.
intros Hp l0 l1 h0 h1 Fl0 Fl1 Nl Fh0 Fh1 Nh Hlh.
unfold mid_core2.
generalize (halve_facts Hp l0 l1 Fl0 Fl1 Nl). destruct (mul_pow2_2 l0 l1 half) as [hl0 hl1].
intros [Fa0 [Fa1 [Na [Ba Ea]]]].
generalize (halve_facts Hp h0 h1 Fh0 Fh1 Nh). destruct (mul_pow2_2 h0 h1 half) as [hu0 hu1].
intros [Fb0 [Fb1 [Nb [Bb Eb]]]].
assert (HltH : forall x : R, Rabs x <= Om / 2 -> Rabs x < bpow radix2 (emax - 1)).
{ intros x Hx. generalize (Omega_eq prec emax) (bpow_gt_0 radix2 (emax - prec)). lra. }
generalize (add_2_2_values_finite_half prec emax nan_plus nan_minus nan_opp nan_fma Hp
              hl0 hl1 hu0 hu1 Fa0 Fa1 Fb0 Fb1 Na Nb (HltH _ Ba) (HltH _ Bb))
           (add_2_2_values_correct prec emax nan_plus nan_minus nan_opp nan_fma Hp
              hl0 hl1 hu0 hu1 Fa0 Fa1 Fb0 Fb1 Na Nb).
destruct (add_2_2 hl0 hl1 hu0 hu1) as [ma0 ma1].
intros [_ [Fm0 _]] C. destruct (C Fm0) as [Fm1 [Nm Em]].
assert (CF := clamp2_facts l0 l1 h0 h1 ma0 ma1 Fl0 Fl1 Nl Fh0 Fh1 Nh Fm0 Fm1 Nm Hlh).
cbv zeta in CF. cbv beta iota zeta.
destruct CF as [Fc0 [Fc1 [Nc [Bc Cc]]]].
split; [exact Fc0|split; [exact Fc1|split; [exact Nc|split; [exact Bc|]]]].
set (vl := b2r l0 + b2r l1) in *. set (vh := b2r h0 + b2r h1) in *.
set (s := (b2r hl0 + b2r hl1) + (b2r hu0 + b2r hu1)) in *.
set (mid := (vl + vh) / 2).
destruct (rel2_le Hp) as [R0 R1].
assert (E0 : 0 < eta emin) by (unfold eta; apply bpow_gt_0).
assert (Hs : Rabs (s - mid) <= eta emin).
{ replace (s - mid) with ((b2r hl0 + b2r hl1 - vl / 2) + (b2r hu0 + b2r hu1 - vh / 2))
    by (unfold s, mid; field).
  apply Rle_trans with (1 := Rabs_triang _ _). lra. }
assert (Ha : Rabs (b2r ma0 + b2r ma1 - mid) <= rel2 * Rabs mid + 2 * eta emin).
{ assert (S1 : Rabs s <= Rabs mid + eta emin).
  { generalize (Rabs_triang (s - mid) mid). replace (s - mid + mid) with s by ring. lra. }
  assert (S2 : rel2 * Rabs s <= rel2 * Rabs mid + rel2 * eta emin).
  { rewrite <- Rmult_plus_distr_l. apply Rmult_le_compat_l; lra. }
  assert (S3 : rel2 * eta emin <= 1 * eta emin) by (apply Rmult_le_compat_r; lra).
  generalize (Rabs_triang (b2r ma0 + b2r ma1 - s) (s - mid)).
  replace (b2r ma0 + b2r ma1 - s + (s - mid)) with (b2r ma0 + b2r ma1 - mid) by ring. lra. }
apply Rle_trans with (2 := Ha). apply Cc. unfold mid. lra.
Qed.

(** * A side of the radius *)

(* IeeeBallCompare2.dist_2 with the relative bound of add_2_2: (z, e) = add_ball_2_2 of x and
   -y; e is nonnegative, +inf or NaN; when it is finite, z is a finite canonical pair, x and y
   are finite, and z is within e, and within rel2 |x - y|, of x - y. *)
Lemma dist_2_rel :
  (3 <= prec)%Z ->
  forall x0 x1 y0 y1 : float, canonical_2 x0 x1 -> canonical_2 y0 y1 ->
  let '(z0, z1, e) := add_ball_2_2 x0 x1 (neg y0) (neg y1) in
  nonneg_ext e /\
  (fin e -> fin z0 /\ canonical_2 z0 z1 /\ fin x0 /\ fin y0 /\
   Rabs ((b2r x0 + b2r x1) - (b2r y0 + b2r y1) - (b2r z0 + b2r z1)) <= b2r e /\
   Rabs ((b2r z0 + b2r z1) - ((b2r x0 + b2r x1) - (b2r y0 + b2r y1)))
   <= rel2 * Rabs ((b2r x0 + b2r x1) - (b2r y0 + b2r y1))).
Proof.
intros Hp x0 x1 y0 y1 Cx Cy.
assert (Cny : canonical_2 (neg y0) (neg y1)).
{ generalize (neg_2_ext prec emax nan_opp y0 y1 Cy). unfold IeeeModel.neg_2. cbv zeta. tauto. }
destruct (consts_ball_add_2 prec emax Hp) as [[_ [_ N0]] [[_ [_ N1]] [_ [_ N2]]]].
generalize (add_ball_2_2_ieee_core prec emax nan_plus nan_minus nan_opp nan_abs nan_fma Hp
              x0 x1 (neg y0) (neg y1) Cx Cny).
unfold IeeeModel.add_ball_2_2.
destruct (IeeeModel.add_2_2 prec emax nan_plus nan_minus x0 x1 (neg y0) (neg y1)) as [z0 z1].
cbv zeta. intros Core.
destruct (prod_nonneg prec emax nan_fma (fabs z0) (IeeeModel.up_ball_add_2_0 prec emax)
            (abs_nonneg prec emax nan_abs z0) N0) as [Nt Ft].
destruct (fma_nonneg prec emax nan_fma _ _ _ Nt N1 N2) as [Ne Fe].
split; [exact Ne|]. intros FE.
destruct (Fe FE) as [Ftt _]. destruct (Ft Ftt) as [Fa _].
rewrite (abs_finite prec emax nan_abs) in Fa.
destruct (Core Fa) as [F0 [F1 [G0 [G1 [Nx [Ny [Fz1 [Ez [_ Ed]]]]]]]]].
generalize (add_ball_2_2_correct emin prec Hp (b2r x0) (b2r x1) (b2r (neg y0)) (b2r (neg y1)) Nx Ny).
unfold Model.add_ball_2_2. rewrite <- Ez. cbv beta iota zeta. intros [_ [Nz [Rl D]]].
rewrite 2!(IeeeExt.neg_value prec emax nan_opp) in D.
rewrite 2!(IeeeExt.neg_value prec emax nan_opp) in Rl.
assert (FY0 : fin y0) by (rewrite <- (IeeeExt.neg_finite prec emax nan_opp); exact G0).
split; [exact Fa|split; [left; exact (conj Fa (conj Fz1 Nz))|split; [exact F0|split; [exact FY0|split]]]].
- rewrite (Ed FE). eapply Rle_trans; [|apply Rle_refl].
  replace (b2r x0 + b2r x1 - (b2r y0 + b2r y1) - (b2r z0 + b2r z1))
    with (b2r x0 + b2r x1 + (- b2r y0 + - b2r y1) - (b2r z0 + b2r z1)) by ring.
  exact D.
- replace (b2r x0 + b2r x1 - (b2r y0 + b2r y1))
    with (b2r x0 + b2r x1 + (- b2r y0 + - b2r y1)) by ring.
  exact Rl.
Qed.

(* The rounding up of a finite canonical pair that is not negative is not negative: a number
   or +infinity. *)
Lemma to_up_2_nonneg :
  forall z0 z1 : float, canonical_2 z0 z1 -> fin z0 -> 0 <= b2r z0 + b2r z1 ->
  nonneg_ext (to_up_2 z0 z1).
Proof.
intros z0 z1 C F0 P.
assert (Hp1 : (1 <= prec)%Z) by (generalize prec_gt_0_; unfold Prec_gt_0; lia).
assert (E := to_up_2_ext prec emax Hp1 z0 z1 C).
rewrite (xval_2_fin prec emax z0 z1 F0) in E. cbn [xround] in E. unfold overflow_of in E.
assert (R0 : 0 <= RU emin prec (b2r z0 + b2r z1)).
{ apply Rle_trans with (1 := P). unfold RU.
  destruct (round_UP_pt radix2 fexp (b2r z0 + b2r z1)) as [_ [K _]]. exact K. }
revert E. destruct (Rlt_bool (Rabs (RU emin prec (b2r z0 + b2r z1))) (bpow radix2 emax)); intros E.
- assert (F := xval_fin_inv prec emax _ _ E). rewrite (xval_fin prec emax _ F) in E.
  injection E as E. apply (nonneg_ext_finite prec emax); [exact F|]. rewrite E. exact R0.
- rewrite Rlt_bool_false in E by lra. right; left. exact (xval_inf_inv prec emax _ false E).
Qed.

(* radd with a second operand that is +infinity or a NaN is +infinity or a NaN, whatever the
   first operand: not below +infinity. *)
Lemma radd_not_lt_pinf :
  forall a e : float, nonneg_ext e -> is_finite prec emax e = false ->
  flt (radd a e) pinf = false.
Proof.
intros a e [N|[I|[F _]]] NF; [| |congruence].
- assert (Nr : is_nan prec emax (radd a e) = true).
  { unfold IeeeModel.radd. cbv zeta. rewrite (succ_nan prec emax).
    apply (add_nan_r prec emax nan_plus). exact N. }
  rewrite (lt_xval prec emax), (xval_nan prec emax _ Nr). reflexivity.
- subst e. unfold IeeeModel.radd. cbv zeta.
  assert (E : add a (infinity prec emax false) = pinf \/
              is_nan prec emax (add a (infinity prec emax false)) = true).
  { destruct a as [s|[|]|s pl Ha|s m ex Ha]; first [left; reflexivity|right; reflexivity]. }
  destruct E as [E|E].
  + rewrite E, (succ_pinf prec emax). reflexivity.
  + assert (Nr : is_nan prec emax (fsucc (add a (infinity prec emax false))) = true)
      by (rewrite (succ_nan prec emax); exact E).
    rewrite (lt_xval prec emax), (xval_nan prec emax _ Nr). reflexivity.
Qed.

Lemma lt_pinf_l : forall x : float, flt pinf x = false.
Proof.
intros x. rewrite (lt_xval prec emax). change (xv pinf) with (XInf false).
destruct (xv x) as [|[|]|r]; reflexivity.
Qed.

Lemma lt_fin_pinf : forall x : float, fin x -> flt x pinf = true.
Proof. intros x F. rewrite (lt_xval prec emax), (xval_fin prec emax x F). reflexivity. Qed.

(* One side of the radius: an upper bound of a - b, made +infinity when it is not below
   +infinity. *)
Definition side (a0 a1 b0 b1 : float) : float :=
  let '(z0, z1, e) := add_ball_2_2 a0 a1 (neg b0) (neg b1) in
  let rs := radd (to_up_2 z0 z1) e in
  if flt rs pinf then rs else pinf.

(* For canonical a and b with finite leading limbs and b <= a: +infinity, or a finite number
   that is at least a - b. *)
Lemma side_facts :
  (3 <= prec)%Z -> forall a0 a1 b0 b1 : float, canonical_2 a0 a1 -> canonical_2 b0 b1 ->
  b2r b0 + b2r b1 <= b2r a0 + b2r a1 ->
  side a0 a1 b0 b1 = pinf \/
  (fin (side a0 a1 b0 b1) /\
   (b2r a0 + b2r a1) - (b2r b0 + b2r b1) <= b2r (side a0 a1 b0 b1)).
Proof.
intros Hp a0 a1 b0 b1 Ca Cb Hab. assert (Hp2 : (2 <= prec)%Z) by lia.
generalize (dist_2_rel Hp a0 a1 b0 b1 Ca Cb). unfold side.
destruct (add_ball_2_2 a0 a1 (neg b0) (neg b1)) as [[z0 z1] e]. intros [Ne D]. cbv zeta.
destruct (finite_dec prec emax e) as [Fe|NFe].
- destruct (D Fe) as [Fz0 [Cz [_ [_ [K Rl]]]]].
  destruct (rel2_le Hp) as [R0 R1].
  assert (Pz : 0 <= b2r z0 + b2r z1).
  { apply Rabs_le_inv in Rl. rewrite Rabs_pos_eq in Rl by lra.
    assert (K1 : rel2 * (b2r a0 + b2r a1 - (b2r b0 + b2r b1))
                 <= 1 * (b2r a0 + b2r a1 - (b2r b0 + b2r b1)))
      by (apply Rmult_le_compat_r; lra).
    lra. }
  assert (Nta := to_up_2_nonneg z0 z1 Cz Fz0 Pz).
  destruct (radd_ext prec emax nan_plus Hp2 (to_up_2 z0 z1) e Nta Ne) as [Nr Fr].
  destruct Nr as [N|[I|[F P]]].
  + left. rewrite (lt_xval prec emax), (xval_nan prec emax _ N). reflexivity.
  + left. rewrite I. reflexivity.
  + right. rewrite (lt_fin_pinf _ F). split; [exact F|].
    destruct (Fr F) as [Fta [_ [L _]]].
    assert (Tu := to_up_2_above prec emax z0 z1 Cz Fz0 Fta).
    apply Rabs_le_inv in K. lra.
- left. rewrite (radd_not_lt_pinf _ e Ne NFe). reflexivity.
Qed.

(* A side is finite when both operands are at most 2^(emax - 2) in magnitude, by their
   leading limbs, and their difference at most 9/8 of that. *)
Lemma side_small :
  (3 <= prec)%Z -> forall a0 a1 b0 b1 : float,
  fin a0 -> fin a1 -> normalized_2 emin prec (b2r a0) (b2r a1) ->
  fin b0 -> fin b1 -> normalized_2 emin prec (b2r b0) (b2r b1) ->
  Rabs (b2r a0) <= QT -> Rabs (b2r b0) <= QT ->
  Rabs ((b2r a0 + b2r a1) - (b2r b0 + b2r b1)) <= 9 / 8 * QT ->
  fin (side a0 a1 b0 b1).
Proof.
intros Hp a0 a1 b0 b1 Fa0 Fa1 Na Fb0 Fb1 Nb Ha Hb Hv.
assert (Hp2 : (2 <= prec)%Z) by lia. assert (Hp1 : (1 <= prec)%Z) by lia.
assert (Ca := canonical_fin a0 a1 Fa0 Fa1 Na).
assert (Fn0 : fin (neg b0)) by (rewrite (IeeeExt.neg_finite prec emax nan_opp); exact Fb0).
assert (Fn1 : fin (neg b1)) by (rewrite (IeeeExt.neg_finite prec emax nan_opp); exact Fb1).
assert (Nn : normalized_2 emin prec (b2r (neg b0)) (b2r (neg b1))).
{ rewrite 2!(IeeeExt.neg_value prec emax nan_opp). now apply normalized_2_opp. }
assert (Cnb := canonical_fin (neg b0) (neg b1) Fn0 Fn1 Nn).
assert (Hn : Rabs (b2r (neg b0)) <= QT)
  by (rewrite (IeeeExt.neg_value prec emax nan_opp), Rabs_Ropp; exact Hb).
generalize (add_2_2_values_finite prec emax nan_plus nan_minus nan_opp nan_fma Hp
              a0 a1 (neg b0) (neg b1) Fa0 Fa1 Fn0 Fn1 Na Nn Ha Hn)
           (add_ball_2_2_ieee_core prec emax nan_plus nan_minus nan_opp nan_abs nan_fma Hp
              a0 a1 (neg b0) (neg b1) Ca Cnb).
unfold side, IeeeModel.add_ball_2_2.
destruct (IeeeModel.add_2_2 prec emax nan_plus nan_minus a0 a1 (neg b0) (neg b1)) as [z0 z1].
cbv zeta. intros [_ [Fz0 _]] Core.
destruct (Core Fz0) as [_ [_ [_ [_ [_ [_ [Fz1 [Ez _]]]]]]]].
generalize (add_2_2_correct emin prec Hp (b2r a0) (b2r a1) (b2r (neg b0)) (b2r (neg b1)) Na Nn).
rewrite <- Ez. intros [Nz Rl]. rewrite 2!(IeeeExt.neg_value prec emax nan_opp) in Rl.
replace (b2r a0 + b2r a1 + (- b2r b0 + - b2r b1))
  with ((b2r a0 + b2r a1) - (b2r b0 + b2r b1)) in Rl by ring.
set (v := (b2r a0 + b2r a1) - (b2r b0 + b2r b1)) in *.
destruct (rel2_le Hp) as [R0 R1].
assert (T0 : 0 < QT) by apply bpow_gt_0.
assert (Bz : Rabs (b2r z0 + b2r z1) <= 45 / 32 * QT).
{ assert (K1 : rel2 * Rabs v <= / 4 * Rabs v) by (apply Rmult_le_compat_r; [apply Rabs_pos|lra]).
  generalize (Rabs_le_plus_err (b2r z0 + b2r z1) v) (Rabs_pos v). lra. }
assert (Bz0 : Rabs (b2r z0) <= 15 / 8 * QT).
{ generalize (lead_le prec emax Hp2 _ _ Nz). lra. }
(* the radius e *)
destruct (consts_ball_add_2 prec emax Hp) as [[FE [EE _]] [[FG [EG _]] [FH [EH _]]]].
destruct (E_add_2_le_eighth prec emax Hp) as [E0 E1].
destruct (G_3_le prec emax Hp2) as [G0 G1].
destruct (H_add_le_tiny prec emax Hp) as [H0 H1].
assert (B4 : bpow radix2 (emax - 4) = / 4 * QT).
{ replace (emax - 4)%Z with (-2 + (emax - 2))%Z by ring. rewrite bpow_plus. reflexivity. }
assert (Faz : fin (fabs z0)) by (rewrite (abs_finite prec emax nan_abs); exact Fz0).
assert (Eaz : b2r (fabs z0) = Rabs (b2r z0)) by apply (abs_val prec emax nan_abs).
assert (Y0 : 0 <= Rabs (b2r z0) * Model.up_ball_add_2_0 emin prec)
  by (apply Rmult_le_pos; [apply Rabs_pos|lra]).
assert (Y1 : Rabs (b2r z0) * Model.up_ball_add_2_0 emin prec <= bpow radix2 (emax - 4)).
{ rewrite B4. apply Rle_trans with (Rabs (b2r z0) * / 8);
    [apply Rmult_le_compat_l; [apply Rabs_pos|lra]|lra]. }
set (s := rnd (Rabs (b2r z0) * Model.up_ball_add_2_0 emin prec + 0)).
assert (S0 : 0 <= s) by (apply (rnd_pos prec emax); lra).
assert (S1 : s <= bpow radix2 (emax - 4)).
{ apply (rnd_le_format prec emax); [apply (IeeeBallFinite.format_bpow prec emax); lia|lra]. }
assert (TOP : bpow radix2 emax = 4 * QT) by apply top_4.
assert (It : IeeeBridge.inrange emax
               (rnd (b2r (fabs z0) * b2r (IeeeModel.up_ball_add_2_0 prec emax) + 0))).
{ rewrite Eaz, EE. fold s. unfold IeeeBridge.inrange. rewrite Rabs_pos_eq by exact S0. lra. }
destruct (prod_fin prec emax nan_fma _ _ Faz FE It) as [Ft Et].
rewrite Eaz, EE in Et. fold s in Et.
set (dr := rnd (s * Model.up_ball_add_1_1 emin prec + Model.up_ball_add_1_2 emin prec)).
assert (K0 : 0 <= s * Model.up_ball_add_1_1 emin prec) by (apply Rmult_le_pos; lra).
assert (K1 : s * Model.up_ball_add_1_1 emin prec <= bpow radix2 (emax - 4) * 2)
  by (apply Rmult_le_compat; lra).
assert (D0 : 0 <= dr) by (apply (rnd_pos prec emax); lra).
assert (D1 : dr <= QT).
{ apply (rnd_le_format prec emax); [apply (IeeeBallFinite.format_bpow prec emax); lia|lra]. }
assert (Id : IeeeBridge.inrange emax
               (rnd (b2r (prod (fabs z0) (IeeeModel.up_ball_add_2_0 prec emax))
                     * b2r (IeeeModel.up_ball_add_1_1 prec emax)
                     + b2r (IeeeModel.up_ball_add_1_2 prec emax)))).
{ rewrite Et, EG, EH. fold dr. unfold IeeeBridge.inrange. rewrite Rabs_pos_eq by exact D0. lra. }
destruct (fma_fin prec emax nan_fma _ _ _ Ft FG FH Id) as [Fd Ed].
rewrite Et, EG, EH in Ed. fold dr in Ed.
(* to_up_2 z: finite, at most 3/2 of 2^(emax - 2) *)
assert (Cz := canonical_fin z0 z1 Fz0 Fz1 Nz).
assert (F38 := format_3_eighths prec emax Hp2).
assert (T2 := quarter_range_eq emax).
assert (P3 : 0 < bpow radix2 (emax - 3)) by apply bpow_gt_0.
assert (Ru : RU emin prec (b2r z0 + b2r z1) <= 3 * bpow radix2 (emax - 3)).
{ apply (RU_le prec emax); [exact F38|]. apply Rabs_le_inv in Bz. lra. }
assert (Rd : - (3 * bpow radix2 (emax - 3)) <= RU emin prec (b2r z0 + b2r z1)).
{ apply Rle_trans with (b2r z0 + b2r z1); [apply Rabs_le_inv in Bz; lra|].
  unfold RU. destruct (round_UP_pt radix2 fexp (b2r z0 + b2r z1)) as [_ [K _]]. exact K. }
assert (Xta : xv (to_up_2 z0 z1) = XFin (RU emin prec (b2r z0 + b2r z1))).
{ rewrite (to_up_2_ext prec emax Hp1 z0 z1 Cz), (xval_2_fin prec emax z0 z1 Fz0).
  unfold xround, overflow_of. rewrite Rlt_bool_true by (apply Rabs_lt; lra). reflexivity. }
assert (Fta := xval_fin_inv prec emax _ _ Xta).
assert (Eta : b2r (to_up_2 z0 z1) = RU emin prec (b2r z0 + b2r z1)).
{ rewrite (xval_fin prec emax _ Fta) in Xta. injection Xta as K. exact K. }
(* the sum of the two and its successor *)
assert (F34 := format_3_quarters prec emax Hp2).
assert (Bs : Rabs (b2r (to_up_2 z0 z1)
                   + b2r (fma (prod (fabs z0) (IeeeModel.up_ball_add_2_0 prec emax))
                            (IeeeModel.up_ball_add_1_1 prec emax)
                            (IeeeModel.up_ball_add_1_2 prec emax))) <= 3 * QT).
{ rewrite Eta, Ed. apply Rabs_le. lra. }
assert (Br := Format.round_abs_le emin prec tie_even _ _ F34 Bs).
assert (Ia : IeeeBridge.inrange emax
               (rnd (b2r (to_up_2 z0 z1)
                     + b2r (fma (prod (fabs z0) (IeeeModel.up_ball_add_2_0 prec emax))
                              (IeeeModel.up_ball_add_1_1 prec emax)
                              (IeeeModel.up_ball_add_1_2 prec emax))))).
{ unfold IeeeBridge.inrange. lra. }
destruct (add_fin prec emax nan_plus _ _ Fta Fd Ia) as [Fs Es].
unfold IeeeModel.radd. cbv zeta.
destruct (succ_finite prec emax _ Fs) as [[Fr _]|[_ Bad]].
- rewrite (lt_fin_pinf _ Fr). exact Fr.
- exfalso. rewrite Es in Bad.
  assert (O78 := Omega_ge_7_eighths prec emax Hp).
  assert (K : Ulp.succ radix2 fexp
                (rnd (b2r (to_up_2 z0 z1)
                      + b2r (fma (prod (fabs z0) (IeeeModel.up_ball_add_2_0 prec emax))
                               (IeeeModel.up_ball_add_1_1 prec emax)
                               (IeeeModel.up_ball_add_1_2 prec emax)))) <= Om).
  { apply succ_le_lt; auto with typeclass_instances.
    - apply generic_format_round; auto with typeclass_instances.
    - apply (format_Omega prec emax).
    - apply Rabs_le_inv in Br. lra. }
  generalize (Omega_lt_top prec emax). lra.
Qed.

(** * The radius of a bounded interval *)

(* The larger of the two sides, for a midpoint m. *)
Definition rad_core2 (l0 l1 h0 h1 m0 m1 : float) : float :=
  let ra := side m0 m1 l0 l1 in
  let rb := side h0 h1 m0 m1 in
  if flt ra rb then rb else ra.

Lemma rad_core2_facts :
  (3 <= prec)%Z -> forall l0 l1 h0 h1 m0 m1 : float,
  canonical_2 l0 l1 -> canonical_2 h0 h1 -> canonical_2 m0 m1 ->
  b2r l0 + b2r l1 <= b2r m0 + b2r m1 <= b2r h0 + b2r h1 ->
  rad_core2 l0 l1 h0 h1 m0 m1 = pinf \/
  (fin (rad_core2 l0 l1 h0 h1 m0 m1) /\
   forall z : R, b2r l0 + b2r l1 <= z <= b2r h0 + b2r h1 ->
   Rabs (z - (b2r m0 + b2r m1)) <= b2r (rad_core2 l0 l1 h0 h1 m0 m1)).
Proof.
intros Hp l0 l1 h0 h1 m0 m1 Cl Ch Cm [B1 B2]. unfold rad_core2. cbv zeta.
destruct (side_facts Hp m0 m1 l0 l1 Cm Cl B1) as [Ia|[Fa La]].
- left. rewrite Ia, lt_pinf_l. reflexivity.
- destruct (side_facts Hp h0 h1 m0 m1 Ch Cm B2) as [Ib|[Fb Lb]].
  + left. rewrite Ib, (lt_fin_pinf _ Fa). reflexivity.
  + right. rewrite (lt_finite prec emax _ _ Fa Fb).
    destruct (Rlt_bool_spec (b2r (side m0 m1 l0 l1)) (b2r (side h0 h1 m0 m1))) as [C|C].
    * split; [exact Fb|]. intros z Hz. apply Rabs_le. lra.
    * split; [exact Fa|]. intros z Hz. apply Rabs_le. lra.
Qed.

Lemma lead_le_QT :
  forall x0 x1 : float, normalized_2 emin prec (b2r x0) (b2r x1) ->
  Rabs (b2r x0 + b2r x1) <= QT -> Rabs (b2r x0) <= QT.
Proof.
intros x0 x1 [_ [_ E]] Hx. assert (K := RN_abs_le_bpow emin prec _ _ Hx).
rewrite <- E in K. exact K.
Qed.

Lemma rad_core2_small :
  (3 <= prec)%Z -> forall l0 l1 h0 h1 m0 m1 : float,
  fin l0 -> fin l1 -> normalized_2 emin prec (b2r l0) (b2r l1) ->
  fin h0 -> fin h1 -> normalized_2 emin prec (b2r h0) (b2r h1) ->
  fin m0 -> fin m1 -> normalized_2 emin prec (b2r m0) (b2r m1) ->
  b2r l0 + b2r l1 <= b2r m0 + b2r m1 <= b2r h0 + b2r h1 ->
  Rabs (b2r l0 + b2r l1) <= QT -> Rabs (b2r h0 + b2r h1) <= QT ->
  Rabs ((b2r m0 + b2r m1) - ((b2r l0 + b2r l1) + (b2r h0 + b2r h1)) / 2) <= / 8 * QT ->
  fin (rad_core2 l0 l1 h0 h1 m0 m1).
Proof.
intros Hp l0 l1 h0 h1 m0 m1 Fl0 Fl1 Nl Fh0 Fh1 Nh Fm0 Fm1 Nm [B1 B2] Hl Hh Hm.
assert (Hl' := Hl). assert (Hh' := Hh). assert (Hm' := Hm).
apply Rabs_le_inv in Hl'. apply Rabs_le_inv in Hh'. apply Rabs_le_inv in Hm'.
assert (Bm : Rabs (b2r m0 + b2r m1) <= QT) by (apply Rabs_le; lra).
assert (Fa : fin (side m0 m1 l0 l1)).
{ apply (side_small Hp); trivial.
  - exact (lead_le_QT m0 m1 Nm Bm).
  - exact (lead_le_QT l0 l1 Nl Hl).
  - apply Rabs_le. lra. }
assert (Fb : fin (side h0 h1 m0 m1)).
{ apply (side_small Hp); trivial.
  - exact (lead_le_QT h0 h1 Nh Hh).
  - exact (lead_le_QT m0 m1 Nm Bm).
  - apply Rabs_le. lra. }
unfold rad_core2. cbv zeta. destruct (flt (side m0 m1 l0 l1) (side h0 h1 m0 m1)); assumption.
Qed.

(** * interval_mid_rad_2 *)

Ltac destruct_calls :=
  repeat (match goal with
          | |- context [IeeeModel.mul_pow2_2 prec emax ?a ?b ?c ?x ?y ?z] =>
              destruct (IeeeModel.mul_pow2_2 prec emax a b c x y z)
          | |- context [IeeeModel.add_2_2 prec emax ?a ?b ?x ?y ?z ?t] =>
              destruct (IeeeModel.add_2_2 prec emax a b x y z t)
          | |- context [IeeeModel.add_ball_2_2 prec emax ?a ?b ?c ?d ?x ?y ?z ?t] =>
              destruct (IeeeModel.add_ball_2_2 prec emax a b c d x y z t) as [[? ?] ?]
          end; cbv beta iota).

(* What the listing returns, with the cores named. *)
Lemma interval_mid_rad_2_eq :
  forall xl0 xl1 xu0 xu1 : float,
  interval_mid_rad_2 xl0 xl1 xu0 xu1 =
  (let ml := flt xl0 (neg (fpred pinf)) in
   let mu := flt (fpred pinf) xu0 in
   let l0 := if ml then neg (fpred pinf) else xl0 in
   let l1 := if ml then pzero else xl1 in
   let h0 := if mu then fpred pinf else xu0 in
   let h1 := if mu then pzero else xu1 in
   let '(mc0, mc1) := mid_core2 l0 l1 h0 h1 in
   let ne := flt xl0 pinf in
   (if ne then (if andb ml mu then pzero else if mu then fpred pinf
                else if ml then neg (fpred pinf) else mc0) else cnan,
    if ne then (if andb ml mu then pzero else if mu then pzero
                else if ml then pzero else mc1) else cnan,
    if ne then (if orb ml mu then pinf else rad_core2 l0 l1 h0 h1 mc0 mc1) else cnan)).
Proof.
intros xl0 xl1 xu0 xu1.
unfold IeeeModel.interval_mid_rad_2, mid_core2, rad_core2, side. cbv zeta.
destruct_calls. reflexivity.
Qed.

(* A hypothesis of a case that does not apply. *)
Ltac absurd_case xl0 xl1 xu0 xu1 :=
  intros; exfalso;
  repeat match goal with
  | K : interval_empty_2 _ _ _ _ |- _ =>
      apply empty_2_xval in K; destruct K as [? [? ?]]
  | K : interval_bounded_2 _ _ _ _ |- _ => destruct K as [? ?]
  | K : finite xl0 |- _ => apply (fun F => xval_2_fin prec emax xl0 xl1 F) in K
  | K : finite xu0 |- _ => apply (fun F => xval_2_fin prec emax xu0 xu1 F) in K
  end; congruence.

(* interval_mid_rad_2, for a canonical interval, from precision 3: the generated statement
   (first, the midpoint is a canonical 2-limb value: two NaN for the empty set, a zero twice
   for the whole line, (+-Omega, +0) for a half-line, a normalized pair for a bounded
   interval), and that the midpoint of a bounded interval is a normalized pair, in the form the
   proof of interval_to_ball_2 uses. *)
Theorem interval_mid_rad_2_all :
  (3 <= prec)%Z ->
  forall xl0 xl1 xu0 xu1 : float, interval_2 xl0 xl1 xu0 xu1 ->
  let '(m0, m1, r) := interval_mid_rad_2 xl0 xl1 xu0 xu1 in
  (canonical_2 m0 m1 /\
   (interval_empty_2 xl0 xl1 xu0 xu1 -> nan m0 /\ nan m1 /\ nan r) /\
   (xval_2 xl0 xl1 = XInf true -> xval_2 xu0 xu1 = XInf false ->
    zero m0 /\ zero m1 /\ r = infinity prec emax false) /\
   (finite xl0 -> xval_2 xu0 xu1 = XInf false ->
    xval_2 m0 m1 = XFin (omega prec emax) /\ r = infinity prec emax false) /\
   (xval_2 xl0 xl1 = XInf true -> finite xu0 ->
    xval_2 m0 m1 = XFin (- omega prec emax) /\ r = infinity prec emax false) /\
   (interval_bounded_2 xl0 xl1 xu0 xu1 ->
    finite m0 /\ finite m1 /\
    (val xl0 + val xl1) <= (val m0 + val m1) <= (val xu0 + val xu1) /\
    Rabs ((val m0 + val m1) - ((val xl0 + val xl1) + (val xu0 + val xu1)) / 2)
    <= ((3 * (u prec ^ 2)) / (1 - (4 * u prec)))
       * Rabs (((val xl0 + val xl1) + (val xu0 + val xu1)) / 2)
       + (2 * eta (ieee_emin prec emax)) /\
    (r = infinity prec emax false \/
     (finite r /\
      (forall z : R, in_interval_2 xl0 xl1 xu0 xu1 z -> Rabs (z - (val m0 + val m1)) <= val r))) /\
    (Rabs (val xl0 + val xl1) <= bpow radix2 (emax - 2) ->
     Rabs (val xu0 + val xu1) <= bpow radix2 (emax - 2) -> finite r))) /\
  (interval_bounded_2 xl0 xl1 xu0 xu1 ->
   normalized_2 (ieee_emin prec emax) prec (val m0) (val m1)).
Proof.
intros Hp xl0 xl1 xu0 xu1 CX. assert (Hp2 : (2 <= prec)%Z) by lia.
rewrite interval_mid_rad_2_eq. cbv zeta.
destruct (tests_2 xl0 xu0) as [T1 [T2 T3]]. rewrite T1, T2, T3.
destruct (om_facts prec emax nan_opp) as [Fom [Eom [Fmo Emo]]].
assert (Ncnan : nan cnan) by exact (proj2_sig nan_const).
assert (O0 := Omega_gt_0 prec emax).
destruct (interval_2_cases xl0 xl1 xu0 xu1 CX)
  as [E|[N [[Wl [Wu [Wl0 Wu0]]]|[[Fl0 [Fl1 [Nl [Lu Lu0]]]]|[[Ul [Ul0 [Fu0 [Fu1 Nu]]]]|
        [Fl0 [Fl1 [Nl [Fu0 [Fu1 [Nu Hle]]]]]]]]]]].
- (* the empty set *)
  destruct (empty_2_xval _ _ _ _ E) as [Vl [Vu Vl0]].
  rewrite Vl0. cbn [xlt andb orb negb].
  match goal with |- context [mid_core2 ?a ?b ?c ?d] => destruct (mid_core2 a b c d) as [mc0 mc1] end.
  split; [|absurd_case xl0 xl1 xu0 xu1].
  split; [right; right; split; exact Ncnan|].
  split; [intros _; repeat split; exact Ncnan|].
  split; [absurd_case xl0 xl1 xu0 xu1|].
  split; [absurd_case xl0 xl1 xu0 xu1|].
  split; [absurd_case xl0 xl1 xu0 xu1|absurd_case xl0 xl1 xu0 xu1].
- (* the whole line *)
  rewrite Wl0, Wu0. cbn [xlt andb orb negb].
  match goal with |- context [mid_core2 ?a ?b ?c ?d] => destruct (mid_core2 a b c d) as [mc0 mc1] end.
  split; [|absurd_case xl0 xl1 xu0 xu1].
  split; [apply canonical_single; reflexivity|].
  split; [absurd_case xl0 xl1 xu0 xu1|].
  split; [intros _ _; split; [exists false; reflexivity|split; [exists false; reflexivity|reflexivity]]|].
  split; [absurd_case xl0 xl1 xu0 xu1|].
  split; [absurd_case xl0 xl1 xu0 xu1|absurd_case xl0 xl1 xu0 xu1].
- (* [l, +infinity] *)
  assert (Vl := xval_2_fin prec emax xl0 xl1 Fl0).
  rewrite (xval_fin prec emax xl0 Fl0), Lu0. cbn [xlt andb orb negb].
  rewrite (Rlt_bool_false (b2r xl0) (- Om)) by (generalize (b2r_Omega prec emax xl0); lra).
  cbn [andb orb].
  match goal with |- context [mid_core2 ?a ?b ?c ?d] => destruct (mid_core2 a b c d) as [mc0 mc1] end.
  split; [|absurd_case xl0 xl1 xu0 xu1].
  split; [exact (canonical_single _ Fom)|].
  split; [absurd_case xl0 xl1 xu0 xu1|].
  split; [absurd_case xl0 xl1 xu0 xu1|].
  split; [intros _ _; split; [|reflexivity]|].
  { rewrite (xval_2_fin prec emax _ _ Fom), Eom. change (b2r pzero) with 0.
    rewrite Rplus_0_r. reflexivity. }
  split; [absurd_case xl0 xl1 xu0 xu1|absurd_case xl0 xl1 xu0 xu1].
- (* [-infinity, h] *)
  assert (Vu := xval_2_fin prec emax xu0 xu1 Fu0).
  rewrite Ul0, (xval_fin prec emax xu0 Fu0). cbn [xlt andb orb negb].
  rewrite (Rlt_bool_false Om (b2r xu0)) by (generalize (b2r_Omega prec emax xu0); lra).
  cbn [andb orb].
  match goal with |- context [mid_core2 ?a ?b ?c ?d] => destruct (mid_core2 a b c d) as [mc0 mc1] end.
  split; [|absurd_case xl0 xl1 xu0 xu1].
  split; [exact (canonical_single _ Fmo)|].
  split; [absurd_case xl0 xl1 xu0 xu1|].
  split; [absurd_case xl0 xl1 xu0 xu1|].
  split; [absurd_case xl0 xl1 xu0 xu1|].
  split; [intros _ _; split; [|reflexivity]|absurd_case xl0 xl1 xu0 xu1].
  rewrite (xval_2_fin prec emax _ _ Fmo), Emo. change (b2r pzero) with 0.
  rewrite Rplus_0_r. reflexivity.
- (* a bounded interval *)
  assert (Vl := xval_2_fin prec emax xl0 xl1 Fl0).
  assert (Vu := xval_2_fin prec emax xu0 xu1 Fu0).
  rewrite (xval_fin prec emax xl0 Fl0), (xval_fin prec emax xu0 Fu0). cbn [xlt andb orb negb].
  rewrite (Rlt_bool_false (b2r xl0) (- Om)) by (generalize (b2r_Omega prec emax xl0); lra).
  rewrite (Rlt_bool_false Om (b2r xu0)) by (generalize (b2r_Omega prec emax xu0); lra).
  cbn [andb orb].
  generalize (mid_core2_bounded Hp xl0 xl1 xu0 xu1 Fl0 Fl1 Nl Fu0 Fu1 Nu Hle).
  destruct (mid_core2 xl0 xl1 xu0 xu1) as [mc0 mc1].
  intros [Fm0 [Fm1 [Nm [Bm Em]]]].
  assert (Cl := canonical_fin xl0 xl1 Fl0 Fl1 Nl).
  assert (Cu := canonical_fin xu0 xu1 Fu0 Fu1 Nu).
  assert (Cm := canonical_fin mc0 mc1 Fm0 Fm1 Nm).
  assert (RF := rad_core2_facts Hp xl0 xl1 xu0 xu1 mc0 mc1 Cl Cu Cm Bm).
  assert (Ht : 0 < u prec <= / 8) by exact (Ball2.u_bounds prec 3 Hp).
  split; [|intros _; exact Nm].
  split; [exact Cm|].
  split; [absurd_case xl0 xl1 xu0 xu1|].
  split; [absurd_case xl0 xl1 xu0 xu1|].
  split; [absurd_case xl0 xl1 xu0 xu1|].
  split; [absurd_case xl0 xl1 xu0 xu1|].
  intros _. split; [exact Fm0|split; [exact Fm1|split; [exact Bm|split; [|split]]]].
  + replace (3 * u prec ^ 2 / (1 - 4 * u prec)) with rel2 by (field; lra). exact Em.
  + destruct RF as [I|[Fr Cr]]; [left; exact I|right; split; [exact Fr|]].
    intros z [Hz1 Hz2]. rewrite Vl in Hz1. rewrite Vu in Hz2. cbn [xle] in Hz1, Hz2.
    apply Rle_bool_inv in Hz1. apply Rle_bool_inv in Hz2. apply Cr. lra.
  + intros Hl Hu.
    apply (rad_core2_small Hp xl0 xl1 xu0 xu1 mc0 mc1 Fl0 Fl1 Nl Fu0 Fu1 Nu Fm0 Fm1 Nm Bm Hl Hu).
    apply Rle_trans with (1 := Em).
    destruct (rel2_le Hp) as [R0 R1]. assert (TE := two_eta_le Hp).
    assert (T0 : 0 < QT) by apply bpow_gt_0.
    assert (Bmid : Rabs ((b2r xl0 + b2r xl1 + (b2r xu0 + b2r xu1)) / 2) <= QT).
    { unfold val in Hl, Hu. apply Rabs_le_inv in Hl. apply Rabs_le_inv in Hu. apply Rabs_le. lra. }
    assert (K : rel2 * Rabs ((b2r xl0 + b2r xl1 + (b2r xu0 + b2r xu1)) / 2) <= 3 / 32 * QT).
    { apply Rmult_le_compat; try lra. apply Rabs_pos. }
    lra.
Qed.

(** * interval_to_ball_2 *)

Theorem interval_to_ball_2_all :
  (3 <= prec)%Z ->
  forall xl0 xl1 xu0 xu1 : float, interval_2 xl0 xl1 xu0 xu1 ->
  let '(c0, c1, r) := interval_to_ball_2 xl0 xl1 xu0 xu1 in
  ball_2 c0 c1 r /\
  (ball_empty_2 c0 c1 r <-> interval_empty_2 xl0 xl1 xu0 xu1) /\
  (interval_nonempty_2 xl0 xl1 xu0 xu1 -> ~ interval_bounded_2 xl0 xl1 xu0 xu1 ->
   ball_whole_2 c0 c1 r) /\
  (interval_bounded_2 xl0 xl1 xu0 xu1 ->
   forall z : R, in_interval_2 xl0 xl1 xu0 xu1 z -> in_ball_2 c0 c1 r z) /\
  (interval_bounded_2 xl0 xl1 xu0 xu1 ->
   Rabs (val xl0 + val xl1) <= bpow radix2 (emax - 2) ->
   Rabs (val xu0 + val xu1) <= bpow radix2 (emax - 2) ->
   ball_finite_2 c0 c1 r /\
   (val xl0 + val xl1) <= (val c0 + val c1) <= (val xu0 + val xu1) /\
   Rabs ((val c0 + val c1) - ((val xl0 + val xl1) + (val xu0 + val xu1)) / 2)
   <= ((3 * (u prec ^ 2)) / (1 - (4 * u prec)))
      * Rabs (((val xl0 + val xl1) + (val xu0 + val xu1)) / 2)
      + (2 * eta (ieee_emin prec emax)) /\
   (forall z : R, in_interval_2 xl0 xl1 xu0 xu1 z -> Rabs (z - (val c0 + val c1)) <= val r)).
Proof.
intros Hp xl0 xl1 xu0 xu1 CX.
generalize (interval_mid_rad_2_all Hp xl0 xl1 xu0 xu1 CX).
unfold IeeeModel.interval_to_ball_2.
destruct (interval_mid_rad_2 xl0 xl1 xu0 xu1) as [[m0 m1] r]. cbv zeta.
intros [[_ [M1 [M2 [M3 [M4 M5]]]]] MN].
rewrite (eq_xval prec emax r pinf). change (xv pinf) with (XInf false).
assert (WholeZ : ball_2 pzero pzero (infinity prec emax false) /\
                 ~ ball_empty_2 pzero pzero (infinity prec emax false) /\
                 ball_whole_2 pzero pzero (infinity prec emax false)).
{ assert (W : ball_whole_2 pzero pzero (infinity prec emax false))
    by (split; [exists false; reflexivity|split; [exists false; reflexivity|reflexivity]]).
  split; [right; left; exact W|split; [intros [K _]; discriminate K|exact W]]. }
destruct WholeZ as [WB [WN WW]].
assert (Inf : xeq (xv (infinity prec emax false)) (XInf false) = true) by reflexivity.
(* an unbounded nonempty interval: the whole line *)
assert (Unb : interval_nonempty_2 xl0 xl1 xu0 xu1 -> ~ interval_bounded_2 xl0 xl1 xu0 xu1 ->
              r = infinity prec emax false ->
              let c0 := if xeq (xv r) (XInf false) then pzero else m0 in
              let c1 := if xeq (xv r) (XInf false) then pzero else m1 in
              ball_2 c0 c1 r /\
              (ball_empty_2 c0 c1 r <-> interval_empty_2 xl0 xl1 xu0 xu1) /\
              (interval_nonempty_2 xl0 xl1 xu0 xu1 -> ~ interval_bounded_2 xl0 xl1 xu0 xu1 ->
               ball_whole_2 c0 c1 r) /\
              (interval_bounded_2 xl0 xl1 xu0 xu1 ->
               forall z : R, in_interval_2 xl0 xl1 xu0 xu1 z -> in_ball_2 c0 c1 r z) /\
              (interval_bounded_2 xl0 xl1 xu0 xu1 ->
               Rabs (val xl0 + val xl1) <= bpow radix2 (emax - 2) ->
               Rabs (val xu0 + val xu1) <= bpow radix2 (emax - 2) ->
               ball_finite_2 c0 c1 r /\
               (val xl0 + val xl1) <= (val c0 + val c1) <= (val xu0 + val xu1) /\
               Rabs ((val c0 + val c1) - ((val xl0 + val xl1) + (val xu0 + val xu1)) / 2)
               <= ((3 * (u prec ^ 2)) / (1 - (4 * u prec)))
                  * Rabs (((val xl0 + val xl1) + (val xu0 + val xu1)) / 2)
                  + (2 * eta (ieee_emin prec emax)) /\
               (forall z : R, in_interval_2 xl0 xl1 xu0 xu1 z ->
                Rabs (z - (val c0 + val c1)) <= val r))).
{ intros N NB Er. subst r. cbv zeta. rewrite Inf.
  split; [exact WB|].
  split; [split; [intros K; elim (WN K)|intros K; elim (nonempty_not_empty_2 _ _ _ _ N K)]|].
  split; [intros _ _; exact WW|].
  split; [intros K; elim (NB K)|intros K; elim (NB K)]. }
cbv zeta in Unb.
destruct (interval_2_cases xl0 xl1 xu0 xu1 CX)
  as [E|[N [[Wl [Wu [Wl0 Wu0]]]|[[Fl0 [Fl1 [Nl [Lu Lu0]]]]|[[Ul [Ul0 [Fu0 [Fu1 Nu]]]]|
        [Fl0 [Fl1 [Nl [Fu0 [Fu1 [Nu Hle]]]]]]]]]]].
- (* the empty set: the empty ball *)
  destruct (M1 E) as [Nm0 [Nm1 Nr]]. rewrite (xval_nan prec emax r Nr). cbn [xeq].
  assert (BE : ball_empty_2 m0 m1 r) by exact (conj Nm0 (conj Nm1 Nr)).
  split; [right; right; exact BE|].
  split; [split; intros _; [exact E|exact BE]|].
  split; [intros N _; elim (nonempty_not_empty_2 _ _ _ _ N E)|].
  split; [absurd_case xl0 xl1 xu0 xu1|absurd_case xl0 xl1 xu0 xu1].
- apply (Unb N); [intro; absurd_case xl0 xl1 xu0 xu1|exact (proj2 (proj2 (M2 Wl Wu)))].
- apply (Unb N); [intro; absurd_case xl0 xl1 xu0 xu1|exact (proj2 (M3 Fl0 Lu))].
- apply (Unb N); [intro; absurd_case xl0 xl1 xu0 xu1|exact (proj2 (M4 Ul Fu0))].
- (* a bounded interval *)
  assert (BX : interval_bounded_2 xl0 xl1 xu0 xu1) by (split; assumption).
  destruct (M5 BX) as [Fm0 [Fm1 [Bm [Er [Rr Fin]]]]]. assert (Nm := MN BX).
  assert (Vl := xval_2_fin prec emax xl0 xl1 Fl0).
  assert (Vu := xval_2_fin prec emax xu0 xu1 Fu0).
  destruct Rr as [I|[Fr Cn]].
  + (* a radius +infinity: the whole line *)
    subst r. rewrite Inf.
    split; [exact WB|].
    split; [split; [intros K; elim (WN K)|intros K; elim (nonempty_not_empty_2 _ _ _ _ N K)]|].
    split; [intros _ _; exact WW|].
    split; [intros _ z _; left; exact WW|].
    intros _ Hl Hu. discriminate (Fin Hl Hu).
  + rewrite (xval_fin prec emax r Fr). cbn [xeq].
    assert (Ml : in_interval_2 xl0 xl1 xu0 xu1 (val xl0 + val xl1)).
    { split; [rewrite Vl|rewrite Vu]; cbn [xle]; apply Rle_bool_true; unfold val in *; lra. }
    assert (R0 : 0 <= val r).
    { apply Rle_trans with (2 := Cn _ Ml). apply Rabs_pos. }
    assert (BF : ball_finite_2 m0 m1 r)
      by (split; [exact Fm0|split; [exact Fm1|split; [exact Nm|split; [exact Fr|exact R0]]]]).
    split; [left; exact BF|].
    split; [split; [intros [K _]; unfold nan in K; rewrite (finite_not_nan prec emax m0 Fm0) in K;
                    discriminate K|intros K; elim (nonempty_not_empty_2 _ _ _ _ N K)]|].
    split; [intros _ K; elim (K BX)|].
    split; [intros _ z Hz; right; split; [exact BF|exact (Cn z Hz)]|].
    intros _ _ _. exact (conj BF (conj Bm (conj Er Cn))).
Qed.

(** * interval_split_2 *)

(* A real number moved into a nonempty interval of extended real numbers, by the two selects
   of the listing: a point of the interval. *)
Lemma xsplit_point :
  forall (a b : xreal) (v : R), xnonempty a b ->
  let n := if xlt (XFin v) a then a else XFin v in
  let p := if xlt b n then b else n in
  xnonempty a p /\ xnonempty p b.
Proof.
intros a b v [H1 [H2 H3]]. cbv zeta.
assert (Inf : forall x : R, xnonempty (XInf true) (XFin x) /\ xnonempty (XFin x) (XInf false)).
{ intros x. split; (split; [reflexivity|split; reflexivity]). }
destruct a as [|[|]|ra]; destruct b as [|[|]|rb]; cbn in H1, H2, H3;
  try discriminate H1; try discriminate H2; try discriminate H3; cbn [xlt negb andb].
- exact (Inf v).
- destruct (Rlt_bool_spec rb v) as [C|C].
  + split; [exact (proj1 (Inf rb))|apply xnonempty_fin; lra].
  + split; [exact (proj1 (Inf v))|apply xnonempty_fin; lra].
- destruct (Rlt_bool_spec v ra) as [C|C]; cbn [xlt negb andb].
  + split; [apply xnonempty_fin; lra|exact (proj2 (Inf ra))].
  + split; [apply xnonempty_fin; lra|exact (proj2 (Inf v))].
- apply Rle_bool_inv in H1.
  destruct (Rlt_bool_spec v ra) as [C|C]; cbn [xlt negb andb].
  + rewrite Rlt_bool_false by lra. split; apply xnonempty_fin; lra.
  + destruct (Rlt_bool_spec rb v) as [D|D]; split; apply xnonempty_fin; lra.
Qed.

(* The same on limbs: a canonical value with a finite leading limb, moved into a nonempty
   canonical interval by the two selects of lt_2_2. *)
Lemma split_point :
  forall xl0 xl1 xu0 xu1 m0 m1 : float,
  interval_nonempty_2 xl0 xl1 xu0 xu1 -> canonical_2 m0 m1 -> fin m0 ->
  let ka := lt_2_2 m0 m1 xl0 xl1 in
  let n0 := if ka then xl0 else m0 in
  let n1 := if ka then xl1 else m1 in
  let kb := lt_2_2 xu0 xu1 n0 n1 in
  let p0 := if kb then xu0 else n0 in
  let p1 := if kb then xu1 else n1 in
  interval_nonempty_2 xl0 xl1 p0 p1 /\ interval_nonempty_2 p0 p1 xu0 xu1.
Proof.
intros xl0 xl1 xu0 xu1 m0 m1 [Cl [Ch NE]] Cm Fm. cbv zeta.
assert (Hp1 : (1 <= prec)%Z) by (generalize prec_gt_0_; unfold Prec_gt_0; lia).
assert (Em := xval_2_fin prec emax m0 m1 Fm).
rewrite (lt_2_2_ext prec emax Hp1 m0 m1 xl0 xl1 Cm Cl), Em.
set (k1 := xlt (XFin (b2r m0 + b2r m1)) (xv2 xl0 xl1)).
assert (Cn : canonical_2 (if k1 then xl0 else m0) (if k1 then xl1 else m1))
  by (destruct k1; assumption).
assert (En : xv2 (if k1 then xl0 else m0) (if k1 then xl1 else m1)
             = if k1 then xv2 xl0 xl1 else XFin (b2r m0 + b2r m1))
  by (destruct k1; [reflexivity|exact Em]).
rewrite (lt_2_2_ext prec emax Hp1 xu0 xu1 _ _ Ch Cn), En.
set (k2 := xlt (xv2 xu0 xu1) (if k1 then xv2 xl0 xl1 else XFin (b2r m0 + b2r m1))).
assert (Cp : canonical_2 (if k2 then xu0 else if k1 then xl0 else m0)
                         (if k2 then xu1 else if k1 then xl1 else m1))
  by (destruct k2; assumption).
assert (Ep : xv2 (if k2 then xu0 else if k1 then xl0 else m0)
                 (if k2 then xu1 else if k1 then xl1 else m1)
             = if k2 then xv2 xu0 xu1
               else if k1 then xv2 xl0 xl1 else XFin (b2r m0 + b2r m1))
  by (destruct k2; [reflexivity|exact En]).
destruct (xsplit_point (xv2 xl0 xl1) (xv2 xu0 xu1) (b2r m0 + b2r m1) NE) as [A B].
fold k1 in A, B. fold k2 in A, B.
split.
- split; [exact Cl|split; [exact Cp|]]. rewrite Ep. exact A.
- split; [exact Cp|split; [exact Ch|]]. rewrite Ep. exact B.
Qed.

(* What the listing returns, with the core named. *)
Lemma interval_split_2_eq :
  forall xl0 xl1 xu0 xu1 : float,
  interval_split_2 xl0 xl1 xu0 xu1 =
  (let ml := flt xl0 (neg (fpred pinf)) in
   let mu := flt (fpred pinf) xu0 in
   let l0 := if ml then neg (fpred pinf) else xl0 in
   let l1 := if ml then pzero else xl1 in
   let h0 := if mu then fpred pinf else xu0 in
   let h1 := if mu then pzero else xu1 in
   let '(mc0, mc1) := mid_core2 l0 l1 h0 h1 in
   let m0 := if andb ml mu then pzero else if mu then fpred pinf
             else if ml then neg (fpred pinf) else mc0 in
   let m1 := if andb ml mu then pzero else if mu then pzero
             else if ml then pzero else mc1 in
   let ka := lt_2_2 m0 m1 xl0 xl1 in
   let n0 := if ka then xl0 else m0 in
   let n1 := if ka then xl1 else m1 in
   let kb := lt_2_2 xu0 xu1 n0 n1 in
   let p0 := if kb then xu0 else n0 in
   let p1 := if kb then xu1 else n1 in
   let ne := flt xl0 pinf in
   (xl0, xl1, if ne then p0 else neg pinf, if ne then p1 else pzero,
    if ne then p0 else pinf, if ne then p1 else pzero, xu0, xu1)).
Proof.
intros xl0 xl1 xu0 xu1.
unfold IeeeModel.interval_split_2, mid_core2. cbv zeta.
destruct_calls. reflexivity.
Qed.

Theorem interval_split_2_all :
  (3 <= prec)%Z ->
  forall xl0 xl1 xu0 xu1 : float, interval_2 xl0 xl1 xu0 xu1 ->
  let '(al0, al1, au0, au1, bl0, bl1, bu0, bu1) := interval_split_2 xl0 xl1 xu0 xu1 in
  interval_2 al0 al1 au0 au1 /\
  interval_2 bl0 bl1 bu0 bu1 /\
  (interval_empty_2 xl0 xl1 xu0 xu1 ->
   interval_empty_2 al0 al1 au0 au1 /\ interval_empty_2 bl0 bl1 bu0 bu1) /\
  (interval_nonempty_2 xl0 xl1 xu0 xu1 ->
   interval_nonempty_2 al0 al1 au0 au1 /\ interval_nonempty_2 bl0 bl1 bu0 bu1 /\
   xval_2 al0 al1 = xval_2 xl0 xl1 /\ xval_2 bu0 bu1 = xval_2 xu0 xu1 /\
   xval_2 au0 au1 = xval_2 bl0 bl1).
Proof.
intros Hp xl0 xl1 xu0 xu1 CX.
rewrite interval_split_2_eq. cbv zeta.
destruct (tests_2 xl0 xu0) as [T1 [T2 T3]]. rewrite T1, T2, T3.
destruct (om_facts prec emax nan_opp) as [Fom [Eom [Fmo Emo]]].
(* For a nonempty interval and a canonical selected midpoint m with a finite leading limb,
   the parts are [l, p] and [p, h], p the point of split_point. *)
assert (Parts : forall m0 m1 : float,
          interval_nonempty_2 xl0 xl1 xu0 xu1 -> canonical_2 m0 m1 -> fin m0 ->
          let ka := lt_2_2 m0 m1 xl0 xl1 in
          let n0 := if ka then xl0 else m0 in
          let n1 := if ka then xl1 else m1 in
          let kb := lt_2_2 xu0 xu1 n0 n1 in
          let p0 := if kb then xu0 else n0 in
          let p1 := if kb then xu1 else n1 in
          interval_2 xl0 xl1 p0 p1 /\
          interval_2 p0 p1 xu0 xu1 /\
          (interval_empty_2 xl0 xl1 xu0 xu1 ->
           interval_empty_2 xl0 xl1 p0 p1 /\ interval_empty_2 p0 p1 xu0 xu1) /\
          (interval_nonempty_2 xl0 xl1 xu0 xu1 ->
           interval_nonempty_2 xl0 xl1 p0 p1 /\ interval_nonempty_2 p0 p1 xu0 xu1 /\
           xval_2 xl0 xl1 = xval_2 xl0 xl1 /\ xval_2 xu0 xu1 = xval_2 xu0 xu1 /\
           xval_2 p0 p1 = xval_2 p0 p1)).
{ intros m0 m1 N Cm Fm. assert (SP := split_point xl0 xl1 xu0 xu1 m0 m1 N Cm Fm).
  cbv zeta in SP |- *. destruct SP as [A B].
  split; [right; exact A|split; [right; exact B|split]].
  - intros K. elim (nonempty_not_empty_2 _ _ _ _ N K).
  - intros _. split; [exact A|split; [exact B|split; [reflexivity|split; reflexivity]]]. }
cbv zeta in Parts.
destruct (interval_2_cases xl0 xl1 xu0 xu1 CX)
  as [E|[N [[Wl [Wu [Wl0 Wu0]]]|[[Fl0 [Fl1 [Nl [Lu Lu0]]]]|[[Ul [Ul0 [Fu0 [Fu1 Nu]]]]|
        [Fl0 [Fl1 [Nl [Fu0 [Fu1 [Nu Hle]]]]]]]]]]].
- (* the empty set: the empty set twice *)
  destruct (empty_2_xval _ _ _ _ E) as [Vl [Vu Vl0]].
  rewrite Vl0. cbn [xlt andb orb negb].
  match goal with |- context [mid_core2 ?a ?b ?c ?d] => destruct (mid_core2 a b c d) as [mc0 mc1] end.
  destruct E as [E0 [Z1 [E2 Z3]]].
  assert (Zp : zero pzero) by (exists false; reflexivity).
  assert (EA : interval_empty_2 xl0 xl1 (neg pinf) pzero)
    by (split; [exact E0|split; [exact Z1|split; [reflexivity|exact Zp]]]).
  assert (EB : interval_empty_2 pinf pzero xu0 xu1)
    by (split; [reflexivity|split; [exact Zp|split; [exact E2|exact Z3]]]).
  split; [left; exact EA|split; [left; exact EB|split; [intros _; split; assumption|]]].
  intros N. elim (nonempty_not_empty_2 _ _ _ _ N (conj E0 (conj Z1 (conj E2 Z3)))).
- (* the whole line: the midpoint 0 *)
  rewrite Wl0, Wu0. cbn [xlt andb orb negb].
  match goal with |- context [mid_core2 ?a ?b ?c ?d] => destruct (mid_core2 a b c d) as [mc0 mc1] end.
  exact (Parts pzero pzero N (canonical_single pzero eq_refl) eq_refl).
- (* [l, +infinity]: the midpoint Omega *)
  rewrite (xval_fin prec emax xl0 Fl0), Lu0. cbn [xlt andb orb negb].
  rewrite (Rlt_bool_false (b2r xl0) (- Om)) by (generalize (b2r_Omega prec emax xl0); lra).
  cbn [andb orb].
  match goal with |- context [mid_core2 ?a ?b ?c ?d] => destruct (mid_core2 a b c d) as [mc0 mc1] end.
  exact (Parts (fpred pinf) pzero N (canonical_single _ Fom) Fom).
- (* [-infinity, h]: the midpoint -Omega *)
  rewrite Ul0, (xval_fin prec emax xu0 Fu0). cbn [xlt andb orb negb].
  rewrite (Rlt_bool_false Om (b2r xu0)) by (generalize (b2r_Omega prec emax xu0); lra).
  cbn [andb orb].
  match goal with |- context [mid_core2 ?a ?b ?c ?d] => destruct (mid_core2 a b c d) as [mc0 mc1] end.
  exact (Parts (neg (fpred pinf)) pzero N (canonical_single _ Fmo) Fmo).
- (* a bounded interval: its midpoint, which is finite *)
  rewrite (xval_fin prec emax xl0 Fl0), (xval_fin prec emax xu0 Fu0). cbn [xlt andb orb negb].
  rewrite (Rlt_bool_false (b2r xl0) (- Om)) by (generalize (b2r_Omega prec emax xl0); lra).
  rewrite (Rlt_bool_false Om (b2r xu0)) by (generalize (b2r_Omega prec emax xu0); lra).
  cbn [andb orb].
  generalize (mid_core2_bounded Hp xl0 xl1 xu0 xu1 Fl0 Fl1 Nl Fu0 Fu1 Nu Hle).
  destruct (mid_core2 xl0 xl1 xu0 xu1) as [mc0 mc1].
  intros [Fm0 [Fm1 [Nm _]]].
  exact (Parts mc0 mc1 N (canonical_fin mc0 mc1 Fm0 Fm1 Nm) Fm0).
Qed.

End IeeeIntervalConvert2.

(** * The generated statements *)

Theorem interval_mid_rad_2_correct : interval_mid_rad_2_spec.
Proof.
intros prec emax Hp0 He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const Hp xl0 xl1 xu0 xu1 CX.
generalize (interval_mid_rad_2_all prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const
              Hp xl0 xl1 xu0 xu1 CX).
destruct (IeeeModel.interval_mid_rad_2 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma
            nan_const xl0 xl1 xu0 xu1) as [[m0 m1] r].
intros [K _]. exact K.
Qed.

Theorem interval_to_ball_2_correct : interval_to_ball_2_spec.
Proof.
intros prec emax Hp0 He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const Hp xl0 xl1 xu0 xu1 CX.
exact (interval_to_ball_2_all prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const
         Hp xl0 xl1 xu0 xu1 CX).
Qed.

Theorem interval_split_2_correct : interval_split_2_spec.
Proof.
intros prec emax Hp0 He nan_plus nan_minus nan_opp nan_fma Hp xl0 xl1 xu0 xu1 CX.
exact (interval_split_2_all prec emax nan_plus nan_minus nan_opp nan_fma Hp xl0 xl1 xu0 xu1 CX).
Qed.
