(* Phase 0 tracer bullet: theorems about the generated model (out/Model.v), parametric in the
   precision prec, the minimum exponent emin (gradual underflow: Flocq's FLT format, where
   2^emin is the smallest positive subnormal) and the tie-breaking rule of round-to-nearest.
   The first two instantiate theorems Flocq already has; the third is derived here from Flocq's
   representability of the multiplication error. No Admitted, no Axiom. *)
From Stdlib Require Import Reals ZArith.
From Flocq Require Import Core Mult_error Pff2Flocq.
Require Import Model.
Open Scope R_scope.

Section Proofs.
Variable emin prec : Z.
Variable choice : Z -> bool.
Hypothesis prec_gt_1 : (1 < prec)%Z.
Context { prec_gt_0_ : Prec_gt_0 prec }.
Hypothesis emin_neg : (emin <= 0)%Z.
(* The tie-breaking rule is symmetric (ties-to-even and ties-away are). *)
Hypothesis choice_sym : forall x, choice x = negb (choice (- (x + 1))).

Notation format := (generic_format radix2 (FLT_exp emin prec)).
Notation rnd := (round radix2 (FLT_exp emin prec) (Znearest choice)).

(* TwoSum is error-free for all inputs, subnormals included (no overflow in this model). *)
Theorem two_sum_correct :
  forall a b, format a -> format b ->
  let '(s, e) := two_sum emin prec choice a b in
  s = rnd (a + b) /\ s + e = a + b.
Proof.
intros a b Fa Fb. unfold two_sum. split.
- reflexivity.
- apply TwoSum_correct; assumption.
Qed.

(* Fast2Sum, in the operation order the generator emits (z = s - a; e = b - z). *)
Theorem fast_two_sum_correct :
  forall a b, format a -> format b -> Rabs b <= Rabs a ->
  let '(s, e) := fast_two_sum emin prec choice a b in
  s = rnd (a + b) /\ s + e = a + b.
Proof.
intros a b Fa Fb Hab. unfold fast_two_sum. split.
- reflexivity.
- replace (rnd (a + b) - a) with (- (a - rnd (a + b))) by ring.
  rewrite (round_N_opp_sym emin prec choice choice_sym).
  replace (b - - rnd (a - rnd (a + b))) with (b + rnd (a - rnd (a + b))) by ring.
  apply Fast2Sum_correct; assumption.
Qed.

(* Its output is a double-word number: the high part is the rounding of the sum of both. *)
Corollary fast_two_sum_normalized :
  forall a b, format a -> format b -> Rabs b <= Rabs a ->
  let '(s, e) := fast_two_sum emin prec choice a b in
  s = rnd (s + e).
Proof.
intros a b Fa Fb Hab.
generalize (fast_two_sum_correct a b Fa Fb Hab).
destruct (fast_two_sum emin prec choice a b) as [s e].
intros [Hs He]. now rewrite He.
Qed.

(* TwoProd with an FMA, as emitted (the product is an FMA with a zero addend): error-free
   unless the product is nonzero and below 2^(emin + 2 prec - 1). *)
Theorem two_prod_correct :
  forall a b, format a -> format b ->
  (a * b <> 0 -> bpow radix2 (emin + 2 * prec - 1) <= Rabs (a * b)) ->
  let '(p, e) := two_prod emin prec choice a b in
  p = rnd (a * b) /\ p + e = a * b.
Proof.
intros a b Fa Fb H. unfold two_prod. rewrite Rplus_0_r. split.
- reflexivity.
- assert (F : format (rnd (a * b) - a * b)).
  { apply mult_error_FLT; auto with typeclass_instances. }
  replace (a * b + - rnd (a * b)) with (- (rnd (a * b) - a * b)) by ring.
  assert (E : rnd (- (rnd (a * b) - a * b)) = - (rnd (a * b) - a * b)).
  { apply round_generic; auto with typeclass_instances. now apply generic_format_opp. }
  rewrite E. ring.
Qed.

End Proofs.
