(* The predicates, the three-valued comparisons and the relations of IEEE 1788 of intervals with
   bounds of one limb and of two, in the IEEE model, on all values (docs/developer/design/
   milestone2.md, "One enclosure interface" and "Comparisons"; docs/developer/architecture.md,
   "Claims of the enclosure interface: predicates and comparisons"): the 26 kernels
   interval_empty_k, interval_entire_k, interval_contains_k, interval_subset_k,
   interval_positive_k, interval_negative_k, interval_zero_k, interval_less_k,
   interval_less_equal_k, interval_equal_k, interval_rel_equal_k, interval_rel_interior_k and
   interval_rel_disjoint_k, for k = 1 and 2.

   Notation as in IeeeIntervalExact.v: xval and xval_2 are the extended real numbers a limb and a
   canonical 2-limb value stand for; an interval, its members and its emptiness are those of
   IeeeIntervalVocabulary.v; xinterval a b says that the extended real numbers a and b are the
   bounds of a canonical interval (the empty pair (+inf, -inf) or a nonempty pair). X = [a, b]
   and Y = [c, d] are the operands.

   What is proved. Every kernel is exact, for canonical operands and every precision: the mask
   is true exactly when the relation holds (the theorems K_correct at the end of the file are the
   generated statements of proofs/gen/IeeeStatements.v). For the three-valued comparisons, yes is
   true exactly when the relation holds for every choice of members of nonempty operands, no
   exactly when it fails for every choice, and they are never both true.

   The proofs. Everything is said first of the bounds as extended real numbers, in a few facts
   about the members of a nonempty interval [a, b]: every member is below a real s exactly
   when b < s, at most s exactly when b <= s, and symmetrically for a (xupper_lt, xupper_le,
   xlower_gt, xlower_ge). For two nonempty intervals, x < y for every choice of members exactly
   when b < c (xall_lt), x <= y exactly when b <= c (xall_le), and x <> y exactly when b < c or
   d < a (xall_ne). Each relation is then one lemma on extended real numbers (xempty,
   xentire, xsubset, xpositive, ..., xinterior, xdisjoint). A comparison of limbs is the
   comparison of their values (lt_xval, le_xval, eq_xval of IeeeExt.v), and a comparison of
   2-limb values by lt_2_2, le_2_2 and eq_2_2 the comparison of what they stand for
   (lt_2_2_ext, le_2_2_ext, eq_2_2_ext); a test of the leading limb of a canonical 2-limb value
   against 0 or an infinity is the same test of the value (lead_tests: the value of a
   normalized pair has the sign of its leading limb, and is zero exactly when it is). *)
From Stdlib Require Import Reals ZArith Bool Lia Lra Psatz.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements IeeeStatements.
From Kairn Require Import Format Normalized IeeeBridge IeeeVocabulary IeeeOps IeeeExt.
From Kairn Require Import Rectangle IeeeIntervalVocabulary IeeeInterval1 IeeeInterval2.
From Kairn Require Import IeeeIntervalExact.
From Kairn Require IeeeOperations.
From Kairn.Gen Require IeeeModel.
Open Scope R_scope.

(** * The order of the extended real numbers *)

Lemma xeq_eq : forall a b : xreal, xeq a b = true -> a = b.
Proof.
intros [|[|]|x] [|[|]|y]; cbn; intros H; try discriminate H; trivial.
f_equal. destruct (Req_bool_spec x y) as [E|E]; [exact E|discriminate H].
Qed.

(* A number that is not a NaN is equal to itself. *)
Lemma xeq_refl : forall a : xreal, xle a a = true -> xeq a a = true.
Proof. intros [|[|]|x]; xcase. Qed.

Lemma xlt_le : forall a b : xreal, xlt a b = true -> xle a b = true.
Proof. intros [|[|]|x] [|[|]|y]; xcase. Qed.

Lemma xlt_le_trans :
  forall a b c : xreal, xlt a b = true -> xle b c = true -> xlt a c = true.
Proof. intros [|[|]|x] [|[|]|y] [|[|]|z]; xcase. Qed.

Lemma xle_lt_trans :
  forall a b c : xreal, xle a b = true -> xlt b c = true -> xlt a c = true.
Proof. intros [|[|]|x] [|[|]|y] [|[|]|z]; xcase. Qed.

(* Two numbers that are not NaN are in one order or the other. *)
Lemma xlt_false_le :
  forall a b : xreal, xle a a = true -> xle b b = true -> xlt a b = false -> xle b a = true.
Proof. intros [|[|]|x] [|[|]|y]; xcase. Qed.

Lemma xle_false_lt :
  forall a b : xreal, xle a a = true -> xle b b = true -> xle a b = false -> xlt b a = true.
Proof. intros [|[|]|x] [|[|]|y]; xcase. Qed.

(** * The members of a nonempty interval and its bounds *)

Section Members.
Variables a b : xreal.
Hypothesis N : xnonempty a b.

Let Hab : xle a b = true.
Proof. exact (proj1 N). Qed.
Let Ha : xlt a (XInf false) = true.
Proof. exact (proj1 (proj2 N)). Qed.
Let Hb : xlt (XInf true) b = true.
Proof. exact (proj2 (proj2 N)). Qed.

(* Every member is below s exactly when the upper bound is. *)
Lemma xupper_lt :
  forall s : R, (forall x : R, xmember a b x -> x < s) <-> xlt b (XFin s) = true.
Proof.
intros s. split.
- intros H. destruct b as [|[|]|r] eqn:Eb.
  + destruct a; discriminate Hab.
  + discriminate Hb.
  + destruct (xmember_approach_upper a (XInf false) N s eq_refl) as [x [Hx L]].
    generalize (H x Hx). lra.
  + assert (M := xmember_upper a r N). generalize (H r M). intros L.
    cbn. now apply Rlt_bool_true.
- intros H x [_ Hx]. destruct b as [|[|]|r]; cbn in H, Hx; try discriminate H; try discriminate Hx.
  apply Rle_bool_inv in Hx. apply Rlt_bool_inv in H. lra.
Qed.

(* Every member is at most s exactly when the upper bound is. *)
Lemma xupper_le :
  forall s : R, (forall x : R, xmember a b x -> x <= s) <-> xle b (XFin s) = true.
Proof.
intros s. split.
- intros H. destruct b as [|[|]|r] eqn:Eb.
  + destruct a; discriminate Hab.
  + discriminate Hb.
  + destruct (xmember_approach_upper a (XInf false) N s eq_refl) as [x [Hx L]].
    generalize (H x Hx). lra.
  + assert (M := xmember_upper a r N). generalize (H r M). intros L.
    cbn. now apply Rle_bool_true.
- intros H x [_ Hx]. destruct b as [|[|]|r]; cbn in H, Hx; try discriminate H; try discriminate Hx.
  apply Rle_bool_inv in Hx. apply Rle_bool_inv in H. lra.
Qed.

(* Every member is above s exactly when the lower bound is. *)
Lemma xlower_gt :
  forall s : R, (forall x : R, xmember a b x -> s < x) <-> xlt (XFin s) a = true.
Proof.
intros s. split.
- intros H. destruct a as [|[|]|r] eqn:Ea.
  + discriminate Hab.
  + destruct (xmember_approach_lower (XInf true) b N s eq_refl) as [x [Hx L]].
    generalize (H x Hx). lra.
  + discriminate Ha.
  + assert (M := xmember_lower r b N). generalize (H r M). intros L.
    cbn. now apply Rlt_bool_true.
