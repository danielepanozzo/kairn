(* The exact kernels of the round-up interval that return a state, in the IEEE model, on all
   values: the hull, the intersection, the constructor, and the conversions from and to the
   default interval of one limb (docs/developer/design/upward.md, "Hull and intersection",
   "Constructor and conversions", "Statements"). The theorems K_correct establish the generated
   statements K_spec of proofs/gen/UpwardStatements.v about the generated models of
   proofs/gen/UpwardModel.v: upward_hull_1, upward_intersection_1, upward_make_1,
   upward_from_interval_1 and upward_to_interval_1. No operation of these listings rounds, so
   the results are the same in every rounding mode; for every precision, every choice of the
   NaN each operation returns, and (for the hull) every max_nl with the property max_nl_ok.

   Notation: as in IeeeUpwardOps.v. A state (u, n) is the interval [-n, u]; for the operands
   x = (xu, xn) = [a, b] and y = (yu, yn) = [c, d], with a = -xval xn, b = xval xu,
   c = -xval yn, d = xval yu as extended real numbers. xinterval, xhull and xinter are those
   of IeeeIntervalExact.v: the hull [min a c, max b d] and the intersection
   [max a c, min b d] of intervals of extended real numbers.

   What is proved.
   - The hull: the result is canonical, empty exactly when both operands are, contains every
     member of either, and when it is not empty its bounds are the bounds of the union. An
     empty x has two NaN lanes, which the listing tests, and the result is y; for a nonempty x
     the maximum of each lane has a second operand that is not a NaN, so an empty y loses
     (max_nl_nan) and the result is x; for two nonempty operands each lane is the greater of
     the two lanes (max_nl_xval), u the greater upper bound and -n the smaller lower bound.
   - The intersection: canonical, empty exactly when the operands have no common member,
     contains every common member, and when not empty its bounds are those of the set of the
     common members. Each lane is the smaller of the two (select_lt_xmin), so u = min(b, d)
     and -n = -min(-a, -c) = max(a, c); the two tests of crossing, u < -n on one lane and
     n < -u on the other, are the same test (upward_xlt_opp_swap), and the result is the empty
     set when an operand is or when they cross, [max(a, c), min(b, d)] otherwise (xinter).
   - The constructor: the cases of interval_make_1 (IeeeInterval1.v), with the state
     (hi, -lo) for a pair that describes an interval, the whole line (+inf, +inf) for a NaN
     bound and for the same infinity twice, and the empty set for reversed bounds.
   - The conversions: a state and the default interval with the bounds -n and u have the same
     members, and are empty or nonempty together (upward_interval_same); the empty sets are
     told apart by a NaN lane (unord_state) and by the lower bound +infinity
     (interval_1_empty_iff).

   The facts on extended real numbers at the top of the file are the sign changes of the
   comparisons, of the maximum and of the minimum, which the listings use to compare stored
   lanes with negated lanes; IeeeUpwardPredicates.v uses them too. *)
From Stdlib Require Import Reals ZArith Bool Lia Lra Psatz.
From Flocq Require Import Core Binary.
From Kairn Require Import IeeeBridge IeeeVocabulary IeeeOps IeeeExt IeeeDirected.
From Kairn Require Import Rectangle IeeeIntervalVocabulary IeeeInterval1 IeeeIntervalExact.
From Kairn Require Import IeeeUpwardVocabulary IeeeUpwardMax IeeeUpwardOps IeeeUpwardProduct.
From Kairn Require IeeeOperations IeeeUpwardOperations.
From Kairn.Gen Require Import UpwardStatements.
From Kairn.Gen Require UpwardModel.
Open Scope R_scope.

(** * Sign changes of extended real numbers *)

(* The comparisons of real numbers left in the goal once the extended real numbers are given by
   cases, then linear arithmetic, a disequality it contradicts, or the equality of two reals. *)
