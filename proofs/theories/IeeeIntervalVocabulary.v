(* The vocabulary of the statements about intervals, in the IEEE model
   (docs/developer/design/milestone2.md, "Interval kernels": "Values of an interval" and
   "What is stated of an interval kernel"). Written by hand; nothing in this file is a
   proof. It extends IeeeVocabulary.v, whose extended real numbers (xreal), comparisons
   (xle, xlt) and values of a limb and of a canonical 2-limb value (xval, xval_2) it uses.
   The generated statements of the interval kernels (proofs/gen/IeeeStatements.v) are
   written with these definitions, and so are the theorems of IeeeInterval1.v and
   IeeeInterval2.v that establish them or say more.

   An interval is a set of real numbers given by two bounds. The vocabulary is small and
   closed:

     xmember lo hi x               the real number x is between the extended real numbers
                                   lo and hi
     xnonempty lo hi               lo and hi are the bounds of a nonempty interval:
                                   lo <= hi, lo < +infinity, hi > -infinity
     interval_empty_k ...          the empty set: (+infinity, -infinity)
     interval_nonempty_k ...       a nonempty canonical interval
     interval_k ...                a canonical interval: one or the other
     in_interval_k ... x           the real number x is a member
     interval_bounded_k ...        both bounds are finite
     range_1 op X, range_2 op X Y  the exact range of an operation: the set of the real
                                   numbers op x, or op x y, for x in X and y in Y
     range_lower A lo              lo is the lower bound of the set A of real numbers: its
                                   greatest lower bound among the extended real numbers
     range_upper A hi              hi is its upper bound, likewise

   Why each has the form it has.

   - Membership is two comparisons of extended real numbers, with no case on the kind of
     interval. A comparison with a NaN is false and +infinity <= x is false for a real x,
     so the empty set (+infinity, -infinity) has no member and an interval with a NaN
     bound has none, by the same formula that gives [1, +infinity] the members x >= 1
     and not +infinity (x is a real number). Containment, I3, is then one line:
     in X x -> in Y y -> in Z (x o y), unbounded and empty operands included.

   - "Nonempty" is the three comparisons of the design page. xle is false on a NaN, so
     xnonempty says that neither bound is a NaN without a separate clause; an interval
     has a member exactly when it is nonempty (member_nonempty and nonempty_member,
     Rectangle.v). For one limb every limb that is not a NaN is a number of the format
     or an infinity, so nothing more is asked; for two limbs each bound is also a
     canonical 2-limb value (IeeeVocabulary.v), which with "not a NaN" leaves a finite
     normalized pair or an infinity followed by a zero.

   - The empty set is the pair of limbs itself, not a property of the values: there is
     one empty interval, and "Z is empty exactly when an operand is" (I2) is an
     equivalence of two such equalities. For two limbs the second limb of an infinite
     bound is a zero of either sign, as in canonical_2.

   - "Bounded" is that both bounds are finite limbs. It is used only of canonical
     intervals, where it implies nonempty (the bounds of the empty set are infinite).

   - The exact range of an operation is a set of real numbers, a predicate on R, built
     from the membership predicates of the operands, so that I3 says that the range is
     inside the result and I5 that it is within the largest finite number, with the same
     set. Its bounds are extended real numbers, defined by what a bound is (a lower bound
     that no real number above it is) and not by a formula in the bounds of the operands:
     the tightness statement I4 then says "the lower bound of the result is the rounding
     down of the lower bound of the exact range" for a sum, a difference and a product
     alike, and which extended real number that is (a sum of bounds, the least of four
     products of bounds with 0 * infinity = 0) is a lemma about the operation, proved
     once. An unbounded range has the bound -infinity or +infinity, and the empty range
     the bounds +infinity and -infinity, those of the empty interval. *)
From Stdlib Require Import Reals ZArith.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements.
From Kairn Require Import IeeeVocabulary.
Open Scope R_scope.

(** * Intervals of extended real numbers *)

(* The real number x is between lo and hi. False when a bound is a NaN, and for the pair
   (+infinity, -infinity). *)
Definition xmember (lo hi : xreal) (x : R) : Prop :=
  xle lo (XFin x) = true /\ xle (XFin x) hi = true.

(* lo and hi are the bounds of a nonempty interval: lo <= hi, lo < +infinity and
   hi > -infinity. Neither is a NaN, since a comparison with a NaN is false. *)