- intros H x [Hx _]. destruct a as [|[|]|r]; cbn in H, Hx; try discriminate H; try discriminate Hx.
  apply Rle_bool_inv in Hx. apply Rlt_bool_inv in H. lra.
Qed.

(* Every member is at least s exactly when the lower bound is. *)
Lemma xlower_ge :
  forall s : R, (forall x : R, xmember a b x -> s <= x) <-> xle (XFin s) a = true.
Proof.
intros s. split.
- intros H. destruct a as [|[|]|r] eqn:Ea.
  + discriminate Hab.
  + destruct (xmember_approach_lower (XInf true) b N s eq_refl) as [x [Hx L]].
    generalize (H x Hx). lra.
  + discriminate Ha.
  + assert (M := xmember_lower r b N). generalize (H r M). intros L.
    cbn. now apply Rle_bool_true.
- intros H x [Hx _]. destruct a as [|[|]|r]; cbn in H, Hx; try discriminate H; try discriminate Hx.
  apply Rle_bool_inv in Hx. apply Rle_bool_inv in H. lra.
Qed.

(* The same with an extended real number c that is not a NaN in place of s. *)
Lemma xlower_ge_x :
  forall c : xreal, xle c c = true ->
  (forall x : R, xmember a b x -> xle c (XFin x) = true) <-> xle c a = true.
Proof.
intros c Rc. destruct (xnonempty_member a b N) as [m Hm].
destruct c as [|[|]|r].
- discriminate Rc.
- split; [intros _|intros _ x _; reflexivity].
  destruct a as [|[|]|ra]; [discriminate Hab|reflexivity|reflexivity|reflexivity].
- split.
  + intros H. specialize (H m Hm). discriminate H.
  + intros H. exfalso. destruct a as [|[|]|ra]; try discriminate Ha; discriminate H.
- rewrite <- (xlower_ge r). split.
  + intros H x Hx. apply Rle_bool_inv. exact (H x Hx).
  + intros H x Hx. cbn. apply Rle_bool_true. exact (H x Hx).
Qed.

Lemma xupper_le_x :
  forall d : xreal, xle d d = true ->
  (forall x : R, xmember a b x -> xle (XFin x) d = true) <-> xle b d = true.
Proof.
intros d Rd. destruct (xnonempty_member a b N) as [m Hm].
destruct d as [|[|]|r].
- discriminate Rd.
- split.
  + intros H. specialize (H m Hm). discriminate H.
  + intros H. exfalso. destruct b as [|[|]|rb]; try discriminate Hb; discriminate H.
- split; [intros _|intros _ x _; reflexivity].
  destruct b as [|[|]|rb]; [destruct a; discriminate Hab|reflexivity|reflexivity|reflexivity].
- rewrite <- (xupper_le r). split.
  + intros H x Hx. apply Rle_bool_inv. exact (H x Hx).
  + intros H x Hx. cbn. apply Rle_bool_true. exact (H x Hx).
Qed.

End Members.

(* A canonical interval is nonempty exactly when its lower bound is below +infinity, and
   exactly when its upper bound is above -infinity. *)
Lemma xinterval_ne_l :
  forall a b : xreal, xinterval a b -> (xlt a (XInf false) = true <-> xnonempty a b).
Proof.
intros a b [[Ea Eb]|N].
- subst a b. split; intros H; [discriminate H|]. destruct H as [_ [H _]]. exact H.
- split; intros _; [exact N|exact (proj1 (proj2 N))].
Qed.

Lemma xinterval_ne_r :
  forall a b : xreal, xinterval a b -> (xlt (XInf true) b = true <-> xnonempty a b).
Proof.
intros a b [[Ea Eb]|N].
- subst a b. split; intros H; [discriminate H|]. destruct H as [_ [_ H]]. exact H.
- split; intros _; [exact N|exact (proj2 (proj2 N))].
Qed.

(** * Two nonempty intervals: every choice of members *)

Section Pairs.
Variables a b c d : xreal.
Hypothesis NX : xnonempty a b.
Hypothesis NY : xnonempty c d.

(* x < y for every member x of X and y of Y exactly when b < c. *)
Lemma xall_lt :
  (forall x y : R, xmember a b x -> xmember c d y -> x < y) <-> xlt b c = true.
Proof.
destruct (xnonempty_member c d NY) as [m Hm].
assert (E : (forall x y : R, xmember a b x -> xmember c d y -> x < y) <->
            (forall y : R, xmember c d y -> xlt b (XFin y) = true)).
{ split.
  - intros H y Hy. apply (xupper_lt a b NX y). intros x Hx. exact (H x y Hx Hy).
  - intros H x y Hx Hy. exact (proj2 (xupper_lt a b NX y) (H y Hy) x Hx). }
rewrite E. destruct b as [|[|]|r] eqn:Eb.
- destruct a; discriminate (proj1 NX).
- discriminate (proj2 (proj2 NX)).
- split; intros H; [discriminate (H m Hm)|destruct c as [|[|]|rc]; discriminate H].
- rewrite <- (xlower_gt c d NY r). split.
  + intros H y Hy. apply Rlt_bool_inv. exact (H y Hy).
  + intros H y Hy. cbn. apply Rlt_bool_true. exact (H y Hy).
Qed.

(* x <= y for every choice exactly when b <= c. *)
Lemma xall_le :
  (forall x y : R, xmember a b x -> xmember c d y -> x <= y) <-> xle b c = true.
Proof.
destruct (xnonempty_member c d NY) as [m Hm].
assert (E : (forall x y : R, xmember a b x -> xmember c d y -> x <= y) <->
            (forall y : R, xmember c d y -> xle b (XFin y) = true)).
{ split.
  - intros H y Hy. apply (xupper_le a b NX y). intros x Hx. exact (H x y Hx Hy).
  - intros H x y Hx Hy. exact (proj2 (xupper_le a b NX y) (H y Hy) x Hx). }
rewrite E. destruct b as [|[|]|r] eqn:Eb.
- destruct a; discriminate (proj1 NX).
- discriminate (proj2 (proj2 NX)).
- split; intros H; [discriminate (H m Hm)|].
  destruct c as [|[|]|rc]; try discriminate H.
  exfalso. discriminate (proj1 (proj2 NY)).
- rewrite <- (xlower_ge c d NY r). split.
  + intros H y Hy. apply Rle_bool_inv. exact (H y Hy).
  + intros H y Hy. cbn. apply Rle_bool_true. exact (H y Hy).
Qed.

(* x <> y for every choice, that is, no common member, exactly when b < c or d < a. *)
Lemma xall_ne_common :
  (forall x y : R, xmember a b x -> xmember c d y -> x <> y) <->
  ~ (exists z : R, xmember a b z /\ xmember c d z).
Proof.
split.
- intros H [z [Hx Hy]]. exact (H z z Hx Hy eq_refl).
- intros H x y Hx Hy E. subst y. apply H. exists x. split; assumption.
Qed.

End Pairs.

Lemma xall_ne :
  forall a b c d : xreal, xnonempty a b -> xnonempty c d ->
  (forall x y : R, xmember a b x -> xmember c d y -> x <> y) <->
  orb (xlt b c) (xlt d a) = true.
