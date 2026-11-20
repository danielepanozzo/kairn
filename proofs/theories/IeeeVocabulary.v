(* The vocabulary of the statements about the IEEE model. Written by hand; nothing in this
   file is a proof. The statements themselves are generated from the claims
   (proofs/gen/IeeeStatements.v) and use these definitions.

   Every statement is for all precisions prec from the kernel's minimum on and all emax
   with prec < emax (Flocq's condition), for every choice of the NaN returned by each
   operation and of the NaN that `const nan` denotes, with rounding to nearest, ties to
   even. The format is the IEEE format of IeeeOperations.v: its smallest positive number
   is 2^emin with emin = 3 - emax - prec, and the real-model vocabulary (fmt, RN, u, eta,
   normalized_2 of proofs/gen/Statements.v) is used with that emin.

   The vocabulary is small and closed:

     ieee_emin, omega             the smallest exponent; the largest finite number
     finite x, val x              a finite number and its real value
     nan1, nan2, nan3             the type of the NaN an operation returns, as a function of
                                  its one, two or three operands
     nan x, zero x                a NaN; a zero of either sign
     infinity s, pos_zero         the infinity of sign s (true: negative); +0
     canonical_2 x0 x1            a canonical 2-limb value: finite and normalized, or
                                  (+-infinity, +-0), or (NaN, NaN)
     canonical_of t w0 w1         (w0, w1) is the canonical form of the non-finite t:
                                  (t, +0) for an infinity, (NaN, NaN) for a NaN
     xreal, xval a, xval_2 x0 x1  an extended real number (a real, +-infinity or NaN),
                                  and the one a limb or a canonical 2-limb value stands for
     xlt, xle, xeq, xopp, xabs    comparisons and sign changes of extended real numbers
     xadd, xmul                   the sum and the product of IEEE 754 on extended real
                                  numbers: a NaN for a NaN operand, inf - inf and 0 inf
     overflow_of r, xround g x    a real result as an operation of T returns it: itself
                                  below 2^emax in magnitude, the infinity of its sign
                                  otherwise; and g applied that way to a finite x
     xrd x, xru x                 x rounded down and up in the format with overflow: beyond
                                  the largest finite number, that number on the side
                                  toward zero and the infinity on the other
     xsucc x, xpred x             the next number of the format above and below x, as
                                  IEEE 754's nextUp and nextDown on the values
     nonneg_ext r                 nonnegative, +infinity or NaN: what a radius may be
     ball_finite_k, ball_whole_k, ball_empty_k, ball_k
                                  the three states of a canonical ball with a center of
                                  k limbs, and their disjunction
     in_ball_k ... x              the real number x is in the ball

   The shapes of the generated statements.

   An arithmetic kernel K of the finite domain, whose statement in the real model is
   requires(inputs) -> let outputs := K inputs in ensures(inputs, outputs), has up to four:

     K_ieee_bridge_spec         finite inputs -> requires(val inputs) ->
                                finite (output limb 0) ->
                                every value computed by K is finite, and
                                val outputs = (real model of K) (val inputs)
     K_ieee_spec                finite inputs -> requires(val inputs) ->
                                finite (output limb 0) ->
                                the other outputs are finite, and ensures(val inputs, val outputs)
     K_ieee_finite_spec         finite inputs -> requires(val inputs) -> threshold ->
                                every value computed by K is finite
     K_ieee_finite_result_spec  the same under a threshold on the exact result

   "Every value computed by K" is the list of values of K's straight-line program
   (Program.v, proofs/gen/IeeeModel.v).

   A full kernel K_full with core K (K_full_spec) has the conjunction of F1 to F5 of
   docs/developer/design/milestone1.md, in this order. Writing opfin for "the leading limb
   of every 2-limb operand and every one-limb operand is finite", and t for the operation
   of T on the leading limbs (as the kernel computes it):

     F1   canonical_2 w0 w1
     F2   finite w0 -> every operand limb is finite, w1 is finite, and
                       ensures(val operands, val w), the conclusions of K's real-model
                       statement
     F3   opfin -> finite_when -> finite w0
     F4   opfin -> ~ finite w0 -> w0 = infinity (sign of the exact value) /\ w1 = +0
     F5   ~ opfin -> canonical_of t w0 w1

   A full Ball kernel (ball_K_full_spec) has the conjunction of B1 to B4 and of containment
   in every case, in this order:

     B1   the result is a canonical ball
     B2   the result is empty <-> an operand is empty
     B3   the result is a finite ball -> every operand is a finite ball, the scalar is
          finite, and the containment statement of the core holds
     B4   every operand is a finite ball -> the scalar is finite -> finite_when ->
          the result is a finite ball
     C    for all real x, y in the operands, x o y is in the result (whole line included)

   B4 is printed only for a kernel whose claims give conditions (finite_when): ball_neg_k,
   whose result is as finite as its operand, has none and its statement has no B4. A kernel
   whose containment claim is exact under conditions (exact_when) has one more conjunct,
   between B3 and B4:

     E    the result is a finite ball -> the conditions hold of the operands' values ->
          every member of the result is x o y for some x, y in the operands

   A kernel that needs no fix-up has its claims read over extended real numbers (xval,
   xval_2, xround; for a value of two operands xadd, xmul, xrd, xru; for the steps xsucc,
   xpred), on canonical operands; a constructor says which canonical object comes out for
   every operand. *)
From Stdlib Require Import Reals ZArith.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements.
Open Scope R_scope.

(** * Finite numbers and their values *)

Section Vocabulary.
Variable prec emax : Z.

(* The smallest exponent of the IEEE format: its smallest positive number is 2^ieee_emin. *)
Definition ieee_emin : Z := (3 - emax - prec)%Z.

(* x is a finite number: neither an infinity nor a NaN. *)
Definition finite (x : binary_float prec emax) : Prop := is_finite prec emax x = true.

(* The real value of a finite x (and 0 for the others, which no statement uses). *)
Definition val (x : binary_float prec emax) : R := B2R prec emax x.

(* The largest finite number. *)
Definition omega : R := bpow radix2 emax - bpow radix2 (emax - prec).

(* The NaN an operation returns, as a function of its one, two or three operands. *)
Definition nan1 : Type :=
  binary_float prec emax -> {x : binary_float prec emax | is_nan prec emax x = true}.
Definition nan2 : Type :=
  binary_float prec emax -> binary_float prec emax ->
  {x : binary_float prec emax | is_nan prec emax x = true}.
Definition nan3 : Type :=
  binary_float prec emax -> binary_float prec emax -> binary_float prec emax ->
  {x : binary_float prec emax | is_nan prec emax x = true}.

End Vocabulary.

Arguments finite {prec emax} x.
Arguments val {prec emax} x.

(** * The extended domain *)

(* An extended real number: a NaN, an infinity (s = true: the negative one), or a real. *)
Inductive xreal : Type :=
  | XNaN
  | XInf (s : bool)
  | XFin (r : R).

(* The order of the extended real numbers, as IEEE 754 comparisons see it: every
   comparison with a NaN is false. *)
Definition xlt (a b : xreal) : bool :=
  match a, b with
  | XFin x, XFin y => Rlt_bool x y
  | XInf s, XFin _ => s
  | XFin _, XInf s => negb s
  | XInf s, XInf s' => andb s (negb s')
  | _, _ => false
  end.

