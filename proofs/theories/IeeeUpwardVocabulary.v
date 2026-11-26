(* The vocabulary of the statements about the round-up interval, in the IEEE model
   (docs/developer/design/upward.md, "States" and "Statements"). Written by hand. The
   definitions are those of the design page; the generated statements of the upward kernels
   (proofs/gen/UpwardStatements.v) are written with them. The facts at the end of the file are
   proved from these definitions alone, for the proofs of the kernels.

   A state of kairn::upward::Interval<T> is a pair (u, n) of numbers of T: u, the upper bound,
   in lane 0, and n, the lower bound negated, in lane 1. It extends the vocabulary of
   IeeeIntervalVocabulary.v (xmember, xnonempty, range_1, range_2, range_lower, range_upper)
   and of IeeeVocabulary.v (xval, xopp, xle, nan, finite, val):

     upward_empty_1 u n        the empty set: (NaN, NaN)
     upward_nonempty_1 u n     a nonempty interval [-n, u]: the bounds -n and u, as extended
                               real numbers, are those of a nonempty interval
     upward_1 u n              a canonical state: one or the other
     in_upward_1 u n x         the real number x is a member: -n <= x <= u
     upward_bounded_1 u n      both lanes are finite
     in_number_1 t x           the real number x is a member of Interval(t): x = t for a
                               finite t, every real number otherwise

   Why each has the form it has.

   - The bounds are the extended real numbers xopp (xval n) and xval u, and everything else is
     the interval vocabulary on them: nonempty is xnonempty, membership is xmember. So
     "nonempty" says, with no clause of its own, that neither lane is a NaN (a comparison with
     a NaN is false), that the lower bound -n is below +infinity (n is not -infinity) and that
     the upper bound u is above -infinity (u is not -infinity): the table of States of the
     design page. The whole line is (+infinity, +infinity).

   - The empty set is the two NaN lanes, not a property of the bounds: xopp of a NaN is a NaN,
     so in_upward_1 of the empty set has no member by the same formula, and a state with one
     NaN lane is neither empty nor nonempty, hence not canonical.

   - in_number_1 t is the set of members of Interval(t) of the default type: {t} for a finite
     t, and the whole line for an infinite t or a NaN, which the default type makes of them. *)
From Stdlib Require Import Reals ZArith Bool Lra.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements.
From Kairn Require Import IeeeVocabulary IeeeIntervalVocabulary.
Open Scope R_scope.

(** * The vocabulary *)

Section UpwardVocabulary.
Variable prec emax : Z.
Notation float := (binary_float prec emax).

Definition upward_empty_1 (u n : float) : Prop := nan u /\ nan n.
Definition upward_nonempty_1 (u n : float) : Prop := xnonempty (xopp (xval n)) (xval u).
Definition upward_1 (u n : float) : Prop := upward_empty_1 u n \/ upward_nonempty_1 u n.
Definition in_upward_1 (u n : float) (x : R) : Prop := xmember (xopp (xval n)) (xval u) x.
Definition upward_bounded_1 (u n : float) : Prop := finite u /\ finite n.
Definition in_number_1 (t : float) (x : R) : Prop := finite t -> x = val t.

End UpwardVocabulary.

Arguments upward_empty_1 {prec emax} u n.
Arguments upward_nonempty_1 {prec emax} u n.
Arguments upward_1 {prec emax} u n.
Arguments in_upward_1 {prec emax} u n x.
Arguments upward_bounded_1 {prec emax} u n.
Arguments in_number_1 {prec emax} t x.

(** * Facts *)

(* The comparisons of real numbers that xle and xlt leave in the goal once the extended real
   numbers are given by cases (the facts to use are premises of the goal), then linear
   arithmetic. *)
Local Ltac upward_xcase :=
  cbn;
  repeat match goal with
  | |- context [Rle_bool ?x ?y] => destruct (Rle_bool_spec x y); cbn
  | |- context [Rlt_bool ?x ?y] => destruct (Rlt_bool_spec x y); cbn
  end;
  intros;
  repeat match goal with H : _ /\ _ |- _ => destruct H end;
  try discriminate;
  repeat split;
  try reflexivity; try assumption; try lra; try (exfalso; lra).

