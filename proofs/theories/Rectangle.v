(* The product of two intervals: the rectangle lemma, on extended real numbers
   (docs/developer/design/milestone2.md, "Interval kernels", "One limb", the proof of I3
   for the product).

   For bounds xl, xu, yl, yu that are real numbers or infinities, and real numbers x in
   [xl, xu] and y in [yl, yu], the product x y lies between the least and the greatest of
   the four products of bounds xl yl, xl yu, xu yl, xu yu, taken as extended real numbers
   with 0 * infinity = 0.

   The representation. An extended real number is a value of the type xreal of
   IeeeVocabulary.v: a real number, an infinity with its sign, or a NaN, compared by xle
   and xlt, for which every comparison with a NaN is false. This is the type in which the
   statements of the IEEE model already give the value of a limb (xval) and of a
   comparison: IeeeExt.v proves lt a b = xlt (xval a) (xval b) and the same for le,
   for all limbs a and b, infinite and NaN included. So a statement about the bounds of an
   interval kernel, which are limbs, is a statement about their xval with no translation,
   and a hypothesis xle a b = true says at once that neither side is a NaN.

   Contents:
   - xmul0: the product with 0 * infinity = 0, the rule of interval arithmetic for a
     product of bounds; it is monotone in each factor when the other has a sign;
   - xmin and xmax: what `lt` and `select` compute in the listing of interval_mul_1,
     "m = lt(b, a); select(m, b, a)" and "m = lt(a, b); select(m, b, a)". On values that
     are not NaN they are the minimum and the maximum;
   - rectangle: the lemma, with the least and the greatest of the four products written
     with xmin and xmax;
   - rectangle_lower_bound, rectangle_upper_bound: the corollary the kernel needs. The
     minimum of four lower bounds of the four products is a lower bound of x y, and the
     maximum of four upper bounds is an upper bound;
   - interval_mul_lower, interval_mul_upper: the same on limbs, for the six lines of the
     listing that choose the least of four values and the greatest of four values.

   The hypotheses are that x and y are members: xl <= x <= xu and yl <= y <= yu. That
   the intervals are nonempty, xl <= xu, xl < +infinity and xu > -infinity, follows
   (member_nonempty), and conversely an interval with those three properties has a real
   member (nonempty_member).

   Proof of the lemma: t -> x t is monotone, increasing when x >= 0 and decreasing when
   x <= 0, so x y is at least x yl or x yu; and t -> t c is monotone for an extended c
   with a sign, with the convention covering t = 0 and c infinite, so each of those is at
   least one of the two products of bounds with the same c. *)
From Stdlib Require Import Reals ZArith Bool Lia Lra Psatz.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements IeeeStatements.
From Kairn Require Import IeeeVocabulary IeeeExt.
From Kairn Require IeeeOperations.
Open Scope R_scope.

(** * The order of the extended real numbers, as a proposition *)

(* a is not a NaN. *)
Definition xnum (a : xreal) : Prop :=
  match a with
  | XNaN => False
  | _ => True
  end.

(* a <= b, for a and b that are not NaN: what xle a b = true says (xle_iff). *)
Definition xLe (a b : xreal) : Prop :=
  match a, b with
  | XFin x, XFin y => x <= y
  | XInf true, XInf _ => True
  | XInf true, XFin _ => True
  | XFin _, XInf false => True
  | XInf false, XInf false => True
  | _, _ => False
  end.

Lemma xle_iff : forall a b : xreal, xle a b = true <-> xLe a b.
Proof.
intros [|[|]|x] [|[|]|y]; cbn;
  try (split; [intros _; exact I|intros _; reflexivity]);
  try (split; [discriminate|contradiction]).
destruct (Rle_bool_spec x y) as [H|H]; split; intros K; trivial; try discriminate K. lra.
Qed.

(* Case analysis on the comparisons of real numbers that xmul0, xlt and the like leave in
   a goal, then linear or polynomial arithmetic. *)
Ltac xauto :=
  cbn in *;
  repeat match goal with
  | |- context [Req_bool ?x ?y] => destruct (Req_bool_spec x y); cbn
  | |- context [Rlt_bool ?x ?y] => destruct (Rlt_bool_spec x y); cbn
  end;
  try tauto; try lra; try nra; try (subst; lra).

Lemma xLe_num_l : forall a b : xreal, xLe a b -> xnum a.
Proof. intros [|[|]|x] [|[|]|y]; xauto. Qed.