Definition xnonempty (lo hi : xreal) : Prop :=
  xle lo hi = true /\ xlt lo (XInf false) = true /\ xlt (XInf true) hi = true.

(** * The exact range of an operation, and its bounds *)

(* The set of the op x for x in X, and of the op x y for x in X and y in Y. *)
Definition range_1 (op : R -> R) (X : R -> Prop) (z : R) : Prop :=
  exists x : R, X x /\ z = op x.

Definition range_2 (op : R -> R -> R) (X Y : R -> Prop) (z : R) : Prop :=
  exists x y : R, X x /\ Y y /\ z = op x y.

(* lo is the lower bound of A: every member of A is at least lo, and every real number
   above lo is above some member of A. For a set that is unbounded below this is
   lo = -infinity, and for the empty set lo = +infinity (or a NaN, which the statements
   exclude by taking nonempty operands). hi is the upper bound of A, symmetrically. *)
Definition range_lower (A : R -> Prop) (lo : xreal) : Prop :=
  (forall z : R, A z -> xle lo (XFin z) = true) /\
  (forall t : R, xlt lo (XFin t) = true -> exists z : R, A z /\ z < t).

Definition range_upper (A : R -> Prop) (hi : xreal) : Prop :=
  (forall z : R, A z -> xle (XFin z) hi = true) /\
  (forall t : R, xlt (XFin t) hi = true -> exists z : R, A z /\ t < z).

(** * Intervals with bounds of one limb and of two limbs *)

Section IntervalVocabulary.
Variable prec emax : Z.
Notation float := (binary_float prec emax).

(* One limb. The empty set is (+infinity, -infinity); a nonempty interval has bounds
   l <= h that are not NaN, with l < +infinity and h > -infinity; a canonical interval is
   one or the other. *)
Definition interval_empty_1 (l h : float) : Prop :=
  l = infinity prec emax false /\ h = infinity prec emax true.

Definition interval_nonempty_1 (l h : float) : Prop :=
  xnonempty (xval l) (xval h).

Definition interval_1 (l h : float) : Prop :=
  interval_empty_1 l h \/ interval_nonempty_1 l h.

(* The real number x is a member of the interval. *)
Definition in_interval_1 (l h : float) (x : R) : Prop :=
  xmember (xval l) (xval h) x.

(* Both bounds are finite. *)
Definition interval_bounded_1 (l h : float) : Prop :=
  finite l /\ finite h.

(* Two limbs: each bound is a canonical 2-limb value; the empty set is
   ((+infinity, 0), (-infinity, 0)), the zeros of either sign. *)
Definition interval_empty_2 (l0 l1 h0 h1 : float) : Prop :=
  l0 = infinity prec emax false /\ zero l1 /\ h0 = infinity prec emax true /\ zero h1.

Definition interval_nonempty_2 (l0 l1 h0 h1 : float) : Prop :=
  canonical_2 l0 l1 /\ canonical_2 h0 h1 /\ xnonempty (xval_2 l0 l1) (xval_2 h0 h1).

Definition interval_2 (l0 l1 h0 h1 : float) : Prop :=
  interval_empty_2 l0 l1 h0 h1 \/ interval_nonempty_2 l0 l1 h0 h1.

Definition in_interval_2 (l0 l1 h0 h1 : float) (x : R) : Prop :=
  xmember (xval_2 l0 l1) (xval_2 h0 h1) x.

Definition interval_bounded_2 (l0 l1 h0 h1 : float) : Prop :=
  finite l0 /\ finite h0.

End IntervalVocabulary.

Arguments interval_empty_1 {prec emax} l h.
Arguments interval_nonempty_1 {prec emax} l h.
Arguments interval_1 {prec emax} l h.
Arguments in_interval_1 {prec emax} l h x.
Arguments interval_bounded_1 {prec emax} l h.
Arguments interval_empty_2 {prec emax} l0 l1 h0 h1.
Arguments interval_nonempty_2 {prec emax} l0 l1 h0 h1.
Arguments interval_2 {prec emax} l0 l1 h0 h1.
Arguments in_interval_2 {prec emax} l0 l1 h0 h1 x.
Arguments interval_bounded_2 {prec emax} l0 l1 h0 h1.
