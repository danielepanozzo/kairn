(* Hand-written draft of the statements of the first-wave kernels.

   This file stands in for the generated proofs/gen/Statements.v, and is written in the
   form the generator emits, so that a proof file is moved from the draft to the
   generated statements by changing its import line. It has two parts: a fixed
   vocabulary, and one `Definition <kernel>_spec : Prop` per kernel. The proof of a kernel
   is a theorem `<kernel>_correct : <kernel>_spec` in another file of this directory.

   Every statement has the same shape:

     forall emin prec : Z, (PMIN <= prec)%Z ->      the format: any minimum exponent, any
                                                    precision from PMIN on
     forall inputs : R,
     requirement -> ... ->                          fmt for a one-limb input, normalized_2
                                                    for a 2-limb input, Rabs b <= Rabs a
     let '(outputs) := kernel emin prec tie_even inputs in
     claim /\ ... /\ claim

   where a claim is one of

     normalized_2 emin prec z0 z1                                  the result is normalized
     z0 = RN emin prec V                                           leading limb = RN(value)
     (z0 + z1) = V                                                 exact
     Rabs ((z0 + z1) - V) <= C * u prec ^ K * Rabs V + T * eta emin    an error bound
     (V = 0 \/ bpow radix2 (2 * prec - 1) * eta emin <= Rabs V) -> claim
                                                                   a claim for large products

   with V the exact value (a sum or a product of the input values), C and T rational
   constants (C may depend on u), and the term in eta or the term in u left out when its
   constant is zero. Rounding is to nearest, ties to even, with gradual underflow and no
   overflow (the format has no largest exponent). *)
From Stdlib Require Import Reals ZArith.
From Flocq Require Import Core.
From Kairn Require Import ModelDraft.
Open Scope R_scope.

(** * Vocabulary *)

(* The tie rule of round-to-nearest-even, in the form Flocq's `Znearest` expects: given
   the integer just below a midpoint, say whether to round up. *)
Definition tie_even (n : Z) : bool := negb (Z.even n).

Section Vocabulary.
Variable emin prec : Z.

(* x is a number of the format: x = m * 2^q with |m| < 2^prec and q >= emin. *)
Definition fmt (x : R) : Prop := generic_format radix2 (FLT_exp emin prec) x.

(* RN: rounding to the nearest number of the format, ties to even. *)
Definition RN (x : R) : R := round radix2 (FLT_exp emin prec) (Znearest tie_even) x.

(* The unit roundoff u = 2^-prec, and the smallest positive number eta = 2^emin. *)
Definition u : R := bpow radix2 (- prec).
Definition eta : R := bpow radix2 emin.

(* A 2-limb number (x0, x1), of value x0 + x1, is normalized when both limbs are numbers
   of the format and adding the second limb to the first and rounding gives the first
   back. This is the "double-word number" of JMP17 and MR22. *)
Definition normalized_2 (x0 x1 : R) : Prop := fmt x0 /\ fmt x1 /\ x0 = RN (x0 + x1).

End Vocabulary.

(** * Error-free transformations *)

(* TwoSum (Knuth): s is the rounded sum and e is exactly the rounding error. *)
Definition two_sum_spec : Prop :=
  forall emin prec : Z, (2 <= prec)%Z ->
  forall a b : R, fmt emin prec a -> fmt emin prec b ->
  let '(s, e) := two_sum emin prec tie_even a b in
  s = RN emin prec (a + b) /\
  (s + e) = (a + b).

(* Fast2Sum (Dekker): the same when |a| >= |b|; and its result is normalized. *)
Definition fast_two_sum_spec : Prop :=
  forall emin prec : Z, (2 <= prec)%Z ->
  forall a b : R, fmt emin prec a -> fmt emin prec b ->
  Rabs b <= Rabs a ->
  let '(s, e) := fast_two_sum emin prec tie_even a b in
  s = RN emin prec (a + b) /\
  (s + e) = (a + b) /\
  normalized_2 emin prec s e.