Local Ltac xsign :=
  cbn;
  repeat match goal with
  | |- context [Rle_bool ?x ?y] => destruct (Rle_bool_spec x y); cbn
  | |- context [Rlt_bool ?x ?y] => destruct (Rlt_bool_spec x y); cbn
  | |- context [Req_bool ?x ?y] => destruct (Req_bool_spec x y); cbn
  end;
  intros;
  try discriminate; try reflexivity; try congruence;
  try (exfalso; lra);
  try (match goal with H : _ <> _ |- _ => solve [exfalso; apply H; lra] end);
  try (f_equal; lra).

Lemma upward_xlt_opp : forall v w : xreal, xlt (xopp v) (xopp w) = xlt w v.
Proof. intros [|[|]|x] [|[|]|y]; xsign. Qed.

Lemma upward_xle_opp : forall v w : xreal, xle (xopp v) (xopp w) = xle w v.
Proof. intros [|[|]|x] [|[|]|y]; xsign. Qed.

Lemma upward_xeq_opp : forall v w : xreal, xeq (xopp v) (xopp w) = xeq v w.
Proof. intros [|[|]|x] [|[|]|y]; xsign. Qed.

(* v < -w exactly when w < -v: the test of crossing of the intersection, on either lane. *)
Lemma upward_xlt_opp_swap : forall v w : xreal, xlt v (xopp w) = xlt w (xopp v).
Proof. intros [|[|]|x] [|[|]|y]; xsign. Qed.

Lemma upward_xlt_0_opp : forall v : xreal, xlt (XFin 0) (xopp v) = xlt v (XFin 0).
Proof. intros [|[|]|x]; xsign. Qed.

Lemma upward_xeq_opp_0 : forall v : xreal, xeq (xopp v) (XFin 0) = xeq v (XFin 0).
Proof. intros [|[|]|x]; xsign. Qed.

Lemma upward_xeq_opp_ninf : forall v : xreal, xeq (xopp v) (XInf true) = xeq v (XInf false).
Proof. intros [|[|]|x]; xsign. Qed.

(* The greatest of two opposites is the opposite of the least. *)
Lemma upward_xmax_opp : forall v w : xreal, xmax (xopp v) (xopp w) = xopp (xmin v w).
Proof. intros v w. unfold xmax, xmin. rewrite upward_xlt_opp. now destruct (xlt w v). Qed.

Lemma upward_xmax_comm :
  forall v w : xreal, v <> XNaN -> w <> XNaN -> xmax v w = xmax w v.
Proof. intros [|[|]|x] [|[|]|y]; unfold xmax; xsign. Qed.

Lemma upward_xopp_xmax :
  forall v w : xreal, v <> XNaN -> w <> XNaN -> xopp (xmax v w) = xmin (xopp w) (xopp v).
Proof.
intros v w Hv Hw. rewrite (upward_xmax_comm v w Hv Hw). unfold xmax, xmin.
rewrite upward_xlt_opp. now destruct (xlt w v).
Qed.

(* A comparison with a NaN on the right is false. *)
Lemma upward_xlt_nan_r : forall v : xreal, xlt v XNaN = false.
Proof. intros [|[|]|x]; reflexivity. Qed.

Lemma upward_xle_nan_r : forall v : xreal, xle v XNaN = false.
Proof. intros [|[|]|x]; reflexivity. Qed.

Lemma upward_xeq_nan_r : forall v : xreal, xeq v XNaN = false.
Proof. intros [|[|]|x]; reflexivity. Qed.

(* A value below +infinity is not +infinity. *)
Lemma upward_xlt_pinf_xeq : forall v : xreal, xlt v (XInf false) = true -> xeq v (XInf false) = false.
Proof. intros [|[|]|x] H; try reflexivity; discriminate H. Qed.

(** * States *)

Section UpwardStates.
Variable prec emax : Z.
Notation float := (binary_float prec emax).
Notation xv := (@xval prec emax).

(* Two canonical states: one is empty, or both are nonempty. *)
Lemma upward_states_cases :
  forall xu xn yu yn : float, upward_1 xu xn -> upward_1 yu yn ->
  (upward_empty_1 xu xn \/ upward_empty_1 yu yn) \/
  (upward_nonempty_1 xu xn /\ upward_nonempty_1 yu yn).
