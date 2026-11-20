(* The exact interval kernels of stage B1, in the IEEE model, on all values: the negation and
   the constructor of an interval with bounds of two limbs (interval_neg_2, interval_make_2),
   and the hull and the intersection of two intervals with bounds of one and of two limbs
   (interval_hull_1, interval_hull_2, interval_intersection_1, interval_intersection_2)
   (docs/developer/design/milestone2.md, "Interval kernels": "Values of an interval" and
   "Two limbs"; "One enclosure interface").

   Notation as in IeeeInterval1.v and IeeeInterval2.v: xval and xval_2 are the extended real
   numbers a limb and a canonical 2-limb value stand for; an interval, its members, its
   emptiness and the bounds of a set of real numbers are those of IeeeIntervalVocabulary.v.
   X, Y are the operands and Z the result. The six kernels are the generated models of
   proofs/gen/IeeeModel.v, and the theorems K_correct at the end of the file establish their
   generated statements (proofs/gen/IeeeStatements.v). For every precision.

   What is proved.

   - interval_neg_2, for a canonical operand (interval_neg_2_correct): Z is canonical; it is
     empty exactly when X is; it contains -x for every member x of X; its bounds are the
     bounds of the exact range of -x (the negation is exact); and for a bounded X, Z is
     bounded and every member of the exact range is below 2^emax in magnitude (a finite
     canonical 2-limb value is: normalized_inrange of IeeeBallConvert.v), so that both sides
     of the equivalence of the statement hold. The facts the difference needs
     (interval_neg_2_facts): the negated interval is canonical, empty, nonempty or bounded
     exactly when the operand is, and its members are the opposites of the operand's.

   - interval_make_2, for two canonical 2-limb values lo and hi (interval_make_2_correct):
     the result is a canonical interval; it is [lo, hi] when lo <= hi, lo < +infinity and
     hi > -infinity; the whole line ((-inf, +0), (+inf, +0)) when a leading limb is a NaN;
     and the empty set otherwise.

   - The hulls and the intersections, for canonical operands. The hull is [min, max] of the
     bounds: Z is canonical, empty exactly when both operands are, contains every member of
     either operand, and when it is not empty its bounds are the bounds of the union of the
     operands (the hull is the smallest interval that contains both). The intersection is
     [max, min] of the bounds when these are in order, and the empty set otherwise: Z is
     canonical, empty exactly when the operands have no common member, contains every
     common member, and when it is not empty its bounds are the bounds of the set of the
     common members (the intersection is exact).

   The proofs. Everything is said first of intervals of extended real numbers (xinterval:
   the empty pair (+inf, -inf) or a nonempty pair), in xhull and xinter: the hull [min a c,
   max b d] and the intersection [max a c, min b d] of [a, b] and [c, d]. A comparison and a
   select of limbs, or of 2-limb values (lt_2_2, le_2_2 on canonical values, IeeeExt.v), is
   then the minimum or the maximum of what they stand for (select_lt_xmin of Rectangle.v,
   select_lt_2_xmin here), and a canonical interval of two limbs is empty exactly when its
   bounds stand for +infinity and -infinity (interval_2_iff): a canonical value that stands
   for an infinity is that infinity followed by a zero. *)
From Stdlib Require Import Reals ZArith Bool Lia Lra Psatz.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements IeeeStatements.
From Kairn Require Import Format Normalized IeeeBridge IeeeVocabulary IeeeOps IeeeExt IeeeFull.
From Kairn Require Import Rectangle IeeeDirected IeeeIntervalVocabulary IeeeInterval1 IeeeInterval2.
From Kairn Require Import IeeeBallConvert.
From Kairn Require IeeeOperations.
From Kairn.Gen Require IeeeModel.
Open Scope R_scope.

(** * Intervals of extended real numbers *)

(* The pairs of bounds of the canonical intervals: the empty pair (+infinity, -infinity), or
   a nonempty pair. *)
Definition xinterval (a b : xreal) : Prop :=
  (a = XInf false /\ b = XInf true) \/ xnonempty a b.

Lemma xinterval_refl : forall a b : xreal, xinterval a b -> xle a a = true /\ xle b b = true.
Proof.
intros a b [[Ea Eb]|H].
- subst a b. split; reflexivity.
- split; [exact (xle_refl_l _ _ (proj1 H))|exact (xle_refl_r _ _ (proj1 H))].
Qed.

Lemma xopp_eq_inf : forall (a : xreal) (s : bool), xopp a = XInf s <-> a = XInf (negb s).
Proof.
intros a s. split; intros H.
- rewrite <- (xopp_involutive a), H. reflexivity.
- rewrite H. cbn [xopp]. now rewrite negb_involutive.
Qed.

Lemma xinterval_opp : forall a b : xreal, xinterval a b -> xinterval (xopp b) (xopp a).
Proof.
intros a b [[Ea Eb]|H].
- left. subst a b. split; reflexivity.
- right. now apply xnonempty_opp.
Qed.

(* -infinity is below an extended real number exactly when the opposite of that number is
   below +infinity. *)
Lemma xlt_opp_pinf : forall a : xreal, xlt (xopp a) (XInf false) = xlt (XInf true) a.
Proof. intros [|[|]|r]; reflexivity. Qed.

(** * The hull *)

(* The hull of [a, b] and [c, d]: [min a c, max b d] is an interval; it is the empty pair
   exactly when both are; it contains every member of either; and when it is not the empty
   pair its bounds are the bounds of the union. *)
Lemma xhull :
  forall a b c d : xreal, xinterval a b -> xinterval c d ->
  xinterval (xmin a c) (xmax b d) /\
  ((xmin a c = XInf false /\ xmax b d = XInf true) <->
   (a = XInf false /\ b = XInf true) /\ (c = XInf false /\ d = XInf true)) /\
  (forall z : R, xmember a b z \/ xmember c d z -> xmember (xmin a c) (xmax b d) z) /\
  (~ (xmin a c = XInf false /\ xmax b d = XInf true) ->
   forall lo hi : xreal,
   range_lower (fun z : R => xmember a b z \/ xmember c d z) lo ->
   range_upper (fun z : R => xmember a b z \/ xmember c d z) hi ->
   xmin a c = lo /\ xmax b d = hi).