Lemma xLe_num_r : forall a b : xreal, xLe a b -> xnum b.
Proof. intros [|[|]|x] [|[|]|y]; xauto. Qed.

Lemma xLe_refl : forall a : xreal, xnum a -> xLe a a.
Proof. intros [|[|]|x]; xauto. Qed.

Lemma xLe_trans : forall a b c : xreal, xLe a b -> xLe b c -> xLe a c.
Proof. intros [|[|]|x] [|[|]|y] [|[|]|z]; xauto. Qed.

(* Every extended real number that is not a NaN has a sign: it is at least 0 or at
   most 0. *)
Lemma xLe_total0 : forall c : xreal, xnum c -> xLe (XFin 0) c \/ xLe c (XFin 0).
Proof. intros [|[|]|z]; xauto. Qed.

(** * The product with 0 * infinity = 0 *)

(* The product of two extended real numbers in which a zero times an infinity is zero:
   the rule of interval arithmetic for a product of bounds. A NaN gives a NaN. *)
Definition xmul0 (a b : xreal) : xreal :=
  match a, b with
  | XNaN, _ | _, XNaN => XNaN
  | XFin x, XFin y => XFin (x * y)
  | XFin x, XInf s => if Req_bool x 0 then XFin 0 else XInf (xorb (Rlt_bool x 0) s)
  | XInf s, XFin y => if Req_bool y 0 then XFin 0 else XInf (xorb s (Rlt_bool y 0))
  | XInf s, XInf s' => XInf (xorb s s')
  end.