(* An interval of extended real numbers with a real member is nonempty, and a nonempty one has
   a real member (the same as member_nonempty and nonempty_member of Rectangle.v, proved here
   so that this file needs the vocabulary only). *)
Lemma upward_xmember_xnonempty :
  forall (lo hi : xreal) (x : R), xmember lo hi x -> xnonempty lo hi.
Proof.
intros [|[|]|l] [|[|]|h] x; unfold xmember, xnonempty; upward_xcase.
Qed.

Lemma upward_xnonempty_xmember :
  forall lo hi : xreal, xnonempty lo hi -> exists x : R, xmember lo hi x.
Proof.
intros [|[|]|l] [|[|]|h] [H [K L]]; cbn in H, K, L; try discriminate.
- exists 0. split; reflexivity.
- exists h. split; cbn; [reflexivity|apply Rle_bool_true; apply Rle_refl].
- exists l. split; cbn; [apply Rle_bool_true; apply Rle_refl|reflexivity].
- exists l. split; cbn; [apply Rle_bool_true; apply Rle_refl|exact H].
Qed.

(* -n <= x is -x <= n, for every extended real number n. *)
Lemma upward_xle_opp_l :
  forall (n : xreal) (x : R), xle (xopp n) (XFin x) = xle (XFin (- x)) n.
Proof.
intros [|[|]|r] x; cbn; trivial.
destruct (Rle_bool_spec (- r) x); destruct (Rle_bool_spec (- x) r); trivial; exfalso; lra.
Qed.

Section UpwardFacts.
Variable prec emax : Z.
Notation float := (binary_float prec emax).
Notation xv := (@xval prec emax).
Notation ninf := (infinity prec emax true).
Notation pinf := (infinity prec emax false).

(** ** The extended real number of a limb *)

Lemma upward_xval_nan : forall a : float, xv a = XNaN <-> nan a.
Proof.
intros [s|s|s pl H|s m e H]; unfold xval, nan; cbn; split; intros K;
  trivial; discriminate.
Qed.

Lemma upward_xval_inf :
  forall (a : float) (s : bool), xv a = XInf s <-> a = infinity prec emax s.
Proof.
intros [s'|s'|s' pl H|s' m e H] s; unfold xval, infinity; cbn; split; intros K;
  try discriminate; now inversion K.
Qed.

Lemma upward_xval_finite :
  forall a : float, finite a -> xv a = XFin (val a).
Proof. intros a F. unfold xval. unfold finite in F. now rewrite F. Qed.

Lemma upward_xval_real :
  forall (a : float) (r : R), xv a = XFin r -> finite a /\ val a = r.
Proof.
intros [s|s|s pl H|s m e H] r; unfold xval, finite, val; cbn; intros K;
  try discriminate; inversion K; now split.
Qed.

(* A limb is a NaN, an infinity, or finite. *)
Lemma upward_xval_cases :
  forall a : float,
  (nan a /\ xv a = XNaN) \/ (exists s : bool, a = infinity prec emax s /\ xv a = XInf s) \/
  (finite a /\ xv a = XFin (val a)).
Proof.
intros [s|s|s pl H|s m e H].
- right. right. now split.
- right. left. now exists s.
- left. now split.
- right. right. now split.
Qed.

(** ** Canonical states *)

(* The lanes of a nonempty state: neither is a NaN or -infinity; each is a real number or
   +infinity. *)
Lemma upward_nonempty_lanes :
  forall u n : float, upward_nonempty_1 u n ->
  ~ nan u /\ ~ nan n /\ u <> ninf /\ n <> ninf.
Proof.
intros u n [H [K L]].
split; [|split; [|split]].
- intros N. apply upward_xval_nan in N. rewrite N in L. discriminate L.
- intros N. apply upward_xval_nan in N. rewrite N in K. discriminate K.
- intros E. apply (upward_xval_inf u true) in E. rewrite E in L. discriminate L.
- intros E. apply (upward_xval_inf n true) in E. rewrite E in K. discriminate K.
Qed.