Proof.
intros a b c d NX NY. split.
- intros H. apply Bool.not_false_iff_true. intros K. apply orb_false_iff in K.
  destruct K as [K1 K2].
  assert (Ra := xle_refl_l _ _ (proj1 NX)). assert (Rb := xle_refl_r _ _ (proj1 NX)).
  assert (Rc := xle_refl_l _ _ (proj1 NY)). assert (Rd := xle_refl_r _ _ (proj1 NY)).
  assert (Lcb := xlt_false_le b c Rb Rc K1). assert (Lad := xlt_false_le d a Rd Ra K2).
  assert (I : xle (xmax a c) (xmin b d) = true).
  { destruct (xmax_cases a c) as [E|E]; rewrite E;
      destruct (xmin_cases b d) as [F|F]; rewrite F.
    - exact (proj1 NX).
    - exact Lad.
    - exact Lcb.
    - exact (proj1 NY). }
  destruct (xinter a b c d (or_intror NX) (or_intror NY)) as [M [T _]].
  destruct (xnonempty_member _ _ (T I)) as [z Hz].
  apply (proj2 (M z)) in Hz. destruct Hz as [Hx Hy]. exact (H z z Hx Hy eq_refl).
- intros H x y Hx Hy. apply orb_true_iff in H. destruct H as [H|H].
  + apply Rlt_not_eq. exact (proj2 (xall_lt a b c d NX NY) H x y Hx Hy).
  + apply not_eq_sym, Rlt_not_eq. exact (proj2 (xall_lt c d a b NY NX) H y x Hy Hx).
Qed.

(** * The relations, on the bounds *)

(* A canonical interval [a, b] is the empty set exactly when a = +infinity. *)
Lemma xempty :
  forall a b : xreal, xinterval a b ->
  (xeq a (XInf false) = true <-> a = XInf false /\ b = XInf true).
Proof.
intros a b X. split.
- intros H. apply xeq_eq in H. subst a. destruct X as [E|[_ [K _]]]; [exact E|discriminate K].
- intros [E _]. subst a. reflexivity.
Qed.

(* It is the whole line exactly when its bounds are -infinity and +infinity. *)
Lemma xentire :
  forall a b : xreal,
  andb (xeq a (XInf true)) (xeq b (XInf false)) = true <-> (forall z : R, xmember a b z).
Proof.
intros a b. split.
- intros H. apply andb_true_iff in H. destruct H as [H K].
  apply xeq_eq in H. apply xeq_eq in K. subst a b. intros z. split; reflexivity.
- intros H. apply andb_true_iff. split.
  + destruct a as [|[|]|r].
    * destruct (H 0) as [K _]. discriminate K.
    * reflexivity.
    * destruct (H 0) as [K _]. discriminate K.
    * destruct (H (r - 1)) as [K _]. cbn in K. apply Rle_bool_inv in K. lra.
  + destruct b as [|[|]|r].
    * destruct (H 0) as [_ K]. discriminate K.
    * destruct (H 0) as [_ K]. discriminate K.
    * reflexivity.
    * destruct (H (r + 1)) as [_ K]. cbn in K. apply Rle_bool_inv in K. lra.
Qed.

(* [a, b] is inside [c, d] exactly when c <= a and b <= d; the empty set is inside every set. *)
Lemma xsubset :
  forall a b c d : xreal, xinterval a b -> xinterval c d ->
  (andb (xle c a) (xle b d) = true <-> (forall z : R, xmember a b z -> xmember c d z)).
Proof.
intros a b c d X Y. destruct (xinterval_refl c d Y) as [Rc Rd].
destruct X as [[Ea Eb]|NX].
- subst a b. split; [intros _ z Hz; elim (xmember_empty z Hz)|intros _].
  apply andb_true_iff. split.
  + destruct c as [|[|]|r]; [discriminate Rc|reflexivity|reflexivity|reflexivity].
  + destruct d as [|[|]|r]; [discriminate Rd|reflexivity|reflexivity|reflexivity].
- rewrite andb_true_iff, <- (xlower_ge_x a b NX c Rc), <- (xupper_le_x a b NX d Rd).
  unfold xmember. split.
  + intros [H K] z Hz. split; [exact (H z Hz)|exact (K z Hz)].
  + intros H. split; intros z Hz; apply (H z Hz).
Qed.

(* The signs. *)
Lemma xpositive :
  forall a b : xreal, xinterval a b ->
  (andb (xlt (XFin 0) a) (xlt a (XInf false)) = true <->
   xnonempty a b /\ (forall x : R, xmember a b x -> 0 < x)).
Proof.
intros a b X. rewrite andb_true_iff, (xinterval_ne_l a b X). split.
- intros [P N]. split; [exact N|]. exact (proj2 (xlower_gt a b N 0) P).
- intros [N H]. split; [exact (proj1 (xlower_gt a b N 0) H)|exact N].
Qed.

Lemma xnegative :
  forall a b : xreal, xinterval a b ->
  (andb (xlt b (XFin 0)) (xlt (XInf true) b) = true <->
   xnonempty a b /\ (forall x : R, xmember a b x -> x < 0)).
Proof.
intros a b X. rewrite andb_true_iff, (xinterval_ne_r a b X). split.
- intros [P N]. split; [exact N|]. exact (proj2 (xupper_lt a b N 0) P).
- intros [N H]. split; [exact (proj1 (xupper_lt a b N 0) H)|exact N].
Qed.

Lemma xzero :
  forall a b : xreal,
  andb (xeq a (XFin 0)) (xeq b (XFin 0)) = true <->
  xnonempty a b /\ (forall x : R, xmember a b x -> x = 0).
Proof.
intros a b. split.
- intros H. apply andb_true_iff in H. destruct H as [H K].
  apply xeq_eq in H. apply xeq_eq in K. subst a b.
  assert (N : xnonempty (XFin 0) (XFin 0)).
  { split; [cbn; apply Rle_bool_true; lra|split; reflexivity]. }
  split; [exact N|]. intros x [H K]. cbn in H, K.
  apply Rle_bool_inv in H. apply Rle_bool_inv in K. lra.
- intros [N H].
  assert (Lb : xle b (XFin 0) = true).
  { apply (xupper_le a b N 0). intros x Hx. rewrite (H x Hx). lra. }
  assert (La : xle (XFin 0) a = true).
  { apply (xlower_ge a b N 0). intros x Hx. rewrite (H x Hx). lra. }
  generalize (proj1 N) La Lb. clear H N.
  destruct a as [|[|]|ra]; destruct b as [|[|]|rb]; xcase.
Qed.

(* The three-valued comparisons: the answer yes, the answer no, and that they exclude each
   other. *)
Lemma xless :
  forall a b c d : xreal, xinterval a b -> xinterval c d ->
  (andb (xlt b c) (andb (xlt a (XInf false)) (xlt c (XInf false))) = true <->
   xnonempty a b /\ xnonempty c d /\
   (forall x y : R, xmember a b x -> xmember c d y -> x < y)) /\
  (andb (xle d a) (andb (xlt a (XInf false)) (xlt c (XInf false))) = true <->
   xnonempty a b /\ xnonempty c d /\
   (forall x y : R, xmember a b x -> xmember c d y -> ~ (x < y))).
Proof.
intros a b c d X Y.
rewrite !andb_true_iff, (xinterval_ne_l a b X), (xinterval_ne_l c d Y).
split; split.
- intros [H [NX NY]]. split; [exact NX|split; [exact NY|]].
  exact (proj2 (xall_lt a b c d NX NY) H).
- intros [NX [NY H]]. split; [|split; assumption]. exact (proj1 (xall_lt a b c d NX NY) H).
- intros [H [NX NY]]. split; [exact NX|split; [exact NY|]].
  intros x y Hx Hy. apply Rle_not_lt. exact (proj2 (xall_le c d a b NY NX) H y x Hy Hx).
