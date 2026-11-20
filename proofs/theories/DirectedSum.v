(* Rounding a sum down and up without a rounding mode, in the real model (no overflow):
   two_sum_ord, add_down_1, add_up_1, sub_down_1, sub_up_1
   (docs/developer/design/milestone2.md, "Rounding a sum down and up").

       two_sum_ord(a, b) -> (s, e)        add_down_1(a, b) -> r        add_up_1(a, b) -> r
         aa     = abs(a)                    (s, e) = two_sum_ord(a, b)   (s, e) = two_sum_ord(a, b)
         ab     = abs(b)                    n      = lt(e, 0)            n      = lt(0, e)
         m      = lt(aa, ab)                p      = pred(s)             q      = succ(s)
         h      = select(m, b, a)           r      = select(n, p, s)     r      = select(n, q, s)
         l      = select(m, a, b)
         (s, e) = fast_two_sum(h, l)      sub_down_1(a, b), sub_up_1(a, b): neg(b), then the sum

   Notation: F is the format (precision prec, gradual underflow, smallest positive number
   eta = 2^emin, no largest number); RN, RD, RU are the roundings to nearest (ties to
   even), down and up; pred(s) and succ(s) are the neighbors of s in F.

   What is proved, for all numbers a, b of F and every precision from 2 on:
   - two_sum_ord: s = RN(a + b), s + e = a + b exactly, and (s, e) is normalized. No
     requirement on the operands: the two selects order them by magnitude, which is the
     requirement of fast_two_sum.
   - add_down_1 a b = RD(a + b) and add_up_1 a b = RU(a + b); sub_down_1 a b = RD(a - b)
     and sub_up_1 a b = RU(a - b). Exact in every case.

   Why. (s, e) is a normalized pair of value a + b, and the last three lines of
   add_down_1 are the listing of to_down_2 applied to that pair (those of add_up_1, the
   listing of to_up_2): the definitions are equal by unfolding, and the theorems of
   Convert.v conclude. Their argument: a + b lies strictly between pred(s) and succ(s)
   because s is the number of F nearest to it, and the sign of e = (a + b) - s says in
   which of the two gaps.

   The precision 2 is that of fast_two_sum_correct (Flocq's Fast2Sum_correct); nothing
   else in this file needs more than a positive precision. Precision 1 is not claimed.

   THE MODELS IN THIS FILE ARE WRITTEN BY HAND. Each mirrors a listing of the design page,
   line by line, in the text the generator prints for such a listing (proofs/gen/Model.v:
   abs is Rabs, lt is Rlt_bool, select is if-then-else, pred and succ are Flocq's, a call
   stays a call). When the kernels are generated, Model.two_sum_ord, Model.add_down_1, ...
   replace two_sum_ord_listing, add_down_1_listing, ...: the generated definitions are
   expected to be convertible with these (same body), so that each theorem K_listing_correct
   below proves the generated statement K_spec by `exact`, or after `unfold`. (Checked
   once, outside the build, on the text the generator prints for the kernel descriptions
   of experiments/milestone2/kernels: each definition is equal to its model here by
   reflexivity.) The theorems are stated in the shape the generator gives a statement:
   the hypotheses that the inputs are numbers of the format, then `let` the outputs, then
   that every output is a number of the format and the claims. *)
From Stdlib Require Import Reals ZArith Lia Lra.
From Flocq Require Import Core.
From Kairn.Gen Require Import Model Statements.
From Kairn Require Import Format EFT Convert.
Open Scope R_scope.

(** * The listings, as the generator prints a kernel *)

Section Listings.
Variable emin prec : Z.
Variable choice : Z -> bool.

(* Hand-written model of the listing two_sum_ord; the generated Model.two_sum_ord
   replaces it. *)
Definition two_sum_ord_listing (a b : R) : R * R :=
  let aa := Rabs a in
  let ab := Rabs b in
  let m := Rlt_bool aa ab in
  let h := if m then b else a in
  let l := if m then a else b in
  let '(s, e) := fast_two_sum emin prec choice h l in
  (s, e).

(* Hand-written model of the listing add_down_1; the generated Model.add_down_1 replaces
   it. *)
Definition add_down_1_listing (a b : R) : R :=
  let '(s, e) := two_sum_ord_listing a b in
  let n := Rlt_bool e 0 in
  let p := pred radix2 (FLT_exp emin prec) s in
  let r := if n then p else s in
  r.

(* Hand-written model of the listing add_up_1; the generated Model.add_up_1 replaces it. *)
Definition add_up_1_listing (a b : R) : R :=
  let '(s, e) := two_sum_ord_listing a b in
  let n := Rlt_bool 0 e in
  let q := succ radix2 (FLT_exp emin prec) s in
  let r := if n then q else s in
  r.

(* Hand-written models of the listings sub_down_1 and sub_up_1; the generated
   Model.sub_down_1 and Model.sub_up_1 replace them. *)
Definition sub_down_1_listing (a b : R) : R :=
  let nb := - b in
  let r := add_down_1_listing a nb in
  r.

Definition sub_up_1_listing (a b : R) : R :=
  let nb := - b in
  let r := add_up_1_listing a nb in
  r.

End Listings.

(** * The tail of the directed sums is the listing of to_down_2 and of to_up_2 *)

(* add_down_1 is to_down_2 applied to the pair that two_sum_ord returns, and add_up_1 is
   to_up_2 applied to it: equal by unfolding. *)
Lemma add_down_1_listing_eq :
  forall emin prec choice a b,
  add_down_1_listing emin prec choice a b
  = to_down_2 emin prec (fst (two_sum_ord_listing emin prec choice a b))
                        (snd (two_sum_ord_listing emin prec choice a b)).
Proof.
intros emin prec choice a b. unfold add_down_1_listing.
destruct (two_sum_ord_listing emin prec choice a b) as [s e]. reflexivity.
Qed.

Lemma add_up_1_listing_eq :
  forall emin prec choice a b,
  add_up_1_listing emin prec choice a b
  = to_up_2 emin prec (fst (two_sum_ord_listing emin prec choice a b))
                      (snd (two_sum_ord_listing emin prec choice a b)).
Proof.
intros emin prec choice a b. unfold add_up_1_listing.
destruct (two_sum_ord_listing emin prec choice a b) as [s e]. reflexivity.
Qed.

(** * The directed rounding of a number of which a normalized pair is known *)

(* These two say what the last three lines of the directed sums compute, with no
   reference to a model: if s and e are numbers of the format, s is the rounding to
   nearest of s + e, and s + e is x, then "s, or pred(s) when e < 0" is RD(x) and "s, or
   succ(s) when 0 < e" is RU(x). For every positive precision. *)
Lemma down_of_normalized :
  forall emin prec : Z, (1 <= prec)%Z ->
  forall s e x : R, normalized_2 emin prec s e -> s + e = x ->
  (if Rlt_bool e 0 then pred radix2 (FLT_exp emin prec) s else s) = RD emin prec x.
Proof.
intros emin prec Hp s e x Hn <-.
exact (proj2 (to_down_2_correct emin prec Hp s e Hn)).
Qed.

Lemma up_of_normalized :
  forall emin prec : Z, (1 <= prec)%Z ->
  forall s e x : R, normalized_2 emin prec s e -> s + e = x ->
  (if Rlt_bool 0 e then succ radix2 (FLT_exp emin prec) s else s) = RU emin prec x.
Proof.
intros emin prec Hp s e x Hn <-.
exact (proj2 (to_up_2_correct emin prec Hp s e Hn)).
Qed.

(** * The statements *)

(* two_sum_ord: for all numbers a, b of the format, s = RN(a + b), s + e = a + b, and
   (s, e) is normalized. From precision 2. *)
Theorem two_sum_ord_listing_correct :
  forall emin prec : Z, (2 <= prec)%Z ->
  forall a b : R,
  fmt emin prec a ->
  fmt emin prec b ->
  let '(s, e) := two_sum_ord_listing emin prec tie_even a b in
  s = RN emin prec (a + b) /\
  (s + e) = (a + b) /\
  normalized_2 emin prec s e.
Proof.
intros emin prec Hp a b Fa Fb. unfold two_sum_ord_listing. cbv zeta.
destruct (Rlt_bool_spec (Rabs a) (Rabs b)) as [H|H].
- (* |a| < |b|: fast_two_sum on (b, a) *)
  generalize (fast_two_sum_correct emin prec Hp b a Fb Fa (Rlt_le _ _ H)).
  destruct (fast_two_sum emin prec tie_even b a) as [s e].
  rewrite (Rplus_comm b a). trivial.
- (* |b| <= |a|: fast_two_sum on (a, b) *)
  generalize (fast_two_sum_correct emin prec Hp a b Fa Fb H).
  destruct (fast_two_sum emin prec tie_even a b) as [s e]. trivial.
Qed.

(* The same, on the two components. *)
Corollary two_sum_ord_listing_facts :
  forall emin prec : Z, (2 <= prec)%Z ->
  forall a b : R, fmt emin prec a -> fmt emin prec b ->
  fst (two_sum_ord_listing emin prec tie_even a b) = RN emin prec (a + b) /\
  fst (two_sum_ord_listing emin prec tie_even a b)
  + snd (two_sum_ord_listing emin prec tie_even a b) = a + b /\
  normalized_2 emin prec (fst (two_sum_ord_listing emin prec tie_even a b))
                         (snd (two_sum_ord_listing emin prec tie_even a b)).
Proof.
intros emin prec Hp a b Fa Fb.
generalize (two_sum_ord_listing_correct emin prec Hp a b Fa Fb).
destruct (two_sum_ord_listing emin prec tie_even a b) as [s e]. trivial.
Qed.

(* add_down_1: for all numbers a, b of the format, the result is a number of the format
   and is RD(a + b), the largest number of the format that is at most a + b. From
   precision 2. *)
Theorem add_down_1_listing_correct :
  forall emin prec : Z, (2 <= prec)%Z ->
  forall a b : R,
  fmt emin prec a ->
  fmt emin prec b ->
  let r := add_down_1_listing emin prec tie_even a b in
  fmt emin prec r /\
  r = RD emin prec (a + b).
Proof.
intros emin prec Hp a b Fa Fb r. unfold r. clear r.
destruct (two_sum_ord_listing_facts emin prec Hp a b Fa Fb) as [_ [He Hn]].
rewrite add_down_1_listing_eq, <- He.
apply to_down_2_correct; [lia|exact Hn].
Qed.

(* add_up_1: likewise, RU(a + b), the smallest number of the format that is at least
   a + b. From precision 2. *)
Theorem add_up_1_listing_correct :
  forall emin prec : Z, (2 <= prec)%Z ->
  forall a b : R,
  fmt emin prec a ->
  fmt emin prec b ->
  let r := add_up_1_listing emin prec tie_even a b in
  fmt emin prec r /\
  r = RU emin prec (a + b).
Proof.
intros emin prec Hp a b Fa Fb r. unfold r. clear r.
destruct (two_sum_ord_listing_facts emin prec Hp a b Fa Fb) as [_ [He Hn]].
rewrite add_up_1_listing_eq, <- He.
apply to_up_2_correct; [lia|exact Hn].
Qed.

(* sub_down_1 and sub_up_1: RD(a - b) and RU(a - b), through the sums on a and -b. From
   precision 2. *)
Theorem sub_down_1_listing_correct :
  forall emin prec : Z, (2 <= prec)%Z ->
  forall a b : R,
  fmt emin prec a ->
  fmt emin prec b ->
  let r := sub_down_1_listing emin prec tie_even a b in
  fmt emin prec r /\
  r = RD emin prec (a - b).
Proof.
intros emin prec Hp a b Fa Fb.
exact (add_down_1_listing_correct emin prec Hp a (- b) Fa (generic_format_opp _ _ _ Fb)).
Qed.

Theorem sub_up_1_listing_correct :
  forall emin prec : Z, (2 <= prec)%Z ->
  forall a b : R,
  fmt emin prec a ->
  fmt emin prec b ->
  let r := sub_up_1_listing emin prec tie_even a b in
  fmt emin prec r /\
  r = RU emin prec (a - b).
Proof.
intros emin prec Hp a b Fa Fb.
exact (add_up_1_listing_correct emin prec Hp a (- b) Fa (generic_format_opp _ _ _ Fb)).
Qed.

(* The sign of the computed error is the sign of the exact error, because the computed
   error is the exact error: e = (a + b) - s. *)
Corollary two_sum_ord_listing_error :
  forall emin prec : Z, (2 <= prec)%Z ->
  forall a b : R, fmt emin prec a -> fmt emin prec b ->
  snd (two_sum_ord_listing emin prec tie_even a b) = (a + b) - RN emin prec (a + b).
Proof.
intros emin prec Hp a b Fa Fb.
destruct (two_sum_ord_listing_facts emin prec Hp a b Fa Fb) as [Hs [He _]].
rewrite <- Hs. lra.
Qed.