Definition xle (a b : xreal) : bool :=
  match a, b with
  | XFin x, XFin y => Rle_bool x y
  | XInf s, XFin _ => s
  | XFin _, XInf s => negb s
  | XInf s, XInf s' => orb s (negb s')
  | _, _ => false
  end.

Definition xeq (a b : xreal) : bool :=
  match a, b with
  | XFin x, XFin y => Req_bool x y
  | XInf s, XInf s' => Bool.eqb s s'
  | _, _ => false
  end.

Definition xopp (a : xreal) : xreal :=
  match a with
  | XNaN => XNaN
  | XInf s => XInf (negb s)
  | XFin r => XFin (- r)
  end.

Definition xabs (a : xreal) : xreal :=
  match a with
  | XNaN => XNaN
  | XInf _ => XInf false
  | XFin r => XFin (Rabs r)
  end.

(* The sum and the product of two extended real numbers, as IEEE 754 defines the operations on
   the values of their operands: a NaN when an operand is a NaN, for the sum of the two infinities
   and for the product of a zero and an infinity; otherwise an infinity when an operand is one
   (for a product, with the sign of the product of the signs); otherwise the exact real result,
   before any rounding. *)
Definition xadd (a b : xreal) : xreal :=
  match a, b with
  | XNaN, _ | _, XNaN => XNaN
  | XInf s, XInf s' => if Bool.eqb s s' then XInf s else XNaN
  | XInf s, XFin _ => XInf s
  | XFin _, XInf s => XInf s
  | XFin x, XFin y => XFin (x + y)
  end.

