(* The interval kernels with bounds of one limb, in the IEEE model, on all values:
   interval_make_1, interval_neg_1, interval_add_1, interval_sub_1 and interval_mul_1
   (docs/developer/design/milestone2.md, "Interval kernels": "Values of an interval",
   "What is stated of an interval kernel" and "One limb").

   Notation: T is the IEEE format of IeeeOperations.v; Omega is its largest number;
   xval a is the extended real number a limb stands for; xrd and xru are the roundings
   down and up in the format with overflow (IeeeVocabulary.v); an interval, its members
   and the exact range of an operation are those of IeeeIntervalVocabulary.v. X, Y are the
   operands and Z the result.

   What is proved.

   - interval_make_1, for any two values of T (interval_make_1_correct): the result is a
     canonical interval; it is the interval [lo, hi] when lo <= hi, lo < +infinity and
     hi > -infinity; the whole line when a bound is a NaN, whatever the other bound is;
     and the empty set otherwise, in particular for reversed bounds and for the two pairs
     of equal infinities (interval_make_1_reversed, interval_make_1_equal_infinities).
     For every precision.

   - interval_neg_1, for a canonical operand (interval_neg_1_correct): I1 the result is
     canonical; I2 it is empty exactly when the operand is; I3 it contains -x for every
     member x; I4 it is exact: its members are exactly the -x; I5 it is bounded exactly
     when the operand is. For every precision.

   - interval_add_1 and interval_sub_1, for canonical operands, from precision 2
     (interval_add_1_correct, interval_sub_1_correct):
       I1  Z is canonical;
       I2  Z is empty exactly when an operand is;
       I3  x + y (x - y) is a member of Z for all members x of X and y of Y, unbounded
           operands included;
       I4  for nonempty operands, the lower bound of Z is the rounding down, in the
           format with overflow, of the lower bound of the exact range, and its upper
           bound the rounding up of the upper bound of the exact range; an infinite
           bound of the exact range is returned as that infinity;
       I5  for bounded operands, Z is bounded exactly when every member of the exact
           range is at most Omega in magnitude.
     The bounds of the exact range are those of the vocabulary (range_lower,
     range_upper); that they are the sums of the bounds of the operands, as extended real
     numbers, is range_add_lower and range_add_upper (range_sub_lower, range_sub_upper).

   - interval_mul_1, for canonical operands, for every precision
     (interval_mul_1_correct): I1, I2, I3 and I5 as above. I4, for nonempty operands
     (interval_mul_1_tight_range): with lo and hi the bounds of the exact range, the
     lower bound of Z is the rounding down of lo in the format with overflow or the
     number of the format before it, and its upper bound the rounding up of hi or the
     number after it; and they are the rounding down of lo and the rounding up of hi
     when each of the four products of bounds is zero, infinite or at least
     2^(2 prec - 1) eta in magnitude (product_large). The same statement with lo and hi
     the least and the greatest of the four products of bounds, taken with
     0 * infinity = 0, is interval_mul_1_tight; that these are the bounds of the exact
     range is range_mul_lower and range_mul_upper.

   What is not proved for the product: nothing of I1 to I5 as the design page states
   them. The page does not say which of the two values a bound takes when a product of
   bounds is below 2^(2 prec - 1) eta, and neither does this file.

   The listings. The five kernels are not generated yet: interval_make_1_listing and the
   four others, in section Listings, are their listings written by hand in the text the
   generator prints for the IEEE model (checked against the generator's printer on the
   kernel descriptions), and the generated IeeeModel.interval_make_1 and the others
   will replace them. interval_mul_1_listing calls mul_dir_1_ieee_listing of
   IeeeDirectedProd.v, which is in the same situation.

   The proofs. A limb is replaced by the extended real number it stands for as early as
   possible: a comparison of limbs is the comparison of their values (lt_xval, le_xval,
   eq_xval), the directed sums are xrd and xru of the sum of the values (IeeeDirected.v),
   and what remains is about extended real numbers, by cases on what a bound is. The
   last five lines of the sum, shared by the difference and the product, are treated
   once (interval_tail): they return the empty set exactly when an operand is empty, and
   containment for nonempty operands gives the canonical form, since an interval with a
   member is a nonempty canonical interval. *)
From Stdlib Require Import Reals ZArith Bool Lia Lra Psatz.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements IeeeStatements.
From Kairn Require Import Format Normalized Convert DirectedSum DirectedProd.
From Kairn Require Import IeeeBridge IeeeVocabulary IeeeEFT IeeeOps IeeeExt.
From Kairn Require Import Rectangle IeeeProduct IeeeDirected IeeeDirectedProd IeeeEntry.
From Kairn Require Import IeeeIntervalVocabulary.
From Kairn Require IeeeOperations.
From Kairn.Gen Require IeeeModel.
Open Scope R_scope.

(** * The listings *)

Section Listings.
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

Local Notation pinf := (IeeeOperations.pinf prec emax).
Local Notation neg := (IeeeOperations.neg prec emax nan_opp).
Local Notation lt := (IeeeOperations.lt prec emax).
Local Notation le := (IeeeOperations.le prec emax).
Local Notation eq := (IeeeOperations.eq prec emax).
Local Notation guard := (IeeeOperations.guard prec emax nan_plus).
Local Notation add_down_1 := (IeeeModel.add_down_1 prec emax nan_plus nan_minus nan_abs).
Local Notation add_up_1 := (IeeeModel.add_up_1 prec emax nan_plus nan_minus nan_abs).
Local Notation sub_down_1 := (IeeeModel.sub_down_1 prec emax nan_plus nan_minus nan_opp nan_abs).
Local Notation sub_up_1 := (IeeeModel.sub_up_1 prec emax nan_plus nan_minus nan_opp nan_abs).
Local Notation mul_dir_1 := (mul_dir_1_ieee_listing prec emax nan_opp nan_abs nan_fma).

(* Hand-written IEEE models of the listings of the five kernels, in the text the generator
   prints for the IEEE model. The kernels are not generated yet; the generated
   IeeeModel.interval_make_1, interval_neg_1, interval_add_1, interval_sub_1 and
   interval_mul_1 will replace these definitions. *)
Definition interval_make_1_listing (lo hi : float) : float * float :=
  let gl := guard lo in
  let gu := guard hi in
  let ok := le gl gu in
  let nl := lt gl pinf in
  let mi := neg pinf in
  let nu := lt mi gu in
  let va := andb ok nl in
  let v := andb va nu in
  let ql := eq gl gl in
  let qu := eq gu gu in
  let nn := andb ql qu in
  let el := if nn then pinf else mi in
  let eu := if nn then mi else pinf in
  let zl := if v then gl else el in
  let zu := if v then gu else eu in
  (zl, zu).

Definition interval_neg_1_listing (xl xu : float) : float * float :=
  let zl := neg xu in
  let zu := neg xl in
  (zl, zu).

Definition interval_add_1_listing (xl xu yl yu : float) : float * float :=
  let l := add_down_1 xl yl in
  let h := add_up_1 xu yu in
  let nx := lt xl pinf in
  let ny := lt yl pinf in
  let ne := andb nx ny in
  let mi := neg pinf in
  let zl := if ne then l else pinf in
  let zu := if ne then h else mi in
  (zl, zu).

Definition interval_sub_1_listing (xl xu yl yu : float) : float * float :=
  let l := sub_down_1 xl yu in
  let h := sub_up_1 xu yl in
  let nx := lt xl pinf in
  let ny := lt yl pinf in
  let ne := andb nx ny in
  let mi := neg pinf in
  let zl := if ne then l else pinf in
  let zu := if ne then h else mi in
  (zl, zu).

Definition interval_mul_1_listing (xl xu yl yu : float) : float * float :=
  let '(d1, v1) := mul_dir_1 xl yl in
  let '(d2, v2) := mul_dir_1 xl yu in
  let '(d3, v3) := mul_dir_1 xu yl in
  let '(d4, v4) := mul_dir_1 xu yu in
  let ma := lt d2 d1 in
  let da := if ma then d2 else d1 in
  let mb := lt d4 d3 in
  let db := if mb then d4 else d3 in
  let mc := lt db da in
  let l := if mc then db else da in
  let na := lt v1 v2 in
  let va := if na then v2 else v1 in
  let nb := lt v3 v4 in
  let vb := if nb then v4 else v3 in
  let nc := lt va vb in
  let h := if nc then vb else va in
  let nx := lt xl pinf in
  let ny := lt yl pinf in
  let ne := andb nx ny in
  let mi := neg pinf in
  let zl := if ne then l else pinf in
  let zu := if ne then h else mi in
  (zl, zu).

End Listings.

(** * Extended real numbers: comparisons as propositions, by cases *)

Lemma Rle_bool_inv : forall x y : R, Rle_bool x y = true -> x <= y.
Proof. intros x y. destruct (Rle_bool_spec x y); [trivial|intros K; discriminate K]. Qed.

Lemma Rlt_bool_inv : forall x y : R, Rlt_bool x y = true -> x < y.
Proof. intros x y. destruct (Rlt_bool_spec x y); [trivial|intros K; discriminate K]. Qed.

(* Case analysis on the comparisons of real numbers that a goal about xle, xlt and the
   like contains once the extended real numbers are given by cases, then linear
   arithmetic. The facts to use must be in the goal, as premises. *)
Ltac xfinish :=
  intros;
  repeat match goal with H : _ /\ _ |- _ => destruct H end;
  try discriminate;
  repeat split;
  try reflexivity; try assumption; try lra; try (exfalso; lra).

Ltac xcase :=
  cbn;
  repeat match goal with
  | |- context [Rle_bool ?x ?y] => destruct (Rle_bool_spec x y); cbn
  | |- context [Rlt_bool ?x ?y] => destruct (Rlt_bool_spec x y); cbn
  | |- context [Req_bool ?x ?y] => destruct (Req_bool_spec x y); cbn
  end;
  xfinish.

(* a is a real number. *)
Definition xfin (a : xreal) : Prop :=
  match a with
  | XFin _ => True
  | _ => False
  end.

Lemma xopp_involutive : forall a : xreal, xopp (xopp a) = a.
Proof.
intros [|s|r]; cbn; [reflexivity|now rewrite negb_involutive|now rewrite Ropp_involutive].
Qed.

Lemma xle_antisym : forall a b : xreal, xle a b = true -> xle b a = true -> a = b.
Proof.
intros [|[|]|x] [|[|]|y]; cbn; intros H K; try discriminate H; try discriminate K; trivial.
f_equal. apply Rle_antisym; now apply Rle_bool_inv.
Qed.

(** * Members *)

(* The pair (+infinity, -infinity) has no member. *)
Lemma xmember_empty : forall x : R, ~ xmember (XInf false) (XInf true) x.
Proof. intros x [H _]. discriminate H. Qed.

(* An interval of extended real numbers has a member exactly when it is nonempty
   (member_nonempty and nonempty_member, Rectangle.v). *)
Lemma xmember_nonempty : forall (a b : xreal) (x : R), xmember a b x -> xnonempty a b.
Proof. intros a b x [H K]. exact (member_nonempty a b x H K). Qed.

Lemma xnonempty_member : forall a b : xreal, xnonempty a b -> exists x : R, xmember a b x.
Proof. intros a b [H [K L]]. exact (nonempty_member a b H K L). Qed.

(* The opposite of a member is a member of the interval of the opposite bounds,
   exchanged. *)
Lemma xmember_opp :
  forall (c d : xreal) (y : R), xmember c d y -> xmember (xopp d) (xopp c) (- y).
Proof. intros [|[|]|c] [|[|]|d] y; unfold xmember; xcase. Qed.

Lemma xnonempty_opp : forall c d : xreal, xnonempty c d -> xnonempty (xopp d) (xopp c).
Proof.
intros c d H. destruct (xnonempty_member c d H) as [y Hy].
exact (xmember_nonempty _ _ _ (xmember_opp c d y Hy)).
Qed.

(* A finite lower bound of a nonempty interval is a member, and a finite upper bound. *)
Lemma xmember_lower : forall (r : R) (b : xreal), xnonempty (XFin r) b -> xmember (XFin r) b r.
Proof.
intros r b [H _]. split; [|exact H]. cbn. apply Rle_bool_true. apply Rle_refl.
Qed.

Lemma xmember_upper : forall (a : xreal) (r : R), xnonempty a (XFin r) -> xmember a (XFin r) r.
Proof.
intros a r [H _]. split; [exact H|]. cbn. apply Rle_bool_true. apply Rle_refl.
Qed.

(* The lower bound of a nonempty interval is approached by its members: below every real
   number above it there is a member. Likewise the upper bound. *)
Lemma xmember_approach_lower :
  forall a b : xreal, xnonempty a b ->
  forall s : R, xlt a (XFin s) = true -> exists x : R, xmember a b x /\ x < s.
Proof.
intros a b H s Hs. destruct (xnonempty_member a b H) as [m [M1 M2]].
destruct a as [|[|]|r]; cbn in Hs; try discriminate Hs.
- assert (Q1 := Rmin_l m (s - 1)). assert (Q2 := Rmin_r m (s - 1)).
  set (q := Rmin m (s - 1)) in *. clearbody q.
  exists q. split; [split; [reflexivity|]|lra].
  revert M2 Q1. destruct b as [|[|]|rb]; xcase.
- exists r. split; [exact (xmember_lower r b H)|now apply Rlt_bool_inv].
Qed.

Lemma xmember_approach_upper :
  forall a b : xreal, xnonempty a b ->
  forall s : R, xlt (XFin s) b = true -> exists x : R, xmember a b x /\ s < x.
Proof.
intros a b H s Hs. destruct (xnonempty_member a b H) as [m [M1 M2]].
destruct b as [|[|]|r]; cbn in Hs; try discriminate Hs.
- assert (Q1 := Rmax_l m (s + 1)). assert (Q2 := Rmax_r m (s + 1)).
  set (q := Rmax m (s + 1)) in *. clearbody q.
  exists q. split; [split; [|reflexivity]|lra].
  revert M1 Q1. destruct a as [|[|]|ra]; xcase.
- exists r. split; [exact (xmember_upper a r H)|now apply Rlt_bool_inv].
Qed.

(** * The bounds of a set of real numbers *)

(* A set with a member has one lower bound and one upper bound. *)
Lemma range_lower_unique :
  forall (A : R -> Prop) (lo lo' : xreal),
  (exists z : R, A z) -> range_lower A lo -> range_lower A lo' -> lo = lo'.
Proof.
intros A lo lo' [z0 Hz] [L1 G1] [L2 G2].
generalize (L1 z0 Hz) (L2 z0 Hz).
destruct lo as [|[|]|r]; destruct lo' as [|[|]|r']; cbn; intros E1 E2;
  try discriminate E1; try discriminate E2; trivial.