Lemma xmul0_comm : forall a b : xreal, xmul0 a b = xmul0 b a.
Proof.
intros [|s|x] [|s'|y]; cbn; trivial;
  try (destruct (Req_bool _ 0); trivial);
  try (now rewrite xorb_comm);
  now rewrite Rmult_comm.
Qed.

(* The product of two values that are not NaN is not a NaN: with 0 * infinity = 0 there
   is no invalid product. *)
Lemma xmul0_num : forall a b : xreal, xnum a -> xnum b -> xnum (xmul0 a b).
Proof. intros [|[|]|x] [|[|]|y]; xauto. Qed.

(* Multiplying by c >= 0 keeps the order, and multiplying by c <= 0 reverses it; c may
   be an infinity, and the factors too. *)
Lemma xmul0_le_r_nonneg :
  forall a b c : xreal, xLe a b -> xLe (XFin 0) c -> xLe (xmul0 a c) (xmul0 b c).
Proof. intros [|[|]|x] [|[|]|y] [|[|]|z]; xauto. Qed.

Lemma xmul0_le_r_nonpos :
  forall a b c : xreal, xLe a b -> xLe c (XFin 0) -> xLe (xmul0 b c) (xmul0 a c).
Proof. intros [|[|]|x] [|[|]|y] [|[|]|z]; xauto. Qed.

Lemma xmul0_le_l_nonneg :
  forall a b c : xreal, xLe a b -> xLe (XFin 0) c -> xLe (xmul0 c a) (xmul0 c b).
Proof.
intros a b c H K. rewrite (xmul0_comm c a), (xmul0_comm c b). now apply xmul0_le_r_nonneg.
Qed.

Lemma xmul0_le_l_nonpos :
  forall a b c : xreal, xLe a b -> xLe c (XFin 0) -> xLe (xmul0 c b) (xmul0 c a).
Proof.
intros a b c H K. rewrite (xmul0_comm c a), (xmul0_comm c b). now apply xmul0_le_r_nonpos.
Qed.

(** * The minimum and the maximum that lt and select compute *)

(* "m = lt(b, a); select(m, b, a)" and "m = lt(a, b); select(m, b, a)". *)
Definition xmin (a b : xreal) : xreal := if xlt b a then b else a.
Definition xmax (a b : xreal) : xreal := if xlt a b then b else a.

Lemma xmin_cases : forall a b : xreal, xmin a b = a \/ xmin a b = b.
Proof. intros a b. unfold xmin. destruct (xlt b a); auto. Qed.

Lemma xmax_cases : forall a b : xreal, xmax a b = a \/ xmax a b = b.
Proof. intros a b. unfold xmax. destruct (xlt a b); auto. Qed.

Lemma xmin_num : forall a b : xreal, xnum a -> xnum b -> xnum (xmin a b).
Proof. intros a b Ha Hb. destruct (xmin_cases a b) as [E|E]; now rewrite E. Qed.

Lemma xmax_num : forall a b : xreal, xnum a -> xnum b -> xnum (xmax a b).
Proof. intros a b Ha Hb. destruct (xmax_cases a b) as [E|E]; now rewrite E. Qed.

(* On values that are not NaN, xmin is at most both and xmax at least both. *)
Lemma xmin_le : forall a b : xreal, xnum a -> xnum b -> xLe (xmin a b) a /\ xLe (xmin a b) b.
Proof. intros [|[|]|x] [|[|]|y]; unfold xmin; xauto. Qed.

Lemma xmax_ge : forall a b : xreal, xnum a -> xnum b -> xLe a (xmax a b) /\ xLe b (xmax a b).
Proof. intros [|[|]|x] [|[|]|y]; unfold xmax; xauto. Qed.

(* The least of four values is at most anything that one of them is at most, and the
   greatest of four is at least anything that one of them is at least. *)
Lemma xmin4_lower :
  forall d1 d2 d3 d4 c : xreal,
  xnum d1 -> xnum d2 -> xnum d3 -> xnum d4 ->
  xLe d1 c \/ xLe d2 c \/ xLe d3 c \/ xLe d4 c ->
  xLe (xmin (xmin d1 d2) (xmin d3 d4)) c.
Proof.
intros d1 d2 d3 d4 c N1 N2 N3 N4 H.
destruct (xmin_le d1 d2 N1 N2) as [A1 A2].
destruct (xmin_le d3 d4 N3 N4) as [B1 B2].
destruct (xmin_le _ _ (xmin_num d1 d2 N1 N2) (xmin_num d3 d4 N3 N4)) as [C1 C2].
destruct H as [H|[H|[H|H]]].
- exact (xLe_trans _ _ _ C1 (xLe_trans _ _ _ A1 H)).
- exact (xLe_trans _ _ _ C1 (xLe_trans _ _ _ A2 H)).
- exact (xLe_trans _ _ _ C2 (xLe_trans _ _ _ B1 H)).
- exact (xLe_trans _ _ _ C2 (xLe_trans _ _ _ B2 H)).
Qed.

Lemma xmax4_upper :
  forall v1 v2 v3 v4 c : xreal,
  xnum v1 -> xnum v2 -> xnum v3 -> xnum v4 ->
  xLe c v1 \/ xLe c v2 \/ xLe c v3 \/ xLe c v4 ->
  xLe c (xmax (xmax v1 v2) (xmax v3 v4)).
Proof.
intros v1 v2 v3 v4 c N1 N2 N3 N4 H.
destruct (xmax_ge v1 v2 N1 N2) as [A1 A2].
destruct (xmax_ge v3 v4 N3 N4) as [B1 B2].
destruct (xmax_ge _ _ (xmax_num v1 v2 N1 N2) (xmax_num v3 v4 N3 N4)) as [C1 C2].
destruct H as [H|[H|[H|H]]].
- exact (xLe_trans _ _ _ (xLe_trans _ _ _ H A1) C1).
- exact (xLe_trans _ _ _ (xLe_trans _ _ _ H A2) C1).
- exact (xLe_trans _ _ _ (xLe_trans _ _ _ H B1) C2).
- exact (xLe_trans _ _ _ (xLe_trans _ _ _ H B2) C2).
Qed.

(** * The rectangle lemma *)

Section Rectangle.
Variables xl xu yl yu : xreal.
Variables x y : R.
Hypothesis Hxl : xLe xl (XFin x).
Hypothesis Hxu : xLe (XFin x) xu.
Hypothesis Hyl : xLe yl (XFin y).
Hypothesis Hyu : xLe (XFin y) yu.

(* One of the four products of bounds is at most x y. *)
Lemma rectangle_some_below :
  xLe (xmul0 xl yl) (XFin (x * y)) \/ xLe (xmul0 xl yu) (XFin (x * y)) \/
  xLe (xmul0 xu yl) (XFin (x * y)) \/ xLe (xmul0 xu yu) (XFin (x * y)).
Proof.
change (XFin (x * y)) with (xmul0 (XFin x) (XFin y)).
destruct (Rle_or_lt 0 x) as [Px|Nx].
- (* x >= 0: x yl <= x y *)
  assert (S : xLe (xmul0 (XFin x) yl) (xmul0 (XFin x) (XFin y))).
  { apply xmul0_le_l_nonneg; [exact Hyl|exact Px]. }
  destruct (xLe_total0 yl (xLe_num_l _ _ Hyl)) as [C|C].
  + left. apply xLe_trans with (2 := S). now apply xmul0_le_r_nonneg.
  + right. right. left. apply xLe_trans with (2 := S). now apply xmul0_le_r_nonpos.
- (* x <= 0: x yu <= x y *)
  assert (S : xLe (xmul0 (XFin x) yu) (xmul0 (XFin x) (XFin y))).
  { apply xmul0_le_l_nonpos; [exact Hyu|exact (Rlt_le _ _ Nx)]. }
  destruct (xLe_total0 yu (xLe_num_r _ _ Hyu)) as [C|C].
  + right. left. apply xLe_trans with (2 := S). now apply xmul0_le_r_nonneg.
  + right. right. right. apply xLe_trans with (2 := S). now apply xmul0_le_r_nonpos.
Qed.

(* One of the four products of bounds is at least x y. *)
Lemma rectangle_some_above :
  xLe (XFin (x * y)) (xmul0 xl yl) \/ xLe (XFin (x * y)) (xmul0 xl yu) \/
  xLe (XFin (x * y)) (xmul0 xu yl) \/ xLe (XFin (x * y)) (xmul0 xu yu).
Proof.
change (XFin (x * y)) with (xmul0 (XFin x) (XFin y)).
destruct (Rle_or_lt 0 x) as [Px|Nx].
- (* x >= 0: x y <= x yu *)
  assert (S : xLe (xmul0 (XFin x) (XFin y)) (xmul0 (XFin x) yu)).
  { apply xmul0_le_l_nonneg; [exact Hyu|exact Px]. }
  destruct (xLe_total0 yu (xLe_num_r _ _ Hyu)) as [C|C].
  + right. right. right. apply xLe_trans with (1 := S). now apply xmul0_le_r_nonneg.
  + right. left. apply xLe_trans with (1 := S). now apply xmul0_le_r_nonpos.
- (* x <= 0: x y <= x yl *)
  assert (S : xLe (xmul0 (XFin x) (XFin y)) (xmul0 (XFin x) yl)).
  { apply xmul0_le_l_nonpos; [exact Hyl|exact (Rlt_le _ _ Nx)]. }
  destruct (xLe_total0 yl (xLe_num_l _ _ Hyl)) as [C|C].
  + right. right. left. apply xLe_trans with (1 := S). now apply xmul0_le_r_nonneg.
  + left. apply xLe_trans with (1 := S). now apply xmul0_le_r_nonpos.
Qed.

Let Num_xl : xnum xl := xLe_num_l _ _ Hxl.
Let Num_xu : xnum xu := xLe_num_r _ _ Hxu.
Let Num_yl : xnum yl := xLe_num_l _ _ Hyl.
Let Num_yu : xnum yu := xLe_num_r _ _ Hyu.

Lemma rectangle_prop :
  xLe (xmin (xmin (xmul0 xl yl) (xmul0 xl yu)) (xmin (xmul0 xu yl) (xmul0 xu yu)))
      (XFin (x * y)) /\
  xLe (XFin (x * y))
      (xmax (xmax (xmul0 xl yl) (xmul0 xl yu)) (xmax (xmul0 xu yl) (xmul0 xu yu))).
Proof.
split.
- apply xmin4_lower; try (now apply xmul0_num). exact rectangle_some_below.
- apply xmax4_upper; try (now apply xmul0_num). exact rectangle_some_above.
Qed.

End Rectangle.

(* The rectangle lemma. For bounds xl, xu, yl, yu that are real numbers or infinities and
   real numbers x in [xl, xu] and y in [yl, yu], the product x y lies between the least
   and the greatest of the four products of bounds, taken with 0 * infinity = 0. *)
Theorem rectangle :
  forall (xl xu yl yu : xreal) (x y : R),
  xle xl (XFin x) = true -> xle (XFin x) xu = true ->
  xle yl (XFin y) = true -> xle (XFin y) yu = true ->
  xle (xmin (xmin (xmul0 xl yl) (xmul0 xl yu)) (xmin (xmul0 xu yl) (xmul0 xu yu)))
      (XFin (x * y)) = true /\
  xle (XFin (x * y))
      (xmax (xmax (xmul0 xl yl) (xmul0 xl yu)) (xmax (xmul0 xu yl) (xmul0 xu yu))) = true.
Proof.
intros xl xu yl yu x y Hxl Hxu Hyl Hyu.
apply xle_iff in Hxl, Hxu, Hyl, Hyu.
destruct (rectangle_prop xl xu yl yu x y Hxl Hxu Hyl Hyu) as [L U].
split; now apply xle_iff.
Qed.

(* The corollary the product of intervals needs, below: the minimum (as lt and select
   compute it) of four lower bounds d1, d2, d3, d4 of the four products of bounds is a
   lower bound of x y. *)
Theorem rectangle_lower_bound :
  forall (xl xu yl yu : xreal) (x y : R),
  xle xl (XFin x) = true -> xle (XFin x) xu = true ->
  xle yl (XFin y) = true -> xle (XFin y) yu = true ->
  forall d1 d2 d3 d4 : xreal,
  xle d1 (xmul0 xl yl) = true -> xle d2 (xmul0 xl yu) = true ->
  xle d3 (xmul0 xu yl) = true -> xle d4 (xmul0 xu yu) = true ->
  xle (xmin (xmin d1 d2) (xmin d3 d4)) (XFin (x * y)) = true.
Proof.
intros xl xu yl yu x y Hxl Hxu Hyl Hyu d1 d2 d3 d4 H1 H2 H3 H4.
apply xle_iff in Hxl, Hxu, Hyl, Hyu, H1, H2, H3, H4. apply xle_iff.
apply xmin4_lower; try (eapply xLe_num_l; eassumption).
destruct (rectangle_some_below xl xu yl yu x y Hxl Hxu Hyl Hyu) as [K|[K|[K|K]]].
- left. exact (xLe_trans _ _ _ H1 K).
- right. left. exact (xLe_trans _ _ _ H2 K).
- right. right. left. exact (xLe_trans _ _ _ H3 K).
- right. right. right. exact (xLe_trans _ _ _ H4 K).
Qed.

(* And above: the maximum of four upper bounds v1, v2, v3, v4 of the four products of
   bounds is an upper bound of x y. *)
Theorem rectangle_upper_bound :
  forall (xl xu yl yu : xreal) (x y : R),
  xle xl (XFin x) = true -> xle (XFin x) xu = true ->
  xle yl (XFin y) = true -> xle (XFin y) yu = true ->
  forall v1 v2 v3 v4 : xreal,
  xle (xmul0 xl yl) v1 = true -> xle (xmul0 xl yu) v2 = true ->
  xle (xmul0 xu yl) v3 = true -> xle (xmul0 xu yu) v4 = true ->
  xle (XFin (x * y)) (xmax (xmax v1 v2) (xmax v3 v4)) = true.
Proof.
intros xl xu yl yu x y Hxl Hxu Hyl Hyu v1 v2 v3 v4 H1 H2 H3 H4.
apply xle_iff in Hxl, Hxu, Hyl, Hyu, H1, H2, H3, H4. apply xle_iff.
apply xmax4_upper; try (eapply xLe_num_r; eassumption).
destruct (rectangle_some_above xl xu yl yu x y Hxl Hxu Hyl Hyu) as [K|[K|[K|K]]].
- left. exact (xLe_trans _ _ _ K H1).
- right. left. exact (xLe_trans _ _ _ K H2).
- right. right. left. exact (xLe_trans _ _ _ K H3).
- right. right. right. exact (xLe_trans _ _ _ K H4).
Qed.

(** * Members and nonempty intervals *)

(* An interval with a real member is nonempty in the sense of the design page:
   xl <= xu, xl < +infinity and xu > -infinity (and neither bound is a NaN). *)
Lemma member_nonempty :
  forall (xl xu : xreal) (x : R),
  xle xl (XFin x) = true -> xle (XFin x) xu = true ->
  xle xl xu = true /\ xlt xl (XInf false) = true /\ xlt (XInf true) xu = true.
Proof.
intros [|[|]|l] [|[|]|h] x; cbn; intros H K; try discriminate; auto.
split; [|now split]. apply Rle_bool_true.
destruct (Rle_bool_spec l x); try discriminate. destruct (Rle_bool_spec x h); try discriminate. lra.
Qed.

(* Conversely such an interval has a real member. *)
Lemma nonempty_member :
  forall xl xu : xreal,
  xle xl xu = true -> xlt xl (XInf false) = true -> xlt (XInf true) xu = true ->
  exists x : R, xle xl (XFin x) = true /\ xle (XFin x) xu = true.
Proof.
intros [|[|]|l] [|[|]|h]; cbn; intros H K L; try discriminate.
- exists 0. now split.
- exists h. split; [reflexivity|]. apply Rle_bool_true. apply Rle_refl.
- exists l. split; [|reflexivity]. apply Rle_bool_true. apply Rle_refl.
- exists l. split; [|exact H]. apply Rle_bool_true. apply Rle_refl.
Qed.

(** * The six selections of interval_mul_1, on limbs *)

Section Limbs.
Variable prec emax : Z.

Notation float := (binary_float prec emax).
Notation flt := (IeeeOperations.lt prec emax).
Notation xv := (@xval prec emax).

(* "m = lt(b, a); select(m, b, a)" is xmin on the extended real numbers the limbs stand
   for, and "m = lt(a, b); select(m, b, a)" is xmax: for all limbs, NaN included. *)
Lemma select_lt_xmin : forall a b : float, xv (if flt b a then b else a) = xmin (xv a) (xv b).
Proof. intros a b. unfold xmin. rewrite lt_xval. now destruct (xlt (xv b) (xv a)). Qed.

Lemma select_lt_xmax : forall a b : float, xv (if flt a b then b else a) = xmax (xv a) (xv b).
Proof. intros a b. unfold xmax. rewrite lt_xval. now destruct (xlt (xv a) (xv b)). Qed.

Variables xl xu yl yu : xreal.
Variables x y : R.
Hypothesis Hxl : xle xl (XFin x) = true.
Hypothesis Hxu : xle (XFin x) xu = true.
Hypothesis Hyl : xle yl (XFin y) = true.
Hypothesis Hyu : xle (XFin y) yu = true.

(* The lower bound of the product of two intervals. If the limbs d1, d2, d3, d4 are at
   most the four products of bounds, then the limb l that the three lines
       ma = lt(d2, d1);  da = select(ma, d2, d1)
       mb = lt(d4, d3);  db = select(mb, d4, d3)
       mc = lt(db, da);  l  = select(mc, db, da)
   of interval_mul_1 compute is at most x y, for all real x in [xl, xu], y in [yl, yu]. *)
Theorem interval_mul_lower :
  forall d1 d2 d3 d4 : float,
  xle (xv d1) (xmul0 xl yl) = true -> xle (xv d2) (xmul0 xl yu) = true ->
  xle (xv d3) (xmul0 xu yl) = true -> xle (xv d4) (xmul0 xu yu) = true ->
  let ma := flt d2 d1 in
  let da := if ma then d2 else d1 in
  let mb := flt d4 d3 in
  let db := if mb then d4 else d3 in
  let mc := flt db da in
  let l := if mc then db else da in
  xle (xv l) (XFin (x * y)) = true.
Proof.
intros d1 d2 d3 d4 H1 H2 H3 H4. cbv zeta.
rewrite 3!select_lt_xmin.
exact (rectangle_lower_bound xl xu yl yu x y Hxl Hxu Hyl Hyu _ _ _ _ H1 H2 H3 H4).
Qed.

(* The upper bound, likewise: if the limbs v1, v2, v3, v4 are at least the four products
   of bounds, then the limb h of the three lines
       na = lt(v1, v2);  va = select(na, v2, v1)
       nb = lt(v3, v4);  vb = select(nb, v4, v3)
       nc = lt(va, vb);  h  = select(nc, vb, va)
   is at least x y. *)
Theorem interval_mul_upper :
  forall v1 v2 v3 v4 : float,
  xle (xmul0 xl yl) (xv v1) = true -> xle (xmul0 xl yu) (xv v2) = true ->
  xle (xmul0 xu yl) (xv v3) = true -> xle (xmul0 xu yu) (xv v4) = true ->
  let na := flt v1 v2 in
  let va := if na then v2 else v1 in
  let nb := flt v3 v4 in
  let vb := if nb then v4 else v3 in
  let nc := flt va vb in
  let h := if nc then vb else va in
  xle (XFin (x * y)) (xv h) = true.
Proof.
intros v1 v2 v3 v4 H1 H2 H3 H4. cbv zeta.
rewrite 3!select_lt_xmax.
exact (rectangle_upper_bound xl xu yl yu x y Hxl Hxu Hyl Hyu _ _ _ _ H1 H2 H3 H4).
Qed.

(* The limb chosen is one of the four, so what is known of each of the four (that it is
   the rounding of a product of bounds, or one step beyond it) is known of the bound
   returned. *)
Lemma select_lt_one_of_four :
  forall (d1 d2 d3 d4 : float) (m1 m2 m3 : bool),
  let da := if m1 then d2 else d1 in
  let db := if m2 then d4 else d3 in
  let l := if m3 then db else da in
  l = d1 \/ l = d2 \/ l = d3 \/ l = d4.
Proof. intros d1 d2 d3 d4 [|] [|] [|]; cbv zeta; auto. Qed.

End Limbs.