Lemma upward_nonempty_lane_values :
  forall u n : float, upward_nonempty_1 u n ->
  (xv u = XInf false \/ exists r : R, xv u = XFin r) /\
  (xv n = XInf false \/ exists r : R, xv n = XFin r).
Proof.
intros u n H. destruct (upward_nonempty_lanes u n H) as [Nu [Nn [Iu In]]].
split.
- destruct (upward_xval_cases u) as [[N _]|[[[|] [E V]]|[_ V]]].
  + now elim Nu.
  + now elim Iu.
  + now left.
  + right. now exists (val u).
- destruct (upward_xval_cases n) as [[N _]|[[[|] [E V]]|[_ V]]].
  + now elim Nn.
  + now elim In.
  + now left.
  + right. now exists (val n).
Qed.

(* No lane of a canonical state is -infinity. *)
Lemma upward_1_not_ninf :
  forall u n : float, upward_1 u n -> u <> ninf /\ n <> ninf.
Proof.
intros u n [[Nu Nn]|H].
- unfold nan in Nu, Nn. split; intros E; subst; discriminate.
- now destruct (upward_nonempty_lanes u n H) as [_ [_ K]].
Qed.

(* A NaN lane of a canonical state is never alone: a state with a NaN lane is the empty set,
   and a state without one is nonempty. *)
Lemma upward_1_nan :
  forall u n : float, upward_1 u n -> nan u \/ nan n -> upward_empty_1 u n.
Proof.
intros u n [E|H] K; trivial.
destruct (upward_nonempty_lanes u n H) as [Nu [Nn _]]. tauto.
Qed.

Lemma upward_1_nan_iff :
  forall u n : float, upward_1 u n -> (nan u <-> nan n).
Proof.
intros u n H. split; intros K.
- exact (proj2 (upward_1_nan u n H (or_introl K))).
- exact (proj1 (upward_1_nan u n H (or_intror K))).
Qed.

Lemma upward_1_not_nan :
  forall u n : float, upward_1 u n -> ~ nan u \/ ~ nan n -> upward_nonempty_1 u n.
Proof.
intros u n [[Nu Nn]|H] K; trivial. tauto.
Qed.

Lemma upward_empty_not_nonempty :
  forall u n : float, upward_empty_1 u n -> ~ upward_nonempty_1 u n.
Proof.
intros u n [Nu _] H. now destruct (upward_nonempty_lanes u n H) as [K _].
Qed.

Lemma upward_nonempty_not_empty :
  forall u n : float, upward_nonempty_1 u n -> ~ upward_empty_1 u n.
Proof. intros u n H E. exact (upward_empty_not_nonempty u n E H). Qed.

(* A bounded canonical state is nonempty. *)
Lemma upward_bounded_nonempty :
  forall u n : float, upward_1 u n -> upward_bounded_1 u n -> upward_nonempty_1 u n.
Proof.
intros u n [[Nu _]|H] [Fu _]; trivial.
unfold nan, finite in *. destruct u; discriminate.
Qed.

(** ** Members *)

(* Membership through the stored lanes: x <= u and -x <= n. *)
Lemma in_upward_1_iff :
  forall (u n : float) (x : R),
  in_upward_1 u n x <-> xle (XFin x) (xv u) = true /\ xle (XFin (- x)) (xv n) = true.
Proof.
intros u n x. unfold in_upward_1, xmember. rewrite upward_xle_opp_l. tauto.
Qed.

(* The empty set has no member; a state with a member is nonempty; a nonempty state has a
   member. *)
Lemma upward_empty_no_member :
  forall (u n : float) (x : R), upward_empty_1 u n -> ~ in_upward_1 u n x.
Proof.
intros u n x [_ Nn] [H _]. apply upward_xval_nan in Nn. rewrite Nn in H. discriminate H.
Qed.