Proof.
intros a b c d X Y.
destruct (xinterval_refl a b X) as [Ra Rb]. destruct (xinterval_refl c d Y) as [Rc Rd].
assert (I3 : forall z : R, xmember a b z \/ xmember c d z -> xmember (xmin a c) (xmax b d) z).
{ intros z [[H K]|[H K]]; split.
  - exact (xle_trans _ _ _ (xmin_le_l a c Ra Rc) H).
  - exact (xle_trans _ _ _ K (xmax_ge_l b d Rb Rd)).
  - exact (xle_trans _ _ _ (xmin_le_r a c Ra Rc) H).
  - exact (xle_trans _ _ _ K (xmax_ge_r b d Rb Rd)). }
assert (Both : (a = XInf false /\ b = XInf true) /\ (c = XInf false /\ d = XInf true) ->
               xmin a c = XInf false /\ xmax b d = XInf true).
{ intros [[Ea Eb] [Ec Ed]]. subst a b c d. split; reflexivity. }
assert (Some : ~ ((a = XInf false /\ b = XInf true) /\ (c = XInf false /\ d = XInf true)) ->
               exists z : R, xmember a b z \/ xmember c d z).
{ intros N. destruct X as [EX|NX]; [destruct Y as [EY|NY]|].
  - elim N. split; assumption.
  - destruct (xnonempty_member c d NY) as [z Hz]. exists z. now right.
  - destruct (xnonempty_member a b NX) as [z Hz]. exists z. now left. }
assert (I2 : (xmin a c = XInf false /\ xmax b d = XInf true) <->
             (a = XInf false /\ b = XInf true) /\ (c = XInf false /\ d = XInf true)).
{ split; [|exact Both]. intros [E1 E2].
  destruct X as [EX|NX]; [destruct Y as [EY|NY]|].
  - split; assumption.
  - exfalso. destruct (xnonempty_member c d NY) as [z Hz].
    apply (xmember_empty z). rewrite <- E1, <- E2. apply I3. now right.
  - exfalso. destruct (xnonempty_member a b NX) as [z Hz].
    apply (xmember_empty z). rewrite <- E1, <- E2. apply I3. now left. }
assert (I1 : xinterval (xmin a c) (xmax b d)).
{ destruct X as [EX|NX]; [destruct Y as [EY|NY]|].
  - left. apply Both. split; assumption.
  - right. destruct (xnonempty_member c d NY) as [z Hz].
    apply (xmember_nonempty _ _ z). apply I3. now right.
  - right. destruct (xnonempty_member a b NX) as [z Hz].
    apply (xmember_nonempty _ _ z). apply I3. now left. }
split; [exact I1|split; [exact I2|split; [exact I3|]]].
intros NE lo hi Hlo Hhi.
assert (Ex : exists z : R, xmember a b z \/ xmember c d z).
{ apply Some. intros K. apply NE. exact (Both K). }
split.
- apply (range_lower_unique _ _ _ Ex); [|exact Hlo]. split.
  + intros z Hz. exact (proj1 (I3 z Hz)).
  + intros t Ht. destruct (xmin_cases a c) as [E|E]; rewrite E in Ht.
    * destruct X as [[Ea _]|NX]; [subst a; cbn in Ht; discriminate Ht|].
      destruct (xmember_approach_lower a b NX t Ht) as [z [Hz Lz]].
      exists z. split; [now left|exact Lz].
    * destruct Y as [[Ec _]|NY]; [subst c; cbn in Ht; discriminate Ht|].
      destruct (xmember_approach_lower c d NY t Ht) as [z [Hz Lz]].
      exists z. split; [now right|exact Lz].
- apply (range_upper_unique _ _ _ Ex); [|exact Hhi]. split.
  + intros z Hz. exact (proj2 (I3 z Hz)).
  + intros t Ht. destruct (xmax_cases b d) as [E|E]; rewrite E in Ht.
    * destruct X as [[_ Eb]|NX]; [subst b; cbn in Ht; discriminate Ht|].
      destruct (xmember_approach_upper a b NX t Ht) as [z [Hz Lz]].
      exists z. split; [now left|exact Lz].
    * destruct Y as [[_ Ed]|NY]; [subst d; cbn in Ht; discriminate Ht|].
      destruct (xmember_approach_upper c d NY t Ht) as [z [Hz Lz]].
      exists z. split; [now right|exact Lz].
Qed.

(** * The intersection *)

(* For bounds that are not NaN: the larger of two lower bounds is at most z exactly when
   both are, and the smaller of two upper bounds is at least z exactly when both are. *)
Lemma xmax_le_iff :
  forall (a c : xreal) (z : R), xle a a = true -> xle c c = true ->
  xle (xmax a c) (XFin z) = andb (xle a (XFin z)) (xle c (XFin z)).
Proof. intros [|[|]|a] [|[|]|c] z; unfold xmax; xcase. Qed.

Lemma xmin_ge_iff :
  forall (b d : xreal) (z : R), xle b b = true -> xle d d = true ->
  xle (XFin z) (xmin b d) = andb (xle (XFin z) b) (xle (XFin z) d).
Proof. intros [|[|]|b] [|[|]|d] z; unfold xmin; xcase. Qed.

Lemma xmember_inter :
  forall a b c d : xreal,
  xle a a = true -> xle b b = true -> xle c c = true -> xle d d = true ->
  forall z : R, xmember a b z /\ xmember c d z <-> xmember (xmax a c) (xmin b d) z.
Proof.
intros a b c d Ra Rb Rc Rd z. unfold xmember.
rewrite (xmax_le_iff a c z Ra Rc), (xmin_ge_iff b d z Rb Rd).
rewrite !andb_true_iff. tauto.
Qed.

Lemma xmax_pinf_l : forall c : xreal, xmax (XInf false) c = XInf false.
Proof. intros [|[|]|c]; reflexivity. Qed.

Lemma xmin_ninf_l : forall d : xreal, xmin (XInf true) d = XInf true.
Proof. intros [|[|]|d]; reflexivity. Qed.