- intros [NX [NY H]]. split; [|split; assumption].
  apply (proj1 (xall_le c d a b NY NX)). intros y x Hy Hx. apply Rnot_lt_le.
  exact (H x y Hx Hy).
Qed.

Lemma xless_equal :
  forall a b c d : xreal, xinterval a b -> xinterval c d ->
  (andb (xle b c) (andb (xlt a (XInf false)) (xlt c (XInf false))) = true <->
   xnonempty a b /\ xnonempty c d /\
   (forall x y : R, xmember a b x -> xmember c d y -> x <= y)) /\
  (andb (xlt d a) (andb (xlt a (XInf false)) (xlt c (XInf false))) = true <->
   xnonempty a b /\ xnonempty c d /\
   (forall x y : R, xmember a b x -> xmember c d y -> ~ (x <= y))).
Proof.
intros a b c d X Y.
rewrite !andb_true_iff, (xinterval_ne_l a b X), (xinterval_ne_l c d Y).
split; split.
- intros [H [NX NY]]. split; [exact NX|split; [exact NY|]].
  exact (proj2 (xall_le a b c d NX NY) H).
- intros [NX [NY H]]. split; [|split; assumption]. exact (proj1 (xall_le a b c d NX NY) H).
- intros [H [NX NY]]. split; [exact NX|split; [exact NY|]].
  intros x y Hx Hy. apply Rlt_not_le. exact (proj2 (xall_lt c d a b NY NX) H y x Hy Hx).
- intros [NX [NY H]]. split; [|split; assumption].
  apply (proj1 (xall_lt c d a b NY NX)). intros y x Hy Hx. apply Rnot_le_lt.
  exact (H x y Hx Hy).
Qed.

Lemma xequal :
  forall a b c d : xreal, xinterval a b -> xinterval c d ->
  (andb (andb (xeq a b) (xeq b c)) (xeq c d) = true <->
   xnonempty a b /\ xnonempty c d /\
   (forall x y : R, xmember a b x -> xmember c d y -> x = y)) /\
  (andb (orb (xlt b c) (xlt d a)) (andb (xlt a (XInf false)) (xlt c (XInf false))) = true <->
   xnonempty a b /\ xnonempty c d /\
   (forall x y : R, xmember a b x -> xmember c d y -> ~ (x = y))).
Proof.
intros a b c d X Y. destruct (xinterval_refl a b X) as [Ra _].
split.
- split.
  + intros H. apply andb_true_iff in H. destruct H as [H K]. apply andb_true_iff in H.
    destruct H as [H L]. apply xeq_eq in H. apply xeq_eq in K. apply xeq_eq in L.
    subst b c d.
    assert (N : xnonempty a a).
    { destruct X as [[E F]|N]; [rewrite E in F; discriminate F|exact N]. }
    split; [exact N|split; [exact N|]].
    intros x y [Hx Kx] [Hy Ky].
    destruct a as [|[|]|r]; try discriminate (proj1 (proj2 N));
      try discriminate (proj2 (proj2 N)); try discriminate Hx.
    cbn in Hx, Kx, Hy, Ky. apply Rle_bool_inv in Hx. apply Rle_bool_inv in Kx.
    apply Rle_bool_inv in Hy. apply Rle_bool_inv in Ky. lra.
  + intros [NX [NY H]].
    assert (Lbc : xle b c = true).
    { apply (xall_le a b c d NX NY). intros x y Hx Hy. rewrite (H x y Hx Hy). lra. }
    assert (Lda : xle d a = true).
    { apply (xall_le c d a b NY NX). intros y x Hy Hx. rewrite (H x y Hx Hy). lra. }
    assert (Lab := proj1 NX). assert (Lcd := proj1 NY).
    assert (Eab : a = b) by
      (apply xle_antisym; [exact Lab|exact (xle_trans _ _ _ Lbc (xle_trans _ _ _ Lcd Lda))]).
    assert (Ebc : b = c) by
      (apply xle_antisym; [exact Lbc|exact (xle_trans _ _ _ Lcd (xle_trans _ _ _ Lda Lab))]).
    assert (Ecd : c = d) by
      (apply xle_antisym; [exact Lcd|exact (xle_trans _ _ _ Lda (xle_trans _ _ _ Lab Lbc))]).
    subst b c d. rewrite (xeq_refl a Ra). reflexivity.
- rewrite !andb_true_iff, (xinterval_ne_l a b X), (xinterval_ne_l c d Y).
  split.
  + intros [H [NX NY]]. split; [exact NX|split; [exact NY|]].
    exact (proj2 (xall_ne a b c d NX NY) H).
  + intros [NX [NY H]]. split; [|split; assumption]. exact (proj1 (xall_ne a b c d NX NY) H).
Qed.

(* The relations of IEEE 1788. *)
Lemma xrel_equal :
  forall a b c d : xreal, xinterval a b -> xinterval c d ->
  (andb (xeq a c) (xeq b d) = true <-> (forall z : R, xmember a b z <-> xmember c d z)).
Proof.
intros a b c d X Y.
destruct (xinterval_refl c d Y) as [Rc Rd].
split.
- intros H. apply andb_true_iff in H. destruct H as [H K].
  apply xeq_eq in H. apply xeq_eq in K. subst c d. tauto.
- intros H.
  assert (S1 : andb (xle c a) (xle b d) = true)
    by (apply (xsubset a b c d X Y); intros z; apply H).
  assert (S2 : andb (xle a c) (xle d b) = true)
    by (apply (xsubset c d a b Y X); intros z; apply H).
  apply andb_true_iff in S1. apply andb_true_iff in S2.
  destruct S1 as [S1 T1]. destruct S2 as [S2 T2].
  rewrite (xle_antisym a c S2 S1), (xle_antisym b d T1 T2).
  rewrite (xeq_refl c Rc), (xeq_refl d Rd). reflexivity.
Qed.

(* A real number strictly between c and d has a neighbourhood made of members of [c, d]. *)
Lemma xopen :
  forall (c d : xreal) (z : R), xlt c (XFin z) = true -> xlt (XFin z) d = true ->
  exists e : R, 0 < e /\ (forall w : R, Rabs (w - z) < e -> xmember c d w).
Proof.
intros c d z Hc Hd.
assert (Gc : exists ec : R, 0 < ec /\ forall w : R, z - ec < w -> xle c (XFin w) = true).
{ destruct c as [|[|]|rc]; cbn in Hc; try discriminate Hc.
  - exists 1. split; [lra|]. intros w _. reflexivity.
  - apply Rlt_bool_inv in Hc. exists (z - rc). split; [lra|].
    intros w Hw. cbn. apply Rle_bool_true. lra. }
assert (Gd : exists ed : R, 0 < ed /\ forall w : R, w < z + ed -> xle (XFin w) d = true).
{ destruct d as [|[|]|rd]; cbn in Hd; try discriminate Hd.
  - exists 1. split; [lra|]. intros w _. reflexivity.
  - apply Rlt_bool_inv in Hd. exists (rd - z). split; [lra|].
    intros w Hw. cbn. apply Rle_bool_true. lra. }
destruct Gc as [ec [Pc Gc]]. destruct Gd as [ed [Pd Gd]].
exists (Rmin ec ed). split; [apply Rmin_glb_lt; assumption|].
intros w Hw. apply Rabs_def2 in Hw. destruct Hw as [H1 H2].
assert (Q1 := Rmin_l ec ed). assert (Q2 := Rmin_r ec ed).
split; [apply Gc; lra|apply Gd; lra].
Qed.

(* [a, b] is interior to [c, d] exactly when it is empty, or each bound of [c, d] is beyond
   the bound of [a, b] on its side or both are that infinity. *)
