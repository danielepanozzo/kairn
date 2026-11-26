(* The predicates, the three-valued comparisons and the relations of IEEE 1788 of the round-up
   interval, in the IEEE model, on all values (docs/developer/design/upward.md, "Predicates and
   comparisons", "Statements"): the thirteen kernels upward_empty_1, upward_entire_1,
   upward_contains_1, upward_subset_1, upward_positive_1, upward_negative_1, upward_zero_1,
   upward_less_1, upward_less_equal_1, upward_equal_1, upward_rel_equal_1,
   upward_rel_interior_1 and upward_rel_disjoint_1. The theorems K_correct establish the
   generated statements K_spec of proofs/gen/UpwardStatements.v about the generated models of
   proofs/gen/UpwardModel.v. Every kernel is exact, for canonical operands and every precision:
   the mask is true exactly when the relation holds; for the three-valued comparisons, yes is
   true exactly when the relation holds for every choice of members of nonempty operands, no
   exactly when it fails for every choice, and they are never both true.

   Notation: as in IeeeUpwardExact.v. For the operands x = (xu, xn) = [a, b] and
   y = (yu, yn) = [c, d], a = -xval xn, b = xval xu, c = -xval yn, d = xval yu.

   The proofs. Each listing is the default kernel's on the bounds a and b, with the
   comparisons written on the stored lanes, so each kernel is the lemma of the default kernel
   on extended real numbers (xempty, xentire, xsubset, xpositive, ..., xinterior, xdisjoint of
   IeeeIntervalPredicates.v) once a comparison of limbs is the comparison of their values
   (lt_xval, le_xval, eq_xval of IeeeExt.v) and a comparison of negated lanes the comparison of
   the bounds (upward_xlt_opp and the others of IeeeUpwardExact.v): b < c is xu < -yn, c < a is
   xn < yn, and so on. A nonempty state is an interval of extended real numbers of xinterval.
   The empty set (NaN, NaN) is not, and is taken on its own: a comparison with a NaN is false,
   which gives the default answer with no test, and the listings test unord where the answer
   for the empty set is true. *)
From Stdlib Require Import Reals ZArith Bool Lia Lra Psatz.
From Flocq Require Import Core Binary.
From Kairn Require Import IeeeBridge IeeeVocabulary IeeeOps IeeeExt IeeeDirected.
From Kairn Require Import Rectangle IeeeIntervalVocabulary IeeeInterval1 IeeeIntervalExact.
From Kairn Require Import IeeeIntervalPredicates.
From Kairn Require Import IeeeUpwardVocabulary IeeeUpwardMax IeeeUpwardOps IeeeUpwardExact.
From Kairn Require IeeeOperations IeeeUpwardOperations.
From Kairn.Gen Require Import UpwardStatements.
From Kairn.Gen Require UpwardModel.
Open Scope R_scope.

(** * The shape of the three-valued comparisons *)

(* When an operand is empty, yes and no are both false. *)
Lemma upward_trit_none :
  forall (NX NY A B : Prop) (yes no : bool),
  ~ (NX /\ NY) -> yes = false -> no = false ->
  (yes = true <-> NX /\ NY /\ A) /\ (no = true <-> NX /\ NY /\ B) /\ ~ (yes = true /\ no = true).
Proof.
intros NX NY A B yes no H Y N. subst yes no.
split; [|split]; [split; [intros K; discriminate K|intros [K1 [K2 _]]; elim (H (conj K1 K2))]..|].
intros [K _]. discriminate K.
Qed.

(* yes and no exclude each other when both operands have members. *)
Lemma upward_trit_exclusive :
  forall (X Y : R -> Prop) (rel : R -> R -> Prop) (NX NY : Prop) (yes no : bool),
  (NX -> exists x : R, X x) -> (NY -> exists y : R, Y y) ->
  (yes = true <-> NX /\ NY /\ (forall x y : R, X x -> Y y -> rel x y)) ->
  (no = true <-> NX /\ NY /\ (forall x y : R, X x -> Y y -> ~ rel x y)) ->
  ~ (yes = true /\ no = true).
Proof.
intros X Y rel NX NY yes no MX MY HY HN [K L].
apply HY in K. apply HN in L. destruct K as [AX [AY K]]. destruct L as [_ [_ L]].
destruct (MX AX) as [x Hx]. destruct (MY AY) as [y Hy].
exact (L x y Hx Hy (K x y Hx Hy)).
Qed.

(* The values of an empty operand in the comparisons of the listings: NaN, then false. *)
Local Ltac upward_nan_lanes E :=
  let A := fresh "A" in let B := fresh "B" in
  destruct E as [E|E]; destruct (upward_empty_xval _ _ _ _ E) as [A B]; rewrite ?A, ?B;
  cbn [xopp xlt xle xeq andb orb];
  rewrite ?upward_xlt_nan_r, ?upward_xle_nan_r, ?upward_xeq_nan_r, ?andb_false_r, ?orb_false_r;
  cbn [andb orb]; try reflexivity.

(** * The generated statements *)

Theorem upward_empty_1_correct : upward_empty_1_spec.
Proof.
intros prec emax Hp He xu xn CX. cbv zeta.
unfold UpwardModel.upward_empty_1. cbv zeta.
exact (proj1 (unord_state prec emax xu xn CX)).
Qed.

Theorem upward_entire_1_correct : upward_entire_1_spec.
Proof.
intros prec emax Hp He xu xn CX. cbv zeta.
unfold UpwardModel.upward_entire_1. cbv zeta.
rewrite 2!(eq_xval prec emax). change (xval (IeeeOperations.pinf prec emax)) with (XInf false).
rewrite <- (upward_xeq_opp_ninf (xval xn)), andb_comm.
exact (xentire (xopp (xval xn)) (xval xu)).
Qed.

Theorem upward_contains_1_correct : upward_contains_1_spec.
Proof.
intros prec emax Hp He nan_opp nan_abs xu xn t CX. cbv zeta.
unfold UpwardModel.upward_contains_1. cbv zeta.
rewrite 2!(le_xval prec emax), (lt_abs_pinf prec emax nan_abs t), (xval_neg prec emax).
destruct (is_finite prec emax t) eqn:F.
- rewrite andb_true_r, (upward_xval_finite prec emax t F). cbn [xopp].
  unfold in_upward_1, xmember. rewrite upward_xle_opp_l, andb_true_iff.
  split; [intros [K L]; split; [exact F|split; assumption]|intros [_ [K L]]; split; assumption].
- rewrite andb_false_r. split; [intros K; discriminate K|intros [K _]].
  unfold finite in K. congruence.
Qed.

Theorem upward_subset_1_correct : upward_subset_1_spec.
Proof.
intros prec emax Hp He xu xn yu yn CX CY. cbv zeta.
unfold UpwardModel.upward_subset_1. cbv zeta.
destruct (unord_state prec emax xu xn CX) as [Ku _].
destruct CX as [EX|NX].
- (* the empty set is inside every set *)
  rewrite (proj2 Ku EX), orb_true_l.
  split; [intros _ z Hz; elim (upward_empty_no_member prec emax xu xn z EX Hz)|intros _; reflexivity].
- destruct (upward_nonempty_lanes prec emax xu xn NX) as [Nu _].
  rewrite (unord_not_nan prec emax xu xu Nu Nu), orb_false_l, 2!(le_xval prec emax).
  destruct CY as [EY|NY].
  + (* a nonempty set is inside no empty set *)
    destruct (upward_empty_xval prec emax yu yn EY) as [_ B].
    rewrite B, upward_xle_nan_r, andb_false_l.
    split; [intros K; discriminate K|intros H; exfalso].
    destruct (upward_nonempty_member prec emax xu xn NX) as [m Hm].
    exact (upward_empty_no_member prec emax yu yn m EY (H m Hm)).
  + rewrite <- (upward_xle_opp (xval yn) (xval xn)).
    exact (xsubset (xopp (xval xn)) (xval xu) (xopp (xval yn)) (xval yu)
             (or_intror NX) (or_intror NY)).
Qed.

Theorem upward_positive_1_correct : upward_positive_1_spec.
Proof.
intros prec emax Hp He xu xn CX. cbv zeta.
unfold UpwardModel.upward_positive_1. cbv zeta.
rewrite (lt_xval prec emax). change (xval (IeeeOperations.pzero prec emax)) with (XFin 0).
destruct CX as [EX|NX].
- destruct (upward_empty_xval prec emax xu xn EX) as [_ B]. rewrite B. cbn [xlt].
  split; [intros K; discriminate K|intros [N _]].
  elim (upward_empty_not_nonempty prec emax xu xn EX N).
- rewrite <- upward_xlt_0_opp.
  pose proof (xpositive (xopp (xval xn)) (xval xu) (or_intror NX)) as P.
  rewrite (proj1 (proj2 NX)), andb_true_r in P. exact P.
Qed.

Theorem upward_negative_1_correct : upward_negative_1_spec.
Proof.
intros prec emax Hp He xu xn CX. cbv zeta.
unfold UpwardModel.upward_negative_1. cbv zeta.
rewrite (lt_xval prec emax). change (xval (IeeeOperations.pzero prec emax)) with (XFin 0).
destruct CX as [EX|NX].
- destruct (upward_empty_xval prec emax xu xn EX) as [A _]. rewrite A. cbn [xlt].
  split; [intros K; discriminate K|intros [N _]].
  elim (upward_empty_not_nonempty prec emax xu xn EX N).
- pose proof (xnegative (xopp (xval xn)) (xval xu) (or_intror NX)) as P.
  rewrite (proj2 (proj2 NX)), andb_true_r in P. exact P.
Qed.

Theorem upward_zero_1_correct : upward_zero_1_spec.
Proof.
intros prec emax Hp He xu xn CX. cbv zeta.
unfold UpwardModel.upward_zero_1. cbv zeta.
rewrite 2!(eq_xval prec emax). change (xval (IeeeOperations.pzero prec emax)) with (XFin 0).
rewrite <- (upward_xeq_opp_0 (xval xn)).
exact (xzero (xopp (xval xn)) (xval xu)).
Qed.

Theorem upward_less_1_correct : upward_less_1_spec.
Proof.
intros prec emax Hp He nan_opp xu xn yu yn CX CY.
unfold UpwardModel.upward_less_1. cbv beta iota zeta.
rewrite (lt_xval prec emax), (le_xval prec emax), 2!(xval_neg prec emax).
destruct (upward_states_cases prec emax xu xn yu yn CX CY) as [E|[NX NY]].
- apply upward_trit_none.
  + intros [NX NY]. destruct E as [E|E]; [exact (upward_empty_not_nonempty _ _ _ _ E NX)|
                                          exact (upward_empty_not_nonempty _ _ _ _ E NY)].
  + upward_nan_lanes E.
  + upward_nan_lanes E.
- destruct (xless _ _ _ _ (or_intror NX) (or_intror NY)) as [Y N].
  rewrite (proj1 (proj2 NX)), (proj1 (proj2 NY)), !andb_true_r in Y, N.
  split; [exact Y|split; [exact N|]].
  exact (upward_trit_exclusive _ _ _ _ _ _ _ (upward_nonempty_member prec emax xu xn)
           (upward_nonempty_member prec emax yu yn) Y N).
Qed.

Theorem upward_less_equal_1_correct : upward_less_equal_1_spec.
Proof.
intros prec emax Hp He nan_opp xu xn yu yn CX CY.
unfold UpwardModel.upward_less_equal_1. cbv beta iota zeta.
rewrite (le_xval prec emax), (lt_xval prec emax), 2!(xval_neg prec emax).
destruct (upward_states_cases prec emax xu xn yu yn CX CY) as [E|[NX NY]].
- apply upward_trit_none.
  + intros [NX NY]. destruct E as [E|E]; [exact (upward_empty_not_nonempty _ _ _ _ E NX)|
                                          exact (upward_empty_not_nonempty _ _ _ _ E NY)].
  + upward_nan_lanes E.
  + upward_nan_lanes E.
- destruct (xless_equal _ _ _ _ (or_intror NX) (or_intror NY)) as [Y N].
  rewrite (proj1 (proj2 NX)), (proj1 (proj2 NY)), !andb_true_r in Y, N.
  split; [exact Y|split; [exact N|]].
  exact (upward_trit_exclusive _ _ _ _ _ _ _ (upward_nonempty_member prec emax xu xn)
           (upward_nonempty_member prec emax yu yn) Y N).
Qed.

Theorem upward_equal_1_correct : upward_equal_1_spec.
Proof.
intros prec emax Hp He nan_opp xu xn yu yn CX CY.
unfold UpwardModel.upward_equal_1. cbv beta iota zeta.
rewrite 3!(eq_xval prec emax), 2!(lt_xval prec emax), 2!(xval_neg prec emax).
destruct (upward_states_cases prec emax xu xn yu yn CX CY) as [E|[NX NY]].
- apply upward_trit_none.
  + intros [NX NY]. destruct E as [E|E]; [exact (upward_empty_not_nonempty _ _ _ _ E NX)|
                                          exact (upward_empty_not_nonempty _ _ _ _ E NY)].
  + upward_nan_lanes E.
  + upward_nan_lanes E.
- destruct (xequal _ _ _ _ (or_intror NX) (or_intror NY)) as [Y N].
  rewrite (proj1 (proj2 NX)), (proj1 (proj2 NY)), !andb_true_r in N.
  split; [exact Y|split; [exact N|]].
  exact (upward_trit_exclusive _ _ _ _ _ _ _ (upward_nonempty_member prec emax xu xn)
           (upward_nonempty_member prec emax yu yn) Y N).
Qed.

Theorem upward_rel_equal_1_correct : upward_rel_equal_1_spec.
Proof.
intros prec emax Hp He xu xn yu yn CX CY. cbv zeta.
unfold UpwardModel.upward_rel_equal_1. cbv zeta.
rewrite 2!(eq_xval prec emax).
destruct (unord_state prec emax xu xn CX) as [Kx _].
destruct (unord_state prec emax yu yn CY) as [Ky _].
destruct CX as [EX|NX]; destruct CY as [EY|NY].
- (* two empty sets *)
  rewrite (proj2 Kx EX), (proj2 Ky EY), andb_true_l, orb_true_r.
  split; [intros _ z|intros _; reflexivity].
  split; intros H; exfalso;
    [exact (upward_empty_no_member prec emax _ _ z EX H)|exact (upward_empty_no_member prec emax _ _ z EY H)].
- (* the empty set and a nonempty one *)
  destruct (upward_nonempty_lanes prec emax yu yn NY) as [Mu _].
  destruct (upward_empty_xval prec emax xu xn EX) as [A _].
  rewrite (proj2 Kx EX), (unord_not_nan prec emax yu yu Mu Mu), A. cbn [xeq andb orb].
  split; [intros K; discriminate K|intros H; exfalso].
  destruct (upward_nonempty_member prec emax yu yn NY) as [m Hm].
  exact (upward_empty_no_member prec emax _ _ m EX (proj2 (H m) Hm)).
- destruct (upward_nonempty_lanes prec emax xu xn NX) as [Nu _].
  destruct (upward_empty_xval prec emax yu yn EY) as [A _].
  rewrite (unord_not_nan prec emax xu xu Nu Nu), (proj2 Ky EY), A, upward_xeq_nan_r.
  cbn [andb orb].
  split; [intros K; discriminate K|intros H; exfalso].
  destruct (upward_nonempty_member prec emax xu xn NX) as [m Hm].
  exact (upward_empty_no_member prec emax _ _ m EY (proj1 (H m) Hm)).
- (* two nonempty states: the same bounds *)
  destruct (upward_nonempty_lanes prec emax xu xn NX) as [Nu _].
  destruct (upward_nonempty_lanes prec emax yu yn NY) as [Mu _].
  rewrite (unord_not_nan prec emax xu xu Nu Nu), (unord_not_nan prec emax yu yu Mu Mu).
  rewrite andb_false_l, orb_false_r, <- (upward_xeq_opp (xval xn) (xval yn)), andb_comm.
  exact (xrel_equal (xopp (xval xn)) (xval xu) (xopp (xval yn)) (xval yu)
           (or_intror NX) (or_intror NY)).
Qed.

Theorem upward_rel_interior_1_correct : upward_rel_interior_1_spec.
Proof.
intros prec emax Hp He xu xn yu yn CX CY. cbv zeta.
unfold UpwardModel.upward_rel_interior_1. cbv zeta.
rewrite 2!(lt_xval prec emax), 4!(eq_xval prec emax).
change (xval (IeeeOperations.pinf prec emax)) with (XInf false).
destruct (unord_state prec emax xu xn CX) as [Kx _].
destruct CX as [EX|NX].
- (* the empty set is interior to every set *)
  rewrite (proj2 Kx EX), orb_true_l.
  split; [intros _ z Hz; elim (upward_empty_no_member prec emax xu xn z EX Hz)|intros _; reflexivity].
- destruct (upward_nonempty_lanes prec emax xu xn NX) as [Nu _].
  rewrite (unord_not_nan prec emax xu xu Nu Nu), orb_false_l.
  destruct CY as [EY|NY].
  + (* a nonempty set is interior to no empty set *)
    destruct (upward_empty_xval prec emax yu yn EY) as [_ B].
    rewrite B, upward_xlt_nan_r. cbn [xeq andb orb].
    split; [intros K; discriminate K|intros H; exfalso].
    destruct (upward_nonempty_member prec emax xu xn NX) as [m Hm].
    destruct (H m Hm) as [e [Pe He']].
    apply (upward_empty_no_member prec emax yu yn m EY). apply He'.
    rewrite Rminus_diag, Rabs_R0. exact Pe.
  + pose proof (xinterior (xopp (xval xn)) (xval xu) (xopp (xval yn)) (xval yu)
                  (or_intror NX) (or_intror NY)) as P.
    rewrite (upward_xlt_pinf_xeq _ (proj1 (proj2 NX))), orb_false_l, upward_xlt_opp,
      2!upward_xeq_opp_ninf in P.
    exact P.
Qed.

Theorem upward_rel_disjoint_1_correct : upward_rel_disjoint_1_spec.
Proof.
intros prec emax Hp He nan_opp xu xn yu yn CX CY. cbv zeta.
unfold UpwardModel.upward_rel_disjoint_1. cbv zeta.
rewrite 2!(lt_xval prec emax), 2!(xval_neg prec emax).
destruct (unord_states prec emax xu xn yu yn CX CY) as [Ku _].
destruct (upward_states_cases prec emax xu xn yu yn CX CY) as [E|[NX NY]].
- (* an empty operand: no common member *)
  rewrite (proj2 Ku E), orb_true_l.
  split; [intros _ [z [Hx Hy]]|intros _; reflexivity].
  destruct E as [EX|EY];
    [exact (upward_empty_no_member prec emax _ _ z EX Hx)|exact (upward_empty_no_member prec emax _ _ z EY Hy)].
- destruct (upward_nonempty_lanes prec emax xu xn NX) as [Nu _].
  destruct (upward_nonempty_lanes prec emax yu yn NY) as [Mu _].
  rewrite (unord_not_nan prec emax xu yu Nu Mu), orb_false_l.
  pose proof (xdisjoint (xopp (xval xn)) (xval xu) (xopp (xval yn)) (xval yu)
                (or_intror NX) (or_intror NY)) as P.
  rewrite (upward_xlt_pinf_xeq _ (proj1 (proj2 NX))), (upward_xlt_pinf_xeq _ (proj1 (proj2 NY))),
    !orb_false_l in P.
  exact P.
Qed.