Lemma xmax_pinf_r : forall a : xreal, xlt a (XInf false) = true -> xmax a (XInf false) = XInf false.
Proof. intros a H. unfold xmax. now rewrite H. Qed.

Lemma xmin_ninf_r : forall b : xreal, xlt (XInf true) b = true -> xmin b (XInf true) = XInf true.
Proof. intros b H. unfold xmin. now rewrite H. Qed.

(* The intersection of [a, b] and [c, d]: its members are those of [max a c, min b d]; that
   pair is a nonempty interval when its bounds are in order, and the two have no common
   member otherwise. *)
Lemma xinter :
  forall a b c d : xreal, xinterval a b -> xinterval c d ->
  (forall z : R, xmember a b z /\ xmember c d z <-> xmember (xmax a c) (xmin b d) z) /\
  (xle (xmax a c) (xmin b d) = true -> xnonempty (xmax a c) (xmin b d)) /\
  (xle (xmax a c) (xmin b d) = false -> forall z : R, ~ (xmember a b z /\ xmember c d z)).
Proof.
intros a b c d X Y.
destruct (xinterval_refl a b X) as [Ra Rb]. destruct (xinterval_refl c d Y) as [Rc Rd].
assert (M := xmember_inter a b c d Ra Rb Rc Rd).
split; [exact M|split].
- intros H.
  destruct X as [[Ea Eb]|NX].
  { exfalso. subst a b. rewrite xmax_pinf_l, xmin_ninf_l in H. discriminate H. }
  destruct Y as [[Ec Ed]|NY].
  { exfalso. subst c d.
    rewrite (xmax_pinf_r a (proj1 (proj2 NX))), (xmin_ninf_r b (proj2 (proj2 NX))) in H.
    discriminate H. }
  split; [exact H|split].
  + destruct (xmax_cases a c) as [E|E]; rewrite E;
      [exact (proj1 (proj2 NX))|exact (proj1 (proj2 NY))].
  + destruct (xmin_cases b d) as [E|E]; rewrite E;
      [exact (proj2 (proj2 NX))|exact (proj2 (proj2 NY))].
- intros H z Hz. destruct (proj1 (M z) Hz) as [K1 K2].
  rewrite (xle_trans _ _ _ K1 K2) in H. discriminate H.
Qed.

(** * Limbs and 2-limb values *)

Section IeeeIntervalExact.
Variable prec emax : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Context {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}.

Notation float := (binary_float prec emax).
Notation nan_of := {x : float | is_nan prec emax x = true}.

Notation emin := (3 - emax - prec)%Z.
Notation fin x := (is_finite prec emax x = true).
Notation b2r := (B2R prec emax).
Notation flt := (IeeeOperations.lt prec emax).
Notation fle := (IeeeOperations.le prec emax).
Notation pzero := (IeeeOperations.pzero prec emax).
Notation pinf := (IeeeOperations.pinf prec emax).
Notation ninf := (B754_infinity prec emax true).
Notation xv := (@xval prec emax).
Notation xv2 := (@xval_2 prec emax).
Notation lt_2_2 := (IeeeModel.lt_2_2 prec emax).
Notation le_2_2 := (IeeeModel.le_2_2 prec emax).

Let Hp1 : (1 <= prec)%Z.
Proof. generalize prec_gt_0_. unfold Prec_gt_0. lia. Qed.

(* One limb: a canonical interval is a pair of bounds of xinterval. *)
Lemma interval_1_xinterval : forall l h : float, interval_1 l h <-> xinterval (xv l) (xv h).
Proof.
intros l h. unfold interval_1, xinterval, interval_nonempty_1.
rewrite (interval_empty_1_xval prec emax). tauto.
Qed.

(* Two limbs. A canonical value that stands for an infinity is that infinity followed by a
   zero. *)
Lemma canonical_inf :
  forall x0 x1 : float, canonical_2 x0 x1 ->
  forall s : bool, xv2 x0 x1 = XInf s -> x0 = infinity prec emax s /\ zero x1.