Lemma xinterior :
  forall a b c d : xreal, xinterval a b -> xinterval c d ->
  (orb (xeq a (XInf false))
       (andb (orb (xlt c a) (andb (xeq c (XInf true)) (xeq a (XInf true))))
             (orb (xlt b d) (andb (xeq b (XInf false)) (xeq d (XInf false))))) = true <->
   (forall z : R, xmember a b z ->
    exists e : R, 0 < e /\ (forall w : R, Rabs (w - z) < e -> xmember c d w))).
Proof.
intros a b c d X Y.
destruct X as [[Ea Eb]|NX].
- subst a b. split; [intros _ z Hz; elim (xmember_empty z Hz)|intros _; reflexivity].
- assert (Ea : xeq a (XInf false) = false).
  { destruct a as [|[|]|r]; try reflexivity. discriminate (proj1 (proj2 NX)). }
  rewrite Ea, orb_false_l, !andb_true_iff, !orb_true_iff, !andb_true_iff. split.
  + intros [L U] z [Hz Kz]. apply xopen.
    * destruct L as [L|[L1 L2]]; [exact (xlt_le_trans _ _ _ L Hz)|].
      apply xeq_eq in L1. subst c. reflexivity.
    * destruct U as [U|[U1 U2]]; [exact (xle_lt_trans _ _ _ Kz U)|].
      apply xeq_eq in U2. subst d. reflexivity.
  + intros H.
    assert (S : forall z : R, xmember a b z -> xmember c d z).
    { intros z Hz. destruct (H z Hz) as [e [Pe He]]. apply He.
      rewrite Rminus_diag, Rabs_R0. exact Pe. }
    apply (xsubset a b c d (or_intror NX) Y) in S. apply andb_true_iff in S.
    destruct S as [Sca Sbd].
    split.
    * destruct a as [|[|]|r].
      -- discriminate (proj1 NX).
      -- right. split; [|reflexivity].
         destruct c as [|[|]|rc]; try discriminate Sca; reflexivity.
      -- discriminate (proj1 (proj2 NX)).
      -- left. destruct (H r (xmember_lower r b NX)) as [e [Pe He]].
         destruct (He (r - e / 2)) as [K _]; [rewrite Rabs_left; lra|].
         destruct c as [|[|]|rc]; cbn in K |- *; try discriminate K; [reflexivity|].
         apply Rle_bool_inv in K. apply Rlt_bool_true. lra.
    * destruct b as [|[|]|r].
      -- destruct a; discriminate (proj1 NX).
      -- discriminate (proj2 (proj2 NX)).
      -- right. split; [reflexivity|].
         destruct d as [|[|]|rd]; try discriminate Sbd; reflexivity.
      -- left. destruct (H r (xmember_upper a r NX)) as [e [Pe He]].
         destruct (He (r + e / 2)) as [_ K]; [rewrite Rabs_right; lra|].
         destruct d as [|[|]|rd]; cbn in K |- *; try discriminate K; [reflexivity|].
         apply Rle_bool_inv in K. apply Rlt_bool_true. lra.
Qed.

(* [a, b] and [c, d] have no common member exactly when one is empty, or b < c, or d < a. *)
Lemma xdisjoint :
  forall a b c d : xreal, xinterval a b -> xinterval c d ->
  (orb (orb (xeq a (XInf false)) (xeq c (XInf false))) (orb (xlt b c) (xlt d a)) = true <->
   ~ (exists z : R, xmember a b z /\ xmember c d z)).
Proof.
intros a b c d X Y.
destruct X as [[Ea Eb]|NX].
- subst a b. split; [intros _ [z [Hz _]]; exact (xmember_empty z Hz)|intros _; reflexivity].
- destruct Y as [[Ec Ed]|NY].
  + subst c d. split; [intros _ [z [_ Hz]]; exact (xmember_empty z Hz)|intros _].
    apply orb_true_iff. left. apply orb_true_iff. right. reflexivity.
  + assert (Ea : xeq a (XInf false) = false).
    { destruct a as [|[|]|r]; try reflexivity. discriminate (proj1 (proj2 NX)). }
    assert (Ec : xeq c (XInf false) = false).
    { destruct c as [|[|]|r]; try reflexivity. discriminate (proj1 (proj2 NY)). }
    rewrite Ea, Ec, !orb_false_l, <- (xall_ne a b c d NX NY), xall_ne_common. tauto.
Qed.

(* A point t that stands for v when it is finite. *)
Lemma xcontains :
  forall (a b t : xreal) (f : bool) (v : R), (f = true -> t = XFin v) ->
  (andb (andb (xle a t) (xle t b)) f = true <-> f = true /\ xmember a b v).
Proof.
intros a b t f v H. destruct f.
- rewrite (H eq_refl), andb_true_r, andb_true_iff. unfold xmember. tauto.
- rewrite andb_false_r. split; [intros K; discriminate K|intros [K _]; discriminate K].
Qed.

(** * Limbs and 2-limb values *)

Section IeeeIntervalPredicates.
Variable prec emax : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Context {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}.

Notation float := (binary_float prec emax).
Notation emin := (3 - emax - prec)%Z.
Notation b2r := (B2R prec emax).
Notation xv := (@xval prec emax).
Notation xv2 := (@xval_2 prec emax).

(* A test of the leading limb of a canonical 2-limb value against 0 or an infinity is the
   same test of the value it stands for. *)
Lemma lead_tests :
  forall x0 x1 : float, canonical_2 x0 x1 ->
  xlt (xv x0) (XFin 0) = xlt (xv2 x0 x1) (XFin 0) /\
  xlt (XFin 0) (xv x0) = xlt (XFin 0) (xv2 x0 x1) /\
  xeq (xv x0) (XFin 0) = xeq (xv2 x0 x1) (XFin 0) /\
  (forall s : bool, xeq (xv x0) (XInf s) = xeq (xv2 x0 x1) (XInf s)) /\
  xlt (xv x0) (XInf false) = xlt (xv2 x0 x1) (XInf false) /\
  xlt (XInf true) (xv x0) = xlt (XInf true) (xv2 x0 x1).