Proof.
intros xu xn yu yn [EX|NX] [EY|NY]; [left; now left|left; now left|left; now right|].
right. now split.
Qed.

(* The lanes of the empty set stand for NaN. *)
Lemma upward_empty_xval : forall u n : float, upward_empty_1 u n -> xv u = XNaN /\ xv n = XNaN.
Proof.
intros u n [Nu Nn].
split; [exact (proj2 (upward_xval_nan prec emax u) Nu)|exact (proj2 (upward_xval_nan prec emax n) Nn)].
Qed.

(* A set whose members are those of a nonempty state has the bounds of the state. *)
Lemma upward_bounds_of :
  forall (A : R -> Prop) (u n : float),
  upward_nonempty_1 u n -> (forall z : R, A z <-> in_upward_1 u n z) ->
  forall lo hi : xreal, range_lower A lo -> range_upper A hi -> xopp (xv n) = lo /\ xv u = hi.
Proof.
intros A u n N E lo hi L H.
destruct (upward_nonempty_member prec emax u n N) as [m Hm].
assert (Ex : exists z : R, A z) by (exists m; now apply E).
assert (E' : forall z : R, in_upward_1 u n z <-> A z) by (intros z; symmetry; apply E).
split.
- apply (range_lower_unique A _ _ Ex); [|exact L].
  exact (range_lower_ext _ _ _ E' (range_member_lower _ _ N)).
- apply (range_upper_unique A _ _ Ex); [|exact H].
  exact (range_upper_ext _ _ _ E' (range_member_upper _ _ N)).
Qed.

(** ** The hull *)

(* The hull with an empty operand: the other operand. *)
Lemma upward_hull_empty_l :
  forall xu xn yu yn : float,
  upward_empty_1 xu xn -> upward_1 yu yn ->
  upward_1 yu yn /\
  (upward_empty_1 yu yn <-> upward_empty_1 xu xn /\ upward_empty_1 yu yn) /\
  (forall z : R, in_upward_1 xu xn z \/ in_upward_1 yu yn z -> in_upward_1 yu yn z) /\
  (~ upward_empty_1 yu yn ->
   forall lo hi : xreal,
   range_lower (fun z : R => in_upward_1 xu xn z \/ in_upward_1 yu yn z) lo ->
   range_upper (fun z : R => in_upward_1 xu xn z \/ in_upward_1 yu yn z) hi ->
   xopp (xv yn) = lo /\ xv yu = hi).
Proof.
intros xu xn yu yn EX CY.
assert (M : forall z : R, in_upward_1 xu xn z \/ in_upward_1 yu yn z <-> in_upward_1 yu yn z).
{ intros z. split; [|now right].
  intros [K|K]; [elim (upward_empty_no_member prec emax xu xn z EX K)|exact K]. }
split; [exact CY|split; [tauto|split; [intros z; apply M|]]].
intros NE. destruct CY as [EY|NY]; [elim (NE EY)|].
exact (upward_bounds_of _ yu yn NY M).
Qed.

Lemma upward_hull_empty_r :
  forall xu xn yu yn : float,
  upward_1 xu xn -> upward_empty_1 yu yn ->
  upward_1 xu xn /\
  (upward_empty_1 xu xn <-> upward_empty_1 xu xn /\ upward_empty_1 yu yn) /\
  (forall z : R, in_upward_1 xu xn z \/ in_upward_1 yu yn z -> in_upward_1 xu xn z) /\
  (~ upward_empty_1 xu xn ->
   forall lo hi : xreal,
   range_lower (fun z : R => in_upward_1 xu xn z \/ in_upward_1 yu yn z) lo ->
   range_upper (fun z : R => in_upward_1 xu xn z \/ in_upward_1 yu yn z) hi ->
   xopp (xv xn) = lo /\ xv xu = hi).
Proof.
intros xu xn yu yn CX EY.
assert (M : forall z : R, in_upward_1 xu xn z \/ in_upward_1 yu yn z <-> in_upward_1 xu xn z).
{ intros z. split; [|now left].
  intros [K|K]; [exact K|elim (upward_empty_no_member prec emax yu yn z EY K)]. }
split; [exact CX|split; [tauto|split; [intros z; apply M|]]].
intros NE. destruct CX as [EX|NX]; [elim (NE EX)|].
exact (upward_bounds_of _ xu xn NX M).
Qed.

(* The hull of two nonempty states, for any lanes zu and zn that stand for the greatest upper
   bound and the opposite of the least lower bound: xhull on the bounds. *)
Lemma upward_hull_nonempty :
  forall xu xn yu yn zu zn : float,
  upward_nonempty_1 xu xn -> upward_nonempty_1 yu yn ->
  xopp (xv zn) = xmin (xopp (xv xn)) (xopp (xv yn)) -> xv zu = xmax (xv xu) (xv yu) ->
  upward_1 zu zn /\
  (upward_empty_1 zu zn <-> upward_empty_1 xu xn /\ upward_empty_1 yu yn) /\
  (forall z : R, in_upward_1 xu xn z \/ in_upward_1 yu yn z -> in_upward_1 zu zn z) /\
  (~ upward_empty_1 zu zn ->
   forall lo hi : xreal,
   range_lower (fun z : R => in_upward_1 xu xn z \/ in_upward_1 yu yn z) lo ->
   range_upper (fun z : R => in_upward_1 xu xn z \/ in_upward_1 yu yn z) hi ->
   xopp (xv zn) = lo /\ xv zu = hi).
Proof.
intros xu xn yu yn zu zn NX NY El Eu.
destruct (xhull _ _ _ _ (or_intror NX) (or_intror NY)) as [_ [_ [H3 H4]]].
assert (I3 : forall z : R, in_upward_1 xu xn z \/ in_upward_1 yu yn z -> in_upward_1 zu zn z).
{ intros z K. unfold in_upward_1. rewrite El, Eu. exact (H3 z K). }
destruct (upward_nonempty_member prec emax xu xn NX) as [m Hm].
assert (NZ : upward_nonempty_1 zu zn)
  by exact (in_upward_nonempty prec emax zu zn m (I3 m (or_introl Hm))).
split; [now right|split; [|split; [exact I3|]]].
- split.
  + intros E. elim (upward_empty_not_nonempty prec emax zu zn E NZ).
  + intros [E _]. elim (upward_empty_not_nonempty prec emax xu xn E NX).
- intros _ lo hi L H. rewrite El, Eu. apply H4; [|exact L|exact H].
  intros [K1 K2]. apply (xmember_empty m). rewrite <- K1, <- K2. exact (H3 m (or_introl Hm)).
Qed.

End UpwardStates.

(** * The generated statements *)

Theorem upward_hull_1_correct : upward_hull_1_spec.
Proof.
intros prec emax Hp He max_nl Hm xu xn yu yn CX CY.
unfold UpwardModel.upward_hull_1. cbv beta iota zeta.
destruct (unord_state prec emax xu xn CX) as [Ku Kn].
destruct CX as [EX|NX].
- (* x empty: the result is y *)
  rewrite (proj2 Ku EX), (proj2 Kn EX). cbv beta iota.
  exact (upward_hull_empty_l prec emax xu xn yu yn EX CY).
- destruct (upward_nonempty_lanes prec emax xu xn NX) as [Nu [Nn _]].
  rewrite (unord_not_nan prec emax xu xu Nu Nu), (unord_not_nan prec emax xn xn Nn Nn).
  cbv beta iota.
  destruct CY as [EY|NY].
  + (* y empty: a NaN first operand loses, the result is x *)
    rewrite (max_nl_nan prec emax max_nl Hm yu xu (proj1 EY) Nu),
      (max_nl_nan prec emax max_nl Hm yn xn (proj2 EY) Nn).
    exact (upward_hull_empty_r prec emax xu xn yu yn (or_intror NX) EY).
  + (* both nonempty: the greater of each lane *)
    destruct (upward_nonempty_lanes prec emax yu yn NY) as [Mu [Mn _]].
    apply (upward_hull_nonempty prec emax xu xn yu yn _ _ NX NY).
    * rewrite (max_nl_xval prec emax max_nl Hm yn xn Mn Nn).
      apply upward_xopp_xmax; apply upward_not_nan_xval; assumption.
    * rewrite (max_nl_xval prec emax max_nl Hm yu xu Mu Nu).
      apply upward_xmax_comm; apply upward_not_nan_xval; assumption.
Qed.

Theorem upward_intersection_1_correct : upward_intersection_1_spec.
Proof.
intros prec emax Hp He nan_opp nan_const xu xn yu yn CX CY.
unfold UpwardModel.upward_intersection_1. cbv beta iota zeta.
destruct (unord_states prec emax xu xn yu yn CX CY) as [Ku Kn].
assert (EZ : upward_empty_1 (IeeeOperations.cnan prec emax nan_const)
                            (IeeeOperations.cnan prec emax nan_const))
  by (split; apply cnan_nan).
destruct (upward_states_cases prec emax xu xn yu yn CX CY) as [E|[NX NY]].
- (* an empty operand: the empty set *)
  rewrite (proj2 Ku E), (proj2 Kn E), !orb_true_l. cbv beta iota.
  assert (NC : ~ (exists z : R, in_upward_1 xu xn z /\ in_upward_1 yu yn z)).
  { intros [z [Hx Hy]]. destruct E as [EX|EY].
    - exact (upward_empty_no_member prec emax xu xn z EX Hx).
    - exact (upward_empty_no_member prec emax yu yn z EY Hy). }
  split; [now left|split; [split; [intros _; exact NC|intros _; exact EZ]|split]].
  + intros z K. elim NC. now exists z.
  + intros K. elim (K EZ).
- destruct (upward_nonempty_lanes prec emax xu xn NX) as [Nu [Nn _]].
  destruct (upward_nonempty_lanes prec emax yu yn NY) as [Mu [Mn _]].
  rewrite (unord_not_nan prec emax xu yu Nu Mu), (unord_not_nan prec emax xn yn Nn Mn),
    !orb_false_l.
  set (lu := if IeeeOperations.lt prec emax yu xu then yu else xu).
  set (ln := if IeeeOperations.lt prec emax yn xn then yn else xn).
  assert (Vu : xval lu = xmin (xval xu) (xval yu)) by (unfold lu; apply select_lt_xmin).
  assert (Vn : xval ln = xmin (xval xn) (xval yn)) by (unfold ln; apply select_lt_xmin).
  assert (NL : xval lu <> XNaN)
    by (rewrite Vu; apply xmin_not_nan; apply upward_not_nan_xval; assumption).
  assert (NN : xval ln <> XNaN)
    by (rewrite Vn; apply xmin_not_nan; apply upward_not_nan_xval; assumption).
  rewrite 2!(lt_xval prec emax), 2!(xval_neg prec emax).
  rewrite (upward_xlt_opp_swap (xval ln) (xval lu)).
  (* the intersection of the bounds: [max a c, min b d] = [-ln, lu] *)
  destruct (xinter _ _ _ _ (or_intror NX) (or_intror NY)) as [M [T F]].
  rewrite upward_xmax_opp, <- Vn, <- Vu in M, T, F.
  destruct (xlt (xval lu) (xopp (xval ln))) eqn:C; cbv beta iota.
  + (* crossed lanes: no common member, the empty set *)
    assert (C' : xle (xopp (xval ln)) (xval lu) = false).
    { destruct (xle (xopp (xval ln)) (xval lu)) eqn:K; [|reflexivity].
      exfalso. exact (xle_not_xlt _ _ K C). }
    assert (NC : ~ (exists z : R, in_upward_1 xu xn z /\ in_upward_1 yu yn z)).
    { intros [z Hz]. exact (F C' z Hz). }
    split; [now left|split; [split; [intros _; exact NC|intros _; exact EZ]|split]].
    * intros z K. elim NC. now exists z.
    * intros K. elim (K EZ).
  + (* the lanes in order: the state (lu, ln), whose members are the common members *)
    assert (C' : xle (xopp (xval ln)) (xval lu) = true)
      by (apply upward_xlt_false_xle; [apply xopp_not_nan; exact NN|exact NL|exact C]).
    assert (NZ : upward_nonempty_1 lu ln) by exact (T C').
    assert (Mz : forall z : R, in_upward_1 xu xn z /\ in_upward_1 yu yn z <-> in_upward_1 lu ln z)
      by exact M.
    split; [now right|split; [|split; [intros z K; now apply Mz|]]].
    * split; [intros E; elim (upward_empty_not_nonempty prec emax lu ln E NZ)|intros K; exfalso].
      destruct (upward_nonempty_member prec emax lu ln NZ) as [m Hm].
      apply K. exists m. now apply Mz.
    * intros _. exact (upward_bounds_of prec emax _ lu ln NZ Mz).
Qed.

Theorem upward_make_1_correct : upward_make_1_spec.
Proof.
intros prec emax Hp He nan_opp nan_const lo hi.
unfold UpwardModel.upward_make_1. cbv beta iota zeta.
rewrite (le_xval prec emax), !(lt_xval prec emax), (neg_pinf prec emax nan_opp).
change (xval (IeeeOperations.pinf prec emax)) with (XInf false).
change (xval (B754_infinity prec emax true)) with (XInf true).
destruct (andb (andb (xle (xval lo) (xval hi)) (xlt (xval lo) (XInf false)))
               (xlt (XInf true) (xval hi))) eqn:V; cbv beta iota.
- (* the pair describes an interval: (hi, -lo) *)
  apply andb_true_iff in V. destruct V as [V V3]. apply andb_true_iff in V.
  destruct V as [V1 V2].
  assert (N : xnonempty (xval lo) (xval hi)) by (split; [exact V1|split; [exact V2|exact V3]]).
  assert (E : xopp (xval (IeeeOperations.neg prec emax nan_opp lo)) = xval lo)
    by (now rewrite (xval_neg prec emax), xopp_involutive).
  split; [right; unfold upward_nonempty_1; now rewrite E|].
  split; [intros _; split; [exact E|reflexivity]|].
  split.
  + intros [K|[K|[s [K1 K2]]]]; exfalso.
    * rewrite (proj2 (upward_xval_nan prec emax lo) K) in V1. discriminate V1.
    * rewrite (proj2 (upward_xval_nan prec emax hi) K) in V1.
      destruct (xval lo) as [|[|]|r]; discriminate V1.
    * rewrite K1, K2 in N. destruct N as [_ [W1 W2]]. destruct s; discriminate.
  + intros K. elim (xle_not_xlt _ _ V1 K).
- assert (NN : ~ xnonempty (xval lo) (xval hi)).
  { intros [N1 [N2 N3]]. rewrite N1, N2, N3 in V. discriminate V. }
  destruct (xlt (xval hi) (xval lo)) eqn:R; cbv beta iota.
  + (* reversed bounds: the empty set *)
    split; [left; split; apply cnan_nan|].
    split; [intros K; elim (NN K)|].
    split; [|intros _; split; apply cnan_nan].
    intros [K|[K|[s [K1 K2]]]]; exfalso.
    * rewrite (proj2 (upward_xval_nan prec emax lo) K) in R.
      destruct (xval hi) as [|[|]|r]; discriminate R.
    * rewrite (proj2 (upward_xval_nan prec emax hi) K) in R. discriminate R.
    * rewrite K1, K2 in R. destruct s; discriminate R.
  + (* a NaN bound, or the same infinity twice: the whole line *)
    split; [right; exact (proj1 (upward_whole prec emax))|].
    split; [intros K; elim (NN K)|].
    split; [intros _; split; reflexivity|].
    intros K. discriminate K.
Qed.

Theorem upward_from_interval_1_correct : upward_from_interval_1_spec.
Proof.
intros prec emax Hp He nan_opp nan_const xl xu CX.
unfold UpwardModel.upward_from_interval_1. cbv beta iota zeta.
rewrite (eq_xval prec emax). change (xval (IeeeOperations.pinf prec emax)) with (XInf false).
destruct CX as [EX|NX].
- (* the empty set (+inf, -inf): two NaN lanes *)
  assert (K : xeq (xval xl) (XInf false) = true) by (rewrite (proj1 EX); reflexivity).
  rewrite K. cbv beta iota.
  assert (EZ : upward_empty_1 (IeeeOperations.cnan prec emax nan_const)
                              (IeeeOperations.cnan prec emax nan_const))
    by (split; apply cnan_nan).
  split; [now left|split; [split; intros _; [exact EX|exact EZ]|split]].
  + intros z. split; intros H; exfalso.
    * exact (upward_empty_no_member prec emax _ _ z EZ H).
    * exact (empty_no_member prec emax xl xu z EX H).
  + intros N. elim (nonempty_not_empty prec emax xl xu N EX).
- (* a nonempty interval [l, h]: (h, -l) *)
  assert (K : xeq (xval xl) (XInf false) = false)
    by exact (upward_xlt_pinf_xeq _ (proj1 (proj2 NX))).
  rewrite K. cbv beta iota.
  assert (El : xval xl = xopp (xval (IeeeOperations.neg prec emax nan_opp xl)))
    by (now rewrite (xval_neg prec emax), xopp_involutive).
  destruct (upward_interval_same prec emax xu (IeeeOperations.neg prec emax nan_opp xl) xl xu
              eq_refl El) as [S M].
  assert (NZ := proj1 S NX).
  split; [now right|split; [|split; [intros z; symmetry; apply M|]]].
  + split.
    * intros E. elim (upward_empty_not_nonempty prec emax _ _ E NZ).
    * intros E. elim (nonempty_not_empty prec emax xl xu NX E).
  + intros _. split; [symmetry; exact El|reflexivity].
Qed.

Theorem upward_to_interval_1_correct : upward_to_interval_1_spec.
Proof.
intros prec emax Hp He nan_opp xu xn CX.
unfold UpwardModel.upward_to_interval_1. cbv beta iota zeta.
rewrite (neg_pinf prec emax nan_opp).
destruct (unord_state prec emax xu xn CX) as [Ku _].
destruct CX as [EX|NX].
- (* the empty set: (+inf, -inf) *)
  rewrite (proj2 Ku EX). cbv beta iota.
  assert (EI : interval_empty_1 (IeeeOperations.pinf prec emax) (B754_infinity prec emax true))
    by (split; reflexivity).
  split; [now left|split; [split; intros _; [exact EX|exact EI]|split]].
  + intros z. split; intros H; exfalso.
    * exact (empty_no_member prec emax _ _ z EI H).
    * exact (upward_empty_no_member prec emax xu xn z EX H).
  + intros N. elim (upward_empty_not_nonempty prec emax xu xn EX N).
- (* a nonempty state: [-n, u] *)
  destruct (upward_nonempty_lanes prec emax xu xn NX) as [Nu _].
  rewrite (unord_not_nan prec emax xu xu Nu Nu). cbv beta iota.
  assert (El : xval (IeeeOperations.neg prec emax nan_opp xn) = xopp (xval xn))
    by apply (xval_neg prec emax).
  destruct (upward_interval_same prec emax xu xn (IeeeOperations.neg prec emax nan_opp xn) xu
              eq_refl El) as [S M].
  assert (NI := proj2 S NX).
  split; [now right|split; [|split; [exact M|]]].
  + split.
    * intros E. elim (nonempty_not_empty prec emax _ _ NI E).
    * intros E. elim (upward_empty_not_nonempty prec emax _ _ E NX).
  + intros _. split; [exact El|reflexivity].
Qed.
