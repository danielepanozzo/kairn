(* Whether a ball with a center of two limbs contains a point of two limbs, in the IEEE model,
   on all values: ball_contains_point_2 (docs/developer/design/milestone2.md, "One enclosure
   interface" and "Comparisons"; docs/developer/architecture.md, "Claims of the enclosure
   interface: predicates and comparisons").

   Notation as in IeeeBallCompare2.v, which proves the other comparisons of balls of two limbs.
   (c, r) is the ball and t the point; (z, e) = add_ball_2_2 of t and -c; hi = radd(au, e) with
   au = abs_upper_2(z), an upper bound of |t - c|; lo = -add_up_1(e, -to_down_2(|z|)), a lower
   bound. The listing answers yes when hi <= r, and no when r < lo, or t is not a finite
   number, or r is a NaN. From precision 3.

   What is proved (ball_contains_point_2_correct, the generated statement): a yes only when t is
   finite and a member of the ball, a no only when it is not, never both; and when the ball is
   the empty set or the whole line, or t is not finite, each answer is given exactly when it is
   right.

   The proof, by the state of the ball (ball_contains_point_2_facts).

   - A finite ball. As for the other comparisons (IeeeBallCompare2.dist_2): a finite e means a
     finite canonical z within e of t - c, with t finite. A yes makes hi finite, since r is, and
     hi is at least au + e, at least |z| + e, at least |t - c|. A no by r < lo: lo is a number
     above r or +infinity, and it is not +infinity, because add_up_1 of a nonnegative e does
     not return -infinity (the rounding down of |z| is finite when z is: to_down_2_abs_fin);
     so lo is finite, at most |z| - e, at most |t - c| (lower_bound_2). A point that is not
     finite: yes is false, as above, and no is true by the test of the listing.

   - The empty ball. The radius is a NaN: hi <= r is false, and the listing answers no.

   - The whole line. r = +infinity and the center is (+-0, +-0). r < lo is false. For a finite
     t the answer must be yes, that is, hi must not be a NaN: add_2_2 of t and a pair of zeros
     is t itself, finite (IeeeAdd22Top.add_2_2_zero_right), its error bound e is finite
     (add_ball_radius_fin: the radius of add_ball_2_2 of any finite sum is), and radd of two
     values that are not NaN is not a NaN. For a t that is not finite the answer must not be
     yes, that is, hi must be a NaN: the leading limb of add_2_2 is a NaN
     (IeeeAdd22Top.add_2_2_lead_not_finite), so are abs_upper_2 of it and radd. *)
From Stdlib Require Import Reals ZArith Bool Lia Lra Psatz.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements IeeeStatements.
From Kairn Require Import Format Normalized EFT Directed2 IeeeBridge IeeeVocabulary IeeeOps IeeeExt.
From Kairn Require Import IeeeRange IeeeAdd22Top IeeeFull IeeeBallCores IeeeBallFinite.
From Kairn Require Import IeeeDirected IeeeEntry IeeeMake.
From Kairn Require Import IeeeIntervalVocabulary IeeeInterval1 IeeeInterval2.
From Kairn Require Import IeeeIntervalExact IeeeIntervalPredicates IeeeBallPredicates.
From Kairn Require Import IeeeBallPredicates2 IeeeBallCompare2.
From Kairn Require IeeeOperations.
From Kairn.Gen Require IeeeModel.
Open Scope R_scope.

Section BallContains2.
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
Notation rnd := (round radix2 fexp (Znearest tie_even)).
Notation fin x := (is_finite prec emax x = true).
Notation b2r := (B2R prec emax).
Notation neg := (IeeeOperations.neg prec emax nan_opp).
Notation fabs := (IeeeOperations.abs prec emax nan_abs).
Notation add := (IeeeOperations.add prec emax nan_plus).
Notation prod := (IeeeOperations.prod prec emax nan_fma).
Notation fma := (IeeeOperations.fma prec emax nan_fma).
Notation flt := (IeeeOperations.lt prec emax).
Notation fle := (IeeeOperations.le prec emax).
Notation fsucc := (IeeeOperations.succ prec emax).
Notation pzero := (IeeeOperations.pzero prec emax).
Notation pinf := (IeeeOperations.pinf prec emax).
Notation xv := (@xval prec emax).
Notation xv2 := (@xval_2 prec emax).
Notation Om := (Omega prec emax).
Notation radd := (IeeeModel.radd prec emax nan_plus).
Notation add_up_1 := (IeeeModel.add_up_1 prec emax nan_plus nan_minus nan_abs).
Notation to_down_2 := (IeeeModel.to_down_2 prec emax).
Notation abs_upper_2 := (IeeeModel.abs_upper_2 prec emax nan_opp).
Notation add_ball_2_2 := (IeeeModel.add_ball_2_2 prec emax nan_plus nan_minus nan_abs nan_fma).
Notation ball_contains_point_2 :=
  (IeeeModel.ball_contains_point_2 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma).

Let Hprec : (0 < prec)%Z.
Proof. exact prec_gt_0_. Qed.
Let Hemax : (prec < emax)%Z.
Proof. exact prec_lt_emax_. Qed.

(** * The radius of add_ball_2_2 *)

(* The error bound that add_ball_2_2 computes from a finite leading limb is finite: it is at
   most 2^(emax - 1), whatever the limb. *)
Lemma add_ball_radius_fin :
  (3 <= prec)%Z -> forall z0 : float, fin z0 ->
  fin (fma (prod (fabs z0) (IeeeModel.up_ball_add_2_0 prec emax))
           (IeeeModel.up_ball_add_1_1 prec emax) (IeeeModel.up_ball_add_1_2 prec emax)).
Proof.
intros Hp z0 Fz0. assert (Hp2 : (2 <= prec)%Z) by lia.
destruct (consts_ball_add_2 prec emax Hp) as [[FE [EE _]] [[FG [EG _]] [FH [EH _]]]].
destruct (E_add_2_le_eighth prec emax Hp) as [E0 E1].
destruct (G_3_le prec emax Hp2) as [G0 G1].
destruct (H_add_le_tiny prec emax Hp) as [H0 H1].
assert (P3 : 0 < bpow radix2 (emax - 3)) by apply bpow_gt_0.
assert (TOP : bpow radix2 emax = 8 * bpow radix2 (emax - 3)) by apply top_8.
assert (B4 : bpow radix2 (emax - 4) = / 2 * bpow radix2 (emax - 3)).
{ replace (emax - 4)%Z with (-1 + (emax - 3))%Z by ring. rewrite bpow_plus, pow2_m1. reflexivity. }
assert (B1 : bpow radix2 (emax - 1) = 4 * bpow radix2 (emax - 3)).
{ replace (emax - 1)%Z with (2 + (emax - 3))%Z by ring. rewrite bpow_plus, pow2_2. reflexivity. }
assert (Bz := b2r_le_Omega prec emax z0). assert (LT := Omega_lt_top prec emax).
assert (Faz : fin (fabs z0)) by (rewrite (abs_finite prec emax nan_abs); exact Fz0).
assert (Eaz : b2r (fabs z0) = Rabs (b2r z0)) by apply (abs_val prec emax nan_abs).
assert (Y0 : 0 <= Rabs (b2r z0) * Model.up_ball_add_2_0 emin prec)
  by (apply Rmult_le_pos; [apply Rabs_pos|lra]).
assert (Y1 : Rabs (b2r z0) * Model.up_ball_add_2_0 emin prec <= bpow radix2 (emax - 3)).
{ apply Rle_trans with (Rabs (b2r z0) * / 8);
    [apply Rmult_le_compat_l; [apply Rabs_pos|lra]|lra]. }
set (s := rnd (Rabs (b2r z0) * Model.up_ball_add_2_0 emin prec + 0)).
assert (S0 : 0 <= s) by (apply (rnd_pos prec emax); lra).
assert (S1 : s <= bpow radix2 (emax - 3)).
{ apply (rnd_le_format prec emax); [apply (IeeeBallFinite.format_bpow prec emax); lia|lra]. }
assert (It : IeeeBridge.inrange emax
               (rnd (b2r (fabs z0) * b2r (IeeeModel.up_ball_add_2_0 prec emax) + 0))).
{ rewrite Eaz, EE. fold s. unfold IeeeBridge.inrange. rewrite Rabs_pos_eq by exact S0. lra. }
destruct (prod_fin prec emax nan_fma _ _ Faz FE It) as [Ft Et].
rewrite Eaz, EE in Et. fold s in Et.
set (dr := rnd (s * Model.up_ball_add_1_1 emin prec + Model.up_ball_add_1_2 emin prec)).
assert (K0 : 0 <= s * Model.up_ball_add_1_1 emin prec) by (apply Rmult_le_pos; lra).
assert (K1 : s * Model.up_ball_add_1_1 emin prec <= bpow radix2 (emax - 3) * 2)
  by (apply Rmult_le_compat; lra).
assert (D0 : 0 <= dr) by (apply (rnd_pos prec emax); lra).
assert (D1 : dr <= bpow radix2 (emax - 1)).
{ apply (rnd_le_format prec emax); [apply (IeeeBallFinite.format_bpow prec emax); lia|lra]. }
assert (Id : IeeeBridge.inrange emax
               (rnd (b2r (prod (fabs z0) (IeeeModel.up_ball_add_2_0 prec emax))
                     * b2r (IeeeModel.up_ball_add_1_1 prec emax)
                     + b2r (IeeeModel.up_ball_add_1_2 prec emax)))).
{ rewrite Et, EG, EH. fold dr. unfold IeeeBridge.inrange. rewrite Rabs_pos_eq by exact D0. lra. }
exact (proj1 (fma_fin prec emax nan_fma _ _ _ Ft FG FH Id)).
Qed.

(** * A point against the whole line *)

(* A finite point and a center (+-0, +-0): the difference is finite and canonical, and its
   error bound is finite. *)
Lemma point_zero_center :
  (3 <= prec)%Z -> forall t0 t1 c0 c1 : float, canonical_2 t0 t1 ->
  let '(z0, z1, e) := add_ball_2_2 t0 t1 (neg c0) (neg c1) in
  fin t0 -> zero c0 -> zero c1 -> fin z0 /\ canonical_2 z0 z1 /\ fin e.
Proof.
intros Hp t0 t1 c0 c1 Ct.
generalize (fun F0 F1 N Z0 Z1 =>
              add_2_2_zero_right prec emax nan_plus nan_minus nan_opp nan_fma
                t0 t1 (neg c0) (neg c1) F0 F1 N Z0 Z1).
unfold IeeeModel.add_ball_2_2.
destruct (IeeeModel.add_2_2 prec emax nan_plus nan_minus t0 t1 (neg c0) (neg c1)) as [z0 z1].
cbv zeta. intros V Ft [s0 E0] [s1 E1]. subst c0 c1.
destruct (canonical_2_finite prec emax t0 t1 Ct Ft) as [Ft1 Nt].
assert (Z0 : zero (neg (B754_zero prec emax s0))) by (exists (negb s0); reflexivity).
assert (Z1 : zero (neg (B754_zero prec emax s1))) by (exists (negb s1); reflexivity).
destruct (V Ft Ft1 Nt Z0 Z1) as [Fz0 [Fz1 [Ez0 Ez1]]].
split; [exact Fz0|split; [|exact (add_ball_radius_fin Hp z0 Fz0)]].
left. split; [exact Fz0|split; [exact Fz1|]]. unfold val. rewrite Ez0, Ez1. exact Nt.
Qed.

(* A point whose leading limb is not finite and a center whose leading limb is: the leading
   limb of the difference is a NaN. *)
Lemma point_not_finite :
  forall t0 t1 c0 c1 : float,
  let '(z0, z1, e) := add_ball_2_2 t0 t1 (neg c0) (neg c1) in
  is_finite prec emax t0 = false -> fin c0 -> is_nan prec emax z0 = true.
Proof.
intros t0 t1 c0 c1.
generalize (add_2_2_lead_not_finite prec emax nan_plus nan_minus t0 t1 (neg c0) (neg c1)).
unfold IeeeModel.add_ball_2_2.
destruct (IeeeModel.add_2_2 prec emax nan_plus nan_minus t0 t1 (neg c0) (neg c1)) as [z0 z1].
cbv zeta. cbn [fst]. intros V Nt Fc. apply V; [exact Nt|].
rewrite (IeeeExt.neg_finite prec emax nan_opp). exact Fc.
Qed.

(** * NaN through abs_upper_2 and radd *)

Lemma abs_upper_2_nan :
  forall z0 z1 : float, is_nan prec emax z0 = true -> is_nan prec emax (abs_upper_2 z0 z1) = true.
Proof.
intros z0 z1 N. unfold IeeeModel.abs_upper_2, IeeeModel.abs_2, IeeeModel.to_up_2.
cbv beta iota zeta.
rewrite (lt_xval prec emax z0), (xval_nan prec emax z0 N). cbn [xlt].
destruct (flt pzero z1); [rewrite (succ_nan prec emax)|]; exact N.
Qed.

Lemma abs_upper_2_not_nan :
  forall z0 z1 : float, canonical_2 z0 z1 -> fin z0 ->
  is_nan prec emax (abs_upper_2 z0 z1) = false.
Proof.
intros z0 z1 C F.
assert (Hp1 : (1 <= prec)%Z) by (generalize prec_gt_0_; unfold Prec_gt_0; lia).
assert (E := abs_upper_2_ext prec emax nan_opp Hp1 z0 z1 C).
rewrite (xval_2_fin prec emax z0 z1 F) in E. unfold xabs, xround, overflow_of in E.
destruct (is_nan prec emax (abs_upper_2 z0 z1)) eqn:N; [|reflexivity].
rewrite (xval_nan prec emax _ N) in E. revert E.
match goal with |- context [Rlt_bool ?a ?b] => destruct (Rlt_bool a b) end;
  intros E; discriminate E.
Qed.

Lemma radd_nan_l :
  forall a b : float, is_nan prec emax a = true -> is_nan prec emax (radd a b) = true.
Proof.
intros a b N. unfold IeeeModel.radd. cbv zeta. rewrite (succ_nan prec emax).
apply (add_nan_l prec emax nan_plus). exact N.
Qed.

Lemma radd_not_nan :
  forall a b : float, nonneg_ext a -> nonneg_ext b ->
  is_nan prec emax a = false -> is_nan prec emax b = false ->
  is_nan prec emax (radd a b) = false.
Proof.
intros a b Na Nb Ha Hb. unfold IeeeModel.radd. cbv zeta. rewrite (succ_nan prec emax).
destruct (add_nonneg prec emax nan_plus a b Na Nb) as [_ [_ K]].
destruct (is_nan prec emax (add a b)) eqn:E; [|reflexivity].
destruct (proj1 K eq_refl) as [C|C]; congruence.
Qed.

Lemma lt_inf_l : forall x : float, flt (infinity prec emax false) x = false.
Proof.
intros x. rewrite (lt_xval prec emax). change (xv (infinity prec emax false)) with (XInf false).
destruct (xv x) as [|[|]|r]; reflexivity.
Qed.

(** * The lower bound of the distance *)

(* A rounding up of a real number, in the format with overflow, is not -infinity. *)
Lemma xru_fin_not_ninf : forall x : R, xru prec emax (XFin x) <> XInf true.
Proof.
intros x. rewrite (xru_real prec emax).
destruct (Rlt_bool Om x); [discriminate|]. destruct (Rlt_bool x (- Om)); discriminate.
Qed.

(* The magnitude of a finite canonical pair, as abs_2 returns it, and its rounding down: a
   finite number. *)
Lemma to_down_2_abs_fin :
  forall z0 z1 w0 w1 : float, canonical_2 z0 z1 -> fin z0 ->
  IeeeModel.abs_2 prec emax nan_opp z0 z1 = (w0, w1) ->
  canonical_2 w0 w1 /\ fin w0 /\ b2r w0 + b2r w1 = Rabs (b2r z0 + b2r z1) /\
  fin (to_down_2 w0 w1).
Proof.
intros z0 z1 w0 w1 Cz Fz0 Ew.
assert (Hp1 : (1 <= prec)%Z) by (generalize prec_gt_0_; unfold Prec_gt_0; lia).
generalize (abs_2_ext prec emax nan_opp Hp1 z0 z1 Cz). rewrite Ew. intros [Cw Ewv].
rewrite (xval_2_fin prec emax z0 z1 Fz0) in Ewv. cbn [xabs] in Ewv.
assert (Fw0 := xval_2_lead_fin prec emax w0 w1 _ Ewv).
rewrite (xval_2_fin prec emax w0 w1 Fw0) in Ewv. injection Ewv as Ewv.
split; [exact Cw|split; [exact Fw0|split; [exact Ewv|]]].
destruct (canonical_2_finite prec emax z0 z1 Cz Fz0) as [Fz1 Nz].
assert (B0 := b2r_le_Omega prec emax z0). assert (B1 := tail_le_half_U prec emax z0 z1 Nz).
assert (U0 : 0 < bpow radix2 (emax - prec)) by apply bpow_gt_0.
assert (Bz : Rabs (b2r z0 + b2r z1) < bpow radix2 emax).
{ apply Rle_lt_trans with (1 := Rabs_triang _ _). unfold IeeeBridge.Omega in B0. lra. }
assert (D0 : 0 <= RD emin prec (Rabs (b2r z0 + b2r z1))).
{ unfold RD. apply round_ge_generic; auto with typeclass_instances;
    [apply generic_format_0|apply Rabs_pos]. }
assert (D1 : RD emin prec (Rabs (b2r z0 + b2r z1)) <= Rabs (b2r z0 + b2r z1)).
{ unfold RD. destruct (round_DN_pt radix2 fexp (Rabs (b2r z0 + b2r z1))) as [_ [K _]]. exact K. }
assert (E : xv (to_down_2 w0 w1) = XFin (RD emin prec (Rabs (b2r z0 + b2r z1)))).
{ rewrite (to_down_2_ext prec emax Hp1 w0 w1 Cw), (xval_2_fin prec emax w0 w1 Fw0), Ewv.
  unfold xround, overflow_of. rewrite Rlt_bool_true; [reflexivity|].
  rewrite Rabs_pos_eq by exact D0. lra. }
exact (xval_fin_inv prec emax _ _ E).
Qed.

(* With (z, e) a finite canonical pair within e of a real number v whenever e is finite, and
   e nonnegative, +infinity or a NaN: a finite r below the lower bound that the listing
   computes is below |v|. *)
Lemma lower_bound_2 :
  (3 <= prec)%Z ->
  forall (v : R) (z0 z1 e : float), nonneg_ext e ->
  (fin e -> fin z0 /\ canonical_2 z0 z1 /\ Rabs (v - (b2r z0 + b2r z1)) <= b2r e) ->
  forall w0 w1 : float, IeeeModel.abs_2 prec emax nan_opp z0 z1 = (w0, w1) ->
  forall r : float, fin r ->
  flt r (neg (add_up_1 e (neg (to_down_2 w0 w1)))) = true ->
  b2r r < Rabs v.
Proof.
intros Hp v z0 z1 e Ne D w0 w1 Ew r Fr L. assert (Hp2 : (2 <= prec)%Z) by lia.
rewrite (lt_xval prec emax), (xval_fin prec emax r Fr), (xval_neg prec emax nan_opp) in L.
(* the directed sum is not -infinity *)
assert (NI : xv (add_up_1 e (neg (to_down_2 w0 w1))) <> XInf true).
{ destruct (finite_dec prec emax e) as [Fe|NFe].
  - destruct (D Fe) as [Fz0 [Cz _]].
    destruct (to_down_2_abs_fin z0 z1 w0 w1 Cz Fz0 Ew) as [_ [_ [_ Fwd]]].
    assert (Fnw : fin (neg (to_down_2 w0 w1)))
      by (rewrite (IeeeExt.neg_finite prec emax nan_opp); exact Fwd).
    rewrite (add_up_1_ieee_finite prec emax nan_plus nan_minus nan_abs Hp2 e _ Fe Fnw).
    apply xru_fin_not_ninf.
  - rewrite (add_up_1_ieee_nonfinite prec emax nan_plus nan_minus nan_abs e _ (or_introl NFe)).
    destruct Ne as [N|[I|[F _]]]; [| |congruence].
    + rewrite (xval_nan prec emax e N). cbn [xadd]. discriminate.
    + rewrite I. change (xv (infinity prec emax false)) with (XInf false).
      destruct (xv (neg (to_down_2 w0 w1))) as [|[|]|x]; cbn [xadd Bool.eqb]; discriminate. }
destruct (xval_cases prec emax (add_up_1 e (neg (to_down_2 w0 w1)))) as [[Ftl Etl]|[[s Etl]|Etl]];
  rewrite Etl in L; cbn [xopp xlt negb] in L.
- apply Rlt_bool_inv in L.
  destruct (add_up_1_ge prec emax nan_plus nan_minus nan_abs Hp2 _ _ Ftl) as [Fe [Fnw Lt]].
  rewrite (IeeeExt.neg_finite prec emax nan_opp) in Fnw.
  destruct (D Fe) as [Fz0 [Cz K]].
  destruct (to_down_2_abs_fin z0 z1 w0 w1 Cz Fz0 Ew) as [Cw [Fw0 [Ewv _]]].
  assert (Td := to_down_2_below prec emax w0 w1 Cw Fw0 Fnw). rewrite Ewv in Td.
  rewrite (IeeeExt.neg_value prec emax nan_opp) in Lt.
  generalize (Rabs_le_plus_err (b2r z0 + b2r z1) v).
  rewrite (Rabs_minus_sym (b2r z0 + b2r z1) v). lra.
- destruct s; [elim NI; exact Etl|discriminate L].
- discriminate L.
Qed.

(** * ball_contains_point_2 *)

Lemma ball_contains_point_2_facts :
  (3 <= prec)%Z ->
  forall c0 c1 r t0 t1 : float, ball_2 c0 c1 r -> canonical_2 t0 t1 ->
  let '(yes, no) := ball_contains_point_2 c0 c1 r t0 t1 in
  (yes = true -> fin t0 /\ in_ball_2 c0 c1 r (b2r t0 + b2r t1)) /\
  (no = true -> ~ (fin t0 /\ in_ball_2 c0 c1 r (b2r t0 + b2r t1))) /\
  (ball_empty_2 c0 c1 r \/ ball_whole_2 c0 c1 r \/ ~ fin t0 ->
   (fin t0 /\ in_ball_2 c0 c1 r (b2r t0 + b2r t1) -> yes = true) /\
   (~ (fin t0 /\ in_ball_2 c0 c1 r (b2r t0 + b2r t1)) -> no = true)).
Proof.
intros Hp c0 c1 r t0 t1 B Ct. assert (Hp2 : (2 <= prec)%Z) by lia.
assert (Cc := ball_2_canonical prec emax _ _ _ B).
generalize (dist_2 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma Hp t0 t1 c0 c1 Ct Cc)
           (point_zero_center Hp t0 t1 c0 c1 Ct)
           (point_not_finite t0 t1 c0 c1).
unfold IeeeModel.ball_contains_point_2. cbv zeta.
destruct (add_ball_2_2 t0 t1 (neg c0) (neg c1)) as [[z0 z1] e]. intros [Ne D] W1 W2.
destruct (IeeeModel.abs_2 prec emax nan_opp z0 z1) as [w0 w1] eqn:Ew. cbv beta iota.
rewrite (lt_abs_pinf prec emax nan_abs), (eq_self prec emax r).
set (hi := radd (abs_upper_2 z0 z1) e).
set (lo := neg (add_up_1 e (neg (to_down_2 w0 w1)))).
assert (Nau := abs_upper_2_any prec emax nan_opp z0 z1).
destruct (radd_ext prec emax nan_plus Hp2 (abs_upper_2 z0 z1) e Nau Ne) as [Nh Fh].
fold hi in Nh, Fh.
assert (DD : fin e -> fin z0 /\ canonical_2 z0 z1 /\
             Rabs ((b2r t0 + b2r t1) - (b2r c0 + b2r c1) - (b2r z0 + b2r z1)) <= b2r e).
{ intros Fe. destruct (D Fe) as [A1 [A2 [_ [_ A3]]]]. exact (conj A1 (conj A2 A3)). }
destruct (ball_2_states prec emax _ _ _ B) as [[BF [NW NE]]|[[BW [NF NE]]|[BE [NF NW]]]].
- (* a finite ball *)
  assert (Fr : fin r) by (destruct BF as [_ [_ [_ [K _]]]]; exact K).
  rewrite (finite_not_nan prec emax r Fr). cbn [negb]. rewrite andb_true_r.
  split; [|split].
  + intros Y. assert (FS := nonneg_le_fin prec emax _ _ Nh Y Fr).
    destruct (Fh FS) as [Fau [Fe [L _]]].
    destruct (D Fe) as [Fz0 [Cz [Ft0 [_ K]]]].
    assert (A := abs_upper_2_ge prec emax nan_opp z0 z1 Cz Fz0 Fau).
    rewrite (le_finite prec emax _ _ FS Fr) in Y. apply Rle_bool_inv in Y.
    split; [exact Ft0|right; split; [exact BF|]].
    assert (Tr := Rabs_triang ((b2r t0 + b2r t1) - (b2r c0 + b2r c1) - (b2r z0 + b2r z1))
                    (b2r z0 + b2r z1)).
    replace ((b2r t0 + b2r t1) - (b2r c0 + b2r c1) - (b2r z0 + b2r z1) + (b2r z0 + b2r z1))
      with ((b2r t0 + b2r t1) - (b2r c0 + b2r c1)) in Tr by ring.
    unfold val. fold hi in L. lra.
  + intros N [Ft0 IB]. apply orb_true_iff in N. destruct N as [N|N].
    * assert (LB := lower_bound_2 Hp _ z0 z1 e Ne DD w0 w1 Ew r Fr N).
      destruct IB as [W|[_ IB]]; [exact (NW W)|]. unfold val in IB. lra.
    * rewrite Ft0 in N. discriminate N.
  + intros [S|[S|S]]; [elim (NE S)|elim (NW S)|]. split.
    * intros [Ft0 _]. elim (S Ft0).
    * intros _. destruct (finite_dec prec emax t0) as [Ft|Nt]; [elim (S Ft)|].
      rewrite Nt. cbn [negb]. apply orb_true_r.
- (* the whole line *)
  assert (BW' := BW). destruct BW' as [Zc0 [Zc1 Er]]. subst r.
  change (is_nan prec emax (infinity prec emax false)) with false. cbn [negb].
  rewrite andb_true_r, lt_inf_l. cbn [orb].
  assert (Fc0 : fin c0) by (destruct Zc0 as [s0 E0]; rewrite E0; reflexivity).
  split; [|split].
  + intros Y. destruct (finite_dec prec emax t0) as [Ft0|Nt0].
    * split; [exact Ft0|left; exact BW].
    * exfalso. assert (Nz := W2 Nt0 Fc0).
      assert (Nh' : is_nan prec emax hi = true)
        by (apply radd_nan_l; apply abs_upper_2_nan; exact Nz).
      rewrite (le_xval prec emax), (xval_nan prec emax _ Nh') in Y. discriminate Y.
  + intros N [Ft0 _]. rewrite Ft0 in N. discriminate N.
  + intros _. split.
    * intros [Ft0 _]. destruct (W1 Ft0 Zc0 Zc1) as [Fz0 [Cz Fe]].
      assert (NNh : is_nan prec emax hi = false).
      { apply radd_not_nan; [exact Nau|exact Ne|exact (abs_upper_2_not_nan z0 z1 Cz Fz0)|
                             exact (finite_not_nan prec emax e Fe)]. }
      rewrite (le_xval prec emax). change (xv (infinity prec emax false)) with (XInf false).
      destruct Nh as [N|[I|[F _]]].
      -- unfold nan in N. congruence.
      -- rewrite I. reflexivity.
      -- rewrite (xval_fin prec emax _ F). reflexivity.
    * intros NP. destruct (finite_dec prec emax t0) as [Ft|Nt].
      -- elim NP. split; [exact Ft|left; exact BW].
      -- rewrite Nt. reflexivity.
- (* the empty ball *)
  assert (Nr : is_nan prec emax r = true) by (destruct BE as [_ [_ K]]; exact K).
  rewrite Nr. cbn [negb]. rewrite andb_false_r. cbn [negb]. rewrite orb_true_r.
  assert (Y0 : fle hi r = false).
  { rewrite (le_xval prec emax), (xval_nan prec emax r Nr).
    destruct (xv hi) as [|[|]|x]; reflexivity. }
  rewrite Y0.
  assert (NP : ~ (fin t0 /\ in_ball_2 c0 c1 r (b2r t0 + b2r t1))).
  { intros [_ [W|[F _]]]; [exact (NW W)|exact (NF F)]. }
  split; [intros K; discriminate K|split; [intros _; exact NP|]].
  intros _. split; [intros K; elim (NP K)|intros _; reflexivity].
Qed.

End BallContains2.

(** * The generated statement *)

Theorem ball_contains_point_2_correct : ball_contains_point_2_spec.
Proof.
intros prec emax Hp0 He nan_plus nan_minus nan_opp nan_abs nan_fma Hp c0 c1 r t0 t1 B Ct.
generalize (ball_contains_point_2_facts prec emax nan_plus nan_minus nan_opp nan_abs nan_fma Hp
              c0 c1 r t0 t1 B Ct).
destruct (IeeeModel.ball_contains_point_2 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma
            c0 c1 r t0 t1) as [yes no].
intros [Y [N S]].
split; [exact Y|split; [exact N|split]].
- intros [A A']. exact (N A' (Y A)).
- intros Sp. destruct (S Sp) as [S1 S2]. split; [split; [exact Y|exact S1]|split; [exact N|exact S2]].
Qed.