Lemma in_upward_nonempty :
  forall (u n : float) (x : R), in_upward_1 u n x -> upward_nonempty_1 u n.
Proof. intros u n x H. exact (upward_xmember_xnonempty _ _ x H). Qed.

Lemma upward_nonempty_member :
  forall u n : float, upward_nonempty_1 u n -> exists x : R, in_upward_1 u n x.
Proof. intros u n H. exact (upward_xnonempty_xmember _ _ H). Qed.

(* The whole line, (+infinity, +infinity): nonempty, and every real number is a member. *)
Lemma upward_whole :
  upward_nonempty_1 pinf pinf /\ forall x : R, in_upward_1 pinf pinf x.
Proof.
unfold upward_nonempty_1, in_upward_1, xnonempty, xmember.
split; [|intros x]; cbn; repeat split.
Qed.

(** ** The default interval with the same members *)

(* A default interval [l, h] and a state (u, n) with h = u and l = -n, as extended real
   numbers, are nonempty together and have the same members. The two conversions of the
   design page compute such pairs. *)
Lemma upward_interval_same :
  forall (u n l h : float),
  xv h = xv u -> xv l = xopp (xv n) ->
  (interval_nonempty_1 l h <-> upward_nonempty_1 u n) /\
  (forall x : R, in_interval_1 l h x <-> in_upward_1 u n x).
Proof.
intros u n l h Eh El. unfold interval_nonempty_1, upward_nonempty_1, in_interval_1, in_upward_1.
rewrite Eh, El. split; [tauto|intros x; tauto].
Qed.

(* A canonical default interval is empty exactly when its lower bound is +infinity (the test
   of upward_from_interval_1). *)
Lemma interval_1_empty_iff :
  forall l h : float, interval_1 l h -> (interval_empty_1 l h <-> l = pinf).
Proof.
intros l h [E|N].
- split; [intros [K _]; exact K|intros _; exact E].
- split.
  + intros [K _]. exact K.
  + intros K. exfalso. destruct N as [_ [L _]].
    rewrite K in L. discriminate L.
Qed.

(* The bounds of a nonempty default interval are not NaN, and its lower bound is not
   +infinity. *)
Lemma interval_nonempty_bounds :
  forall l h : float, interval_nonempty_1 l h ->
  ~ nan l /\ ~ nan h /\ l <> pinf /\ h <> ninf.
Proof.
intros l h [H [K L]]. split; [|split; [|split]].
- intros N. apply upward_xval_nan in N. rewrite N in K. discriminate K.
- intros N. apply upward_xval_nan in N. rewrite N in L. discriminate L.
- intros E. apply (upward_xval_inf l false) in E. rewrite E in K. discriminate K.
- intros E. apply (upward_xval_inf h true) in E. rewrite E in L. discriminate L.
Qed.

(** ** A number of the program *)

Lemma in_number_1_finite :
  forall (t : float) (x : R), finite t -> (in_number_1 t x <-> x = val t).
Proof. intros t x F. unfold in_number_1. split; [intros H; exact (H F)|intros H _; exact H]. Qed.

Lemma in_number_1_not_finite :
  forall (t : float) (x : R), ~ finite t -> in_number_1 t x.
Proof. intros t x F K. now elim F. Qed.

Lemma in_number_1_member : forall t : float, in_number_1 t (val t).
Proof. intros t _. reflexivity. Qed.

(* For a finite t, the members of Interval(t) are those of the interval [t, t]. *)
Lemma in_number_1_xmember :
  forall (t : float) (y : R), finite t -> (in_number_1 t y <-> xmember (xv t) (xv t) y).
Proof.
intros t y F. rewrite (in_number_1_finite t y F), (upward_xval_finite t F).
unfold xmember. cbn [xle]. split.
- intros E. subst y. split; apply Rle_bool_true; apply Rle_refl.
- intros [A B]. revert A B.
  destruct (Rle_bool_spec (val t) y); destruct (Rle_bool_spec y (val t));
    intros A B; try discriminate; lra.
Qed.

End UpwardFacts.
