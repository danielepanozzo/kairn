(* The comparisons of balls with a center of two limbs, in the IEEE model, on all values
   (docs/developer/design/milestone2.md, "One enclosure interface" and "Comparisons";
   docs/developer/architecture.md, "Claims of the enclosure interface: predicates and
   comparisons"): ball_less_2 and ball_less_equal_2.

   Notation as in IeeeBallPredicates2.v. From precision 3.

   What is proved, for canonical balls X = (cx, rx) and Y = (cy, ry) (the theorems K_correct at
   the end are the generated statements): the answers are certain, a yes only when every member
   of X is below (at most) every member of Y and a no only when none is, never both; and on the
   special states (an empty ball or the whole line) both are false, which is exact there.

   The proofs. (z, e) = add_ball_2_2 of cy and -cx: when e is finite, so is z, and
   |(cy - cx) - z| <= e (dist_2, from add_ball_2_2_ieee_core of IeeeInterval2.v and
   add_ball_2_2_correct of Directed2.v). The lower bound dl = -RU(e - RD(z)) of cy - cx and the
   upper bound -ml = RU(RU(z) + e), and s = radd(rx, ry) >= rx + ry, are what the comparisons
   use, and each is checked finite by the listing before it answers; a radius that is +inf or
   NaN makes s +inf or NaN, and both answers false. *)
From Stdlib Require Import Reals ZArith Bool Lia Lra Psatz.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements IeeeStatements.
From Kairn Require Import Format Normalized EFT Directed2 IeeeBridge IeeeVocabulary IeeeOps IeeeExt.
From Kairn Require Import IeeeBallCores IeeeDirected IeeeEntry IeeeMake.
From Kairn Require Import IeeeIntervalVocabulary IeeeInterval1 IeeeInterval2.
From Kairn Require Import IeeeIntervalExact IeeeIntervalPredicates IeeeBallPredicates.
From Kairn Require Import IeeeBallPredicates2.
From Kairn Require IeeeOperations.
From Kairn.Gen Require IeeeModel.
Open Scope R_scope.

Section BallCompare2.
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
Notation prod := (IeeeOperations.prod prec emax nan_fma).
Notation fma := (IeeeOperations.fma prec emax nan_fma).
Notation flt := (IeeeOperations.lt prec emax).
Notation fle := (IeeeOperations.le prec emax).
Notation pzero := (IeeeOperations.pzero prec emax).
Notation pinf := (IeeeOperations.pinf prec emax).
Notation xv := (@xval prec emax).
Notation xv2 := (@xval_2 prec emax).
Notation radd := (IeeeModel.radd prec emax nan_plus).
Notation add_up_1 := (IeeeModel.add_up_1 prec emax nan_plus nan_minus nan_abs).
Notation to_up_2 := (IeeeModel.to_up_2 prec emax).
Notation to_down_2 := (IeeeModel.to_down_2 prec emax).
Notation add_ball_2_2 := (IeeeModel.add_ball_2_2 prec emax nan_plus nan_minus nan_abs nan_fma).

(** * The distance of two centers *)

(* (z, e) = add_ball_2_2 of x and -y: e is nonnegative, +inf or NaN; when it is finite, z is a
   finite canonical pair, x and y are finite, and z is within e of x - y. *)
Lemma dist_2 :
  (3 <= prec)%Z ->
  forall x0 x1 y0 y1 : float, canonical_2 x0 x1 -> canonical_2 y0 y1 ->
  let '(z0, z1, e) := add_ball_2_2 x0 x1 (neg y0) (neg y1) in
  nonneg_ext e /\
  (fin e -> fin z0 /\ canonical_2 z0 z1 /\ fin x0 /\ fin y0 /\
   Rabs ((b2r x0 + b2r x1) - (b2r y0 + b2r y1) - (b2r z0 + b2r z1)) <= b2r e).
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
unfold Model.add_ball_2_2. rewrite <- Ez. cbv beta iota zeta. intros [_ [Nz [_ D]]].
rewrite 2!(IeeeExt.neg_value prec emax nan_opp) in D.
assert (FY0 : fin y0) by (rewrite <- (IeeeExt.neg_finite prec emax nan_opp); exact G0).
split; [exact Fa|split; [left; exact (conj Fa (conj Fz1 Nz))|split; [exact F0|split; [exact FY0|]]]].
rewrite (Ed FE). eapply Rle_trans; [|apply Rle_refl].
replace (b2r x0 + b2r x1 - (b2r y0 + b2r y1) - (b2r z0 + b2r z1))
  with (b2r x0 + b2r x1 + (- b2r y0 + - b2r y1) - (b2r z0 + b2r z1)) by ring.
exact D.
Qed.

(** * The directed operations on finite values *)

Lemma add_up_1_ge :
  (2 <= prec)%Z -> forall a b : float, fin (add_up_1 a b) ->
  fin a /\ fin b /\ b2r a + b2r b <= b2r (add_up_1 a b).
Proof.
intros Hp a b F.
destruct (add_up_1_fin_inv prec emax nan_plus nan_minus nan_abs Hp a b F) as [Fa Fb].
split; [exact Fa|split; [exact Fb|]].
assert (E := add_up_1_ieee prec emax nan_plus nan_minus nan_abs Hp a b).
rewrite (xval_fin prec emax _ F), (xval_fin prec emax a Fa), (xval_fin prec emax b Fb) in E.
cbn [xadd] in E.
assert (K := xru_above prec emax (XFin (b2r a + b2r b)) (b2r a + b2r b)).
rewrite <- E in K. cbn [xle] in K. apply Rle_bool_inv. apply K. cbn. apply Rle_bool_true. lra.
Qed.

Lemma to_down_2_below :
  forall z0 z1 : float, canonical_2 z0 z1 -> fin z0 -> fin (to_down_2 z0 z1) ->
  b2r (to_down_2 z0 z1) <= b2r z0 + b2r z1.
Proof.
intros z0 z1 C F0 F.
assert (Hp1 : (1 <= prec)%Z) by (generalize prec_gt_0_; unfold Prec_gt_0; lia).
assert (E := to_down_2_ext prec emax Hp1 z0 z1 C).
rewrite (xval_fin prec emax _ F), (xval_2_fin prec emax z0 z1 F0) in E. cbn [xround] in E.
unfold overflow_of in E. revert E.
destruct (Rlt_bool (Rabs (RD emin prec (b2r z0 + b2r z1))) (bpow radix2 emax));
  intros E; [|discriminate E].
injection E as E. rewrite E. unfold RD.
destruct (round_DN_pt radix2 fexp (b2r z0 + b2r z1)) as [_ [K _]]. exact K.
Qed.

Lemma to_up_2_above :
  forall z0 z1 : float, canonical_2 z0 z1 -> fin z0 -> fin (to_up_2 z0 z1) ->
  b2r z0 + b2r z1 <= b2r (to_up_2 z0 z1).
Proof.
intros z0 z1 C F0 F.
assert (Hp1 : (1 <= prec)%Z) by (generalize prec_gt_0_; unfold Prec_gt_0; lia).
assert (E := to_up_2_ext prec emax Hp1 z0 z1 C).
rewrite (xval_fin prec emax _ F), (xval_2_fin prec emax z0 z1 F0) in E. cbn [xround] in E.
unfold overflow_of in E. revert E.
destruct (Rlt_bool (Rabs (RU emin prec (b2r z0 + b2r z1))) (bpow radix2 emax));
  intros E; [|discriminate E].
injection E as E. rewrite E. unfold RU.
destruct (round_UP_pt radix2 fexp (b2r z0 + b2r z1)) as [_ [K _]]. exact K.
Qed.

(* A value that is nonnegative, +inf or NaN, and below another or at most a finite one, is
   finite. *)
Lemma nonneg_lt_fin : forall s x : float, nonneg_ext s -> flt s x = true -> fin s.
Proof.
intros s x [N|[I|[F _]]] L; [| |exact F]; exfalso.
- rewrite (lt_xval prec emax), (xval_nan prec emax s N) in L. discriminate L.
- subst s. rewrite (lt_xval prec emax) in L. change (xv (infinity prec emax false)) with (XInf false) in L.
  destruct (xv x) as [|[|]|r]; discriminate L.
Qed.

Lemma nonneg_le_fin : forall s x : float, nonneg_ext s -> fle s x = true -> fin x -> fin s.
Proof.
intros s x [N|[I|[F _]]] L Fx; [| |exact F]; exfalso.
- rewrite (le_xval prec emax), (xval_nan prec emax s N) in L. discriminate L.
- subst s. rewrite (le_xval prec emax), (xval_fin prec emax x Fx) in L. discriminate L.
Qed.

(* The radius of a canonical ball is nonnegative, +inf or NaN; finite, it is that of a finite
   ball. *)
Lemma radius_2_nonneg :
  forall c0 c1 r : float, ball_2 c0 c1 r -> nonneg_ext r.
Proof.
intros c0 c1 r [[_ [_ [_ [Fr Pr]]]]|[[_ [_ Er]]|[_ [_ Nr]]]].
- right; right. split; assumption.
- right; left. exact Er.
- left. exact Nr.
Qed.

Lemma ball_2_fin_r : forall c0 c1 r : float, ball_2 c0 c1 r -> fin r -> ball_finite_2 c0 c1 r.
Proof.
intros c0 c1 r [F|[[_ [_ E]]|[_ [_ N]]]] Fr; [exact F| |]; exfalso.
- rewrite E in Fr. discriminate Fr.
- unfold nan in N. rewrite (finite_not_nan prec emax r Fr) in N. discriminate N.
Qed.

(** * ball_less_2 and ball_less_equal_2 *)

(* The bounds the two comparisons compute: with (z, e) the distance of the centers, a finite
   dl = -RU(e - RD(z)) is at most cy - cx, and a finite ml = -RU(RU(z) + e) is at most
   cx - cy. *)
Lemma bounds_dl_ml :
  (3 <= prec)%Z ->
  forall cx0 cx1 cy0 cy1 : float, canonical_2 cx0 cx1 -> canonical_2 cy0 cy1 ->
  let '(z0, z1, e) := add_ball_2_2 cy0 cy1 (neg cx0) (neg cx1) in
  (fin (neg (add_up_1 e (neg (to_down_2 z0 z1)))) ->
   b2r (neg (add_up_1 e (neg (to_down_2 z0 z1)))) <= (b2r cy0 + b2r cy1) - (b2r cx0 + b2r cx1)) /\
  (fin (neg (add_up_1 (to_up_2 z0 z1) e)) ->
   b2r (neg (add_up_1 (to_up_2 z0 z1) e)) <= (b2r cx0 + b2r cx1) - (b2r cy0 + b2r cy1)).
Proof.
intros Hp cx0 cx1 cy0 cy1 Cx Cy. assert (Hp2 : (2 <= prec)%Z) by lia.
generalize (dist_2 Hp cy0 cy1 cx0 cx1 Cy Cx).
destruct (add_ball_2_2 cy0 cy1 (neg cx0) (neg cx1)) as [[z0 z1] e]. intros [Ne D].
split.
- intros F. rewrite (IeeeExt.neg_finite prec emax nan_opp) in F.
  destruct (add_up_1_ge Hp2 _ _ F) as [Fe [Fnz L]].
  rewrite (IeeeExt.neg_finite prec emax nan_opp) in Fnz.
  destruct (D Fe) as [Fz0 [Cz [_ [_ K]]]].
  assert (T := to_down_2_below z0 z1 Cz Fz0 Fnz).
  rewrite (IeeeExt.neg_value prec emax nan_opp) in L |- *.
  apply Rabs_le_inv in K. lra.
- intros F. rewrite (IeeeExt.neg_finite prec emax nan_opp) in F.
  destruct (add_up_1_ge Hp2 _ _ F) as [Fzu [Fe L]].
  destruct (D Fe) as [Fz0 [Cz [_ [_ K]]]].
  assert (T := to_up_2_above z0 z1 Cz Fz0 Fzu).
  rewrite (IeeeExt.neg_value prec emax nan_opp).
  apply Rabs_le_inv in K. lra.
Qed.

(* The sum of the radii: nonnegative, +inf or NaN; finite, at least rx + ry with both finite. *)
Lemma radii_sum_2 :
  (2 <= prec)%Z ->
  forall cx0 cx1 rx cy0 cy1 ry : float, ball_2 cx0 cx1 rx -> ball_2 cy0 cy1 ry ->
  nonneg_ext (radd rx ry) /\
  (fin (radd rx ry) -> ball_finite_2 cx0 cx1 rx /\ ball_finite_2 cy0 cy1 ry /\
   b2r rx + b2r ry <= b2r (radd rx ry)).
Proof.
intros Hp cx0 cx1 rx cy0 cy1 ry BX BY.
destruct (radd_ext prec emax nan_plus Hp rx ry (radius_2_nonneg _ _ _ BX) (radius_2_nonneg _ _ _ BY))
  as [N F].
split; [exact N|]. intros Fs. destruct (F Fs) as [Fx [Fy [L _]]].
split; [exact (ball_2_fin_r _ _ _ BX Fx)|split; [exact (ball_2_fin_r _ _ _ BY Fy)|exact L]].
Qed.

Lemma ball_less_2_facts :
  (3 <= prec)%Z ->
  forall cx0 cx1 rx cy0 cy1 ry : float, ball_2 cx0 cx1 rx -> ball_2 cy0 cy1 ry ->
  let '(yes, no) := IeeeModel.ball_less_2 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma
                      cx0 cx1 rx cy0 cy1 ry in
  (yes = true -> ball_finite_2 cx0 cx1 rx /\ ball_finite_2 cy0 cy1 ry /\
   b2r rx + b2r ry < (b2r cy0 + b2r cy1) - (b2r cx0 + b2r cx1)) /\
  (no = true -> ball_finite_2 cx0 cx1 rx /\ ball_finite_2 cy0 cy1 ry /\
   b2r rx + b2r ry <= (b2r cx0 + b2r cx1) - (b2r cy0 + b2r cy1)) /\
  (is_finite prec emax rx = false \/ is_finite prec emax ry = false -> yes = false /\ no = false).
Proof.
intros Hp cx0 cx1 rx cy0 cy1 ry BX BY. assert (Hp2 : (2 <= prec)%Z) by lia.
generalize (bounds_dl_ml Hp cx0 cx1 cy0 cy1 (ball_2_canonical prec emax _ _ _ BX)
              (ball_2_canonical prec emax _ _ _ BY)).
unfold IeeeModel.ball_less_2. cbv zeta.
destruct (add_ball_2_2 cy0 cy1 (neg cx0) (neg cx1)) as [[z0 z1] e]. intros [Bl Bm].
rewrite 3!(lt_abs_pinf prec emax nan_abs).
destruct (radii_sum_2 Hp2 _ _ _ _ _ _ BX BY) as [Ns Fs].
split; [|split].
- intros Y. apply andb_true_iff in Y. destruct Y as [L Fl].
  assert (FS := nonneg_lt_fin _ _ Ns L).
  destruct (Fs FS) as [FX [FY S]].
  assert (Fdl : fin (neg (add_up_1 e (neg (to_down_2 z0 z1))))) by exact Fl.
  assert (Dl := Bl Fdl).
  rewrite (lt_finite prec emax _ _ FS Fdl) in L. apply Rlt_bool_inv in L.
  split; [exact FX|split; [exact FY|lra]].
- intros N. apply andb_true_iff in N. destruct N as [N Fm]. apply andb_true_iff in N.
  destruct N as [L FS].
  destruct (Fs FS) as [FX [FY S]].
  assert (Dm := Bm Fm).
  rewrite (le_finite prec emax _ _ FS Fm) in L. apply Rle_bool_inv in L.
  split; [exact FX|split; [exact FY|lra]].
- intros H.
  assert (NF : is_finite prec emax (radd rx ry) = false).
  { destruct (finite_dec prec emax (radd rx ry)) as [K|K]; [|exact K].
    destruct (Fs K) as [[_ [_ [_ [Fx _]]]] [[_ [_ [_ [Fy _]]]] _]].
    unfold finite in Fx, Fy. destruct H as [H|H]; rewrite H in *; discriminate. }
  assert (LT : forall x : float, flt (radd rx ry) x = false).
  { intros x. destruct (flt (radd rx ry) x) eqn:K; [|reflexivity].
    rewrite (nonneg_lt_fin _ _ Ns K) in NF. discriminate NF. }
  rewrite LT, NF, andb_false_r. split; reflexivity.
Qed.

Lemma ball_less_equal_2_facts :
  (3 <= prec)%Z ->
  forall cx0 cx1 rx cy0 cy1 ry : float, ball_2 cx0 cx1 rx -> ball_2 cy0 cy1 ry ->
  let '(yes, no) := IeeeModel.ball_less_equal_2 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma
                      cx0 cx1 rx cy0 cy1 ry in
  (yes = true -> ball_finite_2 cx0 cx1 rx /\ ball_finite_2 cy0 cy1 ry /\
   b2r rx + b2r ry <= (b2r cy0 + b2r cy1) - (b2r cx0 + b2r cx1)) /\
  (no = true -> ball_finite_2 cx0 cx1 rx /\ ball_finite_2 cy0 cy1 ry /\
   b2r rx + b2r ry < (b2r cx0 + b2r cx1) - (b2r cy0 + b2r cy1)) /\
  (is_finite prec emax rx = false \/ is_finite prec emax ry = false -> yes = false /\ no = false).
Proof.
intros Hp cx0 cx1 rx cy0 cy1 ry BX BY. assert (Hp2 : (2 <= prec)%Z) by lia.
generalize (bounds_dl_ml Hp cx0 cx1 cy0 cy1 (ball_2_canonical prec emax _ _ _ BX)
              (ball_2_canonical prec emax _ _ _ BY)).
unfold IeeeModel.ball_less_equal_2. cbv zeta.
destruct (add_ball_2_2 cy0 cy1 (neg cx0) (neg cx1)) as [[z0 z1] e]. intros [Bl Bm].
rewrite 3!(lt_abs_pinf prec emax nan_abs).
destruct (radii_sum_2 Hp2 _ _ _ _ _ _ BX BY) as [Ns Fs].
split; [|split].
- intros Y. apply andb_true_iff in Y. destruct Y as [Y Fl]. apply andb_true_iff in Y.
  destruct Y as [L FS].
  destruct (Fs FS) as [FX [FY S]].
  assert (Dl := Bl Fl).
  rewrite (le_finite prec emax _ _ FS Fl) in L. apply Rle_bool_inv in L.
  split; [exact FX|split; [exact FY|lra]].
- intros N. apply andb_true_iff in N. destruct N as [L Fm].
  assert (FS := nonneg_lt_fin _ _ Ns L).
  destruct (Fs FS) as [FX [FY S]].
  assert (Dm := Bm Fm).
  rewrite (lt_finite prec emax _ _ FS Fm) in L. apply Rlt_bool_inv in L.
  split; [exact FX|split; [exact FY|lra]].
- intros H.
  assert (NF : is_finite prec emax (radd rx ry) = false).
  { destruct (finite_dec prec emax (radd rx ry)) as [K|K]; [|exact K].
    destruct (Fs K) as [[_ [_ [_ [Fx _]]]] [[_ [_ [_ [Fy _]]]] _]].
    unfold finite in Fx, Fy. destruct H as [H|H]; rewrite H in *; discriminate. }
  assert (LT : forall x : float, flt (radd rx ry) x = false).
  { intros x. destruct (flt (radd rx ry) x) eqn:K; [|reflexivity].
    rewrite (nonneg_lt_fin _ _ Ns K) in NF. discriminate NF. }
  rewrite LT, NF, andb_false_r. cbn [andb]. split; reflexivity.
Qed.

(** * The relations on the bounds of the balls *)

Lemma xlohi_2_cases :
  forall c0 c1 r : float, ball_2 c0 c1 r ->
  (fin r /\ xlo_2 prec emax c0 c1 r = XFin (b2r c0 + b2r c1 - b2r r) /\
   xhi_2 prec emax c0 c1 r = XFin (b2r c0 + b2r c1 + b2r r)) \/
  (xlo_2 prec emax c0 c1 r = XInf true /\ xhi_2 prec emax c0 c1 r = XInf false) \/
  (xlo_2 prec emax c0 c1 r = XInf false /\ xhi_2 prec emax c0 c1 r = XInf true).
Proof.
intros c0 c1 r [[_ [_ [_ [Fr _]]]]|[[_ [_ Er]]|[_ [_ Nr]]]].
- left. split; [exact Fr|exact (xlohi_2_fin prec emax c0 c1 r Fr)].
- right; left. subst r. exact (xlohi_2_whole prec emax c0 c1).
- right; right. exact (xlohi_2_nan prec emax c0 c1 r Nr).
Qed.

Lemma special_rels_2 :
  forall cx0 cx1 rx cy0 cy1 ry : float, ball_2 cx0 cx1 rx -> ball_2 cy0 cy1 ry ->
  is_finite prec emax rx = false \/ is_finite prec emax ry = false ->
  let a := xlo_2 prec emax cx0 cx1 rx in let b := xhi_2 prec emax cx0 cx1 rx in
  let c := xlo_2 prec emax cy0 cy1 ry in let d := xhi_2 prec emax cy0 cy1 ry in
  let ne := andb (xlt a (XInf false)) (xlt c (XInf false)) in
  andb (xlt b c) ne = false /\ andb (xle d a) ne = false /\
  andb (xle b c) ne = false /\ andb (xlt d a) ne = false /\
  andb (andb (xeq a b) (xeq b c)) (xeq c d) = false /\ andb (orb (xlt b c) (xlt d a)) ne = false.
Proof.
intros cx0 cx1 rx cy0 cy1 ry BX BY H. cbv zeta.
destruct (xlohi_2_cases cx0 cx1 rx BX) as [[Fx [Ea Eb]]|[[Ea Eb]|[Ea Eb]]];
destruct (xlohi_2_cases cy0 cy1 ry BY) as [[Fy [Ec Ed]]|[[Ec Ed]|[Ec Ed]]]; rewrite Ea, Eb, Ec, Ed;
  try (exfalso; destruct H as [K|K]; rewrite K in *; discriminate);
  cbn [xlt xle xeq andb orb negb Bool.eqb]; rewrite ?andb_false_r; repeat split.
Qed.

Lemma special_nonfin_2 :
  forall cx0 cx1 rx cy0 cy1 ry : float,
  ball_empty_2 cx0 cx1 rx \/ ball_whole_2 cx0 cx1 rx \/ ball_empty_2 cy0 cy1 ry \/ ball_whole_2 cy0 cy1 ry ->
  is_finite prec emax rx = false \/ is_finite prec emax ry = false.
Proof.
intros cx0 cx1 rx cy0 cy1 ry [[_ [_ N]]|[[_ [_ E]]|[[_ [_ N]]|[_ [_ E]]]]].
- left. exact (nan_not_finite prec emax rx N).
- left. rewrite E. reflexivity.
- right. exact (nan_not_finite prec emax ry N).
- right. rewrite E. reflexivity.
Qed.

(** * ball_contains_ball_2 and ball_equal_2 *)

(* The magnitude rounded up, abs_upper_2, of any pair is nonnegative, +inf or NaN; of a finite
   canonical pair, it is at least the magnitude. *)
Lemma abs_upper_2_any :
  forall z0 z1 : float, nonneg_ext (IeeeModel.abs_upper_2 prec emax nan_opp z0 z1).
Proof.
intros z0 z1. unfold IeeeModel.abs_upper_2, IeeeModel.abs_2, IeeeModel.to_up_2. cbv beta iota zeta.
assert (A : nonneg_ext (if flt z0 pzero then neg z0 else z0)).
{ rewrite (lt_xval prec emax). change (xv pzero) with (XFin 0).
  destruct (xval_cases prec emax z0) as [[F E]|[[s E]|E]]; rewrite E.
  - cbn [xlt]. destruct (Rlt_bool_spec (b2r z0) 0) as [L|L].
    + apply (nonneg_ext_finite prec emax); [rewrite (IeeeExt.neg_finite prec emax nan_opp); exact F|].
      rewrite (IeeeExt.neg_value prec emax nan_opp). lra.
    + apply (nonneg_ext_finite prec emax); [exact F|lra].
  - rewrite (xval_inf_inv prec emax z0 s E). destruct s; cbn [xlt].
    + right; left. reflexivity.
    + right; left. reflexivity.
  - cbn [xlt]. left. destruct (xval_cases prec emax z0) as [[F E']|[[s E']|E']];
      rewrite E' in E; try discriminate E.
    destruct (finite_dec prec emax z0) as [F|F].
    + rewrite (xval_fin prec emax z0 F) in E'. discriminate E'.
    + destruct (not_finite_cases prec emax z0 F) as [N|[s Es]]; [exact N|].
      subst z0. discriminate E'. }
destruct (flt pzero (if flt z0 pzero then neg z1 else z1)); [|exact A].
exact (proj1 (succ_nonneg prec emax _ A)).
Qed.

Lemma abs_upper_2_ge :
  forall z0 z1 : float, canonical_2 z0 z1 -> fin z0 ->
  fin (IeeeModel.abs_upper_2 prec emax nan_opp z0 z1) ->
  Rabs (b2r z0 + b2r z1) <= b2r (IeeeModel.abs_upper_2 prec emax nan_opp z0 z1).
Proof.
intros z0 z1 C F0 F.
assert (Hp1 : (1 <= prec)%Z) by (generalize prec_gt_0_; unfold Prec_gt_0; lia).
assert (E := abs_upper_2_ext prec emax nan_opp Hp1 z0 z1 C).
rewrite (xval_fin prec emax _ F), (xval_2_fin prec emax z0 z1 F0) in E. cbn [xabs xround] in E.
unfold overflow_of in E. revert E.
destruct (Rlt_bool (Rabs (RU emin prec (Rabs (b2r z0 + b2r z1)))) (bpow radix2 emax));
  intros E; [|discriminate E].
injection E as E. rewrite E. unfold RU.
destruct (round_UP_pt radix2 fexp (Rabs (b2r z0 + b2r z1))) as [_ [K _]]. exact K.
Qed.

Lemma ball_contains_ball_2_facts :
  (3 <= prec)%Z ->
  forall cx0 cx1 rx cy0 cy1 ry : float, ball_2 cx0 cx1 rx -> ball_2 cy0 cy1 ry ->
  let m := IeeeModel.ball_contains_ball_2 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma
             cx0 cx1 rx cy0 cy1 ry in
  (m = true -> rx = infinity prec emax false \/ is_nan prec emax ry = true \/
   (ball_finite_2 cx0 cx1 rx /\ ball_finite_2 cy0 cy1 ry /\
    Rabs ((b2r cy0 + b2r cy1) - (b2r cx0 + b2r cx1)) + b2r ry <= b2r rx)) /\
  (rx = infinity prec emax false -> m = true) /\
  (is_nan prec emax ry = true -> m = true) /\
  (is_nan prec emax rx = true -> is_nan prec emax ry = false -> m = false) /\
  (ry = infinity prec emax false -> fin rx -> m = false).
Proof.
intros Hp cx0 cx1 rx cy0 cy1 ry BX BY. assert (Hp2 : (2 <= prec)%Z) by lia. cbv zeta.
generalize (dist_2 Hp cy0 cy1 cx0 cx1 (ball_2_canonical prec emax _ _ _ BY)
              (ball_2_canonical prec emax _ _ _ BX)).
unfold IeeeModel.ball_contains_ball_2. cbv zeta.
destruct (add_ball_2_2 cy0 cy1 (neg cx0) (neg cx1)) as [[z0 z1] e]. intros [Ne D].
set (au := IeeeModel.abs_upper_2 prec emax nan_opp z0 z1).
set (hi := radd au e). set (s := radd hi ry).
destruct (radd_ext prec emax nan_plus Hp2 au e (abs_upper_2_any z0 z1) Ne) as [Nh Fh].
destruct (radd_ext prec emax nan_plus Hp2 hi ry Nh (radius_2_nonneg _ _ _ BY)) as [Ns Fs].
fold hi in Nh, Fh. fold s in Ns, Fs.
rewrite (eq_xval prec emax rx), (eq_self prec emax ry). change (xv pinf) with (XInf false).
split; [|split; [|split; [|split]]].
- intros M. apply orb_true_iff in M. destruct M as [M|M]; [apply orb_true_iff in M; destruct M as [M|M]|].
  + left. apply xeq_eq in M. exact (xval_inf_inv prec emax rx false M).
  + right; left. rewrite negb_involutive in M. exact M.
  + destruct (ball_2_states prec emax _ _ _ BX) as [[FX _]|[[WX _]|[EX _]]].
    * right; right. assert (FX' := FX). destruct FX' as [_ [_ [_ [Frx _]]]].
      assert (FS := nonneg_le_fin _ _ Ns M Frx).
      destruct (Fs FS) as [Fhi [Fry [L1 _]]].
      destruct (Fh Fhi) as [Fau [Fe [L2 _]]].
      destruct (D Fe) as [Fz0 [Cz [_ [_ K]]]].
      assert (A := abs_upper_2_ge z0 z1 Cz Fz0 Fau). fold au in A.
      rewrite (le_finite prec emax _ _ FS Frx) in M. apply Rle_bool_inv in M.
      split; [exact FX|split; [exact (ball_2_fin_r _ _ _ BY Fry)|]].
      assert (T := Rabs_triang ((b2r cy0 + b2r cy1) - (b2r cx0 + b2r cx1) - (b2r z0 + b2r z1))
                     (b2r z0 + b2r z1)).
      replace ((b2r cy0 + b2r cy1) - (b2r cx0 + b2r cx1) - (b2r z0 + b2r z1) + (b2r z0 + b2r z1))
        with ((b2r cy0 + b2r cy1) - (b2r cx0 + b2r cx1)) in T by ring.
      lra.
    * left. exact (proj2 (proj2 WX)).
    * exfalso. rewrite (le_xval prec emax), (xval_nan prec emax rx (proj2 (proj2 EX))) in M.
      destruct (xv s) as [|[|]|x]; discriminate M.
- intros E. rewrite E. reflexivity.
- intros N. rewrite N. cbn [negb]. rewrite orb_true_r. reflexivity.
- intros Nx Ny. rewrite (xval_nan prec emax rx Nx), Ny. cbn [xeq negb orb].
  rewrite (le_xval prec emax), (xval_nan prec emax rx Nx). destruct (xv s) as [|[|]|x]; reflexivity.
- intros E Frx. rewrite E. cbn [is_nan negb].
  rewrite (xval_fin prec emax rx Frx). cbn [xeq orb].
  destruct (fle s rx) eqn:L; [|reflexivity]. exfalso.
  destruct (Fs (nonneg_le_fin _ _ Ns L Frx)) as [_ [K _]]. rewrite E in K. discriminate K.
Qed.

Lemma ball_equal_2_facts :
  (3 <= prec)%Z ->
  forall cx0 cx1 rx cy0 cy1 ry : float, ball_2 cx0 cx1 rx -> ball_2 cy0 cy1 ry ->
  let '(yes, no) := IeeeModel.ball_equal_2 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma
                      cx0 cx1 rx cy0 cy1 ry in
  (yes = true -> ball_finite_2 cx0 cx1 rx /\ ball_finite_2 cy0 cy1 ry /\
   b2r rx = 0 /\ b2r ry = 0 /\ b2r cx0 + b2r cx1 = b2r cy0 + b2r cy1) /\
  (no = true -> ball_finite_2 cx0 cx1 rx /\ ball_finite_2 cy0 cy1 ry /\
   b2r rx + b2r ry < Rabs ((b2r cy0 + b2r cy1) - (b2r cx0 + b2r cx1))) /\
  (is_finite prec emax rx = false \/ is_finite prec emax ry = false -> yes = false /\ no = false).
Proof.
intros Hp cx0 cx1 rx cy0 cy1 ry BX BY. assert (Hp2 : (2 <= prec)%Z) by lia.
assert (Hp1 : (1 <= prec)%Z) by lia.
assert (Cx := ball_2_canonical prec emax _ _ _ BX). assert (Cy := ball_2_canonical prec emax _ _ _ BY).
generalize (dist_2 Hp cy0 cy1 cx0 cx1 Cy Cx).
unfold IeeeModel.ball_equal_2. cbv zeta.
rewrite (eq_2_2_ext prec emax Hp1 _ _ _ _ Cx Cy), 2!(eq_xval prec emax).
change (xv pzero) with (XFin 0).
destruct (add_ball_2_2 cy0 cy1 (neg cx0) (neg cx1)) as [[z0 z1] e]. intros [Ne D].
destruct (radii_sum_2 Hp2 _ _ _ _ _ _ BX BY) as [Ns Fs].
assert (W : forall w0 w1 : float, IeeeModel.abs_2 prec emax nan_opp z0 z1 = (w0, w1) ->
            fin (neg (add_up_1 e (neg (to_down_2 w0 w1)))) ->
            b2r (neg (add_up_1 e (neg (to_down_2 w0 w1))))
            <= Rabs ((b2r cy0 + b2r cy1) - (b2r cx0 + b2r cx1))).
{ intros w0 w1 Ew F. rewrite (IeeeExt.neg_finite prec emax nan_opp) in F.
  destruct (add_up_1_ge Hp2 _ _ F) as [Fe [Fnw L]].
  rewrite (IeeeExt.neg_finite prec emax nan_opp) in Fnw.
  destruct (D Fe) as [Fz0 [Cz [_ [_ K]]]].
  generalize (abs_2_ext prec emax nan_opp Hp1 z0 z1 Cz). rewrite Ew. intros [Cw Ewv].
  rewrite (xval_2_fin prec emax z0 z1 Fz0) in Ewv. cbn [xabs] in Ewv.
  assert (Fw0 := xval_2_lead_fin prec emax w0 w1 _ Ewv).
  rewrite (xval_2_fin prec emax w0 w1 Fw0) in Ewv. injection Ewv as Ewv.
  assert (T := to_down_2_below w0 w1 Cw Fw0 Fnw). rewrite Ewv in T.
  rewrite (IeeeExt.neg_value prec emax nan_opp) in L |- *.
  assert (T2 := Rabs_triang ((b2r cy0 + b2r cy1) - (b2r cx0 + b2r cx1) - (b2r z0 + b2r z1))
                  ((b2r cx0 + b2r cx1) - (b2r cy0 + b2r cy1))).
  replace ((b2r cy0 + b2r cy1) - (b2r cx0 + b2r cx1) - (b2r z0 + b2r z1)
           + ((b2r cx0 + b2r cx1) - (b2r cy0 + b2r cy1))) with (- (b2r z0 + b2r z1)) in T2 by ring.
  rewrite Rabs_Ropp in T2.
  replace (Rabs ((b2r cx0 + b2r cx1) - (b2r cy0 + b2r cy1)))
    with (Rabs ((b2r cy0 + b2r cy1) - (b2r cx0 + b2r cx1))) in T2
    by (rewrite <- Rabs_Ropp; f_equal; ring).
  lra. }
destruct (IeeeModel.abs_2 prec emax nan_opp z0 z1) as [w0 w1] eqn:Ew.
rewrite (lt_abs_pinf prec emax nan_abs).
split; [|split].
- intros Y. apply andb_true_iff in Y. destruct Y as [Y Ec]. apply andb_true_iff in Y.
  destruct Y as [Ea Eb]. apply xeq_eq in Ea. apply xeq_eq in Eb. apply xeq_eq in Ec.
  assert (Frx := xval_fin_inv prec emax _ _ Ea). assert (Fry := xval_fin_inv prec emax _ _ Eb).
  rewrite (xval_fin prec emax rx Frx) in Ea. rewrite (xval_fin prec emax ry Fry) in Eb.
  injection Ea as Ea. injection Eb as Eb.
  assert (FX := ball_2_fin_r _ _ _ BX Frx). assert (FY := ball_2_fin_r _ _ _ BY Fry).
  destruct FX as [Fx0 _]. destruct FY as [Fy0 _].
  rewrite (xval_2_fin prec emax cx0 cx1 Fx0), (xval_2_fin prec emax cy0 cy1 Fy0) in Ec.
  injection Ec as Ec.
  split; [exact (ball_2_fin_r _ _ _ BX Frx)|split; [exact (ball_2_fin_r _ _ _ BY Fry)|]].
  split; [exact Ea|split; [exact Eb|exact Ec]].
- intros N. apply andb_true_iff in N. destruct N as [L Fa].
  assert (FS := nonneg_lt_fin _ _ Ns L).
  destruct (Fs FS) as [FX [FY S]].
  assert (Da := W w0 w1 eq_refl Fa).
  rewrite (lt_finite prec emax _ _ FS Fa) in L. apply Rlt_bool_inv in L.
  split; [exact FX|split; [exact FY|lra]].
- intros H.
  assert (NF : is_finite prec emax (radd rx ry) = false).
  { destruct (finite_dec prec emax (radd rx ry)) as [K|K]; [|exact K].
    destruct (Fs K) as [[_ [_ [_ [Fx _]]]] [[_ [_ [_ [Fy _]]]] _]].
    unfold finite in Fx, Fy. destruct H as [H|H]; rewrite H in *; discriminate. }
  assert (LT : forall x : float, flt (radd rx ry) x = false).
  { intros x. destruct (flt (radd rx ry) x) eqn:K; [|reflexivity].
    rewrite (nonneg_lt_fin _ _ Ns K) in NF. discriminate NF. }
  rewrite LT. split; [|reflexivity].
  destruct (ball_2_states prec emax _ _ _ BX) as [[[_ [_ [_ [Fx _]]]] _]|[[[_ [_ Ex]] _]|[[_ [_ Nx]] _]]];
  destruct (ball_2_states prec emax _ _ _ BY) as [[[_ [_ [_ [Fy _]]]] _]|[[[_ [_ Ey]] _]|[[_ [_ Ny]] _]]];
    try (exfalso; unfold finite in Fx, Fy; destruct H as [K|K]; rewrite K in *; discriminate);
    rewrite ?Ex, ?Ey, ?(xval_nan prec emax rx Nx), ?(xval_nan prec emax ry Ny);
    change (xv (infinity prec emax false)) with (XInf false);
    cbn [xeq Bool.eqb andb]; rewrite ?andb_false_r; reflexivity.
Qed.

End BallCompare2.

(** * The generated statements *)

(* A certain three-valued comparison: certain answers that exclude each other, exact on S. *)
Lemma trit_certain :
  forall (yes no : bool) (R N S : Prop),
  ~ (R /\ N) -> (yes = true -> R) -> (no = true -> N) ->
  (S -> (yes = true <-> R) /\ (no = true <-> N)) ->
  (yes = true -> R) /\ (no = true -> N) /\ ~ (yes = true /\ no = true) /\
  (S -> (yes = true <-> R) /\ (no = true <-> N)).
Proof.
intros yes no R N S RN Y M HS. split; [exact Y|split; [exact M|split; [|exact HS]]].
intros [A B]. apply RN. split; [apply Y, A|apply M, B].
Qed.

Ltac compare_2_tail LY LN :=
  let A := fresh in let B := fresh in let NX := fresh in let NY := fresh in
  let x := fresh in let y := fresh in let Hx := fresh in let Hy := fresh in
  intros [A B]; apply LY in A; apply LN in B; destruct A as [NX [NY A]];
  destruct B as [_ [_ B]];
  destruct (xnonempty_member _ _ NX) as [x Hx]; destruct (xnonempty_member _ _ NY) as [y Hy];
  exact (B x y Hx Hy (A x y Hx Hy)).

Theorem ball_less_2_correct : ball_less_2_spec.
Proof.
intros prec emax Hp0 He nan_plus nan_minus nan_opp nan_abs nan_fma Hp cx0 cx1 rx cy0 cy1 ry BX BY.
destruct (xball_2 prec emax cx0 cx1 rx BX) as [IX [NX MX]].
destruct (xball_2 prec emax cy0 cy1 ry BY) as [IY [NY MY]].
assert (EY : (~ ball_empty_2 cx0 cx1 rx /\ ~ ball_empty_2 cy0 cy1 ry /\
              (forall x y : R, in_ball_2 cx0 cx1 rx x -> in_ball_2 cy0 cy1 ry y -> x < y)) <->
             (xnonempty (xlo_2 prec emax cx0 cx1 rx) (xhi_2 prec emax cx0 cx1 rx) /\
              xnonempty (xlo_2 prec emax cy0 cy1 ry) (xhi_2 prec emax cy0 cy1 ry) /\
              (forall x y : R, xmember (xlo_2 prec emax cx0 cx1 rx) (xhi_2 prec emax cx0 cx1 rx) x ->
               xmember (xlo_2 prec emax cy0 cy1 ry) (xhi_2 prec emax cy0 cy1 ry) y -> x < y))).
{ rewrite NX, NY. setoid_rewrite MX. setoid_rewrite MY. tauto. }
assert (EN : (~ ball_empty_2 cx0 cx1 rx /\ ~ ball_empty_2 cy0 cy1 ry /\
              (forall x y : R, in_ball_2 cx0 cx1 rx x -> in_ball_2 cy0 cy1 ry y -> ~ (x < y))) <->
             (xnonempty (xlo_2 prec emax cx0 cx1 rx) (xhi_2 prec emax cx0 cx1 rx) /\
              xnonempty (xlo_2 prec emax cy0 cy1 ry) (xhi_2 prec emax cy0 cy1 ry) /\
              (forall x y : R, xmember (xlo_2 prec emax cx0 cx1 rx) (xhi_2 prec emax cx0 cx1 rx) x ->
               xmember (xlo_2 prec emax cy0 cy1 ry) (xhi_2 prec emax cy0 cy1 ry) y -> ~ (x < y)))).
{ rewrite NX, NY. setoid_rewrite MX. setoid_rewrite MY. tauto. }
destruct (xless _ _ _ _ IX IY) as [LY LN].
generalize (ball_less_2_facts prec emax nan_plus nan_minus nan_opp nan_abs nan_fma Hp
              cx0 cx1 rx cy0 cy1 ry BX BY).
destruct (IeeeModel.ball_less_2 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma
            cx0 cx1 rx cy0 cy1 ry) as [yes no].
intros [HY [HN HS]].
rewrite EY, EN, <- LY, <- LN.
apply trit_certain.
- compare_2_tail LY LN.
- intros K. destruct (HY K) as [[_ [_ [_ [Fx _]]]] [[_ [_ [_ [Fy _]]]] L]].
  destruct (xlohi_2_fin prec emax cx0 cx1 rx Fx) as [Ea Eb].
  destruct (xlohi_2_fin prec emax cy0 cy1 ry Fy) as [Ec Ed].
  rewrite ?Ea, ?Eb, ?Ec, ?Ed. cbn [xlt andb negb]. rewrite ?andb_true_r. apply Rlt_bool_true. lra.
- intros K. destruct (HN K) as [[_ [_ [_ [Fx _]]]] [[_ [_ [_ [Fy _]]]] L]].
  destruct (xlohi_2_fin prec emax cx0 cx1 rx Fx) as [Ea Eb].
  destruct (xlohi_2_fin prec emax cy0 cy1 ry Fy) as [Ec Ed].
  rewrite ?Ea, ?Eb, ?Ec, ?Ed. cbn [xle xlt andb negb]. rewrite ?andb_true_r. apply Rle_bool_true. lra.
- intros S. assert (H := special_nonfin_2 prec emax _ _ _ _ _ _ S).
  destruct (HS H) as [Y N].
  destruct (special_rels_2 prec emax _ _ _ _ _ _ BX BY H) as [R1 [R2 _]]. cbv zeta in R1, R2.
  rewrite Y, N, R1, R2. split; split; intros K; discriminate K.
Qed.

Theorem ball_less_equal_2_correct : ball_less_equal_2_spec.
Proof.
intros prec emax Hp0 He nan_plus nan_minus nan_opp nan_abs nan_fma Hp cx0 cx1 rx cy0 cy1 ry BX BY.
destruct (xball_2 prec emax cx0 cx1 rx BX) as [IX [NX MX]].
destruct (xball_2 prec emax cy0 cy1 ry BY) as [IY [NY MY]].
assert (EY : (~ ball_empty_2 cx0 cx1 rx /\ ~ ball_empty_2 cy0 cy1 ry /\
              (forall x y : R, in_ball_2 cx0 cx1 rx x -> in_ball_2 cy0 cy1 ry y -> x <= y)) <->
             (xnonempty (xlo_2 prec emax cx0 cx1 rx) (xhi_2 prec emax cx0 cx1 rx) /\
              xnonempty (xlo_2 prec emax cy0 cy1 ry) (xhi_2 prec emax cy0 cy1 ry) /\
              (forall x y : R, xmember (xlo_2 prec emax cx0 cx1 rx) (xhi_2 prec emax cx0 cx1 rx) x ->
               xmember (xlo_2 prec emax cy0 cy1 ry) (xhi_2 prec emax cy0 cy1 ry) y -> x <= y))).
{ rewrite NX, NY. setoid_rewrite MX. setoid_rewrite MY. tauto. }
assert (EN : (~ ball_empty_2 cx0 cx1 rx /\ ~ ball_empty_2 cy0 cy1 ry /\
              (forall x y : R, in_ball_2 cx0 cx1 rx x -> in_ball_2 cy0 cy1 ry y -> ~ (x <= y))) <->
             (xnonempty (xlo_2 prec emax cx0 cx1 rx) (xhi_2 prec emax cx0 cx1 rx) /\
              xnonempty (xlo_2 prec emax cy0 cy1 ry) (xhi_2 prec emax cy0 cy1 ry) /\
              (forall x y : R, xmember (xlo_2 prec emax cx0 cx1 rx) (xhi_2 prec emax cx0 cx1 rx) x ->
               xmember (xlo_2 prec emax cy0 cy1 ry) (xhi_2 prec emax cy0 cy1 ry) y -> ~ (x <= y)))).
{ rewrite NX, NY. setoid_rewrite MX. setoid_rewrite MY. tauto. }
destruct (xless_equal _ _ _ _ IX IY) as [LY LN].
generalize (ball_less_equal_2_facts prec emax nan_plus nan_minus nan_opp nan_abs nan_fma Hp
              cx0 cx1 rx cy0 cy1 ry BX BY).
destruct (IeeeModel.ball_less_equal_2 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma
            cx0 cx1 rx cy0 cy1 ry) as [yes no].
intros [HY [HN HS]].
rewrite EY, EN, <- LY, <- LN.
apply trit_certain.
- compare_2_tail LY LN.
- intros K. destruct (HY K) as [[_ [_ [_ [Fx _]]]] [[_ [_ [_ [Fy _]]]] L]].
  destruct (xlohi_2_fin prec emax cx0 cx1 rx Fx) as [Ea Eb].
  destruct (xlohi_2_fin prec emax cy0 cy1 ry Fy) as [Ec Ed].
  rewrite ?Ea, ?Eb, ?Ec, ?Ed. cbn [xle xlt andb negb]. rewrite ?andb_true_r. apply Rle_bool_true. lra.
- intros K. destruct (HN K) as [[_ [_ [_ [Fx _]]]] [[_ [_ [_ [Fy _]]]] L]].
  destruct (xlohi_2_fin prec emax cx0 cx1 rx Fx) as [Ea Eb].
  destruct (xlohi_2_fin prec emax cy0 cy1 ry Fy) as [Ec Ed].
  rewrite ?Ea, ?Eb, ?Ec, ?Ed. cbn [xlt andb negb]. rewrite ?andb_true_r. apply Rlt_bool_true. lra.
- intros S. assert (H := special_nonfin_2 prec emax _ _ _ _ _ _ S).
  destruct (HS H) as [Y N].
  destruct (special_rels_2 prec emax _ _ _ _ _ _ BX BY H) as [_ [_ [R3 [R4 _]]]]. cbv zeta in R3, R4.
  rewrite Y, N, R3, R4. split; split; intros K; discriminate K.
Qed.

Theorem ball_contains_ball_2_correct : ball_contains_ball_2_spec.
Proof.
intros prec emax Hp0 He nan_plus nan_minus nan_opp nan_abs nan_fma Hp cx0 cx1 rx cy0 cy1 ry BX BY.
cbv zeta.
destruct (xball_2 prec emax cx0 cx1 rx BX) as [IX [_ MX]].
destruct (xball_2 prec emax cy0 cy1 ry BY) as [IY [_ MY]].
assert (ER : (forall z : R, in_ball_2 cy0 cy1 ry z -> in_ball_2 cx0 cx1 rx z) <->
             andb (xle (xlo_2 prec emax cx0 cx1 rx) (xlo_2 prec emax cy0 cy1 ry))
                  (xle (xhi_2 prec emax cy0 cy1 ry) (xhi_2 prec emax cx0 cx1 rx)) = true).
{ setoid_rewrite MX. setoid_rewrite MY. symmetry. exact (xsubset _ _ _ _ IY IX). }
rewrite ER.
destruct (ball_contains_ball_2_facts prec emax nan_plus nan_minus nan_opp nan_abs nan_fma Hp
            cx0 cx1 rx cy0 cy1 ry BX BY) as [M1 [M2 [M3 [M4 M5]]]].
split.
- intros K. destruct (M1 K) as [E|[E|[FX [FY L]]]].
  + rewrite E. destruct (xlohi_2_whole prec emax cx0 cx1) as [Ea Eb]. rewrite Ea, Eb.
    destruct (xlohi_2_cases prec emax cy0 cy1 ry BY) as [[_ [Ec Ed]]|[[Ec Ed]|[Ec Ed]]];
      rewrite Ec, Ed; reflexivity.
  + destruct (xlohi_2_nan prec emax cy0 cy1 ry E) as [Ec Ed]. rewrite Ec, Ed.
    destruct (xlohi_2_cases prec emax cx0 cx1 rx BX) as [[_ [Ea Eb]]|[[Ea Eb]|[Ea Eb]]];
      rewrite Ea, Eb; reflexivity.
  + destruct FX as [_ [_ [_ [Fx Px]]]]. destruct FY as [_ [_ [_ [Fy Py]]]].
    destruct (xlohi_2_fin prec emax cx0 cx1 rx Fx) as [Ea Eb].
    destruct (xlohi_2_fin prec emax cy0 cy1 ry Fy) as [Ec Ed].
    rewrite Ea, Eb, Ec, Ed. cbn [xle]. apply andb_true_iff.
    unfold val in Px, Py.
    set (dc := (B2R prec emax cy0 + B2R prec emax cy1) - (B2R prec emax cx0 + B2R prec emax cx1)) in L.
    assert (B := Rle_abs dc). assert (D := Rle_abs (- dc)). rewrite Rabs_Ropp in D.
    unfold dc in B, D, L. split; apply Rle_bool_true; lra.
- intros S.
  destruct (ball_2_states prec emax _ _ _ BX) as [[FX [NWX NEX]]|[[WX [NFX NEX]]|[EX [NFX NWX]]]];
  destruct (ball_2_states prec emax _ _ _ BY) as [[FY [NWY NEY]]|[[WY [NFY NEY]]|[EY [NFY NWY]]]];
  [exfalso; destruct S as [K|[K|[K|K]]]; auto| | | | | | | |].
  + (* X finite, Y whole *)
    destruct FX as [_ [_ [_ [Fx _]]]]. destruct WY as [_ [_ Ey]].
    rewrite (M5 Ey Fx). destruct (xlohi_2_fin prec emax cx0 cx1 rx Fx) as [Ea Eb].
    rewrite Ey, Ea, Eb. destruct (xlohi_2_whole prec emax cy0 cy1) as [Ec Ed]. rewrite Ec, Ed.
    reflexivity.
  + (* X finite, Y empty *)
    destruct FX as [_ [_ [_ [Fx _]]]]. destruct EY as [_ [_ Ny]].
    rewrite (M3 Ny). destruct (xlohi_2_fin prec emax cx0 cx1 rx Fx) as [Ea Eb].
    destruct (xlohi_2_nan prec emax cy0 cy1 ry Ny) as [Ec Ed]. rewrite Ea, Eb, Ec, Ed. reflexivity.
  + (* X whole, Y finite *)
    destruct WX as [_ [_ Ex]]. rewrite (M2 Ex), Ex.
    destruct (xlohi_2_whole prec emax cx0 cx1) as [Ea Eb]. rewrite Ea, Eb.
    destruct FY as [_ [_ [_ [Fy _]]]].
    destruct (xlohi_2_fin prec emax cy0 cy1 ry Fy) as [Ec Ed]. rewrite Ec, Ed. reflexivity.
  + (* X whole, Y whole *)
    destruct WX as [_ [_ Ex]]. rewrite (M2 Ex), Ex.
    destruct (xlohi_2_whole prec emax cx0 cx1) as [Ea Eb]. rewrite Ea, Eb.
    destruct WY as [_ [_ Ey]]. rewrite Ey.
    destruct (xlohi_2_whole prec emax cy0 cy1) as [Ec Ed]. rewrite Ec, Ed. reflexivity.
  + (* X whole, Y empty *)
    destruct WX as [_ [_ Ex]]. rewrite (M2 Ex), Ex.
    destruct (xlohi_2_whole prec emax cx0 cx1) as [Ea Eb]. rewrite Ea, Eb.
    destruct EY as [_ [_ Ny]].
    destruct (xlohi_2_nan prec emax cy0 cy1 ry Ny) as [Ec Ed]. rewrite Ec, Ed. reflexivity.
  + (* X empty, Y finite *)
    destruct EX as [_ [_ Nx]]. destruct FY as [_ [_ [_ [Fy _]]]].
    rewrite (M4 Nx (finite_not_nan prec emax ry Fy)).
    destruct (xlohi_2_nan prec emax cx0 cx1 rx Nx) as [Ea Eb].
    destruct (xlohi_2_fin prec emax cy0 cy1 ry Fy) as [Ec Ed]. rewrite Ea, Eb, Ec, Ed. reflexivity.
  + (* X empty, Y whole *)
    destruct EX as [_ [_ Nx]]. destruct WY as [_ [_ Ey]].
    assert (Ny : is_nan prec emax ry = false) by (rewrite Ey; reflexivity).
    rewrite (M4 Nx Ny), Ey.
    destruct (xlohi_2_nan prec emax cx0 cx1 rx Nx) as [Ea Eb].
    destruct (xlohi_2_whole prec emax cy0 cy1) as [Ec Ed]. rewrite Ea, Eb, Ec, Ed. reflexivity.
  + (* X empty, Y empty *)
    destruct EX as [_ [_ Nx]]. destruct EY as [_ [_ Ny]].
    rewrite (M3 Ny). destruct (xlohi_2_nan prec emax cx0 cx1 rx Nx) as [Ea Eb].
    destruct (xlohi_2_nan prec emax cy0 cy1 ry Ny) as [Ec Ed]. rewrite Ea, Eb, Ec, Ed. reflexivity.
Qed.

Theorem ball_equal_2_correct : ball_equal_2_spec.
Proof.
intros prec emax Hp0 He nan_plus nan_minus nan_opp nan_abs nan_fma Hp cx0 cx1 rx cy0 cy1 ry BX BY.
destruct (xball_2 prec emax cx0 cx1 rx BX) as [IX [NX MX]].
destruct (xball_2 prec emax cy0 cy1 ry BY) as [IY [NY MY]].
assert (EY : (~ ball_empty_2 cx0 cx1 rx /\ ~ ball_empty_2 cy0 cy1 ry /\
              (forall x y : R, in_ball_2 cx0 cx1 rx x -> in_ball_2 cy0 cy1 ry y -> x = y)) <->
             (xnonempty (xlo_2 prec emax cx0 cx1 rx) (xhi_2 prec emax cx0 cx1 rx) /\
              xnonempty (xlo_2 prec emax cy0 cy1 ry) (xhi_2 prec emax cy0 cy1 ry) /\
              (forall x y : R, xmember (xlo_2 prec emax cx0 cx1 rx) (xhi_2 prec emax cx0 cx1 rx) x ->
               xmember (xlo_2 prec emax cy0 cy1 ry) (xhi_2 prec emax cy0 cy1 ry) y -> x = y))).
{ rewrite NX, NY. setoid_rewrite MX. setoid_rewrite MY. tauto. }
assert (EN : (~ ball_empty_2 cx0 cx1 rx /\ ~ ball_empty_2 cy0 cy1 ry /\
              (forall x y : R, in_ball_2 cx0 cx1 rx x -> in_ball_2 cy0 cy1 ry y -> ~ (x = y))) <->
             (xnonempty (xlo_2 prec emax cx0 cx1 rx) (xhi_2 prec emax cx0 cx1 rx) /\
              xnonempty (xlo_2 prec emax cy0 cy1 ry) (xhi_2 prec emax cy0 cy1 ry) /\
              (forall x y : R, xmember (xlo_2 prec emax cx0 cx1 rx) (xhi_2 prec emax cx0 cx1 rx) x ->
               xmember (xlo_2 prec emax cy0 cy1 ry) (xhi_2 prec emax cy0 cy1 ry) y -> ~ (x = y)))).
{ rewrite NX, NY. setoid_rewrite MX. setoid_rewrite MY. tauto. }
destruct (xequal _ _ _ _ IX IY) as [LY LN].
generalize (ball_equal_2_facts prec emax nan_plus nan_minus nan_opp nan_abs nan_fma Hp
              cx0 cx1 rx cy0 cy1 ry BX BY).
destruct (IeeeModel.ball_equal_2 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma
            cx0 cx1 rx cy0 cy1 ry) as [yes no].
intros [HY [HN HS]].
rewrite EY, EN, <- LY, <- LN.
apply trit_certain.
- compare_2_tail LY LN.
- intros K. destruct (HY K) as [[_ [_ [_ [Fx _]]]] [[_ [_ [_ [Fy _]]]] [Ex [Ey Ec]]]].
  destruct (xlohi_2_fin prec emax cx0 cx1 rx Fx) as [Ea Eb].
  destruct (xlohi_2_fin prec emax cy0 cy1 ry Fy) as [Ec' Ed].
  rewrite Ea, Eb, Ec', Ed, Ex, Ey, Ec. cbn [xeq].
  rewrite !Req_bool_true by ring. reflexivity.
- intros K. destruct (HN K) as [[_ [_ [_ [Fx Px]]]] [[_ [_ [_ [Fy Py]]]] L]].
  destruct (xlohi_2_fin prec emax cx0 cx1 rx Fx) as [Ea Eb].
  destruct (xlohi_2_fin prec emax cy0 cy1 ry Fy) as [Ec Ed].
  rewrite Ea, Eb, Ec, Ed. cbn [xlt andb negb]. rewrite ?andb_true_r. apply orb_true_iff.
  unfold Rabs in L. destruct (Rcase_abs _) in L.
  + right. apply Rlt_bool_true. lra.
  + left. apply Rlt_bool_true. lra.
- intros S. assert (H := special_nonfin_2 prec emax _ _ _ _ _ _ S).
  destruct (HS H) as [Y N].
  destruct (special_rels_2 prec emax _ _ _ _ _ _ BX BY H) as [_ [_ [_ [_ [R5 R6]]]]].
  cbv zeta in R5, R6.
  rewrite Y, N, R5, R6. split; split; intros K; discriminate K.
Qed.