Definition xmul (a b : xreal) : xreal :=
  match a, b with
  | XNaN, _ | _, XNaN => XNaN
  | XInf s, XInf s' => XInf (xorb s s')
  | XInf s, XFin y => if Req_bool y 0 then XNaN else XInf (xorb s (Rlt_bool y 0))
  | XFin x, XInf s => if Req_bool x 0 then XNaN else XInf (xorb (Rlt_bool x 0) s)
  | XFin x, XFin y => XFin (x * y)
  end.

Section ExtVocabulary.
Variable prec emax : Z.
Notation float := (binary_float prec emax).

(* x is a NaN; x is a zero, of either sign. *)
Definition nan (x : float) : Prop := is_nan prec emax x = true.
Definition zero (x : float) : Prop := exists s : bool, x = B754_zero prec emax s.

(* The infinity of sign s (true: the negative one), and +0. *)
Definition infinity (s : bool) : float := B754_infinity prec emax s.
Definition pos_zero : float := B754_zero prec emax false.

(* A canonical 2-limb value: finite and normalized, or an infinity followed by a zero,
   or two NaN. *)
Definition canonical_2 (x0 x1 : float) : Prop :=
  (finite x0 /\ finite x1 /\ normalized_2 (ieee_emin prec emax) prec (val x0) (val x1)) \/
  ((exists s : bool, x0 = infinity s) /\ zero x1) \/
  (nan x0 /\ nan x1).

(* (w0, w1) is the canonical form of t, for a t that is not finite. *)
Definition canonical_of (t w0 w1 : float) : Prop :=
  (nan t /\ nan w0 /\ nan w1) \/
  (exists s : bool, t = infinity s /\ w0 = infinity s /\ w1 = pos_zero).

(* The extended real number a limb stands for, and the one a canonical 2-limb value
   stands for. *)
Definition xval (a : float) : xreal :=
  if is_finite prec emax a then XFin (val a)
  else if is_nan prec emax a then XNaN
  else XInf (Bsign prec emax a).

Definition xval_2 (x0 x1 : float) : xreal :=
  if is_finite prec emax x0 then XFin (val x0 + val x1)
  else if is_nan prec emax x0 then XNaN
  else XInf (Bsign prec emax x0).

(* A real result r, as an operation of T returns it: r itself when it is below 2^emax in
   magnitude, and otherwise the infinity of its sign. *)
Definition overflow_of (r : R) : xreal :=
  if Rlt_bool (Rabs r) (bpow radix2 emax) then XFin r else XInf (Rlt_bool r 0).

(* A rounding g applied to an extended real number: an infinity or a NaN is unchanged. *)
Definition xround (g : R -> R) (a : xreal) : xreal :=
  match a with
  | XFin r => overflow_of (g r)
  | _ => a
  end.