Proof.
intros x0 x1 C s E.
destruct (canonical_cases prec emax x0 x1 C)
  as [[_ [_ [_ [_ [_ E']]]]]|[[t [t' [E0 [E1 [_ [_ E']]]]]]|[_ [_ [_ [_ E']]]]]];
  rewrite E' in E; try discriminate E.
injection E as E. subst t x0 x1. split; [reflexivity|exists t'; reflexivity].
Qed.

Lemma xval_2_nan : forall x0 x1 : float, is_nan prec emax x0 = true -> xv2 x0 x1 = XNaN.
Proof.
intros x0 x1 N. unfold xval_2. now rewrite (nan_not_finite prec emax x0 N), N.
Qed.

Lemma xlt_ninf_xval_2 :
  forall x0 x1 : float, xlt (XInf true) (xv2 x0 x1) = xlt (XInf true) (xv x0).
Proof.
intros x0 x1. destruct (is_finite prec emax x0) eqn:F.
- rewrite (xval_2_fin prec emax x0 x1 F), (xval_fin prec emax x0 F). reflexivity.
- now rewrite (xval_2_lead prec emax x0 x1 F).
Qed.

(* The bounds of a canonical interval of two limbs are canonical; it is empty exactly when
   they stand for +infinity and -infinity; and a pair of canonical values is a canonical
   interval exactly when what they stand for is a pair of xinterval. *)
Lemma interval_2_canonical :
  forall l0 l1 h0 h1 : float, interval_2 l0 l1 h0 h1 -> canonical_2 l0 l1 /\ canonical_2 h0 h1.
Proof.
intros l0 l1 h0 h1 [[E0 [Z1 [E2 Z3]]]|[Cl [Ch _]]]; [|split; assumption].
split; right; left; (split; [|assumption]); [exists false; exact E0|exists true; exact E2].
Qed.

Lemma interval_2_iff :
  forall l0 l1 h0 h1 : float, canonical_2 l0 l1 -> canonical_2 h0 h1 ->
  (interval_empty_2 l0 l1 h0 h1 <-> xv2 l0 l1 = XInf false /\ xv2 h0 h1 = XInf true) /\
  (interval_2 l0 l1 h0 h1 <-> xinterval (xv2 l0 l1) (xv2 h0 h1)).
Proof.
intros l0 l1 h0 h1 Cl Ch.
assert (E : interval_empty_2 l0 l1 h0 h1 <-> xv2 l0 l1 = XInf false /\ xv2 h0 h1 = XInf true).
{ split.
  - intros [E0 [_ [E2 _]]]. subst l0 h0. split; reflexivity.
  - intros [E0 E2]. destruct (canonical_inf l0 l1 Cl false E0) as [F0 Z1].
    destruct (canonical_inf h0 h1 Ch true E2) as [F2 Z3].
    exact (conj F0 (conj Z1 (conj F2 Z3))). }
split; [exact E|]. unfold interval_2, xinterval, interval_nonempty_2. rewrite E. tauto.
Qed.

(* Selecting by lt_2_2 one of two canonical values gives a canonical value, the smaller or
   the larger of the two. *)
Lemma select_lt_2_xmin :
  forall a0 a1 b0 b1 : float, canonical_2 a0 a1 -> canonical_2 b0 b1 ->
  canonical_2 (if lt_2_2 b0 b1 a0 a1 then b0 else a0) (if lt_2_2 b0 b1 a0 a1 then b1 else a1) /\
  xv2 (if lt_2_2 b0 b1 a0 a1 then b0 else a0) (if lt_2_2 b0 b1 a0 a1 then b1 else a1)
  = xmin (xv2 a0 a1) (xv2 b0 b1).
Proof.
intros a0 a1 b0 b1 Ca Cb. rewrite (lt_2_2_ext prec emax Hp1 b0 b1 a0 a1 Cb Ca). unfold xmin.
destruct (xlt (xv2 b0 b1) (xv2 a0 a1)); split; trivial.
Qed.

Lemma select_lt_2_xmax :
  forall a0 a1 b0 b1 : float, canonical_2 a0 a1 -> canonical_2 b0 b1 ->
  canonical_2 (if lt_2_2 a0 a1 b0 b1 then b0 else a0) (if lt_2_2 a0 a1 b0 b1 then b1 else a1) /\
  xv2 (if lt_2_2 a0 a1 b0 b1 then b0 else a0) (if lt_2_2 a0 a1 b0 b1 then b1 else a1)
  = xmax (xv2 a0 a1) (xv2 b0 b1).
Proof.
intros a0 a1 b0 b1 Ca Cb. rewrite (lt_2_2_ext prec emax Hp1 a0 a1 b0 b1 Ca Cb). unfold xmax.
destruct (xlt (xv2 a0 a1) (xv2 b0 b1)); split; trivial.
Qed.

(** * The hull and the intersection of two intervals with bounds of one limb *)

(* The hull, for any two limbs zl and zu that stand for the minimum of the lower bounds and
   the maximum of the upper bounds. *)
Lemma hull_1_of :
  forall xl xu yl yu zl zu : float,
  interval_1 xl xu -> interval_1 yl yu ->
  xv zl = xmin (xv xl) (xv yl) -> xv zu = xmax (xv xu) (xv yu) ->
  interval_1 zl zu /\
  (interval_empty_1 zl zu <-> interval_empty_1 xl xu /\ interval_empty_1 yl yu) /\
  (forall z : R, in_interval_1 xl xu z \/ in_interval_1 yl yu z -> in_interval_1 zl zu z) /\
  (~ interval_empty_1 zl zu ->
   forall lo hi : xreal,
   range_lower (fun z : R => in_interval_1 xl xu z \/ in_interval_1 yl yu z) lo ->
   range_upper (fun z : R => in_interval_1 xl xu z \/ in_interval_1 yl yu z) hi ->
   xval zl = lo /\ xval zu = hi).
Proof.
intros xl xu yl yu zl zu CX CY El Eu.
apply interval_1_xinterval in CX. apply interval_1_xinterval in CY.
destruct (xhull _ _ _ _ CX CY) as [I1 [I2 [I3 I4]]].
rewrite <- El, <- Eu in I1, I2, I3, I4.
split; [now apply interval_1_xinterval|].
split; [rewrite 3!(interval_empty_1_xval prec emax); exact I2|].
split; [exact I3|].
intros NE. apply I4. intros K. apply NE. now apply (interval_empty_1_xval prec emax).
Qed.

(* The intersection, for any two limbs l and h that stand for the maximum of the lower
   bounds and the minimum of the upper bounds, and ok their comparison. *)
Lemma intersection_1_of :
  forall xl xu yl yu l h : float, forall ok : bool,
  interval_1 xl xu -> interval_1 yl yu ->
  xv l = xmax (xv xl) (xv yl) -> xv h = xmin (xv xu) (xv yu) -> ok = xle (xv l) (xv h) ->
  interval_1 (if ok then l else pinf) (if ok then h else ninf) /\
  (interval_empty_1 (if ok then l else pinf) (if ok then h else ninf) <->
   ~ (exists z : R, in_interval_1 xl xu z /\ in_interval_1 yl yu z)) /\
  (forall z : R, in_interval_1 xl xu z /\ in_interval_1 yl yu z ->
   in_interval_1 (if ok then l else pinf) (if ok then h else ninf) z) /\
  (~ interval_empty_1 (if ok then l else pinf) (if ok then h else ninf) ->
   forall lo hi : xreal,
   range_lower (fun z : R => in_interval_1 xl xu z /\ in_interval_1 yl yu z) lo ->
   range_upper (fun z : R => in_interval_1 xl xu z /\ in_interval_1 yl yu z) hi ->
   xval (if ok then l else pinf) = lo /\ xval (if ok then h else ninf) = hi).
Proof.
intros xl xu yl yu l h ok CX CY El Eh Eok.
apply interval_1_xinterval in CX. apply interval_1_xinterval in CY.
destruct (xinter _ _ _ _ CX CY) as [M [T F]].
rewrite <- El, <- Eh in M, T, F. rewrite <- Eok in T, F.
destruct ok; cbv beta iota.
- assert (N := T eq_refl).
  assert (NE : ~ interval_empty_1 l h) by exact (nonempty_not_empty prec emax l h N).
  destruct (xnonempty_member _ _ N) as [m Hm].
  assert (Ex : exists z : R, in_interval_1 xl xu z /\ in_interval_1 yl yu z)
    by (exists m; now apply M).
  split; [right; exact N|].
  split; [split; [intros K; elim (NE K)|intros K; elim (K Ex)]|].
  split; [intros z Hz; now apply M|].
  intros _ lo hi Hlo Hhi.
  assert (Ext : forall z : R, xmember (xv l) (xv h) z <->
                              in_interval_1 xl xu z /\ in_interval_1 yl yu z)
    by (intros z; split; intros K; now apply M).
  split.
  + exact (range_lower_unique _ _ _ Ex
             (range_lower_ext _ _ _ Ext (range_member_lower _ _ N)) Hlo).
  + exact (range_upper_unique _ _ _ Ex
             (range_upper_ext _ _ _ Ext (range_member_upper _ _ N)) Hhi).
- assert (E : interval_empty_1 pinf ninf) by (split; reflexivity).
  split; [left; exact E|].
  split; [split; [intros _ [z Hz]; exact (F eq_refl z Hz)|intros _; exact E]|].
  split; [intros z Hz; elim (F eq_refl z Hz)|].
  intros K. elim (K E).
Qed.

(** * The hull and the intersection of two intervals with bounds of two limbs *)

Lemma hull_2_of :
  forall xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 zl0 zl1 zu0 zu1 : float,
  interval_2 xl0 xl1 xu0 xu1 -> interval_2 yl0 yl1 yu0 yu1 ->
  canonical_2 zl0 zl1 -> xv2 zl0 zl1 = xmin (xv2 xl0 xl1) (xv2 yl0 yl1) ->
  canonical_2 zu0 zu1 -> xv2 zu0 zu1 = xmax (xv2 xu0 xu1) (xv2 yu0 yu1) ->
  interval_2 zl0 zl1 zu0 zu1 /\
  (interval_empty_2 zl0 zl1 zu0 zu1 <->
   interval_empty_2 xl0 xl1 xu0 xu1 /\ interval_empty_2 yl0 yl1 yu0 yu1) /\
  (forall z : R, in_interval_2 xl0 xl1 xu0 xu1 z \/ in_interval_2 yl0 yl1 yu0 yu1 z ->
   in_interval_2 zl0 zl1 zu0 zu1 z) /\
  (~ interval_empty_2 zl0 zl1 zu0 zu1 ->
   forall lo hi : xreal,
   range_lower (fun z : R => in_interval_2 xl0 xl1 xu0 xu1 z \/ in_interval_2 yl0 yl1 yu0 yu1 z) lo ->
   range_upper (fun z : R => in_interval_2 xl0 xl1 xu0 xu1 z \/ in_interval_2 yl0 yl1 yu0 yu1 z) hi ->
   xval_2 zl0 zl1 = lo /\ xval_2 zu0 zu1 = hi).
Proof.
intros xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 zl0 zl1 zu0 zu1 CX CY Czl El Czu Eu.
destruct (interval_2_canonical _ _ _ _ CX) as [Cxl Cxu].
destruct (interval_2_canonical _ _ _ _ CY) as [Cyl Cyu].
destruct (interval_2_iff _ _ _ _ Cxl Cxu) as [EX IX].
destruct (interval_2_iff _ _ _ _ Cyl Cyu) as [EY IY].
destruct (interval_2_iff _ _ _ _ Czl Czu) as [EZ IZ].
destruct (xhull _ _ _ _ (proj1 IX CX) (proj1 IY CY)) as [I1 [I2 [I3 I4]]].
rewrite <- El, <- Eu in I1, I2, I3, I4.
split; [now apply IZ|].
split; [rewrite EZ, EX, EY; exact I2|].
split; [exact I3|].
intros NE. apply I4. intros K. apply NE. now apply EZ.
Qed.

Lemma intersection_2_of :
  forall xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 l0 l1 h0 h1 : float, forall ok : bool,
  interval_2 xl0 xl1 xu0 xu1 -> interval_2 yl0 yl1 yu0 yu1 ->
  canonical_2 l0 l1 -> xv2 l0 l1 = xmax (xv2 xl0 xl1) (xv2 yl0 yl1) ->
  canonical_2 h0 h1 -> xv2 h0 h1 = xmin (xv2 xu0 xu1) (xv2 yu0 yu1) ->
  ok = xle (xv2 l0 l1) (xv2 h0 h1) ->
  let zl0 := if ok then l0 else pinf in
  let zl1 := if ok then l1 else pzero in
  let zu0 := if ok then h0 else ninf in
  let zu1 := if ok then h1 else pzero in
  interval_2 zl0 zl1 zu0 zu1 /\
  (interval_empty_2 zl0 zl1 zu0 zu1 <->
   ~ (exists z : R, in_interval_2 xl0 xl1 xu0 xu1 z /\ in_interval_2 yl0 yl1 yu0 yu1 z)) /\
  (forall z : R, in_interval_2 xl0 xl1 xu0 xu1 z /\ in_interval_2 yl0 yl1 yu0 yu1 z ->
   in_interval_2 zl0 zl1 zu0 zu1 z) /\
  (~ interval_empty_2 zl0 zl1 zu0 zu1 ->
   forall lo hi : xreal,
   range_lower (fun z : R => in_interval_2 xl0 xl1 xu0 xu1 z /\ in_interval_2 yl0 yl1 yu0 yu1 z) lo ->
   range_upper (fun z : R => in_interval_2 xl0 xl1 xu0 xu1 z /\ in_interval_2 yl0 yl1 yu0 yu1 z) hi ->
   xval_2 zl0 zl1 = lo /\ xval_2 zu0 zu1 = hi).
Proof.
intros xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 l0 l1 h0 h1 ok CX CY Cl El Ch Eh Eok. cbv zeta.
destruct (interval_2_canonical _ _ _ _ CX) as [Cxl Cxu].
destruct (interval_2_canonical _ _ _ _ CY) as [Cyl Cyu].
destruct (interval_2_iff _ _ _ _ Cxl Cxu) as [_ IX].
destruct (interval_2_iff _ _ _ _ Cyl Cyu) as [_ IY].
destruct (xinter _ _ _ _ (proj1 IX CX) (proj1 IY CY)) as [M [T F]].
rewrite <- El, <- Eh in M, T, F. rewrite <- Eok in T, F.
destruct ok; cbv beta iota.
- assert (N := T eq_refl).
  assert (NZ : interval_nonempty_2 l0 l1 h0 h1) by exact (conj Cl (conj Ch N)).
  assert (NE : ~ interval_empty_2 l0 l1 h0 h1).
  { intros K. destruct (xnonempty_member _ _ N) as [m Hm].
    destruct K as [K0 [_ [K2 _]]]. destruct Hm as [Hm _].
    rewrite K0 in Hm. discriminate Hm. }
  destruct (xnonempty_member _ _ N) as [m Hm].
  assert (Ex : exists z : R, in_interval_2 xl0 xl1 xu0 xu1 z /\ in_interval_2 yl0 yl1 yu0 yu1 z)
    by (exists m; now apply M).
  split; [right; exact NZ|].
  split; [split; [intros K; elim (NE K)|intros K; elim (K Ex)]|].
  split; [intros z Hz; now apply M|].
  intros _ lo hi Hlo Hhi.
  assert (Ext : forall z : R, xmember (xv2 l0 l1) (xv2 h0 h1) z <->
                              in_interval_2 xl0 xl1 xu0 xu1 z /\ in_interval_2 yl0 yl1 yu0 yu1 z)
    by (intros z; split; intros K; now apply M).
  split.
  + exact (range_lower_unique _ _ _ Ex
             (range_lower_ext _ _ _ Ext (range_member_lower _ _ N)) Hlo).
  + exact (range_upper_unique _ _ _ Ex
             (range_upper_ext _ _ _ Ext (range_member_upper _ _ N)) Hhi).
- assert (E : interval_empty_2 pinf pzero ninf pzero).
  { split; [reflexivity|split; [exists false; reflexivity|split; [reflexivity|]]].
    exists false; reflexivity. }
  split; [left; exact E|].
  split; [split; [intros _ [z Hz]; exact (F eq_refl z Hz)|intros _; exact E]|].
  split; [intros z Hz; elim (F eq_refl z Hz)|].
  intros K. elim (K E).
Qed.

(* The negation and the constructor use the NaN of a sign change. *)
Variable nan_opp : float -> nan_of.
Notation neg := (IeeeOperations.neg prec emax nan_opp).

(** * interval_neg_2 *)

Lemma xval_2_neg : forall x0 x1 : float, xv2 (neg x0) (neg x1) = xopp (xv2 x0 x1).
Proof.
intros x0 x1. unfold xval_2, val.
rewrite (IeeeExt.neg_finite prec emax nan_opp), (neg_nan prec emax nan_opp).
destruct (is_finite prec emax x0) eqn:F.
- rewrite 2!(IeeeExt.neg_value prec emax nan_opp). cbn [xopp]. f_equal. ring.
- destruct (is_nan prec emax x0) eqn:N; [reflexivity|].
  destruct x0 as [s|s|s pl H|s m e H]; try discriminate F; try discriminate N. reflexivity.
Qed.

(* The negated interval (-xu, -xl): canonical, empty, nonempty and bounded exactly when the
   operand is, and its members are the opposites of the operand's. *)
Lemma interval_neg_2_facts :
  forall xl0 xl1 xu0 xu1 : float, interval_2 xl0 xl1 xu0 xu1 ->
  interval_2 (neg xu0) (neg xu1) (neg xl0) (neg xl1) /\
  (interval_empty_2 (neg xu0) (neg xu1) (neg xl0) (neg xl1) <-> interval_empty_2 xl0 xl1 xu0 xu1) /\
  (interval_nonempty_2 xl0 xl1 xu0 xu1 -> interval_nonempty_2 (neg xu0) (neg xu1) (neg xl0) (neg xl1)) /\
  (interval_bounded_2 (neg xu0) (neg xu1) (neg xl0) (neg xl1) <-> interval_bounded_2 xl0 xl1 xu0 xu1) /\
  (forall x : R, in_interval_2 xl0 xl1 xu0 xu1 x ->
   in_interval_2 (neg xu0) (neg xu1) (neg xl0) (neg xl1) (- x)) /\
  (forall x : R, in_interval_2 (neg xu0) (neg xu1) (neg xl0) (neg xl1) x ->
   in_interval_2 xl0 xl1 xu0 xu1 (- x)) /\
  xv2 (neg xu0) (neg xu1) = xopp (xv2 xu0 xu1) /\ xv2 (neg xl0) (neg xl1) = xopp (xv2 xl0 xl1).
Proof.
intros xl0 xl1 xu0 xu1 CX.
destruct (interval_2_canonical _ _ _ _ CX) as [Cl Ch].
generalize (neg_2_ext prec emax nan_opp xl0 xl1 Cl) (neg_2_ext prec emax nan_opp xu0 xu1 Ch).
unfold IeeeModel.neg_2. cbv beta iota zeta. intros [Cl' _] [Ch' _].
assert (El := xval_2_neg xl0 xl1). assert (Eh := xval_2_neg xu0 xu1).
destruct (interval_2_iff _ _ _ _ Cl Ch) as [EX IX].
destruct (interval_2_iff _ _ _ _ Ch' Cl') as [EZ IZ].
split; [apply IZ; rewrite El, Eh; apply xinterval_opp; now apply IX|].
split.
{ rewrite EZ, EX, El, Eh, 2!xopp_eq_inf. cbn [negb]. tauto. }
split.
{ intros [_ [_ N]]. split; [exact Ch'|split; [exact Cl'|]]. rewrite El, Eh.
  now apply xnonempty_opp. }
split.
{ unfold interval_bounded_2, finite. rewrite 2!(IeeeExt.neg_finite prec emax nan_opp). tauto. }
split.
{ intros x Hx. unfold in_interval_2 in *. rewrite El, Eh. now apply xmember_opp. }
split; [|split; assumption].
intros x Hx. unfold in_interval_2 in *. rewrite El, Eh in Hx.
generalize (xmember_opp _ _ _ Hx). now rewrite 2!xopp_involutive.
Qed.

(* interval_neg_2, for a canonical operand X, for every precision: the generated statement.
   The bounds of Z are the bounds of the exact range of -x (range_neg_lower,
   range_neg_upper); a bounded X gives a bounded Z, and every member of the exact range is
   then below 2^emax in magnitude, so both sides of I5 hold. *)
Theorem interval_neg_2_all :
  forall xl0 xl1 xu0 xu1 : float,
  interval_2 xl0 xl1 xu0 xu1 ->
  let '(zl0, zl1, zu0, zu1) := IeeeModel.interval_neg_2 prec emax nan_opp xl0 xl1 xu0 xu1 in
  interval_2 zl0 zl1 zu0 zu1 /\
  (interval_empty_2 zl0 zl1 zu0 zu1 <-> interval_empty_2 xl0 xl1 xu0 xu1) /\
  (forall x : R, in_interval_2 xl0 xl1 xu0 xu1 x ->
   in_interval_2 zl0 zl1 zu0 zu1 (- x)) /\
  (interval_nonempty_2 xl0 xl1 xu0 xu1 ->
   forall lo hi : xreal,
   range_lower (range_1 (fun x : R => - x) (in_interval_2 xl0 xl1 xu0 xu1)) lo ->
   range_upper (range_1 (fun x : R => - x) (in_interval_2 xl0 xl1 xu0 xu1)) hi ->
   xval_2 zl0 zl1 = lo /\ xval_2 zu0 zu1 = hi) /\
  (interval_bounded_2 xl0 xl1 xu0 xu1 ->
   (interval_bounded_2 zl0 zl1 zu0 zu1 <->
    forall z : R,
    range_1 (fun x : R => - x) (in_interval_2 xl0 xl1 xu0 xu1) z ->
    Rabs z <= bpow radix2 emax)).
Proof.
intros xl0 xl1 xu0 xu1 CX.
unfold IeeeModel.interval_neg_2, IeeeModel.neg_2. cbv beta iota zeta.
destruct (interval_neg_2_facts xl0 xl1 xu0 xu1 CX) as [I1 [I2 [_ [B [I3 [_ [El Eh]]]]]]].
split; [exact I1|split; [exact I2|split; [exact I3|split]]].
- intros NX lo hi Hlo Hhi.
  destruct (xnonempty_member _ _ (proj2 (proj2 NX))) as [mx Mx].
  assert (Ex : exists z : R, range_1 (fun x : R => - x) (in_interval_2 xl0 xl1 xu0 xu1) z).
  { exists (- mx), mx. split; [exact Mx|reflexivity]. }
  rewrite El, Eh. split.
  + exact (range_lower_unique _ _ _ Ex (range_neg_lower _ _ (proj2 (proj2 NX))) Hlo).
  + exact (range_upper_unique _ _ _ Ex (range_neg_upper _ _ (proj2 (proj2 NX))) Hhi).
- intros BX. split; [intros _|intros _; now apply B].
  intros z [x [Hx E]]. cbv beta in E. rewrite E, Rabs_Ropp.
  destruct (interval_2_canonical _ _ _ _ CX) as [Cl Ch].
  destruct BX as [Fl Fh].
  destruct (canonical_2_finite prec emax xl0 xl1 Cl Fl) as [_ Nl].
  destruct (canonical_2_finite prec emax xu0 xu1 Ch Fh) as [_ Nh].
  assert (Ql := normalized_inrange prec emax xl0 xl1 Nl).
  assert (Qh := normalized_inrange prec emax xu0 xu1 Nh).
  destruct Hx as [H K]. unfold val in *.
  rewrite (xval_2_fin prec emax xl0 xl1 Fl) in H. rewrite (xval_2_fin prec emax xu0 xu1 Fh) in K.
  cbn [xle] in H, K. apply Rle_bool_inv in H. apply Rle_bool_inv in K.
  apply Rabs_lt_inv in Ql. apply Rabs_lt_inv in Qh. apply Rabs_le. lra.
Qed.

(** * interval_make_2 *)

(* interval_make_2, for two canonical 2-limb values lo and hi, for every precision: the
   result is a canonical interval; [lo, hi] when lo <= hi, lo < +infinity and
   hi > -infinity; the whole line when a leading limb is a NaN; the empty set otherwise. *)
Theorem interval_make_2_all :
  forall lo0 lo1 hi0 hi1 : float,
  canonical_2 lo0 lo1 -> canonical_2 hi0 hi1 ->
  let '(zl0, zl1, zu0, zu1) := IeeeModel.interval_make_2 prec emax nan_opp lo0 lo1 hi0 hi1 in
  interval_2 zl0 zl1 zu0 zu1 /\
  (xnonempty (xval_2 lo0 lo1) (xval_2 hi0 hi1) ->
   xval_2 zl0 zl1 = xval_2 lo0 lo1 /\ xval_2 zu0 zu1 = xval_2 hi0 hi1) /\
  (nan lo0 \/ nan hi0 ->
   zl0 = infinity prec emax true /\ zu0 = infinity prec emax false /\ zero zl1 /\ zero zu1) /\
  (~ nan lo0 -> ~ nan hi0 -> ~ xnonempty (xval_2 lo0 lo1) (xval_2 hi0 hi1) ->
   interval_empty_2 zl0 zl1 zu0 zu1).
Proof.
intros lo0 lo1 hi0 hi1 Cl Ch.
unfold IeeeModel.interval_make_2. cbv beta iota zeta.
rewrite (le_2_2_ext prec emax Hp1 lo0 lo1 hi0 hi1 Cl Ch).
rewrite (neg_pinf prec emax nan_opp).
rewrite (lt_xval prec emax lo0 pinf), (lt_xval prec emax ninf hi0), 2!(eq_self prec emax).
change (xv pinf) with (XInf false). change (xv ninf) with (XInf true).
rewrite <- (xlt_xval_2_pinf prec emax lo0 lo1), <- (xlt_ninf_xval_2 hi0 hi1).
assert (WholeZ : interval_2 ninf pzero pinf pzero).
{ right. split; [right; left; split; [exists true; reflexivity|exists false; reflexivity]|].
  split; [right; left; split; [exists false; reflexivity|exists false; reflexivity]|].
  split; [reflexivity|split; reflexivity]. }
assert (EmptyZ : interval_empty_2 pinf pzero ninf pzero).
{ split; [reflexivity|split; [exists false; reflexivity|split; [reflexivity|]]].
  exists false; reflexivity. }
destruct (andb (andb (xle (xv2 lo0 lo1) (xv2 hi0 hi1)) (xlt (xv2 lo0 lo1) (XInf false)))
               (xlt (XInf true) (xv2 hi0 hi1))) eqn:V; cbv beta iota.
- (* the pair describes an interval *)
  apply andb_true_iff in V. destruct V as [V V3]. apply andb_true_iff in V.
  destruct V as [V1 V2].
  assert (N : xnonempty (xv2 lo0 lo1) (xv2 hi0 hi1))
    by (split; [exact V1|split; [exact V2|exact V3]]).
  split; [right; exact (conj Cl (conj Ch N))|].
  split; [intros _; split; reflexivity|].
  split.
  + unfold nan. intros [K|K]; exfalso.
    * rewrite (xval_2_nan lo0 lo1 K) in V1. discriminate V1.
    * rewrite (xval_2_nan hi0 hi1 K) in V1. destruct (xv2 lo0 lo1) as [|[|]|r]; discriminate V1.
  + intros _ _ K. elim (K N).
- (* it describes none *)
  assert (NN : ~ xnonempty (xv2 lo0 lo1) (xv2 hi0 hi1)).
  { intros [N1 [N2 N3]]. rewrite N1, N2, N3 in V. discriminate V. }
  destruct (is_nan prec emax lo0) eqn:N1; [|destruct (is_nan prec emax hi0) eqn:N2];
    cbn [andb negb].
  + split; [exact WholeZ|].
    split; [intros K; elim (NN K)|].
    split; [intros _; split; [reflexivity|split; [reflexivity|split; exists false; reflexivity]]|].
    intros K. elim K. exact N1.
  + split; [exact WholeZ|].
    split; [intros K; elim (NN K)|].
    split; [intros _; split; [reflexivity|split; [reflexivity|split; exists false; reflexivity]]|].
    intros _ K. elim K. exact N2.
  + split; [left; exact EmptyZ|].
    split; [intros K; elim (NN K)|].
    split; [unfold nan; intros [K|K]; congruence|].
    intros _ _ _. exact EmptyZ.
Qed.

End IeeeIntervalExact.

(** * The generated statements *)

Theorem interval_neg_2_correct : interval_neg_2_spec.
Proof.
intros prec emax Hp0 He nan_opp xl0 xl1 xu0 xu1 CX.
exact (interval_neg_2_all prec emax nan_opp xl0 xl1 xu0 xu1 CX).
Qed.

Theorem interval_make_2_correct : interval_make_2_spec.
Proof.
intros prec emax Hp0 He nan_opp lo0 lo1 hi0 hi1 Cl Ch.
exact (interval_make_2_all prec emax nan_opp lo0 lo1 hi0 hi1 Cl Ch).
Qed.

Theorem interval_hull_1_correct : interval_hull_1_spec.
Proof.
intros prec emax Hp0 He xl xu yl yu CX CY.
unfold IeeeModel.interval_hull_1. cbv beta iota zeta.
exact (hull_1_of prec emax xl xu yl yu _ _ CX CY
         (select_lt_xmin prec emax xl yl) (select_lt_xmax prec emax xu yu)).
Qed.

Theorem interval_intersection_1_correct : interval_intersection_1_spec.
Proof.
intros prec emax Hp0 He nan_opp xl xu yl yu CX CY.
unfold IeeeModel.interval_intersection_1. cbv beta iota zeta.
rewrite (neg_pinf prec emax nan_opp).
exact (intersection_1_of prec emax xl xu yl yu _ _ _ CX CY
         (select_lt_xmax prec emax xl yl) (select_lt_xmin prec emax xu yu)
         (le_xval prec emax _ _)).
Qed.

Theorem interval_hull_2_correct : interval_hull_2_spec.
Proof.
intros prec emax Hp0 He xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 CX CY.
unfold IeeeModel.interval_hull_2. cbv beta iota zeta.
destruct (interval_2_canonical prec emax _ _ _ _ CX) as [Cxl Cxu].
destruct (interval_2_canonical prec emax _ _ _ _ CY) as [Cyl Cyu].
destruct (select_lt_2_xmin prec emax xl0 xl1 yl0 yl1 Cxl Cyl) as [Czl El].
destruct (select_lt_2_xmax prec emax xu0 xu1 yu0 yu1 Cxu Cyu) as [Czu Eu].
exact (hull_2_of prec emax xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 _ _ _ _ CX CY Czl El Czu Eu).
Qed.

Theorem interval_intersection_2_correct : interval_intersection_2_spec.
Proof.
intros prec emax Hp0 He nan_opp xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 CX CY.
assert (Hp1 : (1 <= prec)%Z) by (generalize Hp0; unfold Prec_gt_0; lia).
unfold IeeeModel.interval_intersection_2. cbv beta iota zeta.
rewrite (neg_pinf prec emax nan_opp).
destruct (interval_2_canonical prec emax _ _ _ _ CX) as [Cxl Cxu].
destruct (interval_2_canonical prec emax _ _ _ _ CY) as [Cyl Cyu].
destruct (select_lt_2_xmax prec emax xl0 xl1 yl0 yl1 Cxl Cyl) as [Cl El].
destruct (select_lt_2_xmin prec emax xu0 xu1 yu0 yu1 Cxu Cyu) as [Ch Eh].
exact (intersection_2_of prec emax xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 _ _ _ _ _ CX CY Cl El Ch Eh
         (le_2_2_ext prec emax Hp1 _ _ _ _ Cl Ch)).
Qed.