- exfalso. destruct (G1 r' eq_refl) as [z [Az Lz]].
  assert (Q := Rle_bool_inv _ _ (L2 z Az)). lra.
- exfalso. destruct (G2 r eq_refl) as [z [Az Lz]].
  assert (Q := Rle_bool_inv _ _ (L1 z Az)). lra.
- f_equal. apply Rle_antisym; apply Rnot_lt_le; intros K.
  + assert (T : xlt (XFin r') (XFin r) = true) by (cbn; now apply Rlt_bool_true).
    destruct (G2 r T) as [z [Az Lz]].
    assert (Q := Rle_bool_inv _ _ (L1 z Az)). lra.
  + assert (T : xlt (XFin r) (XFin r') = true) by (cbn; now apply Rlt_bool_true).
    destruct (G1 r' T) as [z [Az Lz]].
    assert (Q := Rle_bool_inv _ _ (L2 z Az)). lra.
Qed.

Lemma range_upper_unique :
  forall (A : R -> Prop) (hi hi' : xreal),
  (exists z : R, A z) -> range_upper A hi -> range_upper A hi' -> hi = hi'.
Proof.
intros A hi hi' [z0 Hz] [L1 G1] [L2 G2].
generalize (L1 z0 Hz) (L2 z0 Hz).
destruct hi as [|[|]|r]; destruct hi' as [|[|]|r']; cbn; intros E1 E2;
  try discriminate E1; try discriminate E2; trivial.
- exfalso. destruct (G1 r' eq_refl) as [z [Az Lz]].
  assert (Q := Rle_bool_inv _ _ (L2 z Az)). lra.
- exfalso. destruct (G2 r eq_refl) as [z [Az Lz]].
  assert (Q := Rle_bool_inv _ _ (L1 z Az)). lra.
- f_equal. apply Rle_antisym; apply Rnot_lt_le; intros K.
  + assert (T : xlt (XFin r') (XFin r) = true) by (cbn; now apply Rlt_bool_true).
    destruct (G1 r' T) as [z [Az Lz]].
    assert (Q := Rle_bool_inv _ _ (L2 z Az)). lra.
  + assert (T : xlt (XFin r) (XFin r') = true) by (cbn; now apply Rlt_bool_true).
    destruct (G2 r T) as [z [Az Lz]].
    assert (Q := Rle_bool_inv _ _ (L1 z Az)). lra.
Qed.

(* The bounds of a set depend on its members only. *)
Lemma range_lower_ext :
  forall (A B : R -> Prop) (lo : xreal),
  (forall z : R, A z <-> B z) -> range_lower A lo -> range_lower B lo.
Proof.
intros A B lo E [L G]. split.
- intros z Hz. apply L. now apply E.
- intros t Ht. destruct (G t Ht) as [z [Az Lz]]. exists z. split; [now apply E|exact Lz].
Qed.

Lemma range_upper_ext :
  forall (A B : R -> Prop) (hi : xreal),
  (forall z : R, A z <-> B z) -> range_upper A hi -> range_upper B hi.
Proof.
intros A B hi E [L G]. split.
- intros z Hz. apply L. now apply E.
- intros t Ht. destruct (G t Ht) as [z [Az Lz]]. exists z. split; [now apply E|exact Lz].
Qed.

(** * The exact range of a sum and of a difference *)

Lemma xadd_lower :
  forall (a c : xreal) (x y : R),
  xle a (XFin x) = true -> xle c (XFin y) = true -> xle (xadd a c) (XFin (x + y)) = true.
Proof. intros [|[|]|a] [|[|]|c] x y; xcase. Qed.

Lemma xadd_upper :
  forall (b d : xreal) (x y : R),
  xle (XFin x) b = true -> xle (XFin y) d = true -> xle (XFin (x + y)) (xadd b d) = true.
Proof. intros [|[|]|b] [|[|]|d] x y; xcase. Qed.

(* The lower bound of the exact range of the sum of two nonempty intervals is the sum of
   their lower bounds, as extended real numbers: -infinity when one of them is. *)
Lemma range_add_lower :
  forall a b c d : xreal, xnonempty a b -> xnonempty c d ->
  range_lower (range_2 (fun x y : R => x + y) (xmember a b) (xmember c d)) (xadd a c).
Proof.
intros a b c d Hx Hy. split.
- intros z [x [y [[Hxa _] [[Hyc _] E]]]]. cbv beta in E. rewrite E. now apply xadd_lower.
- intros t Ht.
  destruct (xnonempty_member a b Hx) as [mx Mx]. destruct (xnonempty_member c d Hy) as [my My].
  assert (Na := proj1 (proj2 Hx)). assert (Nc := proj1 (proj2 Hy)).
  destruct a as [|[|]|ra]; cbn in Na; try discriminate Na.
  + destruct (xmember_approach_lower _ _ Hx (t - my) eq_refl) as [x [X1 X2]].
    exists (x + my). split; [|lra]. exists x, my. exact (conj X1 (conj My eq_refl)).
  + destruct c as [|[|]|rc]; cbn in Nc; try discriminate Nc.
    * destruct (xmember_approach_lower _ _ Hy (t - mx) eq_refl) as [y [Y1 Y2]].
      exists (mx + y). split; [|lra]. exists mx, y. exact (conj Mx (conj Y1 eq_refl)).
    * cbn in Ht. apply Rlt_bool_inv in Ht.
      exists (ra + rc). split; [|exact Ht]. exists ra, rc.
      exact (conj (xmember_lower ra b Hx) (conj (xmember_lower rc d Hy) eq_refl)).
Qed.

Lemma range_add_upper :
  forall a b c d : xreal, xnonempty a b -> xnonempty c d ->
  range_upper (range_2 (fun x y : R => x + y) (xmember a b) (xmember c d)) (xadd b d).
Proof.
intros a b c d Hx Hy. split.
- intros z [x [y [[_ Hxb] [[_ Hyd] E]]]]. cbv beta in E. rewrite E. now apply xadd_upper.
- intros t Ht.
  destruct (xnonempty_member a b Hx) as [mx Mx]. destruct (xnonempty_member c d Hy) as [my My].
  assert (Nb := proj2 (proj2 Hx)). assert (Nd := proj2 (proj2 Hy)).
  destruct b as [|[|]|rb]; cbn in Nb; try discriminate Nb.
  + destruct (xmember_approach_upper _ _ Hx (t - my) eq_refl) as [x [X1 X2]].
    exists (x + my). split; [|lra]. exists x, my. exact (conj X1 (conj My eq_refl)).
  + destruct d as [|[|]|rd]; cbn in Nd; try discriminate Nd.
    * destruct (xmember_approach_upper _ _ Hy (t - mx) eq_refl) as [y [Y1 Y2]].
      exists (mx + y). split; [|lra]. exists mx, y. exact (conj Mx (conj Y1 eq_refl)).
    * cbn in Ht. apply Rlt_bool_inv in Ht.
      exists (rb + rd). split; [|exact Ht]. exists rb, rd.
      exact (conj (xmember_upper a rb Hx) (conj (xmember_upper c rd Hy) eq_refl)).
Qed.

(* A difference is the sum with the opposite interval: the exact range of x - y for y in
   [c, d] is that of x + y' for y' in [-d, -c]. *)
Lemma range_sub_add :
  forall (a b c d : xreal) (z : R),
  range_2 (fun x y : R => x + y) (xmember a b) (xmember (xopp d) (xopp c)) z <->
  range_2 (fun x y : R => x - y) (xmember a b) (xmember c d) z.
Proof.
intros a b c d z. split.
- intros [x [y [Hx [Hy E]]]]. exists x, (- y). split; [exact Hx|split].
  + generalize (xmember_opp _ _ _ Hy). now rewrite 2!xopp_involutive.
  + cbv beta in *. rewrite E. ring.
- intros [x [y [Hx [Hy E]]]]. exists x, (- y). split; [exact Hx|split].
  + now apply xmember_opp.
  + cbv beta in *. rewrite E. ring.
Qed.

Lemma range_sub_lower :
  forall a b c d : xreal, xnonempty a b -> xnonempty c d ->
  range_lower (range_2 (fun x y : R => x - y) (xmember a b) (xmember c d)) (xadd a (xopp d)).
Proof.
intros a b c d Hx Hy.
apply range_lower_ext with (1 := range_sub_add a b c d).
apply range_add_lower; [exact Hx|now apply xnonempty_opp].
Qed.

Lemma range_sub_upper :
  forall a b c d : xreal, xnonempty a b -> xnonempty c d ->
  range_upper (range_2 (fun x y : R => x - y) (xmember a b) (xmember c d)) (xadd b (xopp c)).
Proof.
intros a b c d Hx Hy.
apply range_upper_ext with (1 := range_sub_add a b c d).
apply range_add_upper; [exact Hx|now apply xnonempty_opp].
Qed.

(** * More of the order of the extended real numbers *)

Lemma xle_refl_l : forall a b : xreal, xle a b = true -> xle a a = true.
Proof. intros [|[|]|x] [|[|]|y]; xcase. Qed.

Lemma xle_refl_r : forall a b : xreal, xle a b = true -> xle b b = true.
Proof. intros [|[|]|x] [|[|]|y]; xcase. Qed.

Lemma xle_trans :
  forall a b c : xreal, xle a b = true -> xle b c = true -> xle a c = true.
Proof. intros [|[|]|x] [|[|]|y] [|[|]|z]; xcase. Qed.

Lemma xle_opp : forall a b : xreal, xle a b = true -> xle (xopp b) (xopp a) = true.
Proof. intros [|[|]|x] [|[|]|y]; xcase. Qed.

(* The minimum and the maximum that lt and select compute (xmin and xmax of Rectangle.v)
   are below and above their operands, when these are not NaN. *)
Lemma xmin_le_l :
  forall a b : xreal, xle a a = true -> xle b b = true -> xle (xmin a b) a = true.
Proof. intros [|[|]|x] [|[|]|y]; unfold xmin; xcase. Qed.

Lemma xmin_le_r :
  forall a b : xreal, xle a a = true -> xle b b = true -> xle (xmin a b) b = true.
Proof. intros [|[|]|x] [|[|]|y]; unfold xmin; xcase. Qed.

Lemma xmax_ge_l :
  forall a b : xreal, xle a a = true -> xle b b = true -> xle a (xmax a b) = true.
Proof. intros [|[|]|x] [|[|]|y]; unfold xmax; xcase. Qed.

Lemma xmax_ge_r :
  forall a b : xreal, xle a a = true -> xle b b = true -> xle b (xmax a b) = true.
Proof. intros [|[|]|x] [|[|]|y]; unfold xmax; xcase. Qed.

Lemma xmin_refl :
  forall a b : xreal, xle a a = true -> xle b b = true -> xle (xmin a b) (xmin a b) = true.
Proof. intros a b Ha Hb. destruct (xmin_cases a b) as [E|E]; rewrite E; assumption. Qed.

Lemma xmax_refl :
  forall a b : xreal, xle a a = true -> xle b b = true -> xle (xmax a b) (xmax a b) = true.
Proof. intros a b Ha Hb. destruct (xmax_cases a b) as [E|E]; rewrite E; assumption. Qed.

(* The least of four values is one of them and is at most each; the greatest of four,
   likewise. *)
Lemma xmin4_cases :
  forall m1 m2 m3 m4 : xreal,
  xmin (xmin m1 m2) (xmin m3 m4) = m1 \/ xmin (xmin m1 m2) (xmin m3 m4) = m2 \/
  xmin (xmin m1 m2) (xmin m3 m4) = m3 \/ xmin (xmin m1 m2) (xmin m3 m4) = m4.
Proof.
intros m1 m2 m3 m4.
destruct (xmin_cases (xmin m1 m2) (xmin m3 m4)) as [E|E]; rewrite E.
- destruct (xmin_cases m1 m2) as [F|F]; rewrite F; auto.
- destruct (xmin_cases m3 m4) as [F|F]; rewrite F; auto.
Qed.

Lemma xmax4_cases :
  forall m1 m2 m3 m4 : xreal,
  xmax (xmax m1 m2) (xmax m3 m4) = m1 \/ xmax (xmax m1 m2) (xmax m3 m4) = m2 \/
  xmax (xmax m1 m2) (xmax m3 m4) = m3 \/ xmax (xmax m1 m2) (xmax m3 m4) = m4.
Proof.
intros m1 m2 m3 m4.
destruct (xmax_cases (xmax m1 m2) (xmax m3 m4)) as [E|E]; rewrite E.
- destruct (xmax_cases m1 m2) as [F|F]; rewrite F; auto.
- destruct (xmax_cases m3 m4) as [F|F]; rewrite F; auto.
Qed.

Lemma xmin4_le_each :
  forall m1 m2 m3 m4 : xreal,
  xle m1 m1 = true -> xle m2 m2 = true -> xle m3 m3 = true -> xle m4 m4 = true ->
  xle (xmin (xmin m1 m2) (xmin m3 m4)) m1 = true /\
  xle (xmin (xmin m1 m2) (xmin m3 m4)) m2 = true /\
  xle (xmin (xmin m1 m2) (xmin m3 m4)) m3 = true /\
  xle (xmin (xmin m1 m2) (xmin m3 m4)) m4 = true.
Proof.
intros m1 m2 m3 m4 R1 R2 R3 R4.
assert (A := xmin_refl m1 m2 R1 R2). assert (B := xmin_refl m3 m4 R3 R4).
assert (L := xmin_le_l _ _ A B). assert (Rr := xmin_le_r _ _ A B).
split; [|split; [|split]].
- exact (xle_trans _ _ _ L (xmin_le_l m1 m2 R1 R2)).
- exact (xle_trans _ _ _ L (xmin_le_r m1 m2 R1 R2)).
- exact (xle_trans _ _ _ Rr (xmin_le_l m3 m4 R3 R4)).
- exact (xle_trans _ _ _ Rr (xmin_le_r m3 m4 R3 R4)).
Qed.

Lemma xmax4_ge_each :
  forall m1 m2 m3 m4 : xreal,
  xle m1 m1 = true -> xle m2 m2 = true -> xle m3 m3 = true -> xle m4 m4 = true ->
  xle m1 (xmax (xmax m1 m2) (xmax m3 m4)) = true /\
  xle m2 (xmax (xmax m1 m2) (xmax m3 m4)) = true /\
  xle m3 (xmax (xmax m1 m2) (xmax m3 m4)) = true /\
  xle m4 (xmax (xmax m1 m2) (xmax m3 m4)) = true.
Proof.
intros m1 m2 m3 m4 R1 R2 R3 R4.
assert (A := xmax_refl m1 m2 R1 R2). assert (B := xmax_refl m3 m4 R3 R4).
assert (L := xmax_ge_l _ _ A B). assert (Rr := xmax_ge_r _ _ A B).
split; [|split; [|split]].
- exact (xle_trans _ _ _ (xmax_ge_l m1 m2 R1 R2) L).
- exact (xle_trans _ _ _ (xmax_ge_r m1 m2 R1 R2) L).
- exact (xle_trans _ _ _ (xmax_ge_l m3 m4 R3 R4) Rr).
- exact (xle_trans _ _ _ (xmax_ge_r m3 m4 R3 R4) Rr).
Qed.

(** * The exact range of a product *)

(* What a bound p of a nonempty interval [a, b] is to its members: a member when it is a
   real number, and otherwise the direction in which the members are unbounded. *)
Definition xbound_of (a b p : xreal) : Prop :=
  match p with
  | XNaN => False
  | XFin r => xmember a b r
  | XInf true => forall M : R, exists x : R, xmember a b x /\ x <= M
  | XInf false => forall M : R, exists x : R, xmember a b x /\ M <= x
  end.

Lemma xbound_lower : forall a b : xreal, xnonempty a b -> xbound_of a b a.
Proof.
intros a b H. assert (Na := proj1 (proj2 H)).
destruct a as [|[|]|r]; cbn in Na; try discriminate Na.
- intros M. destruct (xmember_approach_lower _ _ H M eq_refl) as [x [X1 X2]].
  exists x. split; [exact X1|lra].
- exact (xmember_lower r b H).
Qed.

Lemma xbound_upper : forall a b : xreal, xnonempty a b -> xbound_of a b b.
Proof.
intros a b H. assert (Nb := proj2 (proj2 H)).
destruct b as [|[|]|r]; cbn in Nb; try discriminate Nb.
- intros M. destruct (xmember_approach_upper _ _ H M eq_refl) as [x [X1 X2]].
  exists x. split; [exact X1|lra].
- exact (xmember_upper a r H).
Qed.

Lemma Rabs_neg_le : forall t : R, - Rabs t <= t <= Rabs t.
Proof. intros t. unfold Rabs. destruct (Rcase_abs t); lra. Qed.

(* The product of a bound of X and a bound of Y, taken with 0 * infinity = 0, is
   approached by products of members: below every real number above it there is a
   product x y, and above every real number below it. *)
Lemma corner_approached_below :
  forall a b c d p q : xreal,
  xnonempty a b -> xnonempty c d -> xbound_of a b p -> xbound_of c d q ->
  forall t : R, xlt (xmul0 p q) (XFin t) = true ->
  exists z : R, range_2 (fun x y : R => x * y) (xmember a b) (xmember c d) z /\ z < t.
Proof.
intros a b c d p q HX HY Bp Bq t.
destruct (xnonempty_member a b HX) as [mx Mx]. destruct (xnonempty_member c d HY) as [my My].
assert (Q := Rabs_neg_le t).
destruct p as [|sp|r]; [elim Bp| |]; (destruct q as [|sq|s]; [elim Bq| |]).
- (* two infinite bounds *)
  destruct sp; destruct sq; cbn; intros Ht; try discriminate Ht.
  + destruct (Bp (- (Rabs t + 1))) as [x [X1 X2]]. destruct (Bq 1) as [y [Y1 Y2]].
    exists (x * y). split; [exists x, y; exact (conj X1 (conj Y1 eq_refl))|].
    assert (K : x * y <= x * 1) by (apply Rmult_le_compat_neg_l; lra). lra.
  + destruct (Bp 1) as [x [X1 X2]]. destruct (Bq (- (Rabs t + 1))) as [y [Y1 Y2]].
    exists (x * y). split; [exists x, y; exact (conj X1 (conj Y1 eq_refl))|].
    assert (K : y * x <= y * 1) by (apply Rmult_le_compat_neg_l; lra).
    replace (x * y) with (y * x) by ring. lra.
- (* an infinite bound of X and a real bound of Y *)
  cbn [xmul0]. destruct (Req_bool_spec s 0) as [Z|Z].
  + cbn [xlt]. intros Ht. apply Rlt_bool_inv in Ht.
    exists (mx * s). split; [exists mx, s; exact (conj Mx (conj Bq eq_refl))|].
    rewrite Z, Rmult_0_r. exact Ht.
  + destruct (Rlt_bool_spec s 0) as [N|N]; destruct sp; cbn; intros Ht; try discriminate Ht.
    * destruct (Bp ((t - 1) / s)) as [x [X1 X2]].
      exists (x * s). split; [exists x, s; exact (conj X1 (conj Bq eq_refl))|].
      assert (K : s * x <= s * ((t - 1) / s)) by (apply Rmult_le_compat_neg_l; lra).
      replace (s * ((t - 1) / s)) with (t - 1) in K by (field; exact Z).
      replace (x * s) with (s * x) by ring. lra.
    * destruct (Bp ((t - 1) / s)) as [x [X1 X2]].
      exists (x * s). split; [exists x, s; exact (conj X1 (conj Bq eq_refl))|].
      assert (K : s * x <= s * ((t - 1) / s)) by (apply Rmult_le_compat_l; lra).
      replace (s * ((t - 1) / s)) with (t - 1) in K by (field; exact Z).
      replace (x * s) with (s * x) by ring. lra.
- (* a real bound of X and an infinite bound of Y *)
  cbn [xmul0]. destruct (Req_bool_spec r 0) as [Z|Z].
  + cbn [xlt]. intros Ht. apply Rlt_bool_inv in Ht.
    exists (r * my). split; [exists r, my; exact (conj Bp (conj My eq_refl))|].
    rewrite Z, Rmult_0_l. exact Ht.
  + destruct (Rlt_bool_spec r 0) as [N|N]; destruct sq; cbn; intros Ht; try discriminate Ht.
    * destruct (Bq ((t - 1) / r)) as [y [Y1 Y2]].
      exists (r * y). split; [exists r, y; exact (conj Bp (conj Y1 eq_refl))|].
      assert (K : r * y <= r * ((t - 1) / r)) by (apply Rmult_le_compat_neg_l; lra).
      replace (r * ((t - 1) / r)) with (t - 1) in K by (field; exact Z). lra.
    * destruct (Bq ((t - 1) / r)) as [y [Y1 Y2]].
      exists (r * y). split; [exists r, y; exact (conj Bp (conj Y1 eq_refl))|].
      assert (K : r * y <= r * ((t - 1) / r)) by (apply Rmult_le_compat_l; lra).
      replace (r * ((t - 1) / r)) with (t - 1) in K by (field; exact Z). lra.
- (* two real bounds *)
  cbn. intros Ht. apply Rlt_bool_inv in Ht.
  exists (r * s). split; [exists r, s; exact (conj Bp (conj Bq eq_refl))|exact Ht].
Qed.

Lemma corner_approached_above :
  forall a b c d p q : xreal,
  xnonempty a b -> xnonempty c d -> xbound_of a b p -> xbound_of c d q ->
  forall t : R, xlt (XFin t) (xmul0 p q) = true ->
  exists z : R, range_2 (fun x y : R => x * y) (xmember a b) (xmember c d) z /\ t < z.
Proof.
intros a b c d p q HX HY Bp Bq t.
destruct (xnonempty_member a b HX) as [mx Mx]. destruct (xnonempty_member c d HY) as [my My].
assert (Q := Rabs_neg_le t).
destruct p as [|sp|r]; [elim Bp| |]; (destruct q as [|sq|s]; [elim Bq| |]).
- (* two infinite bounds *)
  destruct sp; destruct sq; cbn; intros Ht; try discriminate Ht.
  + destruct (Bp (- (Rabs t + 1))) as [x [X1 X2]]. destruct (Bq (- 1)) as [y [Y1 Y2]].
    exists (x * y). split; [exists x, y; exact (conj X1 (conj Y1 eq_refl))|].
    assert (K : x * (- 1) <= x * y) by (apply Rmult_le_compat_neg_l; lra). lra.
  + destruct (Bp (Rabs t + 1)) as [x [X1 X2]]. destruct (Bq 1) as [y [Y1 Y2]].
    exists (x * y). split; [exists x, y; exact (conj X1 (conj Y1 eq_refl))|].
    assert (K : x * 1 <= x * y) by (apply Rmult_le_compat_l; lra). lra.
- (* an infinite bound of X and a real bound of Y *)
  cbn [xmul0]. destruct (Req_bool_spec s 0) as [Z|Z].
  + cbn [xlt]. intros Ht. apply Rlt_bool_inv in Ht.
    exists (mx * s). split; [exists mx, s; exact (conj Mx (conj Bq eq_refl))|].
    rewrite Z, Rmult_0_r. exact Ht.
  + destruct (Rlt_bool_spec s 0) as [N|N]; destruct sp; cbn; intros Ht; try discriminate Ht.
    * destruct (Bp ((t + 1) / s)) as [x [X1 X2]].
      exists (x * s). split; [exists x, s; exact (conj X1 (conj Bq eq_refl))|].
      assert (K : s * ((t + 1) / s) <= s * x) by (apply Rmult_le_compat_neg_l; lra).
      replace (s * ((t + 1) / s)) with (t + 1) in K by (field; exact Z).
      replace (x * s) with (s * x) by ring. lra.
    * destruct (Bp ((t + 1) / s)) as [x [X1 X2]].
      exists (x * s). split; [exists x, s; exact (conj X1 (conj Bq eq_refl))|].
      assert (K : s * ((t + 1) / s) <= s * x) by (apply Rmult_le_compat_l; lra).
      replace (s * ((t + 1) / s)) with (t + 1) in K by (field; exact Z).
      replace (x * s) with (s * x) by ring. lra.
- (* a real bound of X and an infinite bound of Y *)
  cbn [xmul0]. destruct (Req_bool_spec r 0) as [Z|Z].
  + cbn [xlt]. intros Ht. apply Rlt_bool_inv in Ht.
    exists (r * my). split; [exists r, my; exact (conj Bp (conj My eq_refl))|].
    rewrite Z, Rmult_0_l. exact Ht.
  + destruct (Rlt_bool_spec r 0) as [N|N]; destruct sq; cbn; intros Ht; try discriminate Ht.
    * destruct (Bq ((t + 1) / r)) as [y [Y1 Y2]].
      exists (r * y). split; [exists r, y; exact (conj Bp (conj Y1 eq_refl))|].
      assert (K : r * ((t + 1) / r) <= r * y) by (apply Rmult_le_compat_neg_l; lra).
      replace (r * ((t + 1) / r)) with (t + 1) in K by (field; exact Z). lra.
    * destruct (Bq ((t + 1) / r)) as [y [Y1 Y2]].
      exists (r * y). split; [exists r, y; exact (conj Bp (conj Y1 eq_refl))|].
      assert (K : r * ((t + 1) / r) <= r * y) by (apply Rmult_le_compat_l; lra).
      replace (r * ((t + 1) / r)) with (t + 1) in K by (field; exact Z). lra.
- (* two real bounds *)
  cbn. intros Ht. apply Rlt_bool_inv in Ht.
  exists (r * s). split; [exists r, s; exact (conj Bp (conj Bq eq_refl))|exact Ht].
Qed.

(* The bounds of the exact range of the product of two nonempty intervals are the least
   and the greatest of the four products of bounds, taken as extended real numbers with
   0 * infinity = 0: the rectangle lemma says that they are bounds, and each of the four
   products is approached by products of members. *)
Lemma range_mul_lower :
  forall a b c d : xreal, xnonempty a b -> xnonempty c d ->
  range_lower (range_2 (fun x y : R => x * y) (xmember a b) (xmember c d))
    (xmin (xmin (xmul0 a c) (xmul0 a d)) (xmin (xmul0 b c) (xmul0 b d))).
Proof.
intros a b c d HX HY. split.
- intros z [x [y [[Hx1 Hx2] [[Hy1 Hy2] E]]]]. cbv beta in E. rewrite E.
  exact (proj1 (rectangle a b c d x y Hx1 Hx2 Hy1 Hy2)).
- intros t Ht.
  assert (Ba := xbound_lower a b HX). assert (Bb := xbound_upper a b HX).
  assert (Bc := xbound_lower c d HY). assert (Bd := xbound_upper c d HY).
  destruct (xmin4_cases (xmul0 a c) (xmul0 a d) (xmul0 b c) (xmul0 b d)) as [E|[E|[E|E]]];
    rewrite E in Ht.
  + exact (corner_approached_below a b c d a c HX HY Ba Bc t Ht).
  + exact (corner_approached_below a b c d a d HX HY Ba Bd t Ht).
  + exact (corner_approached_below a b c d b c HX HY Bb Bc t Ht).
  + exact (corner_approached_below a b c d b d HX HY Bb Bd t Ht).
Qed.

Lemma range_mul_upper :
  forall a b c d : xreal, xnonempty a b -> xnonempty c d ->
  range_upper (range_2 (fun x y : R => x * y) (xmember a b) (xmember c d))
    (xmax (xmax (xmul0 a c) (xmul0 a d)) (xmax (xmul0 b c) (xmul0 b d))).
Proof.
intros a b c d HX HY. split.
- intros z [x [y [[Hx1 Hx2] [[Hy1 Hy2] E]]]]. cbv beta in E. rewrite E.
  exact (proj2 (rectangle a b c d x y Hx1 Hx2 Hy1 Hy2)).
- intros t Ht.
  assert (Ba := xbound_lower a b HX). assert (Bb := xbound_upper a b HX).
  assert (Bc := xbound_lower c d HY). assert (Bd := xbound_upper c d HY).
  destruct (xmax4_cases (xmul0 a c) (xmul0 a d) (xmul0 b c) (xmul0 b d)) as [E|[E|[E|E]]];
    rewrite E in Ht.
  + exact (corner_approached_above a b c d a c HX HY Ba Bc t Ht).
  + exact (corner_approached_above a b c d a d HX HY Ba Bd t Ht).
  + exact (corner_approached_above a b c d b c HX HY Bb Bc t Ht).
  + exact (corner_approached_above a b c d b d HX HY Bb Bd t Ht).
Qed.

Section IeeeInterval1.
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

Notation emin := (3 - emax - prec)%Z.
Notation fexp := (FLT_exp emin prec).
Notation format := (generic_format radix2 fexp).
Notation fin x := (is_finite prec emax x = true).
Notation b2r := (B2R prec emax).
Notation neg := (IeeeOperations.neg prec emax nan_opp).
Notation flt := (IeeeOperations.lt prec emax).
Notation fle := (IeeeOperations.le prec emax).
Notation feq := (IeeeOperations.eq prec emax).
Notation guard := (IeeeOperations.guard prec emax nan_plus).
Notation pzero := (IeeeOperations.pzero prec emax).
Notation pinf := (IeeeOperations.pinf prec emax).
Notation ninf := (B754_infinity prec emax true).
Notation xv := (@xval prec emax).
Notation Om := (Omega prec emax).
Notation add_down_1 := (IeeeModel.add_down_1 prec emax nan_plus nan_minus nan_abs).
Notation add_up_1 := (IeeeModel.add_up_1 prec emax nan_plus nan_minus nan_abs).
Notation sub_down_1 := (IeeeModel.sub_down_1 prec emax nan_plus nan_minus nan_opp nan_abs).
Notation sub_up_1 := (IeeeModel.sub_up_1 prec emax nan_plus nan_minus nan_opp nan_abs).
Notation mul_down_1 := (IeeeModel.mul_down_1 prec emax nan_opp nan_abs nan_fma).
Notation mul_up_1 := (IeeeModel.mul_up_1 prec emax nan_opp nan_abs nan_fma).
Notation mul_dir_1 := (mul_dir_1_ieee_listing prec emax nan_opp nan_abs nan_fma).
Notation interval_make_1 := (interval_make_1_listing prec emax nan_plus nan_opp).
Notation interval_neg_1 := (interval_neg_1_listing prec emax nan_opp).
Notation interval_add_1 :=
  (interval_add_1_listing prec emax nan_plus nan_minus nan_opp nan_abs).
Notation interval_sub_1 :=
  (interval_sub_1_listing prec emax nan_plus nan_minus nan_opp nan_abs).
Notation interval_mul_1 := (interval_mul_1_listing prec emax nan_opp nan_abs nan_fma).

(** * Limbs and their extended real numbers *)

Lemma xval_fin_inv : forall (a : float) (r : R), xv a = XFin r -> fin a.
Proof.
intros a r H. destruct (xval_cases prec emax a) as [[F _]|[[s E]|E]]; trivial;
  rewrite E in H; discriminate H.
Qed.

Lemma finite_xfin : forall a : float, xfin (xv a) -> fin a.
Proof.
intros a H. destruct (xval_cases prec emax a) as [[F _]|[[s E]|E]]; trivial;
  rewrite E in H; elim H.
Qed.

Lemma xval_inf_inv :
  forall (a : float) (s : bool), xv a = XInf s -> a = B754_infinity prec emax s.
Proof.
intros a s H. destruct (finite_dec prec emax a) as [F|F].
- rewrite (xval_fin prec emax a F) in H. discriminate H.
- destruct (not_finite_cases prec emax a F) as [N|[s' E]].
  + rewrite (xval_nan prec emax a N) in H. discriminate H.
  + subst a. rewrite xval_inf in H. inversion H. reflexivity.
Qed.

Lemma neg_pinf : neg pinf = ninf.
Proof. reflexivity. Qed.

Lemma lt_pinf_xval : forall a : float, flt a pinf = xlt (xv a) (XInf false).
Proof. intros a. rewrite lt_xval. reflexivity. Qed.

(* A limb that is not a NaN, from its extended real number. *)
Lemma xnonempty_not_nan :
  forall l h : float, xnonempty (xv l) (xv h) ->
  is_nan prec emax l = false /\ is_nan prec emax h = false.
Proof.
intros l h [H _]. split.
- destruct (is_nan prec emax l) eqn:N; trivial.
  rewrite (xval_nan prec emax l N) in H. discriminate H.
- destruct (is_nan prec emax h) eqn:N; trivial.
  rewrite (xval_nan prec emax h N) in H. destruct (xv l) as [|[|]|r]; discriminate H.
Qed.

(** * Canonical intervals *)

Lemma interval_empty_1_xval :
  forall l h : float, interval_empty_1 l h <-> xv l = XInf false /\ xv h = XInf true.
Proof.
intros l h. unfold interval_empty_1, infinity. split.
- intros [E1 E2]. rewrite E1, E2. split; reflexivity.
- intros [H K]. split; now apply xval_inf_inv.
Qed.

(* The empty set has no member, is not a nonempty interval and is not bounded. *)
Lemma empty_no_member :
  forall (l h : float) (x : R), interval_empty_1 l h -> ~ in_interval_1 l h x.
Proof.
intros l h x E. apply interval_empty_1_xval in E. destruct E as [E1 E2].
unfold in_interval_1. rewrite E1, E2. apply xmember_empty.
Qed.

Lemma nonempty_not_empty :
  forall l h : float, interval_nonempty_1 l h -> ~ interval_empty_1 l h.
Proof.
intros l h N E. destruct (xnonempty_member _ _ N) as [x Hx].
exact (empty_no_member l h x E Hx).
Qed.

Lemma bounded_nonempty :
  forall l h : float, interval_1 l h -> interval_bounded_1 l h -> interval_nonempty_1 l h.
Proof.
intros l h [[E _]|N] [F _]; trivial. rewrite E in F. discriminate F.
Qed.

(* An interval with a member is a nonempty canonical interval. *)
Lemma member_interval :
  forall (l h : float) (x : R), in_interval_1 l h x -> interval_nonempty_1 l h.
Proof. intros l h x H. exact (xmember_nonempty _ _ _ H). Qed.

(* The finite bounds of a nonempty interval are members. *)
Lemma lower_member :
  forall l h : float, interval_nonempty_1 l h -> fin l -> in_interval_1 l h (b2r l).
Proof.
intros l h N F. unfold in_interval_1, interval_nonempty_1 in *.
rewrite (xval_fin prec emax l F) in *. now apply xmember_lower.
Qed.

Lemma upper_member :
  forall l h : float, interval_nonempty_1 l h -> fin h -> in_interval_1 l h (b2r h).
Proof.
intros l h N F. unfold in_interval_1, interval_nonempty_1 in *.
rewrite (xval_fin prec emax h F) in *. now apply xmember_upper.
Qed.

(* A member of a bounded interval is at most Omega in magnitude. *)
Lemma bounded_within :
  forall (l h : float) (z : R),
  interval_bounded_1 l h -> in_interval_1 l h z -> Rabs z <= omega prec emax.
Proof.
intros l h z [Fl Fh] [H K].
rewrite (xval_fin prec emax l Fl) in H. rewrite (xval_fin prec emax h Fh) in K.
cbn [xle] in H, K. apply Rle_bool_inv in H. apply Rle_bool_inv in K.
generalize (b2r_Omega prec emax l) (b2r_Omega prec emax h). intros A B.
change (omega prec emax) with Om. apply Rabs_le. lra.
Qed.

(** * The directed roundings of the format with overflow, on bounds *)

(* Rounding down a lower bound keeps it a lower bound, and rounding up an upper bound
   keeps it an upper bound. *)
Lemma xrd_below :
  forall (t : xreal) (z : R),
  xle t (XFin z) = true -> xle (xrd prec emax t) (XFin z) = true.
Proof.
intros [|[|]|r] z H; cbn in H; try discriminate H.
- reflexivity.
- rewrite (xrd_real prec emax). apply Rle_bool_inv in H.
  destruct (Rlt_bool_spec r (- Om)) as [C|C]; [reflexivity|].
  destruct (Rlt_bool_spec Om r) as [D|D]; cbn [xle]; apply Rle_bool_true; [lra|].
  destruct (round_DN_pt radix2 fexp r) as [_ [K _]]. unfold RD. lra.
Qed.

Lemma xru_above :
  forall (t : xreal) (z : R),
  xle (XFin z) t = true -> xle (XFin z) (xru prec emax t) = true.
Proof.
intros [|[|]|r] z H; cbn in H; try discriminate H.
- reflexivity.
- rewrite (xru_real prec emax). apply Rle_bool_inv in H.
  destruct (Rlt_bool_spec Om r) as [C|C]; [reflexivity|].
  destruct (Rlt_bool_spec r (- Om)) as [D|D]; cbn [xle]; apply Rle_bool_true; [lra|].
  destruct (round_UP_pt radix2 fexp r) as [_ [K _]]. unfold RU. lra.
Qed.

(* The rounding down of a real number that is at least -Omega is a real number, and the
   rounding up of one that is at most Omega. *)
Lemma xrd_fin : forall t : R, - Om <= t -> xfin (xrd prec emax (XFin t)).
Proof.
intros t H. rewrite (xrd_real prec emax). rewrite Rlt_bool_false by exact H.
destruct (Rlt_bool Om t); exact I.
Qed.

Lemma xru_fin : forall t : R, t <= Om -> xfin (xru prec emax (XFin t)).
Proof.
intros t H. rewrite (xru_real prec emax). rewrite Rlt_bool_false by exact H.
destruct (Rlt_bool t (- Om)); exact I.
Qed.

(** * The last five lines of the sum, shared by the difference and the product *)

(* With l and h the bounds computed for nonempty operands, the lines
       nx = lt(xl, inf); ny = lt(yl, inf); ne = and(nx, ny); mi = neg(inf)
       zl = select(ne, l, inf); zu = select(ne, h, mi)
   return the empty set exactly when an operand is empty, and (l, h) otherwise. If
   (l, h) contains x o y for all members x and y of nonempty operands, the result is
   canonical (I1), empty exactly when an operand is (I2), and contains x o y for all
   members of the operands (I3). *)
Lemma interval_tail :
  forall (op : R -> R -> R) (xl xu yl yu l h : float),
  interval_1 xl xu -> interval_1 yl yu ->
  (interval_nonempty_1 xl xu -> interval_nonempty_1 yl yu ->
   forall x y : R, in_interval_1 xl xu x -> in_interval_1 yl yu y ->
   in_interval_1 l h (op x y)) ->
  forall zl zu : float,
  zl = (if andb (flt xl pinf) (flt yl pinf) then l else pinf) ->
  zu = (if andb (flt xl pinf) (flt yl pinf) then h else neg pinf) ->
  interval_1 zl zu /\
  (interval_empty_1 zl zu <-> interval_empty_1 xl xu \/ interval_empty_1 yl yu) /\
  (forall x y : R, in_interval_1 xl xu x -> in_interval_1 yl yu y ->
   in_interval_1 zl zu (op x y)) /\
  (interval_nonempty_1 xl xu -> interval_nonempty_1 yl yu -> zl = l /\ zu = h).
Proof.
intros op xl xu yl yu l h CX CY Core zl zu El Eu.
rewrite 2!lt_pinf_xval in El, Eu. rewrite neg_pinf in Eu.
assert (Empty : interval_empty_1 xl xu \/ interval_empty_1 yl yu ->
                zl = pinf /\ zu = ninf).
{ intros [E|E]; apply interval_empty_1_xval in E; destruct E as [E _];
    rewrite E in El, Eu; cbn in El, Eu.
  - now split.
  - rewrite andb_false_r in El, Eu. now split. }
destruct CX as [EX|NX].
{ destruct (Empty (or_introl EX)) as [Zl Zu]. rewrite Zl, Zu.
  split; [left; split; reflexivity|].
  split; [split; [intros _; left; exact EX|intros _; split; reflexivity]|].
  split.
  - intros x y Hx _. elim (empty_no_member xl xu x EX Hx).
  - intros N _. elim (nonempty_not_empty xl xu N EX). }
destruct CY as [EY|NY].
{ destruct (Empty (or_intror EY)) as [Zl Zu]. rewrite Zl, Zu.
  split; [left; split; reflexivity|].
  split; [split; [intros _; right; exact EY|intros _; split; reflexivity]|].
  split.
  - intros x y _ Hy. elim (empty_no_member yl yu y EY Hy).
  - intros _ N. elim (nonempty_not_empty yl yu N EY). }
assert (NX2 : xlt (xv xl) (XInf false) = true) by exact (proj1 (proj2 NX)).
assert (NY2 : xlt (xv yl) (XInf false) = true) by exact (proj1 (proj2 NY)).
rewrite NX2, NY2 in El, Eu. cbn [andb] in El, Eu.
rewrite El, Eu.
destruct (xnonempty_member _ _ NX) as [mx Mx]. destruct (xnonempty_member _ _ NY) as [my My].
assert (NZ : interval_nonempty_1 l h).
{ exact (member_interval l h _ (Core NX NY mx my Mx My)). }
split; [now right|split; [|split; [exact (Core NX NY)|now split]]].
split.
- intros E. elim (nonempty_not_empty l h NZ E).
- intros [E|E]; [elim (nonempty_not_empty xl xu NX E)|elim (nonempty_not_empty yl yu NY E)].
Qed.

(** * interval_make_1 *)

(* interval_make_1, for any two values lo and hi of T: the result is a canonical
   interval; it is [lo, hi] when lo <= hi, lo < +infinity and hi > -infinity (the bounds
   returned stand for the same extended real numbers as lo and hi; a zero may change its
   sign); it is the whole line when a bound is a NaN, whatever the other bound is; and
   it is the empty set otherwise. For every precision. *)
Theorem interval_make_1_correct :
  forall lo hi : float,
  let '(zl, zu) := interval_make_1 lo hi in
  interval_1 zl zu /\
  (xnonempty (xval lo) (xval hi) -> xval zl = xval lo /\ xval zu = xval hi) /\
  (nan lo \/ nan hi -> zl = infinity prec emax true /\ zu = infinity prec emax false) /\
  (~ nan lo -> ~ nan hi -> ~ xnonempty (xval lo) (xval hi) -> interval_empty_1 zl zu).
Proof.
intros lo hi. unfold interval_make_1_listing. cbv zeta.
rewrite le_xval, 2!lt_xval, 2!eq_self, 2!(guard_nan prec emax nan_plus).
rewrite neg_pinf. rewrite 2!(xval_guard prec emax nan_plus).
change (xv pinf) with (XInf false). change (xv ninf) with (XInf true).
destruct (andb (andb (xle (xv lo) (xv hi)) (xlt (xv lo) (XInf false)))
               (xlt (XInf true) (xv hi))) eqn:V; cbv beta iota.
- (* the pair describes an interval *)
  apply andb_true_iff in V. destruct V as [V V3]. apply andb_true_iff in V.
  destruct V as [V1 V2].
  assert (N : xnonempty (xv lo) (xv hi)) by (split; [exact V1|split; [exact V2|exact V3]]).
  destruct (xnonempty_not_nan lo hi N) as [N1 N2].
  split; [right; unfold interval_nonempty_1; now rewrite 2!(xval_guard prec emax nan_plus)|].
  split; [intros _; split; apply (xval_guard prec emax nan_plus)|].
  split.
  + unfold nan. intros [K|K]; congruence.
  + intros _ _ K. elim (K N).
- (* it describes none *)
  assert (NN : ~ xnonempty (xv lo) (xv hi)).
  { intros [N1 [N2 N3]]. rewrite N1, N2, N3 in V. discriminate V. }
  destruct (is_nan prec emax lo) eqn:N1; [|destruct (is_nan prec emax hi) eqn:N2];
    cbn [andb negb].
  + split; [right; split; [reflexivity|split; reflexivity]|].
    split; [intros K; elim (NN K)|split; [intros _; split; reflexivity|]].
    intros K. elim K. exact N1.
  + split; [right; split; [reflexivity|split; reflexivity]|].
    split; [intros K; elim (NN K)|split; [intros _; split; reflexivity|]].
    intros _ K. elim K. exact N2.
  + split; [left; split; reflexivity|].
    split; [intros K; elim (NN K)|split; [|intros _ _ _; split; reflexivity]].
    unfold nan. intros [K|K]; congruence.
Qed.

(* Reversed bounds, hi < lo, give the empty set. *)
Corollary interval_make_1_reversed :
  forall lo hi : float, xlt (xval hi) (xval lo) = true ->
  let '(zl, zu) := interval_make_1 lo hi in interval_empty_1 zl zu.
Proof.
intros lo hi H. generalize (interval_make_1_correct lo hi).
destruct (interval_make_1 lo hi) as [zl zu]. intros [_ [_ [_ K]]]. apply K.
- unfold nan. intros N. rewrite (xval_nan prec emax lo N) in H.
  destruct (xv hi) as [|[|]|r]; discriminate H.
- unfold nan. intros N. rewrite (xval_nan prec emax hi N) in H. discriminate H.
- intros [N _]. revert H N. destruct (xv lo) as [|[|]|a]; destruct (xv hi) as [|[|]|b]; xcase.
Qed.

(* The two pairs of equal infinities, [+infinity, +infinity] and [-infinity, -infinity],
   give the empty set. *)
Corollary interval_make_1_equal_infinities :
  forall s : bool,
  let '(zl, zu) := interval_make_1 (B754_infinity prec emax s) (B754_infinity prec emax s) in
  interval_empty_1 zl zu.
Proof.
intros s. generalize (interval_make_1_correct (B754_infinity prec emax s) (B754_infinity prec emax s)).
destruct (interval_make_1 (B754_infinity prec emax s) (B754_infinity prec emax s)) as [zl zu].
intros [_ [_ [_ K]]]. apply K.
- unfold nan. intros N. discriminate N.
- unfold nan. intros N. discriminate N.
- intros [_ [N1 N2]]. destruct s; [discriminate N2|discriminate N1].
Qed.

(** * interval_neg_1 *)

(* interval_neg_1, for a canonical operand X: the result Z is canonical (I1); it is
   empty exactly when X is (I2); it contains -x for every member x of X (I3); its
   members are exactly the opposites of the members of X, and its bounds the opposites
   of those of X, exchanged (I4: the negation is exact); and it is bounded exactly when
   X is (I5). For every precision. *)
Theorem interval_neg_1_correct :
  forall xl xu : float,
  interval_1 xl xu ->
  let '(zl, zu) := interval_neg_1 xl xu in
  interval_1 zl zu /\
  (interval_empty_1 zl zu <-> interval_empty_1 xl xu) /\
  (forall x : R, in_interval_1 xl xu x -> in_interval_1 zl zu (- x)) /\
  (forall z : R, in_interval_1 zl zu z <-> range_1 (fun x : R => - x) (in_interval_1 xl xu) z) /\
  (xval zl = xopp (xval xu) /\ xval zu = xopp (xval xl)) /\
  (interval_bounded_1 zl zu <-> interval_bounded_1 xl xu).
Proof.
intros xl xu CX. unfold interval_neg_1_listing. cbv zeta.
assert (I3 : forall x : R, in_interval_1 xl xu x -> in_interval_1 (neg xu) (neg xl) (- x)).
{ intros x Hx. unfold in_interval_1. rewrite 2!xval_neg. now apply xmember_opp. }
assert (I3' : forall z : R, in_interval_1 (neg xu) (neg xl) z -> in_interval_1 xl xu (- z)).
{ intros z. unfold in_interval_1. rewrite 2!xval_neg. intros Hz.
  generalize (xmember_opp _ _ _ Hz). now rewrite 2!xopp_involutive. }
assert (I2 : interval_empty_1 (neg xu) (neg xl) <-> interval_empty_1 xl xu).
{ split; intros E; apply interval_empty_1_xval in E; apply interval_empty_1_xval;
    rewrite ?xval_neg in *; revert E;
    destruct (xv xl) as [|[|]|a]; destruct (xv xu) as [|[|]|b]; cbn;
    intros [H K]; try discriminate H; try discriminate K; split; reflexivity. }
split; [|split; [exact I2|split; [exact I3|split; [|split]]]].
- destruct CX as [E|N].
  + left. now apply I2.
  + right. destruct (xnonempty_member _ _ N) as [x Hx].
    exact (member_interval _ _ _ (I3 x Hx)).
- intros z. split.
  + intros Hz. exists (- z). split; [now apply I3'|cbv beta; ring].
  + intros [x [Hx E]]. cbv beta in E. rewrite E. now apply I3.
- split; apply xval_neg.
- unfold interval_bounded_1, finite. rewrite 2!(IeeeExt.neg_finite prec emax nan_opp). tauto.
Qed.

(** * interval_add_1 and interval_sub_1 *)

Lemma interval_add_1_eq :
  forall xl xu yl yu : float,
  interval_add_1 xl xu yl yu
  = (if andb (flt xl pinf) (flt yl pinf) then add_down_1 xl yl else pinf,
     if andb (flt xl pinf) (flt yl pinf) then add_up_1 xu yu else neg pinf).
Proof. reflexivity. Qed.

Lemma interval_sub_1_eq :
  forall xl xu yl yu : float,
  interval_sub_1 xl xu yl yu
  = (if andb (flt xl pinf) (flt yl pinf) then sub_down_1 xl yu else pinf,
     if andb (flt xl pinf) (flt yl pinf) then sub_up_1 xu yl else neg pinf).
Proof. reflexivity. Qed.

(* What the statements of the sum and of the difference share. l and h are limbs whose
   extended real numbers are the rounding down of lo and the rounding up of hi, where
   lo and hi are the bounds of the exact range of op on the operands whenever these are
   nonempty; (zl, zu) is what the last five lines make of (l, h). *)
Lemma interval_directed_facts :
  forall (op : R -> R -> R) (xl xu yl yu l h zl zu : float) (lo hi : xreal),
  interval_1 xl xu -> interval_1 yl yu ->
  xv l = xrd prec emax lo -> xv h = xru prec emax hi ->
  (interval_nonempty_1 xl xu -> interval_nonempty_1 yl yu ->
   range_lower (range_2 op (in_interval_1 xl xu) (in_interval_1 yl yu)) lo /\
   range_upper (range_2 op (in_interval_1 xl xu) (in_interval_1 yl yu)) hi) ->
  (fin xl -> fin xu -> fin yl -> fin yu -> xfin lo /\ xfin hi) ->
  zl = (if andb (flt xl pinf) (flt yl pinf) then l else pinf) ->
  zu = (if andb (flt xl pinf) (flt yl pinf) then h else neg pinf) ->
  interval_1 zl zu /\
  (interval_empty_1 zl zu <-> interval_empty_1 xl xu \/ interval_empty_1 yl yu) /\
  (forall x y : R, in_interval_1 xl xu x -> in_interval_1 yl yu y ->
   in_interval_1 zl zu (op x y)) /\
  (interval_nonempty_1 xl xu -> interval_nonempty_1 yl yu ->
   forall lo' hi' : xreal,
   range_lower (range_2 op (in_interval_1 xl xu) (in_interval_1 yl yu)) lo' ->
   range_upper (range_2 op (in_interval_1 xl xu) (in_interval_1 yl yu)) hi' ->
   xval zl = xrd prec emax lo' /\ xval zu = xru prec emax hi') /\
  (interval_bounded_1 xl xu -> interval_bounded_1 yl yu ->
   (interval_bounded_1 zl zu <->
    forall z : R, range_2 op (in_interval_1 xl xu) (in_interval_1 yl yu) z ->
    Rabs z <= omega prec emax)).
Proof.
intros op xl xu yl yu l h zl zu lo hi CX CY El Eh Range Fin Ezl Ezu.
assert (Core : interval_nonempty_1 xl xu -> interval_nonempty_1 yl yu ->
               forall x y : R, in_interval_1 xl xu x -> in_interval_1 yl yu y ->
               in_interval_1 l h (op x y)).
{ intros NX NY x y Hx Hy. destruct (Range NX NY) as [[L _] [U _]].
  assert (Hz : range_2 op (in_interval_1 xl xu) (in_interval_1 yl yu) (op x y)).
  { exists x, y. exact (conj Hx (conj Hy eq_refl)). }
  split.
  - rewrite El. apply xrd_below. now apply L.
  - rewrite Eh. apply xru_above. now apply U. }
destruct (interval_tail op xl xu yl yu l h CX CY Core zl zu Ezl Ezu) as [I1 [I2 [I3 EQ]]].
split; [exact I1|split; [exact I2|split; [exact I3|split]]].
- intros NX NY lo' hi' Hlo Hhi. destruct (EQ NX NY) as [Zl Zu]. rewrite Zl, Zu.
  destruct (Range NX NY) as [L U].
  destruct (xnonempty_member _ _ NX) as [mx Mx]. destruct (xnonempty_member _ _ NY) as [my My].
  assert (Ex : exists z : R, range_2 op (in_interval_1 xl xu) (in_interval_1 yl yu) z).
  { exists (op mx my), mx, my. exact (conj Mx (conj My eq_refl)). }
  rewrite (range_lower_unique _ _ _ Ex Hlo L), (range_upper_unique _ _ _ Ex Hhi U).
  now split.
- intros BX BY.
  assert (NX := bounded_nonempty xl xu CX BX). assert (NY := bounded_nonempty yl yu CY BY).
  destruct (EQ NX NY) as [Zl Zu]. destruct (Range NX NY) as [L U].
  destruct BX as [Fxl Fxu]. destruct BY as [Fyl Fyu].
  destruct (Fin Fxl Fxu Fyl Fyu) as [Flo Fhi].
  split.
  + intros BZ z [x [y [Hx [Hy E]]]]. rewrite E.
    exact (bounded_within zl zu _ BZ (I3 x y Hx Hy)).
  + intros W. rewrite Zl, Zu. change (omega prec emax) with Om in W.
    destruct lo as [|sl|rl]; [elim Flo|elim Flo|]. destruct hi as [|sh|rh]; [elim Fhi|elim Fhi|].
    destruct L as [L1 L2]. destruct U as [U1 U2].
    split; apply finite_xfin.
    * rewrite El. apply xrd_fin.
      apply Rnot_lt_le. intros K.
      assert (T : xlt (XFin rl) (XFin (- Om)) = true) by (cbn; now apply Rlt_bool_true).
      destruct (L2 (- Om) T) as [z [Hz Lz]].
      assert (Q := Rabs_le_inv _ _ (W z Hz)). lra.
    * rewrite Eh. apply xru_fin.
      apply Rnot_lt_le. intros K.
      assert (T : xlt (XFin Om) (XFin rh) = true) by (cbn; now apply Rlt_bool_true).
      destruct (U2 Om T) as [z [Hz Lz]].
      assert (Q := Rabs_le_inv _ _ (W z Hz)). lra.
Qed.

(* interval_add_1, for canonical operands X and Y, from precision 2. I1: the result Z is
   canonical. I2: Z is empty exactly when an operand is. I3: x + y is a member of Z for
   all members x of X and y of Y. I4: for nonempty operands, with lo and hi the bounds of
   the exact range, the bounds of Z are the rounding down of lo and the rounding up of
   hi in the format with overflow. I5: for bounded operands, Z is bounded exactly when
   every member of the exact range is at most Omega in magnitude. *)
Theorem interval_add_1_correct :
  (2 <= prec)%Z ->
  forall xl xu yl yu : float,
  interval_1 xl xu -> interval_1 yl yu ->
  let '(zl, zu) := interval_add_1 xl xu yl yu in
  interval_1 zl zu /\
  (interval_empty_1 zl zu <-> interval_empty_1 xl xu \/ interval_empty_1 yl yu) /\
  (forall x y : R, in_interval_1 xl xu x -> in_interval_1 yl yu y ->
   in_interval_1 zl zu (x + y)) /\
  (interval_nonempty_1 xl xu -> interval_nonempty_1 yl yu ->
   forall lo hi : xreal,
   range_lower (range_2 (fun x y : R => x + y) (in_interval_1 xl xu) (in_interval_1 yl yu)) lo ->
   range_upper (range_2 (fun x y : R => x + y) (in_interval_1 xl xu) (in_interval_1 yl yu)) hi ->
   xval zl = xrd prec emax lo /\ xval zu = xru prec emax hi) /\
  (interval_bounded_1 xl xu -> interval_bounded_1 yl yu ->
   (interval_bounded_1 zl zu <->
    forall z : R,
    range_2 (fun x y : R => x + y) (in_interval_1 xl xu) (in_interval_1 yl yu) z ->
    Rabs z <= omega prec emax)).
Proof.
intros Hp xl xu yl yu CX CY. rewrite interval_add_1_eq. cbv beta iota.
apply (interval_directed_facts (fun x y : R => x + y) xl xu yl yu
         (add_down_1 xl yl) (add_up_1 xu yu) _ _
         (xadd (xv xl) (xv yl)) (xadd (xv xu) (xv yu)) CX CY).
- exact (add_down_1_ieee prec emax nan_plus nan_minus nan_abs Hp xl yl).
- exact (add_up_1_ieee prec emax nan_plus nan_minus nan_abs Hp xu yu).
- intros NX NY. split.
  + exact (range_add_lower (xv xl) (xv xu) (xv yl) (xv yu) NX NY).
  + exact (range_add_upper (xv xl) (xv xu) (xv yl) (xv yu) NX NY).
- intros F1 F2 F3 F4.
  rewrite (xval_fin prec emax xl F1), (xval_fin prec emax xu F2),
          (xval_fin prec emax yl F3), (xval_fin prec emax yu F4). split; exact I.
- reflexivity.
- reflexivity.
Qed.

(* interval_sub_1, likewise, with x - y. *)
Theorem interval_sub_1_correct :
  (2 <= prec)%Z ->
  forall xl xu yl yu : float,
  interval_1 xl xu -> interval_1 yl yu ->
  let '(zl, zu) := interval_sub_1 xl xu yl yu in
  interval_1 zl zu /\
  (interval_empty_1 zl zu <-> interval_empty_1 xl xu \/ interval_empty_1 yl yu) /\
  (forall x y : R, in_interval_1 xl xu x -> in_interval_1 yl yu y ->
   in_interval_1 zl zu (x - y)) /\
  (interval_nonempty_1 xl xu -> interval_nonempty_1 yl yu ->
   forall lo hi : xreal,
   range_lower (range_2 (fun x y : R => x - y) (in_interval_1 xl xu) (in_interval_1 yl yu)) lo ->
   range_upper (range_2 (fun x y : R => x - y) (in_interval_1 xl xu) (in_interval_1 yl yu)) hi ->
   xval zl = xrd prec emax lo /\ xval zu = xru prec emax hi) /\
  (interval_bounded_1 xl xu -> interval_bounded_1 yl yu ->
   (interval_bounded_1 zl zu <->
    forall z : R,
    range_2 (fun x y : R => x - y) (in_interval_1 xl xu) (in_interval_1 yl yu) z ->
    Rabs z <= omega prec emax)).
Proof.
intros Hp xl xu yl yu CX CY. rewrite interval_sub_1_eq. cbv beta iota.
apply (interval_directed_facts (fun x y : R => x - y) xl xu yl yu
         (sub_down_1 xl yu) (sub_up_1 xu yl) _ _
         (xadd (xv xl) (xopp (xv yu))) (xadd (xv xu) (xopp (xv yl))) CX CY).
- exact (sub_down_1_ieee prec emax nan_plus nan_minus nan_opp nan_abs Hp xl yu).
- exact (sub_up_1_ieee prec emax nan_plus nan_minus nan_opp nan_abs Hp xu yl).
- intros NX NY. split.
  + exact (range_sub_lower (xv xl) (xv xu) (xv yl) (xv yu) NX NY).
  + exact (range_sub_upper (xv xl) (xv xu) (xv yl) (xv yu) NX NY).
- intros F1 F2 F3 F4.
  rewrite (xval_fin prec emax xl F1), (xval_fin prec emax xu F2),
          (xval_fin prec emax yl F3), (xval_fin prec emax yu F4). split; exact I.
- reflexivity.
- reflexivity.
Qed.

(** * interval_mul_1 *)

(* The least of four limbs and the greatest of four limbs, as the six lines
       ma = lt(d2, d1); da = select(ma, d2, d1); mb = lt(d4, d3); db = select(mb, d4, d3);
       mc = lt(db, da); l = select(mc, db, da)
   of the listing select them, and the six lines of the upper bound. *)
Definition limb_min4 (d1 d2 d3 d4 : float) : float :=
  let da := if flt d2 d1 then d2 else d1 in
  let db := if flt d4 d3 then d4 else d3 in
  if flt db da then db else da.

Definition limb_max4 (v1 v2 v3 v4 : float) : float :=
  let va := if flt v1 v2 then v2 else v1 in
  let vb := if flt v3 v4 then v4 else v3 in
  if flt va vb then vb else va.

Lemma limb_min4_cases :
  forall d1 d2 d3 d4 : float,
  limb_min4 d1 d2 d3 d4 = d1 \/ limb_min4 d1 d2 d3 d4 = d2 \/
  limb_min4 d1 d2 d3 d4 = d3 \/ limb_min4 d1 d2 d3 d4 = d4.
Proof.
intros d1 d2 d3 d4.
exact (select_lt_one_of_four prec emax d1 d2 d3 d4 (flt d2 d1) (flt d4 d3)
         (flt (if flt d4 d3 then d4 else d3) (if flt d2 d1 then d2 else d1))).
Qed.

Lemma limb_max4_cases :
  forall v1 v2 v3 v4 : float,
  limb_max4 v1 v2 v3 v4 = v1 \/ limb_max4 v1 v2 v3 v4 = v2 \/
  limb_max4 v1 v2 v3 v4 = v3 \/ limb_max4 v1 v2 v3 v4 = v4.
Proof.
intros v1 v2 v3 v4.
exact (select_lt_one_of_four prec emax v1 v2 v3 v4 (flt v1 v2) (flt v3 v4)
         (flt (if flt v1 v2 then v2 else v1) (if flt v3 v4 then v4 else v3))).
Qed.

(* The listing returns the least of the four lower values and the greatest of the four
   upper ones, or the empty set. *)
Lemma interval_mul_1_eq :
  forall xl xu yl yu : float,
  interval_mul_1 xl xu yl yu
  = (if andb (flt xl pinf) (flt yl pinf)
     then limb_min4 (fst (mul_dir_1 xl yl)) (fst (mul_dir_1 xl yu))
                    (fst (mul_dir_1 xu yl)) (fst (mul_dir_1 xu yu))
     else pinf,
     if andb (flt xl pinf) (flt yl pinf)
     then limb_max4 (snd (mul_dir_1 xl yl)) (snd (mul_dir_1 xl yu))
                    (snd (mul_dir_1 xu yl)) (snd (mul_dir_1 xu yu))
     else neg pinf).
Proof.
intros xl xu yl yu. unfold interval_mul_1_listing.
destruct (mul_dir_1 xl yl) as [d1 v1]. destruct (mul_dir_1 xl yu) as [d2 v2].
destruct (mul_dir_1 xu yl) as [d3 v3]. destruct (mul_dir_1 xu yu) as [d4 v4].
reflexivity.
Qed.

(* The two outputs of mul_dir_1 enclose the product of two bounds that are not NaN, taken
   with 0 * infinity = 0 (mul_dir_1_ieee_encloses, on the components). *)
Lemma mul_dir_1_encloses :
  forall a b : float, is_nan prec emax a = false -> is_nan prec emax b = false ->
  xle (xv (fst (mul_dir_1 a b))) (xmul0 (xv a) (xv b)) = true /\
  xle (xmul0 (xv a) (xv b)) (xv (snd (mul_dir_1 a b))) = true.
Proof.
intros a b Na Nb.
generalize (mul_dir_1_ieee_encloses prec emax nan_opp nan_abs nan_fma a b Na Nb).
destruct (mul_dir_1 a b) as [d v]. cbn [fst snd]. trivial.
Qed.

(* Both outputs of mul_dir_1 are finite when the operands are finite and their product is
   at most Omega in magnitude. *)
Lemma mul_dir_1_finite :
  forall a b : float, fin a -> fin b -> Rabs (b2r a * b2r b) <= Om ->
  fin (fst (mul_dir_1 a b)) /\ fin (snd (mul_dir_1 a b)).
Proof.
intros a b Fa Fb W. rewrite (mul_dir_1_ieee_eq prec emax nan_opp nan_abs nan_fma a b).
cbn [fst snd].
destruct (orb (feq a pzero) (feq b pzero)); [split; reflexivity|].
apply Rabs_le_inv in W.
destruct (mul_down_1_ieee_finite prec emax nan_opp nan_abs nan_fma a b Fa Fb) as [_ [C _]].
destruct (mul_up_1_ieee_finite prec emax nan_opp nan_abs nan_fma a b Fa Fb) as [_ [D _]].
split.
- destruct C as [C|[F _]]; [|exact F]. apply finite_xfin. rewrite C. apply xrd_fin. lra.
- destruct D as [D|[F _]]; [|exact F]. apply finite_xfin. rewrite D. apply xru_fin. lra.
Qed.

(* Containment for nonempty operands: the rectangle lemma on the four enclosures. *)
Lemma interval_mul_1_core :
  forall xl xu yl yu : float,
  interval_nonempty_1 xl xu -> interval_nonempty_1 yl yu ->
  forall x y : R, in_interval_1 xl xu x -> in_interval_1 yl yu y ->
  in_interval_1
    (limb_min4 (fst (mul_dir_1 xl yl)) (fst (mul_dir_1 xl yu))
               (fst (mul_dir_1 xu yl)) (fst (mul_dir_1 xu yu)))
    (limb_max4 (snd (mul_dir_1 xl yl)) (snd (mul_dir_1 xl yu))
               (snd (mul_dir_1 xu yl)) (snd (mul_dir_1 xu yu)))
    (x * y).
Proof.
intros xl xu yl yu NX NY x y [Hx1 Hx2] [Hy1 Hy2].
destruct (xnonempty_not_nan xl xu NX) as [Nxl Nxh].
destruct (xnonempty_not_nan yl yu NY) as [Nyl Nyh].
destruct (mul_dir_1_encloses xl yl Nxl Nyl) as [L1 U1].
destruct (mul_dir_1_encloses xl yu Nxl Nyh) as [L2 U2].
destruct (mul_dir_1_encloses xu yl Nxh Nyl) as [L3 U3].
destruct (mul_dir_1_encloses xu yu Nxh Nyh) as [L4 U4].
split.
- exact (interval_mul_lower prec emax (xv xl) (xv xu) (xv yl) (xv yu) x y Hx1 Hx2 Hy1 Hy2
           _ _ _ _ L1 L2 L3 L4).
- exact (interval_mul_upper prec emax (xv xl) (xv xu) (xv yl) (xv yu) x y Hx1 Hx2 Hy1 Hy2
           _ _ _ _ U1 U2 U3 U4).
Qed.

(* interval_mul_1, for canonical operands X and Y, for every precision. I1: the result Z
   is canonical. I2: Z is empty exactly when an operand is. I3: x y is a member of Z for
   all members x of X and y of Y, unbounded operands included. I5: for bounded operands,
   Z is bounded exactly when every member of the exact range is at most Omega in
   magnitude. (I4 is interval_mul_1_tight and interval_mul_1_tight_range, below.) *)
Theorem interval_mul_1_correct :
  forall xl xu yl yu : float,
  interval_1 xl xu -> interval_1 yl yu ->
  let '(zl, zu) := interval_mul_1 xl xu yl yu in
  interval_1 zl zu /\
  (interval_empty_1 zl zu <-> interval_empty_1 xl xu \/ interval_empty_1 yl yu) /\
  (forall x y : R, in_interval_1 xl xu x -> in_interval_1 yl yu y ->
   in_interval_1 zl zu (x * y)) /\
  (interval_bounded_1 xl xu -> interval_bounded_1 yl yu ->
   (interval_bounded_1 zl zu <->
    forall z : R,
    range_2 (fun x y : R => x * y) (in_interval_1 xl xu) (in_interval_1 yl yu) z ->
    Rabs z <= omega prec emax)).
Proof.
intros xl xu yl yu CX CY. rewrite interval_mul_1_eq. cbv beta iota.
destruct (interval_tail (fun x y : R => x * y) xl xu yl yu _ _ CX CY
            (interval_mul_1_core xl xu yl yu) _ _ eq_refl eq_refl) as [I1 [I2 [I3 EQ]]].
split; [exact I1|split; [exact I2|split; [exact I3|]]].
intros BX BY.
assert (NX := bounded_nonempty xl xu CX BX). assert (NY := bounded_nonempty yl yu CY BY).
destruct (EQ NX NY) as [Zl Zu]. rewrite Zl, Zu.
split.
- intros BZ z [x [y [Hx [Hy E]]]]. cbv beta in E. rewrite E.
  apply (bounded_within _ _ _ BZ). exact (interval_mul_1_core xl xu yl yu NX NY x y Hx Hy).
- intros W. change (omega prec emax) with Om in W.
  destruct BX as [Fxl Fxu]. destruct BY as [Fyl Fyu].
  assert (C : forall a b : float, fin a -> fin b ->
              in_interval_1 xl xu (b2r a) -> in_interval_1 yl yu (b2r b) ->
              fin (fst (mul_dir_1 a b)) /\ fin (snd (mul_dir_1 a b))).
  { intros a b Fa Fb Ha Hb. apply mul_dir_1_finite; trivial. apply W.
    exists (b2r a), (b2r b). exact (conj Ha (conj Hb eq_refl)). }
  assert (Mxl := lower_member xl xu NX Fxl). assert (Mxu := upper_member xl xu NX Fxu).
  assert (Myl := lower_member yl yu NY Fyl). assert (Myu := upper_member yl yu NY Fyu).
  destruct (C xl yl Fxl Fyl Mxl Myl) as [A1 B1]. destruct (C xl yu Fxl Fyu Mxl Myu) as [A2 B2].
  destruct (C xu yl Fxu Fyl Mxu Myl) as [A3 B3]. destruct (C xu yu Fxu Fyu Mxu Myu) as [A4 B4].
  split; unfold finite.
  + destruct (limb_min4_cases (fst (mul_dir_1 xl yl)) (fst (mul_dir_1 xl yu))
                (fst (mul_dir_1 xu yl)) (fst (mul_dir_1 xu yu))) as [E|[E|[E|E]]];
      rewrite E; assumption.
  + destruct (limb_max4_cases (snd (mul_dir_1 xl yl)) (snd (mul_dir_1 xl yu))
                (snd (mul_dir_1 xu yl)) (snd (mul_dir_1 xu yu))) as [E|[E|[E|E]]];
      rewrite E; assumption.
Qed.

(** * The tightness of the product *)

(* The directed roundings of the format with overflow keep the order. *)
Lemma xrd_mono :
  forall a b : xreal, xle a b = true -> xle (xrd prec emax a) (xrd prec emax b) = true.
Proof.
intros [|[|]|ra] [|[|]|rb]; cbn [xle]; intros H; try discriminate H.
- reflexivity.
- reflexivity.
- rewrite (xrd_real prec emax).
  destruct (Rlt_bool rb (- Om)); [reflexivity|]. destruct (Rlt_bool Om rb); reflexivity.
- reflexivity.
- rewrite (xrd_real prec emax).
  destruct (Rlt_bool ra (- Om)); [reflexivity|]. destruct (Rlt_bool Om ra); reflexivity.
- apply Rle_bool_inv in H. generalize (Omega_gt_0 prec emax). intros P0.
  rewrite 2!(xrd_real prec emax).
  destruct (Rlt_bool_spec ra (- Om)) as [A|A].
  + destruct (Rlt_bool rb (- Om)); [reflexivity|]. destruct (Rlt_bool Om rb); reflexivity.
  + rewrite (Rlt_bool_false rb (- Om)) by lra.
    destruct (Rlt_bool_spec Om ra) as [B|B].
    * rewrite (Rlt_bool_true Om rb) by lra. cbn [xle]. apply Rle_bool_true. apply Rle_refl.
    * destruct (Rlt_bool_spec Om rb) as [C|C]; cbn [xle]; apply Rle_bool_true.
      -- destruct (round_DN_pt radix2 fexp ra) as [_ [K _]]. unfold RD. lra.
      -- unfold RD. apply round_le; auto with typeclass_instances.
Qed.

Lemma xru_mono :
  forall a b : xreal, xle a b = true -> xle (xru prec emax a) (xru prec emax b) = true.
Proof. intros a b H. unfold xru. apply xle_opp. apply xrd_mono. now apply xle_opp. Qed.

(* The extended real number of a limb is its own rounding, down and up. *)
Lemma xrd_float : forall q : float, xrd prec emax (xv q) = xv q.
Proof.
intros q. destruct (xval_cases prec emax q) as [[F E]|[[s E]|E]]; rewrite E.
- rewrite (xrd_in prec emax _ (b2r_Omega prec emax q)). f_equal.
  unfold RD. apply round_generic; auto with typeclass_instances. apply (b2r_format prec emax).
- reflexivity.
- reflexivity.
Qed.

Lemma xru_float : forall q : float, xru prec emax (xv q) = xv q.
Proof.
intros q. destruct (xval_cases prec emax q) as [[F E]|[[s E]|E]]; rewrite E.
- rewrite (xru_in prec emax _ (b2r_Omega prec emax q)). f_equal.
  unfold RU. apply round_generic; auto with typeclass_instances. apply (b2r_format prec emax).
- destruct s; reflexivity.
- reflexivity.
Qed.

Lemma xrd_0 : xrd prec emax (XFin 0) = XFin 0.
Proof.
generalize (Omega_gt_0 prec emax). intros P0.
rewrite (xrd_in prec emax 0) by lra. unfold RD. now rewrite round_0 by auto with typeclass_instances.
Qed.

Lemma xru_0 : xru prec emax (XFin 0) = XFin 0.
Proof.
generalize (Omega_gt_0 prec emax). intros P0.
rewrite (xru_in prec emax 0) by lra. unfold RU. now rewrite round_0 by auto with typeclass_instances.
Qed.

(* The number after the largest one is 2^emax. *)
Lemma succ_Omega : Ulp.succ radix2 fexp Om = bpow radix2 emax.
Proof.
rewrite <- (pred_top prec emax). apply succ_pred; auto with typeclass_instances.
apply (format_top prec emax).
Qed.

(* One step down and one step up from a number of the format between -Omega and Omega:
   the neighbor in the format, or the infinity beyond -Omega and Omega. *)
Lemma xpred_format :
  forall f : R, format f -> - Om <= f <= Om ->
  xpred prec emax (XFin f)
  = if Rlt_bool (- Om) f then XFin (Ulp.pred radix2 fexp f) else XInf true.
Proof.
intros f Ff [H1 H2]. generalize (Omega_gt_0 prec emax) (Omega_lt_top prec emax). intros P0 P1.
destruct (Rlt_bool_spec (- Om) f) as [C|C].
- apply (xpred_fin prec emax).
  assert (K : - Om <= Ulp.pred radix2 fexp f).
  { apply pred_ge_gt; auto with typeclass_instances.
    apply generic_format_opp. apply (format_Omega prec emax). }
  generalize (pred_le_id radix2 fexp f). intros L. apply Rabs_lt. lra.
- assert (E : f = - Om) by lra. subst f.
  unfold xpred, xsucc. cbn [xopp]. rewrite Ropp_involutive.
  change (ieee_emin prec emax) with emin.
  rewrite succ_Omega. unfold overflow_of.
  rewrite Rlt_bool_false by (rewrite Rabs_pos_eq; [apply Rle_refl|apply bpow_ge_0]).
  rewrite Rlt_bool_false by apply bpow_ge_0. reflexivity.
Qed.

Lemma xsucc_format :
  forall f : R, format f -> - Om <= f <= Om ->
  xsucc prec emax (XFin f)
  = if Rlt_bool f Om then XFin (Ulp.succ radix2 fexp f) else XInf false.
Proof.
intros f Ff [H1 H2].
assert (E : xsucc prec emax (XFin f) = xopp (xpred prec emax (XFin (- f)))).
{ unfold xpred. cbn [xopp]. rewrite Ropp_involutive. now rewrite xopp_involutive. }
rewrite E, (xpred_format (- f) (generic_format_opp _ _ _ Ff)) by lra.
destruct (Rlt_bool_spec (- Om) (- f)) as [C|C].
- rewrite Rlt_bool_true by lra. cbn [xopp]. unfold Ulp.pred. now rewrite 2!Ropp_involutive.
- rewrite Rlt_bool_false by lra. reflexivity.
Qed.

(* One step below the rounding down of a bound is below it, and one step above its
   rounding up is above it. *)
Lemma xpred_xrd_le :
  forall t : xreal, xle t t = true ->
  xle (xpred prec emax (xrd prec emax t)) (xrd prec emax t) = true.
Proof.
intros [|[|]|r] H; try discriminate H.
- reflexivity.
- reflexivity.
- apply (xpred_le_xrd prec emax).
Qed.

Lemma xsucc_xru_ge :
  forall t : xreal, xle t t = true ->
  xle (xru prec emax t) (xsucc prec emax (xru prec emax t)) = true.
Proof.
intros [|[|]|r] H; try discriminate H.
- reflexivity.
- reflexivity.
- apply (xsucc_ge_xru prec emax).
Qed.

(* The condition under which a product of two bounds is rounded exactly by mul_dir_1:
   for finite bounds, their product is zero or at least 2^(2 prec - 1) eta in magnitude
   (the condition product_large of the claims). An infinite bound makes the product zero
   or infinite, and the condition holds. *)
Definition product_large (a b : float) : Prop :=
  fin a /\ fin b ->
  b2r a * b2r b = 0 \/ bpow radix2 (2 * prec - 1) * eta emin <= Rabs (b2r a * b2r b).

(* With an operand that is not finite, both outputs of mul_dir_1 are the product itself,
   zero or an infinity, which is its own rounding. *)
Lemma mul_dir_1_nonfinite :
  forall a b : float, is_nan prec emax a = false -> is_nan prec emax b = false ->
  is_finite prec emax a = false \/ is_finite prec emax b = false ->
  xv (fst (mul_dir_1 a b)) = xrd prec emax (xmul0 (xv a) (xv b)) /\
  xv (snd (mul_dir_1 a b)) = xru prec emax (xmul0 (xv a) (xv b)).
Proof.
intros a b Na Nb NF.
generalize (mul_dir_1_encloses a b Na Nb).
rewrite (mul_dir_1_ieee_eq prec emax nan_opp nan_abs nan_fma a b). cbn [fst snd].
rewrite (mul_down_1_ieee_nonfinite prec emax nan_opp nan_abs nan_fma a b NF),
        (mul_up_1_ieee_nonfinite prec emax nan_opp nan_abs nan_fma a b NF).
generalize (if orb (feq a pzero) (feq b pzero) then pzero
            else IeeeOperations.prod prec emax nan_fma a b).
intros q [H K]. assert (E := xle_antisym _ _ H K). rewrite <- E.
split; [symmetry; apply xrd_float|symmetry; apply xru_float].
Qed.

(* The lower output d of mul_dir_1 on two bounds that are not NaN, with m their product
   taken with 0 * infinity = 0: m is not a NaN; d is at least the number before the
   rounding down of anything that is at most m; d is at most the rounding down of m; and
   d is the rounding down of m when the product is large. *)
Lemma mul_dir_1_lower :
  forall a b : float, is_nan prec emax a = false -> is_nan prec emax b = false ->
  xle (xmul0 (xv a) (xv b)) (xmul0 (xv a) (xv b)) = true /\
  (forall lo : xreal, xle lo (xmul0 (xv a) (xv b)) = true ->
   xle (xpred prec emax (xrd prec emax lo)) (xv (fst (mul_dir_1 a b))) = true) /\
  xle (xv (fst (mul_dir_1 a b))) (xrd prec emax (xmul0 (xv a) (xv b))) = true /\
  (product_large a b -> xv (fst (mul_dir_1 a b)) = xrd prec emax (xmul0 (xv a) (xv b))).
Proof.
intros a b Na Nb.
destruct (mul_dir_1_encloses a b Na Nb) as [Enc _].
assert (Mm := xle_refl_r _ _ Enc).
split; [exact Mm|].
assert (Exact : xv (fst (mul_dir_1 a b)) = xrd prec emax (xmul0 (xv a) (xv b)) ->
  (forall lo : xreal, xle lo (xmul0 (xv a) (xv b)) = true ->
   xle (xpred prec emax (xrd prec emax lo)) (xv (fst (mul_dir_1 a b))) = true) /\
  xle (xv (fst (mul_dir_1 a b))) (xrd prec emax (xmul0 (xv a) (xv b))) = true /\
  (product_large a b -> xv (fst (mul_dir_1 a b)) = xrd prec emax (xmul0 (xv a) (xv b)))).
{ intros E. split; [|split; [|intros _; exact E]].
  - intros lo Hlo. rewrite E. apply xle_trans with (xrd prec emax lo).
    + apply xpred_xrd_le. exact (xle_refl_l _ _ Hlo).
    + now apply xrd_mono.
  - rewrite E. exact (xrd_mono _ _ Mm). }
destruct (finite_dec prec emax a) as [Fa|Fa]; [destruct (finite_dec prec emax b) as [Fb|Fb]|].
- (* finite operands *)
  clear Enc Mm. revert Exact.
  rewrite (xval_fin prec emax a Fa), (xval_fin prec emax b Fb). cbn [xmul0].
  rewrite (mul_dir_1_ieee_eq prec emax nan_opp nan_abs nan_fma a b). cbn [fst snd].
  rewrite (eq_finite prec emax a pzero Fa eq_refl), (eq_finite prec emax b pzero Fb eq_refl).
  change (b2r pzero) with 0.
  destruct (Req_bool_spec (b2r a) 0) as [Za|Za]; cbn [orb].
  { intros Exact. apply Exact. rewrite Za, Rmult_0_l. symmetry. exact xrd_0. }
  destruct (Req_bool_spec (b2r b) 0) as [Zb|Zb]; cbn [orb].
  { intros Exact. apply Exact. rewrite Zb, Rmult_0_r. symmetry. exact xrd_0. }
  intros Exact.
  destruct (mul_down_1_ieee_finite prec emax nan_opp nan_abs nan_fma a b Fa Fb) as [_ [C X]].
  destruct C as [C|[Fr [Er [Nz Bd]]]]; [now apply Exact|].
  (* one step beyond: a small product, within Omega *)
  assert (Rg := small_round_in_range prec emax _ Bd).
  assert (Ex := xrd_in prec emax _ Rg).
  assert (FX : format (RD emin prec (b2r a * b2r b)))
    by (unfold RD; apply generic_format_round; auto with typeclass_instances).
  split; [|split].
  + intros lo Hlo. rewrite (xval_fin prec emax _ Fr), Er.
    destruct lo as [|[|]|r]; cbn [xle] in Hlo; try discriminate Hlo.
    * reflexivity.
    * apply Rle_bool_inv in Hlo. rewrite (xrd_real prec emax).
      destruct (Rlt_bool_spec r (- Om)) as [A|A]; [reflexivity|].
      rewrite (Rlt_bool_false Om r) by lra. cbv beta iota.
      assert (FR : format (RD emin prec r))
        by (unfold RD; apply generic_format_round; auto with typeclass_instances).
      assert (BR : - Om <= RD emin prec r <= Om).
      { unfold RD. destruct (round_DN_pt radix2 fexp r) as [_ [K1 K2]]. split; [|lra].
        apply K2; [|exact A]. apply generic_format_opp. apply (format_Omega prec emax). }
      rewrite (xpred_format _ FR BR).
      destruct (Rlt_bool (- Om) (RD emin prec r)); [|reflexivity].
      cbn [xle]. apply Rle_bool_true.
      apply (pred_le radix2 fexp _ _ FR FX).
      unfold RD. apply round_le; auto with typeclass_instances; lra.
  + rewrite (xval_fin prec emax _ Fr), Er, Ex. cbn [xle]. apply Rle_bool_true.
    apply pred_le_id.
  + intros L. apply X. destruct (L (conj Fa Fb)) as [Z|K]; [now left|right].
    unfold eta in K. rewrite (P_split emin prec) in K.
    apply (round_abs_ge emin prec tie_even); [exact (format_P prec emax)|exact K].
- apply Exact. apply (mul_dir_1_nonfinite a b Na Nb). now right.
- apply Exact. apply (mul_dir_1_nonfinite a b Na Nb). now left.
Qed.

(* The upper output v of mul_dir_1, likewise: v is at most the number after the rounding
   up of anything that is at least m; v is at least the rounding up of m; and v is the
   rounding up of m when the product is large. *)
Lemma mul_dir_1_upper :
  forall a b : float, is_nan prec emax a = false -> is_nan prec emax b = false ->
  (forall hi : xreal, xle (xmul0 (xv a) (xv b)) hi = true ->
   xle (xv (snd (mul_dir_1 a b))) (xsucc prec emax (xru prec emax hi)) = true) /\
  xle (xru prec emax (xmul0 (xv a) (xv b))) (xv (snd (mul_dir_1 a b))) = true /\
  (product_large a b -> xv (snd (mul_dir_1 a b)) = xru prec emax (xmul0 (xv a) (xv b))).
Proof.
intros a b Na Nb.
destruct (mul_dir_1_encloses a b Na Nb) as [Enc _].
assert (Mm := xle_refl_r _ _ Enc).
assert (Exact : xv (snd (mul_dir_1 a b)) = xru prec emax (xmul0 (xv a) (xv b)) ->
  (forall hi : xreal, xle (xmul0 (xv a) (xv b)) hi = true ->
   xle (xv (snd (mul_dir_1 a b))) (xsucc prec emax (xru prec emax hi)) = true) /\
  xle (xru prec emax (xmul0 (xv a) (xv b))) (xv (snd (mul_dir_1 a b))) = true /\
  (product_large a b -> xv (snd (mul_dir_1 a b)) = xru prec emax (xmul0 (xv a) (xv b)))).
{ intros E. split; [|split; [|intros _; exact E]].
  - intros hi Hhi. rewrite E. apply xle_trans with (xru prec emax hi).
    + now apply xru_mono.
    + apply xsucc_xru_ge. exact (xle_refl_r _ _ Hhi).
  - rewrite E. exact (xru_mono _ _ Mm). }
destruct (finite_dec prec emax a) as [Fa|Fa]; [destruct (finite_dec prec emax b) as [Fb|Fb]|].
- (* finite operands *)
  clear Enc Mm. revert Exact.
  rewrite (xval_fin prec emax a Fa), (xval_fin prec emax b Fb). cbn [xmul0].
  rewrite (mul_dir_1_ieee_eq prec emax nan_opp nan_abs nan_fma a b). cbn [fst snd].
  rewrite (eq_finite prec emax a pzero Fa eq_refl), (eq_finite prec emax b pzero Fb eq_refl).
  change (b2r pzero) with 0.
  destruct (Req_bool_spec (b2r a) 0) as [Za|Za]; cbn [orb].
  { intros Exact. apply Exact. rewrite Za, Rmult_0_l. symmetry. exact xru_0. }
  destruct (Req_bool_spec (b2r b) 0) as [Zb|Zb]; cbn [orb].
  { intros Exact. apply Exact. rewrite Zb, Rmult_0_r. symmetry. exact xru_0. }
  intros Exact.
  destruct (mul_up_1_ieee_finite prec emax nan_opp nan_abs nan_fma a b Fa Fb) as [_ [C X]].
  destruct C as [C|[Fr [Er [Nz Bd]]]]; [now apply Exact|].
  assert (Rg := small_round_in_range prec emax _ Bd).
  assert (Ex := xru_in prec emax _ Rg).
  assert (FX : format (RU emin prec (b2r a * b2r b)))
    by (unfold RU; apply generic_format_round; auto with typeclass_instances).
  split; [|split].
  + intros hi Hhi. rewrite (xval_fin prec emax _ Fr), Er.
    destruct hi as [|[|]|r]; cbn [xle] in Hhi; try discriminate Hhi.
    * reflexivity.
    * apply Rle_bool_inv in Hhi. rewrite (xru_real prec emax).
      destruct (Rlt_bool_spec Om r) as [A|A]; [reflexivity|].
      rewrite (Rlt_bool_false r (- Om)) by lra. cbv beta iota.
      assert (FR : format (RU emin prec r))
        by (unfold RU; apply generic_format_round; auto with typeclass_instances).
      assert (BR : - Om <= RU emin prec r <= Om).
      { unfold RU. destruct (round_UP_pt radix2 fexp r) as [_ [K1 K2]]. split; [lra|].
        apply K2; [|exact A]. apply (format_Omega prec emax). }
      rewrite (xsucc_format _ FR BR).
      destruct (Rlt_bool (RU emin prec r) Om); [|reflexivity].
      cbn [xle]. apply Rle_bool_true.
      apply (succ_le radix2 fexp _ _ FX FR).
      unfold RU. apply round_le; auto with typeclass_instances; lra.
  + rewrite (xval_fin prec emax _ Fr), Er, Ex. cbn [xle]. apply Rle_bool_true.
    apply succ_ge_id.
  + intros L. apply X. destruct (L (conj Fa Fb)) as [Z|K]; [now left|right].
    unfold eta in K. rewrite (P_split emin prec) in K.
    apply (round_abs_ge emin prec tie_even); [exact (format_P prec emax)|exact K].
- apply Exact. apply (mul_dir_1_nonfinite a b Na Nb). now right.
- apply Exact. apply (mul_dir_1_nonfinite a b Na Nb). now left.
Qed.

(* The least of four lower outputs against the least of the four products, and the
   greatest of four upper outputs against the greatest of the four products. *)
Lemma xmin4_sandwich :
  forall m1 m2 m3 m4 d1 d2 d3 d4 : xreal,
  xle m1 m1 = true -> xle m2 m2 = true -> xle m3 m3 = true -> xle m4 m4 = true ->
  (forall lo, xle lo m1 = true -> xle (xpred prec emax (xrd prec emax lo)) d1 = true) ->
  (forall lo, xle lo m2 = true -> xle (xpred prec emax (xrd prec emax lo)) d2 = true) ->
  (forall lo, xle lo m3 = true -> xle (xpred prec emax (xrd prec emax lo)) d3 = true) ->
  (forall lo, xle lo m4 = true -> xle (xpred prec emax (xrd prec emax lo)) d4 = true) ->
  xle d1 (xrd prec emax m1) = true -> xle d2 (xrd prec emax m2) = true ->
  xle d3 (xrd prec emax m3) = true -> xle d4 (xrd prec emax m4) = true ->
  xle (xpred prec emax (xrd prec emax (xmin (xmin m1 m2) (xmin m3 m4))))
      (xmin (xmin d1 d2) (xmin d3 d4)) = true /\
  xle (xmin (xmin d1 d2) (xmin d3 d4))
      (xrd prec emax (xmin (xmin m1 m2) (xmin m3 m4))) = true /\
  (d1 = xrd prec emax m1 -> d2 = xrd prec emax m2 ->
   d3 = xrd prec emax m3 -> d4 = xrd prec emax m4 ->
   xmin (xmin d1 d2) (xmin d3 d4) = xrd prec emax (xmin (xmin m1 m2) (xmin m3 m4))).
Proof.
intros m1 m2 m3 m4 d1 d2 d3 d4 R1 R2 R3 R4 A1 A2 A3 A4 B1 B2 B3 B4.
destruct (xmin4_le_each m1 m2 m3 m4 R1 R2 R3 R4) as [M1 [M2 [M3 M4]]].
destruct (xmin4_le_each d1 d2 d3 d4 (xle_refl_l _ _ B1) (xle_refl_l _ _ B2)
            (xle_refl_l _ _ B3) (xle_refl_l _ _ B4)) as [D1 [D2 [D3 D4]]].
assert (Up : xle (xmin (xmin d1 d2) (xmin d3 d4))
                 (xrd prec emax (xmin (xmin m1 m2) (xmin m3 m4))) = true).
{ destruct (xmin4_cases m1 m2 m3 m4) as [E|[E|[E|E]]]; rewrite E.
  - exact (xle_trans _ _ _ D1 B1).
  - exact (xle_trans _ _ _ D2 B2).
  - exact (xle_trans _ _ _ D3 B3).
  - exact (xle_trans _ _ _ D4 B4). }
split; [|split; [exact Up|]].
- destruct (xmin4_cases d1 d2 d3 d4) as [E|[E|[E|E]]]; rewrite E.
  + exact (A1 _ M1).
  + exact (A2 _ M2).
  + exact (A3 _ M3).
  + exact (A4 _ M4).
- intros E1 E2 E3 E4. apply xle_antisym; [exact Up|].
  destruct (xmin4_cases d1 d2 d3 d4) as [E|[E|[E|E]]]; rewrite E.
  + rewrite E1. exact (xrd_mono _ _ M1).
  + rewrite E2. exact (xrd_mono _ _ M2).
  + rewrite E3. exact (xrd_mono _ _ M3).
  + rewrite E4. exact (xrd_mono _ _ M4).
Qed.

Lemma xmax4_sandwich :
  forall m1 m2 m3 m4 v1 v2 v3 v4 : xreal,
  xle m1 m1 = true -> xle m2 m2 = true -> xle m3 m3 = true -> xle m4 m4 = true ->
  (forall hi, xle m1 hi = true -> xle v1 (xsucc prec emax (xru prec emax hi)) = true) ->
  (forall hi, xle m2 hi = true -> xle v2 (xsucc prec emax (xru prec emax hi)) = true) ->
  (forall hi, xle m3 hi = true -> xle v3 (xsucc prec emax (xru prec emax hi)) = true) ->
  (forall hi, xle m4 hi = true -> xle v4 (xsucc prec emax (xru prec emax hi)) = true) ->
  xle (xru prec emax m1) v1 = true -> xle (xru prec emax m2) v2 = true ->
  xle (xru prec emax m3) v3 = true -> xle (xru prec emax m4) v4 = true ->
  xle (xru prec emax (xmax (xmax m1 m2) (xmax m3 m4)))
      (xmax (xmax v1 v2) (xmax v3 v4)) = true /\
  xle (xmax (xmax v1 v2) (xmax v3 v4))
      (xsucc prec emax (xru prec emax (xmax (xmax m1 m2) (xmax m3 m4)))) = true /\
  (v1 = xru prec emax m1 -> v2 = xru prec emax m2 ->
   v3 = xru prec emax m3 -> v4 = xru prec emax m4 ->
   xmax (xmax v1 v2) (xmax v3 v4) = xru prec emax (xmax (xmax m1 m2) (xmax m3 m4))).
Proof.
intros m1 m2 m3 m4 v1 v2 v3 v4 R1 R2 R3 R4 A1 A2 A3 A4 B1 B2 B3 B4.
destruct (xmax4_ge_each m1 m2 m3 m4 R1 R2 R3 R4) as [M1 [M2 [M3 M4]]].
destruct (xmax4_ge_each v1 v2 v3 v4 (xle_refl_r _ _ B1) (xle_refl_r _ _ B2)
            (xle_refl_r _ _ B3) (xle_refl_r _ _ B4)) as [D1 [D2 [D3 D4]]].
assert (Lo : xle (xru prec emax (xmax (xmax m1 m2) (xmax m3 m4)))
                 (xmax (xmax v1 v2) (xmax v3 v4)) = true).
{ destruct (xmax4_cases m1 m2 m3 m4) as [E|[E|[E|E]]]; rewrite E.
  - exact (xle_trans _ _ _ B1 D1).
  - exact (xle_trans _ _ _ B2 D2).
  - exact (xle_trans _ _ _ B3 D3).
  - exact (xle_trans _ _ _ B4 D4). }
split; [exact Lo|split].
- destruct (xmax4_cases v1 v2 v3 v4) as [E|[E|[E|E]]]; rewrite E.
  + exact (A1 _ M1).
  + exact (A2 _ M2).
  + exact (A3 _ M3).
  + exact (A4 _ M4).
- intros E1 E2 E3 E4. apply xle_antisym; [|exact Lo].
  destruct (xmax4_cases v1 v2 v3 v4) as [E|[E|[E|E]]]; rewrite E.
  + rewrite E1. exact (xru_mono _ _ M1).
  + rewrite E2. exact (xru_mono _ _ M2).
  + rewrite E3. exact (xru_mono _ _ M3).
  + rewrite E4. exact (xru_mono _ _ M4).
Qed.

Lemma xval_limb_min4 :
  forall d1 d2 d3 d4 : float,
  xv (limb_min4 d1 d2 d3 d4) = xmin (xmin (xv d1) (xv d2)) (xmin (xv d3) (xv d4)).
Proof. intros d1 d2 d3 d4. unfold limb_min4. cbv zeta. now rewrite 3!select_lt_xmin. Qed.

Lemma xval_limb_max4 :
  forall v1 v2 v3 v4 : float,
  xv (limb_max4 v1 v2 v3 v4) = xmax (xmax (xv v1) (xv v2)) (xmax (xv v3) (xv v4)).
Proof. intros v1 v2 v3 v4. unfold limb_max4. cbv zeta. now rewrite 3!select_lt_xmax. Qed.

(* interval_mul_1, I4, for nonempty canonical operands X and Y, for every precision. With
   lo the least and hi the greatest of the four products of bounds, taken as extended
   real numbers with 0 * infinity = 0: the lower bound of Z is the rounding down of lo in
   the format with overflow, or the number of the format before it, and its upper bound
   is the rounding up of hi, or the number after it; and they are the rounding down of lo
   and the rounding up of hi when each of the four products of bounds is zero, infinite
   or at least 2^(2 prec - 1) eta in magnitude. *)
Theorem interval_mul_1_tight :
  forall xl xu yl yu : float,
  interval_nonempty_1 xl xu -> interval_nonempty_1 yl yu ->
  let '(zl, zu) := interval_mul_1 xl xu yl yu in
  let lo := xmin (xmin (xmul0 (xval xl) (xval yl)) (xmul0 (xval xl) (xval yu)))
                 (xmin (xmul0 (xval xu) (xval yl)) (xmul0 (xval xu) (xval yu))) in
  let hi := xmax (xmax (xmul0 (xval xl) (xval yl)) (xmul0 (xval xl) (xval yu)))
                 (xmax (xmul0 (xval xu) (xval yl)) (xmul0 (xval xu) (xval yu))) in
  xle (xpred prec emax (xrd prec emax lo)) (xval zl) = true /\
  xle (xval zl) (xrd prec emax lo) = true /\
  xle (xru prec emax hi) (xval zu) = true /\
  xle (xval zu) (xsucc prec emax (xru prec emax hi)) = true /\
  (product_large xl yl -> product_large xl yu ->
   product_large xu yl -> product_large xu yu ->
   xval zl = xrd prec emax lo /\ xval zu = xru prec emax hi).
Proof.
intros xl xu yl yu NX NY. rewrite interval_mul_1_eq.
assert (NX2 : xlt (xv xl) (XInf false) = true) by exact (proj1 (proj2 NX)).
assert (NY2 : xlt (xv yl) (XInf false) = true) by exact (proj1 (proj2 NY)).
rewrite 2!lt_pinf_xval, NX2, NY2. cbn [andb]. cbv beta iota zeta.
rewrite xval_limb_min4, xval_limb_max4.
destruct (xnonempty_not_nan xl xu NX) as [Nxl Nxh].
destruct (xnonempty_not_nan yl yu NY) as [Nyl Nyh].
destruct (mul_dir_1_lower xl yl Nxl Nyl) as [R1 [A1 [B1 C1]]].
destruct (mul_dir_1_lower xl yu Nxl Nyh) as [R2 [A2 [B2 C2]]].
destruct (mul_dir_1_lower xu yl Nxh Nyl) as [R3 [A3 [B3 C3]]].
destruct (mul_dir_1_lower xu yu Nxh Nyh) as [R4 [A4 [B4 C4]]].
destruct (mul_dir_1_upper xl yl Nxl Nyl) as [A1' [B1' C1']].
destruct (mul_dir_1_upper xl yu Nxl Nyh) as [A2' [B2' C2']].
destruct (mul_dir_1_upper xu yl Nxh Nyl) as [A3' [B3' C3']].
destruct (mul_dir_1_upper xu yu Nxh Nyh) as [A4' [B4' C4']].
destruct (xmin4_sandwich _ _ _ _ _ _ _ _ R1 R2 R3 R4 A1 A2 A3 A4 B1 B2 B3 B4) as [L1 [L2 L3]].
destruct (xmax4_sandwich _ _ _ _ _ _ _ _ R1 R2 R3 R4 A1' A2' A3' A4' B1' B2' B3' B4')
  as [U1 [U2 U3]].
split; [exact L1|split; [exact L2|split; [exact U1|split; [exact U2|]]]].
intros P1 P2 P3 P4.
split; [exact (L3 (C1 P1) (C2 P2) (C3 P3) (C4 P4))|exact (U3 (C1' P1) (C2' P2) (C3' P3) (C4' P4))].
Qed.

(* The same with the bounds of the exact range, as the vocabulary defines them: for
   nonempty canonical operands, with lo and hi the lower and the upper bound of the set
   of the products x y, the lower bound of Z is the rounding down of lo or the number of
   the format before it, its upper bound is the rounding up of hi or the number after
   it, and they are the rounding down of lo and the rounding up of hi when each of the
   four products of bounds is zero, infinite or at least 2^(2 prec - 1) eta in
   magnitude. An infinite bound of the exact range is returned as that infinity, or as
   the largest finite number on its side. For every precision. *)
Theorem interval_mul_1_tight_range :
  forall xl xu yl yu : float,
  interval_nonempty_1 xl xu -> interval_nonempty_1 yl yu ->
  let '(zl, zu) := interval_mul_1 xl xu yl yu in
  forall lo hi : xreal,
  range_lower (range_2 (fun x y : R => x * y) (in_interval_1 xl xu) (in_interval_1 yl yu)) lo ->
  range_upper (range_2 (fun x y : R => x * y) (in_interval_1 xl xu) (in_interval_1 yl yu)) hi ->
  xle (xpred prec emax (xrd prec emax lo)) (xval zl) = true /\
  xle (xval zl) (xrd prec emax lo) = true /\
  xle (xru prec emax hi) (xval zu) = true /\
  xle (xval zu) (xsucc prec emax (xru prec emax hi)) = true /\
  (product_large xl yl -> product_large xl yu ->
   product_large xu yl -> product_large xu yu ->
   xval zl = xrd prec emax lo /\ xval zu = xru prec emax hi).
Proof.
intros xl xu yl yu NX NY.
generalize (interval_mul_1_tight xl xu yl yu NX NY).
destruct (interval_mul_1 xl xu yl yu) as [zl zu]. cbv zeta.
intros T lo hi Hlo Hhi.
destruct (xnonempty_member _ _ NX) as [mx Mx]. destruct (xnonempty_member _ _ NY) as [my My].
assert (Ex : exists z : R,
             range_2 (fun x y : R => x * y) (in_interval_1 xl xu) (in_interval_1 yl yu) z).
{ exists (mx * my), mx, my. exact (conj Mx (conj My eq_refl)). }
rewrite (range_lower_unique _ _ _ Ex Hlo (range_mul_lower (xv xl) (xv xu) (xv yl) (xv yu) NX NY)).
rewrite (range_upper_unique _ _ _ Ex Hhi (range_mul_upper (xv xl) (xv xu) (xv yl) (xv yu) NX NY)).
exact T.
Qed.

End IeeeInterval1.
