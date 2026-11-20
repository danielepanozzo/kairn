(* Rounding a sum down and up without a rounding mode, in the real model (no overflow):
   two_sum_ord, add_down_1, add_up_1, sub_down_1, sub_up_1 and the entry forms of the four
   directed kernels (docs/developer/design/milestone2.md, "Rounding a sum down and up").

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

   What is proved (the generated statements of proofs/gen/Statements.v), for all numbers
   a, b of F and every precision from 2 on:
   - two_sum_ord: s = RN(a + b), s + e = a + b exactly, and (s, e) is normalized. No
     requirement on the operands: the two selects order them by magnitude, which is the
     requirement of fast_two_sum.
   - add_down_1 a b = RD(a + b) and add_up_1 a b = RU(a + b); sub_down_1 a b = RD(a - b)
     and sub_up_1 a b = RU(a - b). Exact in every case.
   - add_down_entry, add_up_entry, sub_down_entry, sub_up_entry: the same, since the
     guard of a number of F is that number.

   Why. (s, e) is a normalized pair of value a + b, and the last three lines of
   add_down_1 are the listing of to_down_2 applied to that pair (those of add_up_1, the
   listing of to_up_2): the definitions are equal by unfolding, and the theorems of
   Convert.v conclude. Their argument: a + b lies strictly between pred(s) and succ(s)
   because s is the number of F nearest to it, and the sign of e = (a + b) - s says in
   which of the two gaps.

   The precision 2 is that of fast_two_sum_correct (Flocq's Fast2Sum_correct); nothing
   else in this file needs more than a positive precision. Precision 1 is not claimed. *)
From Stdlib Require Import Reals ZArith Lia Lra.
From Flocq Require Import Core.
From Kairn.Gen Require Import Model Statements.
From Kairn Require Import Format Guard EFT Convert.
Open Scope R_scope.

(** * The tail of the directed sums is the listing of to_down_2 and of to_up_2 *)

(* add_down_1 is to_down_2 applied to the pair that two_sum_ord returns, and add_up_1 is
   to_up_2 applied to it: equal by unfolding. *)
Lemma add_down_1_eq :
  forall emin prec choice a b,
  add_down_1 emin prec choice a b
  = to_down_2 emin prec (fst (two_sum_ord emin prec choice a b))
                        (snd (two_sum_ord emin prec choice a b)).
Proof.
intros emin prec choice a b. unfold add_down_1.
destruct (two_sum_ord emin prec choice a b) as [s e]. reflexivity.
Qed.

Lemma add_up_1_eq :
  forall emin prec choice a b,
  add_up_1 emin prec choice a b
  = to_up_2 emin prec (fst (two_sum_ord emin prec choice a b))
                      (snd (two_sum_ord emin prec choice a b)).
Proof.
intros emin prec choice a b. unfold add_up_1.
destruct (two_sum_ord emin prec choice a b) as [s e]. reflexivity.
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

(** * The generated statements *)

(* two_sum_ord: for all numbers a, b of the format, s = RN(a + b), s + e = a + b, and
   (s, e) is normalized. From precision 2. *)
Theorem two_sum_ord_correct : two_sum_ord_spec.
Proof.
intros emin prec Hp a b Fa Fb. unfold two_sum_ord. cbv zeta.
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
Corollary two_sum_ord_facts :
  forall emin prec : Z, (2 <= prec)%Z ->
  forall a b : R, fmt emin prec a -> fmt emin prec b ->
  fst (two_sum_ord emin prec tie_even a b) = RN emin prec (a + b) /\
  fst (two_sum_ord emin prec tie_even a b)
  + snd (two_sum_ord emin prec tie_even a b) = a + b /\
  normalized_2 emin prec (fst (two_sum_ord emin prec tie_even a b))
                         (snd (two_sum_ord emin prec tie_even a b)).
Proof.
intros emin prec Hp a b Fa Fb.
generalize (two_sum_ord_correct emin prec Hp a b Fa Fb).
destruct (two_sum_ord emin prec tie_even a b) as [s e]. trivial.
Qed.

(* add_down_1: for all numbers a, b of the format, the result is a number of the format
   and is RD(a + b), the largest number of the format that is at most a + b. From
   precision 2. *)
Theorem add_down_1_correct : add_down_1_spec.
Proof.
intros emin prec Hp a b Fa Fb r. unfold r. clear r.
destruct (two_sum_ord_facts emin prec Hp a b Fa Fb) as [_ [He Hn]].
rewrite add_down_1_eq, <- He.
apply to_down_2_correct; [lia|exact Hn].
Qed.

(* add_up_1: likewise, RU(a + b), the smallest number of the format that is at least
   a + b. From precision 2. *)
Theorem add_up_1_correct : add_up_1_spec.
Proof.
intros emin prec Hp a b Fa Fb r. unfold r. clear r.
destruct (two_sum_ord_facts emin prec Hp a b Fa Fb) as [_ [He Hn]].
rewrite add_up_1_eq, <- He.
apply to_up_2_correct; [lia|exact Hn].
Qed.

(* sub_down_1 and sub_up_1: RD(a - b) and RU(a - b), through the sums on a and -b. From
   precision 2. *)
Theorem sub_down_1_correct : sub_down_1_spec.
Proof.
intros emin prec Hp a b Fa Fb.
exact (add_down_1_correct emin prec Hp a (- b) Fa (generic_format_opp _ _ _ Fb)).
Qed.

Theorem sub_up_1_correct : sub_up_1_spec.
Proof.
intros emin prec Hp a b Fa Fb.
exact (add_up_1_correct emin prec Hp a (- b) Fa (generic_format_opp _ _ _ Fb)).
Qed.

(* The sign of the computed error is the sign of the exact error, because the computed
   error is the exact error: e = (a + b) - s. *)
Corollary two_sum_ord_error :
  forall emin prec : Z, (2 <= prec)%Z ->
  forall a b : R, fmt emin prec a -> fmt emin prec b ->
  snd (two_sum_ord emin prec tie_even a b) = (a + b) - RN emin prec (a + b).
Proof.
intros emin prec Hp a b Fa Fb.
destruct (two_sum_ord_facts emin prec Hp a b Fa Fb) as [Hs [He _]].
rewrite <- Hs. lra.
Qed.

(** * The entry forms: the same kernels on their guarded operands *)

(* The guard of a number of the format is that number (Guard.v), so an entry form
   computes what the kernel it calls computes. *)
Theorem add_down_entry_correct : add_down_entry_spec.
Proof.
intros emin prec Hp a b Fa Fb. unfold add_down_entry. cbv zeta.
rewrite 2!guard_real_any by assumption.
exact (add_down_1_correct emin prec Hp a b Fa Fb).
Qed.

Theorem add_up_entry_correct : add_up_entry_spec.
Proof.
intros emin prec Hp a b Fa Fb. unfold add_up_entry. cbv zeta.
rewrite 2!guard_real_any by assumption.
exact (add_up_1_correct emin prec Hp a b Fa Fb).
Qed.

Theorem sub_down_entry_correct : sub_down_entry_spec.
Proof.
intros emin prec Hp a b Fa Fb. unfold sub_down_entry. cbv zeta.
rewrite 2!guard_real_any by assumption.
exact (sub_down_1_correct emin prec Hp a b Fa Fb).
Qed.

Theorem sub_up_entry_correct : sub_up_entry_spec.
Proof.
intros emin prec Hp a b Fa Fb. unfold sub_up_entry. cbv zeta.
rewrite 2!guard_real_any by assumption.
exact (sub_up_1_correct emin prec Hp a b Fa Fb).
Qed.
