(* The hull and the intersection of two balls, with a center of one limb and of two, in the
   IEEE model, on all values (docs/developer/design/milestone2.md, "One enclosure interface":
   "Hull, intersection and split of balls"; docs/developer/architecture.md, "Claims of the
   enclosure interface: the set operations of a ball"): ball_hull_1, ball_intersection_1,
   ball_hull_2 and ball_intersection_2.

   Notation as in IeeeIntervalConvert.v, IeeeIntervalConvert2.v and IeeeBallSets.v: a ball, its
   states (finite, the whole line, the empty set) and its members are those of
   IeeeVocabulary.v, an interval and its members those of IeeeIntervalVocabulary.v. X and Y are
   the operands, canonical balls, and Z the result. From precision 2 for a center of one limb
   and 3 for two. The theorems K_correct at the end are the generated statements.

   What is proved, for canonical balls X and Y.

   - The hull (ball_hull_1_correct, ball_hull_2_correct): Z is a canonical ball; it is empty
     exactly when X and Y both are; when X is empty, Z is Y as it is; when Y is empty and X is
     not, Z is X as it is; and every member of X or of Y is a member of Z.

   - The intersection (ball_intersection_1_correct, ball_intersection_2_correct): Z is a
     canonical ball; it is empty when X or Y is; when X is the whole line, Z is Y as it is; when
     Y is the whole line and X is not, Z is X as it is; and every member of both X and Y is a
     member of Z.

   "As it is" is the equality of the limbs themselves, as values of binary_float: the sign of
   a zero, and the sign and the payload of a NaN, included. The selects of the listings return
   an operand. Nothing is said the other way when both operands are special, and it would be
   false: the hull of two empty balls is Y, whose NaNs need not be those of X, and the
   intersection of two whole lines is Y, whose center may be -0 where X's is +0.

   The proofs. Each listing selects among the operands by tests of their radii (for a canonical
   ball, a NaN radius is the empty set and +infinity the whole line: radius_tests_1,
   radius_tests_2) and a composition of proved kernels: ball_to_interval_k of each operand, the
   hull or the intersection of the two intervals, interval_to_ball_k of the result. The
   composition contains the set because each step does: the interval of a ball contains its
   members, the hull (the intersection) of two intervals contains the members of either (of
   both), and the ball of a canonical interval contains its members (to_ball_1_members,
   to_ball_2_members: a bounded interval by its radius, an unbounded one as the whole line,
   and the empty set has none). Each step is empty exactly when what it is made of is, which
   gives the emptiness of Z. ball_intersection_1 computes the composition in another order:
   when both radii are numbers its bounds are those of ball_to_interval_1, its [l, h] is the
   result of interval_intersection_1 when l <= h, and otherwise it selects the empty ball, which
   is what interval_to_ball_1 makes of the empty interval that interval_intersection_1 returns
   then; when a radius is a NaN it selects the empty ball too, and what it computed from the
   bounds of that ball is not used. *)
From Stdlib Require Import Reals ZArith Bool Lia Lra Psatz.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements IeeeStatements.
From Kairn Require Import Format Normalized IeeeBridge IeeeVocabulary IeeeOps IeeeExt.
From Kairn Require Import IeeeBall IeeeIntervalVocabulary IeeeInterval1 IeeeInterval2.
From Kairn Require Import IeeeBallConvert IeeeIntervalExact IeeeIntervalConvert.
From Kairn Require Import IeeeBallConvert2 IeeeIntervalConvert2.
From Kairn Require IeeeOperations.
From Kairn.Gen Require IeeeModel.
Open Scope R_scope.

Section IeeeBallHull.
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

Notation fin x := (is_finite prec emax x = true).
Notation feq := (IeeeOperations.eq prec emax).
Notation fle := (IeeeOperations.le prec emax).
Notation pinf := (IeeeOperations.pinf prec emax).
Notation cnan := (IeeeOperations.cnan prec emax nan_const).
Notation ninf := (B754_infinity prec emax true).
Notation xv := (@xval prec emax).
Notation xv2 := (@xval_2 prec emax).
Notation sub_down_1 := (IeeeModel.sub_down_1 prec emax nan_plus nan_minus nan_opp nan_abs).
Notation add_up_1 := (IeeeModel.add_up_1 prec emax nan_plus nan_minus nan_abs).
Notation ball_to_interval_1 :=
  (IeeeModel.ball_to_interval_1 prec emax nan_plus nan_minus nan_opp nan_abs).
Notation interval_to_ball_1 :=
  (IeeeModel.interval_to_ball_1 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const).
Notation ball_to_interval_2 :=
  (IeeeModel.ball_to_interval_2 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma).
Notation interval_to_ball_2 :=
  (IeeeModel.interval_to_ball_2 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const).

(** * The tests of the radii *)

(* For a canonical ball, the radius is a NaN exactly for the empty set, and +infinity exactly
   for the whole line. *)
Lemma radius_tests_1 :
  forall c r : float, ball_1 c r ->
  (is_nan prec emax r = true <-> ball_empty_1 c r) /\ (feq r pinf = true <-> ball_whole_1 c r).
Proof.
intros c r B. split; [exact (ball_1_empty prec emax c r B)|].
rewrite (eq_xval prec emax r pinf). change (xv pinf) with (XInf false).
destruct B as [[Fc [Fr Pr]]|[[Zc Er]|[Nc Nr]]].
- rewrite (xval_fin prec emax r Fr). cbn [xeq].
  split; [intros K; discriminate K|intros [_ K]; rewrite K in Fr; discriminate Fr].
- split; [intros _; exact (conj Zc Er)|intros _; rewrite Er; reflexivity].
- rewrite (xval_nan prec emax r Nr). cbn [xeq].
  split; [intros K; discriminate K|intros [_ K]; rewrite K in Nr; discriminate Nr].
Qed.

Lemma radius_tests_2 :
  forall c0 c1 r : float, ball_2 c0 c1 r ->
  (is_nan prec emax r = true <-> ball_empty_2 c0 c1 r) /\
  (feq r pinf = true <-> ball_whole_2 c0 c1 r).
Proof.
intros c0 c1 r B. split; [exact (ball_2_empty prec emax c0 c1 r B)|].
rewrite (eq_xval prec emax r pinf). change (xv pinf) with (XInf false).
destruct B as [[F0 [F1 [Nc [Fr Pr]]]]|[[Z0 [Z1 Er]]|[N0 [N1 Nr]]]].
- rewrite (xval_fin prec emax r Fr). cbn [xeq].
  split; [intros K; discriminate K|intros [_ [_ K]]; rewrite K in Fr; discriminate Fr].
- split; [intros _; exact (conj Z0 (conj Z1 Er))|intros _; rewrite Er; reflexivity].
- rewrite (xval_nan prec emax r Nr). cbn [xeq].
  split; [intros K; discriminate K|intros [_ [_ K]]; rewrite K in Nr; discriminate Nr].
Qed.

Lemma whole_not_empty_1 : forall c r : float, ball_whole_1 c r -> ~ ball_empty_1 c r.
Proof. intros c r [_ E] [_ N]. rewrite E in N. discriminate N. Qed.

Lemma whole_not_empty_2 : forall c0 c1 r : float, ball_whole_2 c0 c1 r -> ~ ball_empty_2 c0 c1 r.
Proof. intros c0 c1 r [_ [_ E]] [_ [_ N]]. rewrite E in N. discriminate N. Qed.

Lemma empty_ball_cnan_1 : ball_1 cnan cnan /\ ball_empty_1 cnan cnan.
Proof.
assert (E : ball_empty_1 cnan cnan) by (split; exact (proj2_sig nan_const)).
split; [right; right; exact E|exact E].
Qed.

(** * The ball of a canonical interval contains its members *)

Lemma to_ball_1_members :
  (2 <= prec)%Z ->
  forall xl xu : float, interval_1 xl xu ->
  let '(c, r) := interval_to_ball_1 xl xu in
  forall z : R, in_interval_1 xl xu z -> in_ball_1 c r z.
Proof.
intros Hp xl xu I.
generalize (interval_to_ball_1_all prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const
              Hp xl xu I).
destruct (interval_to_ball_1 xl xu) as [c r]. intros [_ [_ [B3 B4]]] z Hz.
assert (N := member_interval prec emax xl xu z Hz).
destruct (is_finite prec emax xl) eqn:Fl; [destruct (is_finite prec emax xu) eqn:Fu|].
- destruct (B4 (conj Fl Fu)) as [BF [_ [_ [Cn _]]]]. right. split; [exact BF|exact (Cn z Hz)].
- left. apply (B3 N). intros [_ K]. unfold finite in K. congruence.
- left. apply (B3 N). intros [K _]. unfold finite in K. congruence.
Qed.

(* An empty interval of two limbs has no member. *)
Lemma empty_2_no_member :
  forall (xl0 xl1 xu0 xu1 : float) (z : R),
  interval_empty_2 xl0 xl1 xu0 xu1 -> ~ in_interval_2 xl0 xl1 xu0 xu1 z.
Proof.
intros xl0 xl1 xu0 xu1 z E. destruct (empty_2_xval prec emax _ _ _ _ E) as [El [Eu _]].
unfold in_interval_2. rewrite El, Eu. apply xmember_empty.
Qed.

Lemma to_ball_2_members :
  (3 <= prec)%Z ->
  forall xl0 xl1 xu0 xu1 : float, interval_2 xl0 xl1 xu0 xu1 ->
  let '(c0, c1, r) := interval_to_ball_2 xl0 xl1 xu0 xu1 in
  forall z : R, in_interval_2 xl0 xl1 xu0 xu1 z -> in_ball_2 c0 c1 r z.
Proof.
intros Hp xl0 xl1 xu0 xu1 I.
generalize (interval_to_ball_2_all prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const
              Hp xl0 xl1 xu0 xu1 I).
destruct (interval_to_ball_2 xl0 xl1 xu0 xu1) as [[c0 c1] r]. intros [_ [_ [B3 [B4 _]]]] z Hz.
assert (N : interval_nonempty_2 xl0 xl1 xu0 xu1).
{ destruct I as [E|N]; [elim (empty_2_no_member _ _ _ _ z E Hz)|exact N]. }
destruct (is_finite prec emax xl0) eqn:Fl; [destruct (is_finite prec emax xu0) eqn:Fu|].
- exact (B4 (conj Fl Fu) z Hz).
- left. apply (B3 N). intros [_ K]. unfold finite in K. congruence.
- left. apply (B3 N). intros [K _]. unfold finite in K. congruence.
Qed.

(** * ball_hull_1 *)

Theorem ball_hull_1_all :
  (2 <= prec)%Z ->
  forall cx rx cy ry : float, ball_1 cx rx -> ball_1 cy ry ->
  let '(cz, rz) :=
    IeeeModel.ball_hull_1 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const
      cx rx cy ry in
  ball_1 cz rz /\
  (ball_empty_1 cz rz <-> ball_empty_1 cx rx /\ ball_empty_1 cy ry) /\
  (ball_empty_1 cx rx -> cz = cy /\ rz = ry) /\
  (ball_empty_1 cy ry /\ ~ ball_empty_1 cx rx -> cz = cx /\ rz = rx) /\
  (forall z : R, in_ball_1 cx rx z \/ in_ball_1 cy ry z -> in_ball_1 cz rz z).
Proof.
intros Hp cx rx cy ry BX BY. unfold IeeeModel.ball_hull_1.
generalize (ball_to_interval_1_all prec emax nan_plus nan_minus nan_opp nan_abs Hp cx rx BX).
destruct (ball_to_interval_1 cx rx) as [xl xu]. intros [IX [EX [CX _]]].
generalize (ball_to_interval_1_all prec emax nan_plus nan_minus nan_opp nan_abs Hp cy ry BY).
destruct (ball_to_interval_1 cy ry) as [yl yu]. intros [IY [EY [CY _]]].
generalize (interval_hull_1_correct prec emax prec_gt_0_ prec_lt_emax_ xl xu yl yu IX IY).
destruct (IeeeModel.interval_hull_1 prec emax xl xu yl yu) as [zl zu]. intros [IZ [EZ [CZ _]]].
generalize (to_ball_1_members Hp zl zu IZ).
generalize (interval_to_ball_1_all prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const
              Hp zl zu IZ).
destruct (interval_to_ball_1 zl zu) as [c r]. intros [B1 [B2 _]] M.
cbv beta iota zeta. rewrite 2!(eq_self prec emax).
destruct (radius_tests_1 cx rx BX) as [NX _].
destruct (radius_tests_1 cy ry BY) as [NY _].
destruct (is_nan prec emax rx) eqn:Nx; [|destruct (is_nan prec emax ry) eqn:Ny];
  cbn [negb]; cbv beta iota.
- (* X empty: Y as it is *)
  assert (Ex := proj1 NX eq_refl).
  split; [exact BY|].
  split; [split; [intros K; exact (conj Ex K)|intros [_ K]; exact K]|].
  split; [intros _; split; reflexivity|].
  split; [intros [_ K]; elim (K Ex)|].
  intros z [K|K]; [elim (in_ball_1_not_empty prec emax cx rx z K Ex)|exact K].
- (* Y empty and X not: X as it is *)
  assert (NEx : ~ ball_empty_1 cx rx) by (intros K; apply NX in K; discriminate K).
  assert (Ey := proj1 NY eq_refl).
  split; [exact BX|].
  split; [split; [intros K; elim (NEx K)|intros [K _]; elim (NEx K)]|].
  split; [intros K; elim (NEx K)|].
  split; [intros _; split; reflexivity|].
  intros z [K|K]; [exact K|elim (in_ball_1_not_empty prec emax cy ry z K Ey)].
- (* neither empty: the composition *)
  assert (NEx : ~ ball_empty_1 cx rx) by (intros K; apply NX in K; discriminate K).
  assert (NEy : ~ ball_empty_1 cy ry) by (intros K; apply NY in K; discriminate K).
  split; [exact B1|].
  split.
  { split; [|intros [K _]; elim (NEx K)].
    intros K. apply B2, EZ in K. destruct K as [K _]. apply EX in K. elim (NEx K). }
  split; [intros K; elim (NEx K)|].
  split; [intros [K _]; elim (NEy K)|].
  intros z Hz. apply M, CZ.
  destruct Hz as [K|K]; [left; exact (CX z K)|right; exact (CY z K)].
Qed.

(** * ball_intersection_1 *)

Theorem ball_intersection_1_all :
  (2 <= prec)%Z ->
  forall cx rx cy ry : float, ball_1 cx rx -> ball_1 cy ry ->
  let '(cz, rz) :=
    IeeeModel.ball_intersection_1 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const
      cx rx cy ry in
  ball_1 cz rz /\
  (ball_empty_1 cx rx \/ ball_empty_1 cy ry -> ball_empty_1 cz rz) /\
  (ball_whole_1 cx rx -> cz = cy /\ rz = ry) /\
  (ball_whole_1 cy ry /\ ~ ball_whole_1 cx rx -> cz = cx /\ rz = rx) /\
  (forall z : R, in_ball_1 cx rx z /\ in_ball_1 cy ry z -> in_ball_1 cz rz z).
Proof.
intros Hp cx rx cy ry BX BY. unfold IeeeModel.ball_intersection_1. cbv zeta.
destruct (radius_tests_1 cx rx BX) as [NX WX].
destruct (radius_tests_1 cy ry BY) as [NY WY].
destruct empty_ball_cnan_1 as [Bn En].
destruct (feq rx pinf) eqn:Wx.
{ (* X is the whole line: Y as it is *)
  assert (Wx' := proj1 WX eq_refl).
  match goal with |- context [interval_to_ball_1 ?a ?b] => destruct (interval_to_ball_1 a b) as [c r] end.
  cbn [negb]. cbv beta iota.
  split; [exact BY|].
  split; [intros [K|K]; [elim (whole_not_empty_1 cx rx Wx' K)|exact K]|].
  split; [intros _; split; reflexivity|].
  split; [intros [_ K]; elim (K Wx')|].
  intros z [_ K]. exact K. }
assert (NWx : ~ ball_whole_1 cx rx) by (intros K; apply WX in K; congruence).
destruct (feq ry pinf) eqn:Wy.
{ (* Y is the whole line and X is not: X as it is *)
  assert (Wy' := proj1 WY eq_refl).
  match goal with |- context [interval_to_ball_1 ?a ?b] => destruct (interval_to_ball_1 a b) as [c r] end.
  cbn [negb]. cbv beta iota.
  split; [exact BX|].
  split; [intros [K|K]; [exact K|elim (whole_not_empty_1 cy ry Wy' K)]|].
  split; [intros K; elim (NWx K)|].
  split; [intros _; split; reflexivity|].
  intros z [K _]. exact K. }
assert (NWy : ~ ball_whole_1 cy ry) by (intros K; apply WY in K; congruence).
cbn [negb]. cbv beta iota. rewrite 2!(eq_self prec emax).
(* neither is the whole line: the composition, or the empty ball *)
assert (Empty : ball_1 cnan cnan /\
                 (ball_empty_1 cx rx \/ ball_empty_1 cy ry -> ball_empty_1 cnan cnan) /\
                 (ball_whole_1 cx rx -> cnan = cy /\ cnan = ry) /\
                 (ball_whole_1 cy ry /\ ~ ball_whole_1 cx rx -> cnan = cx /\ cnan = rx)).
{ split; [exact Bn|]. split; [intros _; exact En|].
  split; [intros K; elim (NWx K)|]. intros [K _]; elim (NWy K). }
destruct (is_nan prec emax rx) eqn:Nx.
{ (* X empty: the empty ball *)
  assert (Ex := proj1 NX eq_refl).
  match goal with |- context [interval_to_ball_1 ?a ?b] => destruct (interval_to_ball_1 a b) as [c r] end.
  cbn [negb]. rewrite andb_false_r. cbn [andb]. cbv beta iota.
  destruct Empty as [E1 [E2 [E3 E4]]].
  split; [exact E1|split; [exact E2|split; [exact E3|split; [exact E4|]]]].
  intros z [K _]. elim (in_ball_1_not_empty prec emax cx rx z K Ex). }
destruct (is_nan prec emax ry) eqn:Ny.
{ (* Y empty: the empty ball *)
  assert (Ey := proj1 NY eq_refl).
  match goal with |- context [interval_to_ball_1 ?a ?b] => destruct (interval_to_ball_1 a b) as [c r] end.
  cbn [negb]. rewrite andb_false_r. cbv beta iota.
  destruct Empty as [E1 [E2 [E3 E4]]].
  split; [exact E1|split; [exact E2|split; [exact E3|split; [exact E4|]]]].
  intros z [_ K]. elim (in_ball_1_not_empty prec emax cy ry z K Ey). }
(* both nonempty: the bounds are those of ball_to_interval_1 *)
assert (NEx : ~ ball_empty_1 cx rx) by (intros K; apply NX in K; congruence).
assert (NEy : ~ ball_empty_1 cy ry) by (intros K; apply NY in K; congruence).
cbn [negb]. rewrite 2!andb_true_r.
assert (EqX : ball_to_interval_1 cx rx = (sub_down_1 cx rx, add_up_1 cx rx)).
{ unfold IeeeModel.ball_to_interval_1. cbv zeta. rewrite (eq_self prec emax), Nx. reflexivity. }
assert (EqY : ball_to_interval_1 cy ry = (sub_down_1 cy ry, add_up_1 cy ry)).
{ unfold IeeeModel.ball_to_interval_1. cbv zeta. rewrite (eq_self prec emax), Ny. reflexivity. }
generalize (ball_to_interval_1_all prec emax nan_plus nan_minus nan_opp nan_abs Hp cx rx BX).
rewrite EqX. intros [IX [_ [CX _]]].
generalize (ball_to_interval_1_all prec emax nan_plus nan_minus nan_opp nan_abs Hp cy ry BY).
rewrite EqY. intros [IY [_ [CY _]]].
generalize (interval_intersection_1_correct prec emax prec_gt_0_ prec_lt_emax_ nan_opp
              _ _ _ _ IX IY).
unfold IeeeModel.interval_intersection_1. cbv beta iota zeta.
rewrite (neg_pinf prec emax nan_opp).
match goal with |- context [fle ?a ?b] => destruct (fle a b) eqn:Ok end; cbv beta iota.
- (* l <= h: interval_to_ball_1 of the intersection [l, h] *)
  intros [IZ [_ [CZ _]]].
  match goal with |- context [interval_to_ball_1 ?a ?b] =>
    generalize (to_ball_1_members Hp a b IZ);
    generalize (interval_to_ball_1_all prec emax nan_plus nan_minus nan_opp nan_abs nan_fma
                  nan_const Hp a b IZ);
    destruct (interval_to_ball_1 a b) as [c r] end.
  intros [B1 _] M. cbv beta iota.
  split; [exact B1|].
  split; [intros [K|K]; [elim (NEx K)|elim (NEy K)]|].
  split; [intros K; elim (NWx K)|].
  split; [intros [K _]; elim (NWy K)|].
  intros z [Kx Ky]. apply M, CZ. split; [exact (CX z Kx)|exact (CY z Ky)].
- (* l > h: the intersection is empty, and so is the ball *)
  intros [_ [EZ _]].
  match goal with |- context [interval_to_ball_1 ?a ?b] => destruct (interval_to_ball_1 a b) as [c r] end.
  cbv beta iota.
  destruct Empty as [E1 [E2 [E3 E4]]].
  split; [exact E1|split; [exact E2|split; [exact E3|split; [exact E4|]]]].
  intros z [Kx Ky]. exfalso.
  apply (proj1 EZ (conj eq_refl eq_refl)). exists z. split; [exact (CX z Kx)|exact (CY z Ky)].
Qed.

(** * ball_hull_2 *)

Theorem ball_hull_2_all :
  (3 <= prec)%Z ->
  forall cx0 cx1 rx cy0 cy1 ry : float, ball_2 cx0 cx1 rx -> ball_2 cy0 cy1 ry ->
  let '(cz0, cz1, rz) :=
    IeeeModel.ball_hull_2 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const
      cx0 cx1 rx cy0 cy1 ry in
  ball_2 cz0 cz1 rz /\
  (ball_empty_2 cz0 cz1 rz <-> ball_empty_2 cx0 cx1 rx /\ ball_empty_2 cy0 cy1 ry) /\
  (ball_empty_2 cx0 cx1 rx -> cz0 = cy0 /\ cz1 = cy1 /\ rz = ry) /\
  (ball_empty_2 cy0 cy1 ry /\ ~ ball_empty_2 cx0 cx1 rx -> cz0 = cx0 /\ cz1 = cx1 /\ rz = rx) /\
  (forall z : R, in_ball_2 cx0 cx1 rx z \/ in_ball_2 cy0 cy1 ry z -> in_ball_2 cz0 cz1 rz z).
Proof.
intros Hp cx0 cx1 rx cy0 cy1 ry BX BY. unfold IeeeModel.ball_hull_2.
generalize (ball_to_interval_2_correct prec emax prec_gt_0_ prec_lt_emax_
              nan_plus nan_minus nan_opp nan_abs nan_fma Hp cx0 cx1 rx BX).
destruct (ball_to_interval_2 cx0 cx1 rx) as [[[xl0 xl1] xu0] xu1]. intros [IX [EX [CX _]]].
generalize (ball_to_interval_2_correct prec emax prec_gt_0_ prec_lt_emax_
              nan_plus nan_minus nan_opp nan_abs nan_fma Hp cy0 cy1 ry BY).
destruct (ball_to_interval_2 cy0 cy1 ry) as [[[yl0 yl1] yu0] yu1]. intros [IY [EY [CY _]]].
generalize (interval_hull_2_correct prec emax prec_gt_0_ prec_lt_emax_
              xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 IX IY).
destruct (IeeeModel.interval_hull_2 prec emax xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1)
  as [[[zl0 zl1] zu0] zu1].
intros [IZ [EZ [CZ _]]].
generalize (to_ball_2_members Hp zl0 zl1 zu0 zu1 IZ).
generalize (interval_to_ball_2_all prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const
              Hp zl0 zl1 zu0 zu1 IZ).
destruct (interval_to_ball_2 zl0 zl1 zu0 zu1) as [[c0 c1] r]. intros [B1 [B2 _]] M.
cbv beta iota zeta. rewrite 2!(eq_self prec emax).
destruct (radius_tests_2 cx0 cx1 rx BX) as [NX _].
destruct (radius_tests_2 cy0 cy1 ry BY) as [NY _].
destruct (is_nan prec emax rx) eqn:Nx; [|destruct (is_nan prec emax ry) eqn:Ny];
  cbn [negb]; cbv beta iota.
- (* X empty: Y as it is *)
  assert (Ex := proj1 NX eq_refl).
  split; [exact BY|].
  split; [split; [intros K; exact (conj Ex K)|intros [_ K]; exact K]|].
  split; [intros _; split; [reflexivity|split; reflexivity]|].
  split; [intros [_ K]; elim (K Ex)|].
  intros z [K|K]; [elim (in_ball_2_not_empty prec emax cx0 cx1 rx z K Ex)|exact K].
- (* Y empty and X not: X as it is *)
  assert (NEx : ~ ball_empty_2 cx0 cx1 rx) by (intros K; apply NX in K; discriminate K).
  assert (Ey := proj1 NY eq_refl).
  split; [exact BX|].
  split; [split; [intros K; elim (NEx K)|intros [K _]; elim (NEx K)]|].
  split; [intros K; elim (NEx K)|].
  split; [intros _; split; [reflexivity|split; reflexivity]|].
  intros z [K|K]; [exact K|elim (in_ball_2_not_empty prec emax cy0 cy1 ry z K Ey)].
- (* neither empty: the composition *)
  assert (NEx : ~ ball_empty_2 cx0 cx1 rx) by (intros K; apply NX in K; discriminate K).
  assert (NEy : ~ ball_empty_2 cy0 cy1 ry) by (intros K; apply NY in K; discriminate K).
  split; [exact B1|].
  split.
  { split; [|intros [K _]; elim (NEx K)].
    intros K. apply B2, EZ in K. destruct K as [K _]. apply EX in K. elim (NEx K). }
  split; [intros K; elim (NEx K)|].
  split; [intros [K _]; elim (NEy K)|].
  intros z Hz. apply M, CZ.
  destruct Hz as [K|K]; [left; exact (CX z K)|right; exact (CY z K)].
Qed.

(** * ball_intersection_2 *)

Theorem ball_intersection_2_all :
  (3 <= prec)%Z ->
  forall cx0 cx1 rx cy0 cy1 ry : float, ball_2 cx0 cx1 rx -> ball_2 cy0 cy1 ry ->
  let '(cz0, cz1, rz) :=
    IeeeModel.ball_intersection_2 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const
      cx0 cx1 rx cy0 cy1 ry in
  ball_2 cz0 cz1 rz /\
  (ball_empty_2 cx0 cx1 rx \/ ball_empty_2 cy0 cy1 ry -> ball_empty_2 cz0 cz1 rz) /\
  (ball_whole_2 cx0 cx1 rx -> cz0 = cy0 /\ cz1 = cy1 /\ rz = ry) /\
  (ball_whole_2 cy0 cy1 ry /\ ~ ball_whole_2 cx0 cx1 rx -> cz0 = cx0 /\ cz1 = cx1 /\ rz = rx) /\
  (forall z : R, in_ball_2 cx0 cx1 rx z /\ in_ball_2 cy0 cy1 ry z -> in_ball_2 cz0 cz1 rz z).
Proof.
intros Hp cx0 cx1 rx cy0 cy1 ry BX BY. unfold IeeeModel.ball_intersection_2.
generalize (ball_to_interval_2_correct prec emax prec_gt_0_ prec_lt_emax_
              nan_plus nan_minus nan_opp nan_abs nan_fma Hp cx0 cx1 rx BX).
destruct (ball_to_interval_2 cx0 cx1 rx) as [[[xl0 xl1] xu0] xu1]. intros [IX [EX [CX _]]].
generalize (ball_to_interval_2_correct prec emax prec_gt_0_ prec_lt_emax_
              nan_plus nan_minus nan_opp nan_abs nan_fma Hp cy0 cy1 ry BY).
destruct (ball_to_interval_2 cy0 cy1 ry) as [[[yl0 yl1] yu0] yu1]. intros [IY [EY [CY _]]].
generalize (interval_intersection_2_correct prec emax prec_gt_0_ prec_lt_emax_ nan_opp
              xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 IX IY).
destruct (IeeeModel.interval_intersection_2 prec emax nan_opp xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1)
  as [[[zl0 zl1] zu0] zu1].
intros [IZ [EZ [CZ _]]].
generalize (to_ball_2_members Hp zl0 zl1 zu0 zu1 IZ).
generalize (interval_to_ball_2_all prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const
              Hp zl0 zl1 zu0 zu1 IZ).
destruct (interval_to_ball_2 zl0 zl1 zu0 zu1) as [[c0 c1] r]. intros [B1 [B2 _]] M.
cbv beta iota zeta.
destruct (radius_tests_2 cx0 cx1 rx BX) as [_ WX].
destruct (radius_tests_2 cy0 cy1 ry BY) as [_ WY].
destruct (feq rx pinf) eqn:Wx; [|destruct (feq ry pinf) eqn:Wy]; cbn [negb]; cbv beta iota.
- (* X is the whole line: Y as it is *)
  assert (Wx' := proj1 WX eq_refl).
  split; [exact BY|].
  split; [intros [K|K]; [elim (whole_not_empty_2 cx0 cx1 rx Wx' K)|exact K]|].
  split; [intros _; split; [reflexivity|split; reflexivity]|].
  split; [intros [_ K]; elim (K Wx')|].
  intros z [_ K]. exact K.
- (* Y is the whole line and X is not: X as it is *)
  assert (NWx : ~ ball_whole_2 cx0 cx1 rx) by (intros K; apply WX in K; congruence).
  assert (Wy' := proj1 WY eq_refl).
  split; [exact BX|].
  split; [intros [K|K]; [exact K|elim (whole_not_empty_2 cy0 cy1 ry Wy' K)]|].
  split; [intros K; elim (NWx K)|].
  split; [intros _; split; [reflexivity|split; reflexivity]|].
  intros z [K _]. exact K.
- (* neither is the whole line: the composition *)
  assert (NWx : ~ ball_whole_2 cx0 cx1 rx) by (intros K; apply WX in K; congruence).
  assert (NWy : ~ ball_whole_2 cy0 cy1 ry) by (intros K; apply WY in K; congruence).
  split; [exact B1|].
  split.
  { intros K. apply B2, EZ. intros [z [Kx Ky]].
    destruct K as [K|K].
    - apply EX in K. exact (empty_2_no_member _ _ _ _ z K Kx).
    - apply EY in K. exact (empty_2_no_member _ _ _ _ z K Ky). }
  split; [intros K; elim (NWx K)|].
  split; [intros [K _]; elim (NWy K)|].
  intros z [Kx Ky]. apply M, CZ. split; [exact (CX z Kx)|exact (CY z Ky)].
Qed.

End IeeeBallHull.

(** * The generated statements *)

(* The two instances on the precision are given explicitly, the hypotheses of the statement: left
   implicit, the check of the theorem of ball_hull_2 ran out of memory (presumably another
   instance was found and the models were compared unfolded); given, every check is immediate. *)

Theorem ball_hull_1_correct : ball_hull_1_spec.
Proof.
intros prec emax Hp0 He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const Hp cx rx cy ry BX BY.
exact (@ball_hull_1_all prec emax Hp0 He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const
         Hp cx rx cy ry BX BY).
Qed.

Theorem ball_intersection_1_correct : ball_intersection_1_spec.
Proof.
intros prec emax Hp0 He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const Hp cx rx cy ry BX BY.
exact (@ball_intersection_1_all prec emax Hp0 He nan_plus nan_minus nan_opp nan_abs nan_fma
         nan_const Hp cx rx cy ry BX BY).
Qed.

Theorem ball_hull_2_correct : ball_hull_2_spec.
Proof.
intros prec emax Hp0 He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const Hp
  cx0 cx1 rx cy0 cy1 ry BX BY.
exact (@ball_hull_2_all prec emax Hp0 He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const
         Hp cx0 cx1 rx cy0 cy1 ry BX BY).
Qed.

Theorem ball_intersection_2_correct : ball_intersection_2_spec.
Proof.
intros prec emax Hp0 He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const Hp
  cx0 cx1 rx cy0 cy1 ry BX BY.
exact (@ball_intersection_2_all prec emax Hp0 He nan_plus nan_minus nan_opp nan_abs nan_fma
         nan_const Hp cx0 cx1 rx cy0 cy1 ry BX BY).
Qed.