Proof.
intros x0 x1 C.
destruct (canonical_cases prec emax x0 x1 C)
  as [[F0 [F1 [N [E0 [E1 E]]]]]|[[s [s' [_ [_ [E0 [E1 E]]]]]]|[_ [_ [E0 [E1 E]]]]]];
  rewrite E0, E; [|repeat split; reflexivity|repeat split; reflexivity].
assert (Cases : (b2r x0 < 0 /\ b2r x0 + b2r x1 < 0) \/ (b2r x0 = 0 /\ b2r x0 + b2r x1 = 0) \/
                (0 < b2r x0 /\ 0 < b2r x0 + b2r x1)).
{ destruct (Rtotal_order (b2r x0) 0) as [L|[Z|G]].
  - left. split; [exact L|exact (normalized_2_neg emin prec _ _ N L)].
  - right; left. split; [exact Z|]. rewrite Z, (normalized_2_zero emin prec _ _ N Z). ring.
  - right; right. split; [exact G|exact (normalized_2_pos emin prec _ _ N G)]. }
cbn [xlt xeq].
split; [|split; [|split; [|split; [|split]]]]; try (intros s; reflexivity); try reflexivity;
  repeat match goal with
  | |- context [Rlt_bool ?x ?y] => destruct (Rlt_bool_spec x y)
  | |- context [Req_bool ?x ?y] => destruct (Req_bool_spec x y)
  end;
  try reflexivity; exfalso; destruct Cases as [[A B]|[[A B]|[A B]]]; lra.
Qed.

(* One limb: a canonical interval is a pair of xinterval. *)
Lemma interval_1_parts :
  forall l h : float, interval_1 l h ->
  xinterval (xv l) (xv h) /\
  (interval_empty_1 l h <-> xv l = XInf false /\ xv h = XInf true).
Proof.
intros l h C. split; [now apply interval_1_xinterval|apply interval_empty_1_xval].
Qed.

(* Two limbs: the bounds are canonical, and the interval is a pair of xinterval. *)
Lemma interval_2_parts :
  forall l0 l1 h0 h1 : float, interval_2 l0 l1 h0 h1 ->
  canonical_2 l0 l1 /\ canonical_2 h0 h1 /\
  xinterval (xv2 l0 l1) (xv2 h0 h1) /\
  (interval_empty_2 l0 l1 h0 h1 <-> xv2 l0 l1 = XInf false /\ xv2 h0 h1 = XInf true) /\
  (interval_nonempty_2 l0 l1 h0 h1 <-> xnonempty (xv2 l0 l1) (xv2 h0 h1)).
Proof.
intros l0 l1 h0 h1 C.
destruct (interval_2_canonical prec emax _ _ _ _ C) as [Cl Ch].
destruct (interval_2_iff prec emax _ _ _ _ Cl Ch) as [E I].
split; [exact Cl|split; [exact Ch|split; [now apply I|split; [exact E|]]]].
unfold interval_nonempty_2. tauto.
Qed.

End IeeeIntervalPredicates.

(** * The generated statements: one limb *)

(* The values of the constants of the listings. *)
Ltac consts prec emax :=
  change (xval (IeeeOperations.pzero prec emax)) with (XFin 0) in *;
  change (xval (IeeeOperations.pinf prec emax)) with (XInf false) in *;
  change (xval (B754_infinity prec emax true)) with (XInf true) in *.

Theorem interval_empty_1_correct : interval_empty_1_spec.
Proof.
intros prec emax Hp0 He xl xu CX.
destruct (interval_1_parts prec emax xl xu CX) as [I E].
unfold IeeeModel.interval_empty_1. cbv zeta.
rewrite (eq_xval prec emax). consts prec emax. rewrite E. exact (xempty _ _ I).
Qed.

Theorem interval_entire_1_correct : interval_entire_1_spec.
Proof.
intros prec emax Hp0 He nan_opp xl xu CX.
unfold IeeeModel.interval_entire_1. cbv zeta.
rewrite (neg_pinf prec emax nan_opp), 2!(eq_xval prec emax). consts prec emax.
exact (xentire _ _).
Qed.

Theorem interval_contains_1_correct : interval_contains_1_spec.
Proof.
intros prec emax Hp0 He nan_abs xl xu t CX.
unfold IeeeModel.interval_contains_1. cbv zeta.
rewrite 2!(le_xval prec emax), (lt_abs_pinf prec emax nan_abs).
exact (xcontains (xval xl) (xval xu) (xval t) (is_finite prec emax t) (val t)
         (xval_fin prec emax t)).
Qed.

Theorem interval_subset_1_correct : interval_subset_1_spec.
Proof.
intros prec emax Hp0 He xl xu yl yu CX CY.
destruct (interval_1_parts prec emax xl xu CX) as [IX _].
destruct (interval_1_parts prec emax yl yu CY) as [IY _].
unfold IeeeModel.interval_subset_1. cbv zeta.
rewrite 2!(le_xval prec emax). exact (xsubset _ _ _ _ IX IY).
Qed.

Theorem interval_positive_1_correct : interval_positive_1_spec.
Proof.
intros prec emax Hp0 He xl xu CX.
destruct (interval_1_parts prec emax xl xu CX) as [I _].
unfold IeeeModel.interval_positive_1. cbv zeta.
rewrite 2!(lt_xval prec emax). consts prec emax. exact (xpositive _ _ I).
Qed.

Theorem interval_negative_1_correct : interval_negative_1_spec.
Proof.
intros prec emax Hp0 He nan_opp xl xu CX.
destruct (interval_1_parts prec emax xl xu CX) as [I _].
unfold IeeeModel.interval_negative_1. cbv zeta.
rewrite (neg_pinf prec emax nan_opp), 2!(lt_xval prec emax). consts prec emax.
exact (xnegative _ _ I).
Qed.

Theorem interval_zero_1_correct : interval_zero_1_spec.
Proof.
intros prec emax Hp0 He xl xu CX.
unfold IeeeModel.interval_zero_1. cbv zeta.
rewrite 2!(eq_xval prec emax). consts prec emax. exact (xzero _ _).
Qed.

Theorem interval_less_1_correct : interval_less_1_spec.
Proof.
intros prec emax Hp0 He xl xu yl yu CX CY.
destruct (interval_1_parts prec emax xl xu CX) as [IX _].
destruct (interval_1_parts prec emax yl yu CY) as [IY _].
unfold IeeeModel.interval_less_1. cbv zeta.
rewrite 3!(lt_xval prec emax), (le_xval prec emax). consts prec emax.
destruct (xless _ _ _ _ IX IY) as [Y N].
split; [exact Y|split; [exact N|]].
intros [Hy Hn]. apply Y in Hy. apply N in Hn. destruct Hy as [NX [NY Hy]].
destruct Hn as [_ [_ Hn]].
destruct (xnonempty_member _ _ NX) as [x Hx]. destruct (xnonempty_member _ _ NY) as [y Hy'].
exact (Hn x y Hx Hy' (Hy x y Hx Hy')).
Qed.

Theorem interval_less_equal_1_correct : interval_less_equal_1_spec.
Proof.
intros prec emax Hp0 He xl xu yl yu CX CY.
destruct (interval_1_parts prec emax xl xu CX) as [IX _].
destruct (interval_1_parts prec emax yl yu CY) as [IY _].
unfold IeeeModel.interval_less_equal_1. cbv zeta.
rewrite 3!(lt_xval prec emax), (le_xval prec emax). consts prec emax.
destruct (xless_equal _ _ _ _ IX IY) as [Y N].
split; [exact Y|split; [exact N|]].
intros [Hy Hn]. apply Y in Hy. apply N in Hn. destruct Hy as [NX [NY Hy]].
destruct Hn as [_ [_ Hn]].
destruct (xnonempty_member _ _ NX) as [x Hx]. destruct (xnonempty_member _ _ NY) as [y Hy'].
exact (Hn x y Hx Hy' (Hy x y Hx Hy')).
Qed.

Theorem interval_equal_1_correct : interval_equal_1_spec.
Proof.
intros prec emax Hp0 He xl xu yl yu CX CY.
destruct (interval_1_parts prec emax xl xu CX) as [IX _].
destruct (interval_1_parts prec emax yl yu CY) as [IY _].
unfold IeeeModel.interval_equal_1. cbv zeta.
rewrite 3!(eq_xval prec emax), 4!(lt_xval prec emax). consts prec emax.
destruct (xequal _ _ _ _ IX IY) as [Y N].
split; [exact Y|split; [exact N|]].
intros [Hy Hn]. apply Y in Hy. apply N in Hn. destruct Hy as [NX [NY Hy]].
destruct Hn as [_ [_ Hn]].
destruct (xnonempty_member _ _ NX) as [x Hx]. destruct (xnonempty_member _ _ NY) as [y Hy'].
exact (Hn x y Hx Hy' (Hy x y Hx Hy')).
Qed.

Theorem interval_rel_equal_1_correct : interval_rel_equal_1_spec.
Proof.
intros prec emax Hp0 He xl xu yl yu CX CY.
destruct (interval_1_parts prec emax xl xu CX) as [IX _].
destruct (interval_1_parts prec emax yl yu CY) as [IY _].
unfold IeeeModel.interval_rel_equal_1. cbv zeta.
rewrite 2!(eq_xval prec emax). exact (xrel_equal _ _ _ _ IX IY).
Qed.

Theorem interval_rel_interior_1_correct : interval_rel_interior_1_spec.
Proof.
intros prec emax Hp0 He nan_opp xl xu yl yu CX CY.
destruct (interval_1_parts prec emax xl xu CX) as [IX _].
destruct (interval_1_parts prec emax yl yu CY) as [IY _].
unfold IeeeModel.interval_rel_interior_1. cbv zeta.
rewrite (neg_pinf prec emax nan_opp), 5!(eq_xval prec emax), 2!(lt_xval prec emax).
consts prec emax. exact (xinterior _ _ _ _ IX IY).
Qed.

Theorem interval_rel_disjoint_1_correct : interval_rel_disjoint_1_spec.
Proof.
intros prec emax Hp0 He xl xu yl yu CX CY.
destruct (interval_1_parts prec emax xl xu CX) as [IX _].
destruct (interval_1_parts prec emax yl yu CY) as [IY _].
unfold IeeeModel.interval_rel_disjoint_1. cbv zeta.
rewrite 2!(eq_xval prec emax), 2!(lt_xval prec emax). consts prec emax.
exact (xdisjoint _ _ _ _ IX IY).
Qed.

(** * The generated statements: two limbs *)

Theorem interval_empty_2_correct : interval_empty_2_spec.
Proof.
intros prec emax Hp0 He xl0 xl1 xu0 xu1 CX.
destruct (interval_2_parts prec emax _ _ _ _ CX) as [Cl [Ch [I [E _]]]].
destruct (lead_tests prec emax _ _ Cl) as [_ [_ [_ [L _]]]].
unfold IeeeModel.interval_empty_2. cbv zeta.
rewrite (eq_xval prec emax). consts prec emax. rewrite L, E. exact (xempty _ _ I).
Qed.

Theorem interval_entire_2_correct : interval_entire_2_spec.
Proof.
intros prec emax Hp0 He nan_opp xl0 xl1 xu0 xu1 CX.
destruct (interval_2_parts prec emax _ _ _ _ CX) as [Cl [Ch _]].
destruct (lead_tests prec emax _ _ Cl) as [_ [_ [_ [Ll _]]]].
destruct (lead_tests prec emax _ _ Ch) as [_ [_ [_ [Lh _]]]].
unfold IeeeModel.interval_entire_2. cbv zeta.
rewrite (neg_pinf prec emax nan_opp), 2!(eq_xval prec emax). consts prec emax.
rewrite Ll, Lh. exact (xentire _ _).
Qed.

Theorem interval_contains_2_correct : interval_contains_2_spec.
Proof.
intros prec emax Hp0 He nan_abs xl0 xl1 xu0 xu1 t0 t1 CX Ct.
assert (Hp1 : (1 <= prec)%Z) by (generalize Hp0; unfold Prec_gt_0; lia).
destruct (interval_2_parts prec emax _ _ _ _ CX) as [Cl [Ch _]].
unfold IeeeModel.interval_contains_2. cbv zeta.
rewrite (le_2_2_ext prec emax Hp1 _ _ _ _ Cl Ct), (le_2_2_ext prec emax Hp1 _ _ _ _ Ct Ch).
rewrite (lt_abs_pinf prec emax nan_abs).
exact (xcontains (xval_2 xl0 xl1) (xval_2 xu0 xu1) (xval_2 t0 t1) (is_finite prec emax t0)
         (val t0 + val t1) (xval_2_fin prec emax t0 t1)).
Qed.

Theorem interval_subset_2_correct : interval_subset_2_spec.
Proof.
intros prec emax Hp0 He xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 CX CY.
assert (Hp1 : (1 <= prec)%Z) by (generalize Hp0; unfold Prec_gt_0; lia).
destruct (interval_2_parts prec emax _ _ _ _ CX) as [Cxl [Cxu [IX _]]].
destruct (interval_2_parts prec emax _ _ _ _ CY) as [Cyl [Cyu [IY _]]].
unfold IeeeModel.interval_subset_2. cbv zeta.
rewrite (le_2_2_ext prec emax Hp1 _ _ _ _ Cyl Cxl), (le_2_2_ext prec emax Hp1 _ _ _ _ Cxu Cyu).
exact (xsubset _ _ _ _ IX IY).
Qed.

Theorem interval_positive_2_correct : interval_positive_2_spec.
Proof.
intros prec emax Hp0 He xl0 xl1 xu0 xu1 CX.
destruct (interval_2_parts prec emax _ _ _ _ CX) as [Cl [Ch [I [_ NE]]]].
destruct (lead_tests prec emax _ _ Cl) as [_ [L2 [_ [_ [L5 _]]]]].
unfold IeeeModel.interval_positive_2. cbv zeta.
rewrite 2!(lt_xval prec emax). consts prec emax.
rewrite L2, L5, NE. exact (xpositive _ _ I).
Qed.

Theorem interval_negative_2_correct : interval_negative_2_spec.
Proof.
intros prec emax Hp0 He nan_opp xl0 xl1 xu0 xu1 CX.
destruct (interval_2_parts prec emax _ _ _ _ CX) as [Cl [Ch [I [_ NE]]]].
destruct (lead_tests prec emax _ _ Ch) as [L1 [_ [_ [_ [_ L6]]]]].
unfold IeeeModel.interval_negative_2. cbv zeta.
rewrite (neg_pinf prec emax nan_opp), 2!(lt_xval prec emax). consts prec emax.
rewrite L1, L6, NE. exact (xnegative _ _ I).
Qed.

Theorem interval_zero_2_correct : interval_zero_2_spec.
Proof.
intros prec emax Hp0 He xl0 xl1 xu0 xu1 CX.
destruct (interval_2_parts prec emax _ _ _ _ CX) as [Cl [Ch [I [_ NE]]]].
destruct (lead_tests prec emax _ _ Cl) as [_ [_ [Ll _]]].
destruct (lead_tests prec emax _ _ Ch) as [_ [_ [Lh _]]].
unfold IeeeModel.interval_zero_2. cbv zeta.
rewrite 2!(eq_xval prec emax). consts prec emax.
rewrite Ll, Lh, NE. exact (xzero _ _).
Qed.

Theorem interval_less_2_correct : interval_less_2_spec.
Proof.
intros prec emax Hp0 He xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 CX CY.
assert (Hp1 : (1 <= prec)%Z) by (generalize Hp0; unfold Prec_gt_0; lia).
destruct (interval_2_parts prec emax _ _ _ _ CX) as [Cxl [Cxu [IX [_ NX]]]].
destruct (interval_2_parts prec emax _ _ _ _ CY) as [Cyl [Cyu [IY [_ NY]]]].
destruct (lead_tests prec emax _ _ Cxl) as [_ [_ [_ [_ [Lx _]]]]].
destruct (lead_tests prec emax _ _ Cyl) as [_ [_ [_ [_ [Ly _]]]]].
unfold IeeeModel.interval_less_2. cbv zeta.
rewrite 2!(lt_xval prec emax). consts prec emax. rewrite Lx, Ly.
rewrite (lt_2_2_ext prec emax Hp1 _ _ _ _ Cxu Cyl), (le_2_2_ext prec emax Hp1 _ _ _ _ Cyu Cxl).
rewrite NX, NY.
destruct (xless _ _ _ _ IX IY) as [Y N].
split; [exact Y|split; [exact N|]].
intros [Hy Hn]. apply Y in Hy. apply N in Hn. destruct Hy as [AX [AY Hy]].
destruct Hn as [_ [_ Hn]].
destruct (xnonempty_member _ _ AX) as [x Hx]. destruct (xnonempty_member _ _ AY) as [y Hy'].
exact (Hn x y Hx Hy' (Hy x y Hx Hy')).
Qed.

Theorem interval_less_equal_2_correct : interval_less_equal_2_spec.
Proof.
intros prec emax Hp0 He xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 CX CY.
assert (Hp1 : (1 <= prec)%Z) by (generalize Hp0; unfold Prec_gt_0; lia).
destruct (interval_2_parts prec emax _ _ _ _ CX) as [Cxl [Cxu [IX [_ NX]]]].
destruct (interval_2_parts prec emax _ _ _ _ CY) as [Cyl [Cyu [IY [_ NY]]]].
destruct (lead_tests prec emax _ _ Cxl) as [_ [_ [_ [_ [Lx _]]]]].
destruct (lead_tests prec emax _ _ Cyl) as [_ [_ [_ [_ [Ly _]]]]].
unfold IeeeModel.interval_less_equal_2. cbv zeta.
rewrite 2!(lt_xval prec emax). consts prec emax. rewrite Lx, Ly.
rewrite (le_2_2_ext prec emax Hp1 _ _ _ _ Cxu Cyl), (lt_2_2_ext prec emax Hp1 _ _ _ _ Cyu Cxl).
rewrite NX, NY.
destruct (xless_equal _ _ _ _ IX IY) as [Y N].
split; [exact Y|split; [exact N|]].
intros [Hy Hn]. apply Y in Hy. apply N in Hn. destruct Hy as [AX [AY Hy]].
destruct Hn as [_ [_ Hn]].
destruct (xnonempty_member _ _ AX) as [x Hx]. destruct (xnonempty_member _ _ AY) as [y Hy'].
exact (Hn x y Hx Hy' (Hy x y Hx Hy')).
Qed.

Theorem interval_equal_2_correct : interval_equal_2_spec.
Proof.
intros prec emax Hp0 He xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 CX CY.
assert (Hp1 : (1 <= prec)%Z) by (generalize Hp0; unfold Prec_gt_0; lia).
destruct (interval_2_parts prec emax _ _ _ _ CX) as [Cxl [Cxu [IX [_ NX]]]].
destruct (interval_2_parts prec emax _ _ _ _ CY) as [Cyl [Cyu [IY [_ NY]]]].
destruct (lead_tests prec emax _ _ Cxl) as [_ [_ [_ [_ [Lx _]]]]].
destruct (lead_tests prec emax _ _ Cyl) as [_ [_ [_ [_ [Ly _]]]]].
unfold IeeeModel.interval_equal_2. cbv zeta.
rewrite 2!(lt_xval prec emax). consts prec emax. rewrite Lx, Ly.
rewrite (eq_2_2_ext prec emax Hp1 _ _ _ _ Cxl Cxu), (eq_2_2_ext prec emax Hp1 _ _ _ _ Cxu Cyl),
  (eq_2_2_ext prec emax Hp1 _ _ _ _ Cyl Cyu).
rewrite (lt_2_2_ext prec emax Hp1 _ _ _ _ Cxu Cyl), (lt_2_2_ext prec emax Hp1 _ _ _ _ Cyu Cxl).
rewrite NX, NY.
destruct (xequal _ _ _ _ IX IY) as [Y N].
split; [exact Y|split; [exact N|]].
intros [Hy Hn]. apply Y in Hy. apply N in Hn. destruct Hy as [AX [AY Hy]].
destruct Hn as [_ [_ Hn]].
destruct (xnonempty_member _ _ AX) as [x Hx]. destruct (xnonempty_member _ _ AY) as [y Hy'].
exact (Hn x y Hx Hy' (Hy x y Hx Hy')).
Qed.

Theorem interval_rel_equal_2_correct : interval_rel_equal_2_spec.
Proof.
intros prec emax Hp0 He xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 CX CY.
assert (Hp1 : (1 <= prec)%Z) by (generalize Hp0; unfold Prec_gt_0; lia).
destruct (interval_2_parts prec emax _ _ _ _ CX) as [Cxl [Cxu [IX _]]].
destruct (interval_2_parts prec emax _ _ _ _ CY) as [Cyl [Cyu [IY _]]].
unfold IeeeModel.interval_rel_equal_2. cbv zeta.
rewrite (eq_2_2_ext prec emax Hp1 _ _ _ _ Cxl Cyl), (eq_2_2_ext prec emax Hp1 _ _ _ _ Cxu Cyu).
exact (xrel_equal _ _ _ _ IX IY).
Qed.

Theorem interval_rel_interior_2_correct : interval_rel_interior_2_spec.
Proof.
intros prec emax Hp0 He nan_opp xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 CX CY.
assert (Hp1 : (1 <= prec)%Z) by (generalize Hp0; unfold Prec_gt_0; lia).
destruct (interval_2_parts prec emax _ _ _ _ CX) as [Cxl [Cxu [IX _]]].
destruct (interval_2_parts prec emax _ _ _ _ CY) as [Cyl [Cyu [IY _]]].
destruct (lead_tests prec emax _ _ Cxl) as [_ [_ [_ [Lxl _]]]].
destruct (lead_tests prec emax _ _ Cxu) as [_ [_ [_ [Lxu _]]]].
destruct (lead_tests prec emax _ _ Cyl) as [_ [_ [_ [Lyl _]]]].
destruct (lead_tests prec emax _ _ Cyu) as [_ [_ [_ [Lyu _]]]].
unfold IeeeModel.interval_rel_interior_2. cbv zeta.
rewrite (neg_pinf prec emax nan_opp), 5!(eq_xval prec emax). consts prec emax.
rewrite !Lxl, !Lxu, !Lyl, !Lyu.
rewrite (lt_2_2_ext prec emax Hp1 _ _ _ _ Cyl Cxl), (lt_2_2_ext prec emax Hp1 _ _ _ _ Cxu Cyu).
exact (xinterior _ _ _ _ IX IY).
Qed.

Theorem interval_rel_disjoint_2_correct : interval_rel_disjoint_2_spec.
Proof.
intros prec emax Hp0 He xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 CX CY.
assert (Hp1 : (1 <= prec)%Z) by (generalize Hp0; unfold Prec_gt_0; lia).
destruct (interval_2_parts prec emax _ _ _ _ CX) as [Cxl [Cxu [IX _]]].
destruct (interval_2_parts prec emax _ _ _ _ CY) as [Cyl [Cyu [IY _]]].
destruct (lead_tests prec emax _ _ Cxl) as [_ [_ [_ [Lxl _]]]].
destruct (lead_tests prec emax _ _ Cyl) as [_ [_ [_ [Lyl _]]]].
unfold IeeeModel.interval_rel_disjoint_2. cbv zeta.
rewrite 2!(eq_xval prec emax). consts prec emax. rewrite Lxl, Lyl.
rewrite (lt_2_2_ext prec emax Hp1 _ _ _ _ Cxu Cyl), (lt_2_2_ext prec emax Hp1 _ _ _ _ Cyu Cxl).
exact (xdisjoint _ _ _ _ IX IY).
Qed.