(* TwoProd with an FMA: p is the rounded product; p + e misses the exact product by at
   most eta/2, and by nothing when the product is zero or at least 2^(2 prec - 1) eta in
   magnitude (in binary64: 2^-969). *)
Definition two_prod_spec : Prop :=
  forall emin prec : Z, (2 <= prec)%Z ->
  forall a b : R, fmt emin prec a -> fmt emin prec b ->
  let '(p, e) := two_prod emin prec tie_even a b in
  p = RN emin prec (a * b) /\
  Rabs ((p + e) - (a * b)) <= (1 / 2) * eta emin /\
  (((a * b) = 0 \/ bpow radix2 (2 * prec - 1) * eta emin <= Rabs (a * b)) -> (p + e) = (a * b)).

(** * Two limbs *)

(* add_2_2, JMP17 Algorithm 6 (AccurateDWPlusDW). The bound is MR22's, and it has no
   underflow term: additions of numbers of the format are exact in the subnormal range. *)
Definition add_2_2_spec : Prop :=
  forall emin prec : Z, (3 <= prec)%Z ->
  forall x0 x1 y0 y1 : R,
  normalized_2 emin prec x0 x1 -> normalized_2 emin prec y0 y1 ->
  let '(z0, z1) := add_2_2 emin prec tie_even x0 x1 y0 y1 in
  normalized_2 emin prec z0 z1 /\
  Rabs ((z0 + z1) - ((x0 + x1) + (y0 + y1)))
    <= (3 / (1 - (4 * u prec))) * u prec ^ 2 * Rabs ((x0 + x1) + (y0 + y1)).

(* add_2_1, JMP17 Algorithm 4 (DWPlusFP): a 2-limb number plus a number of the format.
   The bound is MR22's, again without an underflow term. *)
Definition add_2_1_spec : Prop :=
  forall emin prec : Z, (3 <= prec)%Z ->
  forall x0 x1 a : R,
  normalized_2 emin prec x0 x1 -> fmt emin prec a ->
  let '(z0, z1) := add_2_1 emin prec tie_even x0 x1 a in
  normalized_2 emin prec z0 z1 /\
  Rabs ((z0 + z1) - ((x0 + x1) + a)) <= 2 * u prec ^ 2 * Rabs ((x0 + x1) + a).

(* mul_2_2, JMP17 Algorithm 12 (DWTimesDW3). The relative part of the bound is MR22's
   4u^2; the absolute part, 3/2 eta, accounts for the products that underflow. *)
Definition mul_2_2_spec : Prop :=
  forall emin prec : Z, (4 <= prec)%Z ->
  forall x0 x1 y0 y1 : R,
  normalized_2 emin prec x0 x1 -> normalized_2 emin prec y0 y1 ->
  let '(z0, z1) := mul_2_2 emin prec tie_even x0 x1 y0 y1 in
  normalized_2 emin prec z0 z1 /\
  Rabs ((z0 + z1) - ((x0 + x1) * (y0 + y1)))
    <= 4 * u prec ^ 2 * Rabs ((x0 + x1) * (y0 + y1)) + (3 / 2) * eta emin.

(* mul_2_1, JMP17 Algorithm 9 (DWTimesFP3): a 2-limb number times a number of the
   format. The relative part of the bound is that of JMP17 and MR22; the absolute part,
   eta, accounts for the two operations that can underflow. *)
Definition mul_2_1_spec : Prop :=
  forall emin prec : Z, (2 <= prec)%Z ->
  forall x0 x1 a : R,
  normalized_2 emin prec x0 x1 -> fmt emin prec a ->
  let '(z0, z1) := mul_2_1 emin prec tie_even x0 x1 a in
  normalized_2 emin prec z0 z1 /\
  Rabs ((z0 + z1) - ((x0 + x1) * a))
    <= 2 * u prec ^ 2 * Rabs ((x0 + x1) * a) + 1 * eta emin.