(* Rounding down in the format with overflow (docs/developer/design/milestone2.md, "Notation and
   vocabulary"): a real r becomes RD r, except that it is the largest finite number when r is
   above it, and -infinity when r is below the most negative one (where RD r is beyond 2^emax in
   magnitude). Rounding up is the same on the other side. An infinity or a NaN is unchanged. On a
   real r below 2^emax in magnitude, xrd is xround of RD (and xru of RU). *)
Definition xrd (a : xreal) : xreal :=
  match a with
  | XFin r => if Rlt_bool (omega prec emax) r then XFin (omega prec emax)
              else overflow_of (RD (ieee_emin prec emax) prec r)
  | _ => a
  end.
Definition xru (a : xreal) : xreal := xopp (xrd (xopp a)).

(* The next number of the format above a and the one below, as IEEE 754's nextUp and nextDown
   define them on the values: above the largest finite number is +infinity, above -infinity the
   most negative finite number, above +infinity +infinity, and a NaN stays a NaN; a step that
   arrives at zero gives a zero, whose sign does not exist here. *)
Definition xsucc (a : xreal) : xreal :=
  match a with
  | XNaN => XNaN
  | XInf false => XInf false
  | XInf true => XFin (- omega prec emax)
  | XFin r => overflow_of (Ulp.succ radix2 (FLT_exp (ieee_emin prec emax) prec) r)
  end.
Definition xpred (a : xreal) : xreal := xopp (xsucc (xopp a)).

(* What a radius may be: a nonnegative number, +infinity, or a NaN. *)
Definition nonneg_ext (r : float) : Prop :=
  nan r \/ r = infinity false \/ (finite r /\ 0 <= val r).

(* The states of a canonical ball with a one-limb center c and radius r. *)
Definition ball_finite_1 (c r : float) : Prop :=
  finite c /\ finite r /\ 0 <= val r.
Definition ball_whole_1 (c r : float) : Prop :=
  zero c /\ r = infinity false.
Definition ball_empty_1 (c r : float) : Prop :=
  nan c /\ nan r.
Definition ball_1 (c r : float) : Prop :=
  ball_finite_1 c r \/ ball_whole_1 c r \/ ball_empty_1 c r.

(* The same with a 2-limb center (c0, c1). *)
Definition ball_finite_2 (c0 c1 r : float) : Prop :=
  finite c0 /\ finite c1 /\ normalized_2 (ieee_emin prec emax) prec (val c0) (val c1) /\
  finite r /\ 0 <= val r.
Definition ball_whole_2 (c0 c1 r : float) : Prop :=
  zero c0 /\ zero c1 /\ r = infinity false.
Definition ball_empty_2 (c0 c1 r : float) : Prop :=
  nan c0 /\ nan c1 /\ nan r.
Definition ball_2 (c0 c1 r : float) : Prop :=
  ball_finite_2 c0 c1 r \/ ball_whole_2 c0 c1 r \/ ball_empty_2 c0 c1 r.

(* The real number x is in the ball: the whole line contains every x, the empty set none. *)
Definition in_ball_1 (c r : float) (x : R) : Prop :=
  ball_whole_1 c r \/ (ball_finite_1 c r /\ Rabs (x - val c) <= val r).
Definition in_ball_2 (c0 c1 r : float) (x : R) : Prop :=
  ball_whole_2 c0 c1 r \/ (ball_finite_2 c0 c1 r /\ Rabs (x - (val c0 + val c1)) <= val r).

End ExtVocabulary.

Arguments nan {prec emax} x.
Arguments zero {prec emax} x.
Arguments canonical_2 {prec emax} x0 x1.
Arguments canonical_of {prec emax} t w0 w1.
Arguments xval {prec emax} a.
Arguments xval_2 {prec emax} x0 x1.
Arguments nonneg_ext {prec emax} r.
Arguments ball_finite_1 {prec emax} c r.
Arguments ball_whole_1 {prec emax} c r.
Arguments ball_empty_1 {prec emax} c r.
Arguments ball_1 {prec emax} c r.
Arguments ball_finite_2 {prec emax} c0 c1 r.
Arguments ball_whole_2 {prec emax} c0 c1 r.
Arguments ball_empty_2 {prec emax} c0 c1 r.
Arguments ball_2 {prec emax} c0 c1 r.
Arguments in_ball_1 {prec emax} c r x.
Arguments in_ball_2 {prec emax} c0 c1 r x.
