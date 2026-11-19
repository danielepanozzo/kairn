(* DRAFT of the statements of the non-finite layer, written by hand in the form the
   generator is meant to print, one definition per statement. Nothing in this file is a
   proof; the theorems are in IeeeOps.v, IeeeFull.v, IeeeBall.v, IeeeExt.v and
   IeeeMake.v.

   These are statements about the IEEE model of IeeeDraft.v in which the operands may
   be infinite or NaN (the claims call this the extended domain). As in
   IeeeStatementsDraft.v, every statement is for all precisions prec from the kernel's
   minimum on and all emax with prec < emax, for every choice of the NaN returned by
   each operation and of the NaN that `const nan` denotes, with rounding to nearest,
   ties to even; emin = 3 - emax - prec, and the real-model vocabulary is used with
   that emin.

   The vocabulary (first section) is small and closed:

     finite x, val x              a finite number and its real value (IeeeStatementsDraft.v)
     nan x, zero x                a NaN; a zero of either sign
     infinity s, pos_zero         the infinity of sign s (true: negative); +0
     canonical_2 x0 x1            a canonical 2-limb value: finite and normalized, or
                                  (+-infinity, +-0), or (NaN, NaN)
     canonical_of t w0 w1         (w0, w1) is the canonical form of the non-finite t:
                                  (t, +0) for an infinity, (NaN, NaN) for a NaN
     xreal, xval a, xval_2 x0 x1  an extended real number (a real, +-infinity or NaN),
                                  and the one a limb or a canonical 2-limb value stands for
     xlt, xle, xeq, xopp, xabs    comparisons and sign changes of extended real numbers
     overflow_of r, xround g x    a real result as an operation of T returns it: itself
                                  below 2^emax in magnitude, the infinity of its sign
                                  otherwise; and g applied that way to a finite x
     nonneg_ext r                 nonnegative, +infinity or NaN: what a radius may be
     ball_finite_k, ball_whole_k, ball_empty_k, ball_k
                                  the three states of a canonical ball with a center of
                                  k limbs, and their disjunction
     in_ball_k ... x              the real number x is in the ball

   The statement of a full kernel K_full with core K (K_full_spec) is the conjunction of
   F1 to F5 of docs/developer/design/milestone1.md, in this order. Writing opfin for
   "the leading limb of every 2-limb operand and every one-limb operand is finite", and
   t for the operation of T on the leading limbs (as the kernel computes it):

     F1   canonical_2 w0 w1
     F2   finite w0 -> every operand limb is finite, w1 is finite, and
                       ensures(val operands, val w), the conclusions of K's real-model
                       statement
     F3   opfin -> finite_when -> finite w0
     F4   opfin -> ~ finite w0 -> w0 = infinity (sign of the exact value) /\ w1 = +0
     F5   ~ opfin -> canonical_of t w0 w1

   The statement of a full Ball kernel (ball_K_full_spec) is the conjunction of B1 to B3
   and of containment in every case:

     B1   the result is a canonical ball
     B2   the result is empty <-> an operand is empty
     B3   the result is a finite ball -> every operand is a finite ball, the scalar is
          finite, and the containment statement of the core holds
     C    for all real x, y in the operands, x o y is in the result (whole line included)

   The other statements are described where they are written. *)
From Stdlib Require Import Reals ZArith List.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements.
From Kairn Require Import Program IeeeBridge IeeeStatementsDraft.
From Kairn Require IeeeDraft.
Import ListNotations.
Open Scope R_scope.

(** * Vocabulary *)

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

(** * The guard *)

(* guard a has the value of a: a finite a gives a finite number of the same value, a
   zero gives +0, an infinity gives itself, a NaN gives a NaN. *)
Definition guard_ieee_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus : nan2 prec emax),
  forall a : binary_float prec emax,
  let g := IeeeDraft.guard prec emax nan_plus a in
  (finite g <-> finite a) /\
  val g = val a /\
  (zero a -> g = pos_zero prec emax) /\
  (forall s : bool, a = infinity prec emax s -> g = infinity prec emax s) /\
  (nan g <-> nan a).
(** * The full kernels *)

(* add_2_2_full: add_2_2, then the fix-up; t = add(x0, y0). *)
Definition add_2_2_full_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_abs : nan1 prec emax) (nan_mult : nan2 prec emax),
  (3 <= prec)%Z ->
  forall x0 x1 y0 y1 : binary_float prec emax,
  canonical_2 x0 x1 ->
  canonical_2 y0 y1 ->
  let t := IeeeDraft.add prec emax nan_plus x0 y0 in
  let '(w0, w1) := IeeeDraft.add_2_2_full prec emax nan_plus nan_minus nan_abs nan_mult x0 x1 y0 y1 in
  canonical_2 w0 w1 /\
  (finite w0 ->
   finite x0 /\ finite x1 /\ finite y0 /\ finite y1 /\ finite w1 /\
   normalized_2 (ieee_emin prec emax) prec (val w0) (val w1) /\
   Rabs ((val w0 + val w1) - ((val x0 + val x1) + (val y0 + val y1)))
   <= (3 / (1 - (4 * u prec))) * u prec ^ 2 * Rabs ((val x0 + val x1) + (val y0 + val y1))) /\
  (finite x0 -> finite y0 ->
   Rabs (val x0 + val x1) <= bpow radix2 (emax - 2) ->
   Rabs (val y0 + val y1) <= bpow radix2 (emax - 2) ->
   finite w0) /\
  (finite x0 -> finite y0 -> ~ finite w0 ->
   w0 = infinity prec emax (Rlt_bool ((val x0 + val x1) + (val y0 + val y1)) 0) /\ w1 = pos_zero prec emax) /\
  (~ (finite x0 /\ finite y0) -> canonical_of t w0 w1).

(* mul_2_2_full: mul_2_2, then the fix-up; t = prod(x0, y0). *)
Definition mul_2_2_full_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_opp nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax)
         (nan_mult : nan2 prec emax),
  (4 <= prec)%Z ->
  forall x0 x1 y0 y1 : binary_float prec emax,
  canonical_2 x0 x1 ->
  canonical_2 y0 y1 ->
  let t := IeeeDraft.prod prec emax nan_fma x0 y0 in
  let '(w0, w1) := IeeeDraft.mul_2_2_full prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_mult x0 x1 y0 y1 in
  canonical_2 w0 w1 /\
  (finite w0 ->
   finite x0 /\ finite x1 /\ finite y0 /\ finite y1 /\ finite w1 /\
   normalized_2 (ieee_emin prec emax) prec (val w0) (val w1) /\
   Rabs ((val w0 + val w1) - ((val x0 + val x1) * (val y0 + val y1)))
   <= 4 * u prec ^ 2 * Rabs ((val x0 + val x1) * (val y0 + val y1)) + (3 / 2) * eta (ieee_emin prec emax)) /\
  (finite x0 -> finite y0 ->
   Rabs ((val x0 + val x1) * (val y0 + val y1)) <= bpow radix2 (emax - 1) ->
   finite w0) /\
  (finite x0 -> finite y0 -> ~ finite w0 ->
   w0 = infinity prec emax (Rlt_bool ((val x0 + val x1) * (val y0 + val y1)) 0) /\ w1 = pos_zero prec emax) /\
  (~ (finite x0 /\ finite y0) -> canonical_of t w0 w1).

(** * The full Ball kernels *)

(* The cores are those of the second radius design (BallDraft.v). In the IEEE model the
   statements are from precision 2 on for a center of one limb (and from the minimum of
   the center's kernel for two limbs): the constants G and H of the radius are below
   2^emax in every format from there on. *)

(* ball_add_1_full: the sum of two balls, center of one limb. *)
Definition ball_add_1_full_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus : nan2 prec emax) (nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax),
  (2 <= prec)%Z ->
  forall cx rx cy ry : binary_float prec emax,
  ball_1 cx rx ->
  ball_1 cy ry ->
  let '(cw, rw) := IeeeDraft.ball_add_1_full prec emax nan_plus nan_abs nan_fma cx rx cy ry in
  ball_1 cw rw /\
  (ball_empty_1 cw rw <-> ball_empty_1 cx rx \/ ball_empty_1 cy ry) /\
  (ball_finite_1 cw rw ->
   ball_finite_1 cx rx /\ ball_finite_1 cy ry /\
   (forall x y : R, Rabs (x - val cx) <= val rx -> Rabs (y - val cy) <= val ry ->
    Rabs ((x + y) - val cw) <= val rw)) /\
  (forall x y : R, in_ball_1 cx rx x -> in_ball_1 cy ry y -> in_ball_1 cw rw (x + y)).

(* ball_sub_1_full: the difference of two balls, center of one limb. *)
Definition ball_sub_1_full_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus : nan2 prec emax) (nan_opp nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax),
  (2 <= prec)%Z ->
  forall cx rx cy ry : binary_float prec emax,
  ball_1 cx rx ->
  ball_1 cy ry ->
  let '(cw, rw) := IeeeDraft.ball_sub_1_full prec emax nan_plus nan_opp nan_abs nan_fma cx rx cy ry in
  ball_1 cw rw /\
  (ball_empty_1 cw rw <-> ball_empty_1 cx rx \/ ball_empty_1 cy ry) /\
  (ball_finite_1 cw rw ->
   ball_finite_1 cx rx /\ ball_finite_1 cy ry /\
   (forall x y : R, Rabs (x - val cx) <= val rx -> Rabs (y - val cy) <= val ry ->
    Rabs ((x - y) - val cw) <= val rw)) /\
  (forall x y : R, in_ball_1 cx rx x -> in_ball_1 cy ry y -> in_ball_1 cw rw (x - y)).

(* ball_mul_1_full: the product of two balls, center of one limb. *)
Definition ball_mul_1_full_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus : nan2 prec emax) (nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax),
  (2 <= prec)%Z ->
  forall cx rx cy ry : binary_float prec emax,
  ball_1 cx rx ->
  ball_1 cy ry ->
  let '(cw, rw) := IeeeDraft.ball_mul_1_full prec emax nan_plus nan_abs nan_fma cx rx cy ry in
  ball_1 cw rw /\
  (ball_empty_1 cw rw <-> ball_empty_1 cx rx \/ ball_empty_1 cy ry) /\
  (ball_finite_1 cw rw ->
   ball_finite_1 cx rx /\ ball_finite_1 cy ry /\
   (forall x y : R, Rabs (x - val cx) <= val rx -> Rabs (y - val cy) <= val ry ->
    Rabs ((x * y) - val cw) <= val rw)) /\
  (forall x y : R, in_ball_1 cx rx x -> in_ball_1 cy ry y -> in_ball_1 cw rw (x * y)).

(* ball_scale_1_full: a ball times a value a of T, center of one limb. *)
Definition ball_scale_1_full_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax),
  (2 <= prec)%Z ->
  forall cx rx a : binary_float prec emax,
  ball_1 cx rx ->
  let '(cw, rw) := IeeeDraft.ball_scale_1_full prec emax nan_abs nan_fma cx rx a in
  ball_1 cw rw /\
  (ball_empty_1 cw rw <-> ball_empty_1 cx rx) /\
  (ball_finite_1 cw rw ->
   ball_finite_1 cx rx /\ finite a /\
   (forall x : R, Rabs (x - val cx) <= val rx ->
    Rabs ((x * val a) - val cw) <= val rw)) /\
  (finite a -> forall x : R, in_ball_1 cx rx x -> in_ball_1 cw rw (x * val a)).

(* ball_add_2_full: the sum of two balls, center of two limbs. *)
Definition ball_add_2_full_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax),
  (3 <= prec)%Z ->
  forall cx0 cx1 rx cy0 cy1 ry : binary_float prec emax,
  ball_2 cx0 cx1 rx ->
  ball_2 cy0 cy1 ry ->
  let '(cw0, cw1, rw) := IeeeDraft.ball_add_2_full prec emax nan_plus nan_minus nan_abs nan_fma cx0 cx1 rx cy0 cy1 ry in
  ball_2 cw0 cw1 rw /\
  (ball_empty_2 cw0 cw1 rw <-> ball_empty_2 cx0 cx1 rx \/ ball_empty_2 cy0 cy1 ry) /\
  (ball_finite_2 cw0 cw1 rw ->
   ball_finite_2 cx0 cx1 rx /\ ball_finite_2 cy0 cy1 ry /\
   (forall x y : R, Rabs (x - (val cx0 + val cx1)) <= val rx -> Rabs (y - (val cy0 + val cy1)) <= val ry ->
    Rabs ((x + y) - (val cw0 + val cw1)) <= val rw)) /\
  (forall x y : R, in_ball_2 cx0 cx1 rx x -> in_ball_2 cy0 cy1 ry y -> in_ball_2 cw0 cw1 rw (x + y)).

(* ball_sub_2_full: the difference of two balls, center of two limbs. *)
Definition ball_sub_2_full_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_opp nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax),
  (3 <= prec)%Z ->
  forall cx0 cx1 rx cy0 cy1 ry : binary_float prec emax,
  ball_2 cx0 cx1 rx ->
  ball_2 cy0 cy1 ry ->
  let '(cw0, cw1, rw) := IeeeDraft.ball_sub_2_full prec emax nan_plus nan_minus nan_opp nan_abs nan_fma cx0 cx1 rx cy0 cy1 ry in
  ball_2 cw0 cw1 rw /\
  (ball_empty_2 cw0 cw1 rw <-> ball_empty_2 cx0 cx1 rx \/ ball_empty_2 cy0 cy1 ry) /\
  (ball_finite_2 cw0 cw1 rw ->
   ball_finite_2 cx0 cx1 rx /\ ball_finite_2 cy0 cy1 ry /\
   (forall x y : R, Rabs (x - (val cx0 + val cx1)) <= val rx -> Rabs (y - (val cy0 + val cy1)) <= val ry ->
    Rabs ((x - y) - (val cw0 + val cw1)) <= val rw)) /\
  (forall x y : R, in_ball_2 cx0 cx1 rx x -> in_ball_2 cy0 cy1 ry y -> in_ball_2 cw0 cw1 rw (x - y)).

(* ball_mul_2_full: the product of two balls, center of two limbs. *)
Definition ball_mul_2_full_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_opp nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax),
  (4 <= prec)%Z ->
  forall cx0 cx1 rx cy0 cy1 ry : binary_float prec emax,
  ball_2 cx0 cx1 rx ->
  ball_2 cy0 cy1 ry ->
  let '(cw0, cw1, rw) := IeeeDraft.ball_mul_2_full prec emax nan_plus nan_minus nan_opp nan_abs nan_fma cx0 cx1 rx cy0 cy1 ry in
  ball_2 cw0 cw1 rw /\
  (ball_empty_2 cw0 cw1 rw <-> ball_empty_2 cx0 cx1 rx \/ ball_empty_2 cy0 cy1 ry) /\
  (ball_finite_2 cw0 cw1 rw ->
   ball_finite_2 cx0 cx1 rx /\ ball_finite_2 cy0 cy1 ry /\
   (forall x y : R, Rabs (x - (val cx0 + val cx1)) <= val rx -> Rabs (y - (val cy0 + val cy1)) <= val ry ->
    Rabs ((x * y) - (val cw0 + val cw1)) <= val rw)) /\
  (forall x y : R, in_ball_2 cx0 cx1 rx x -> in_ball_2 cy0 cy1 ry y -> in_ball_2 cw0 cw1 rw (x * y)).

(* ball_scale_2_full: a ball times a value a of T, center of two limbs. *)
Definition ball_scale_2_full_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_opp nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax),
  (2 <= prec)%Z ->
  forall cx0 cx1 rx a : binary_float prec emax,
  ball_2 cx0 cx1 rx ->
  let '(cw0, cw1, rw) := IeeeDraft.ball_scale_2_full prec emax nan_plus nan_minus nan_opp nan_abs nan_fma cx0 cx1 rx a in
  ball_2 cw0 cw1 rw /\
  (ball_empty_2 cw0 cw1 rw <-> ball_empty_2 cx0 cx1 rx) /\
  (ball_finite_2 cw0 cw1 rw ->
   ball_finite_2 cx0 cx1 rx /\ finite a /\
   (forall x : R, Rabs (x - (val cx0 + val cx1)) <= val rx ->
    Rabs ((x * val a) - (val cw0 + val cw1)) <= val rw)) /\
  (finite a -> forall x : R, in_ball_2 cx0 cx1 rx x -> in_ball_2 cw0 cw1 rw (x * val a)).

(* ball_neg_1: no fix-up. *)
Definition ball_neg_1_ieee_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_opp : nan1 prec emax),
  (1 <= prec)%Z ->
  forall cx rx : binary_float prec emax,
  ball_1 cx rx ->
  let '(cz, rz) := IeeeDraft.ball_neg_1 prec emax nan_opp cx rx in
  ball_1 cz rz /\
  (ball_empty_1 cz rz <-> ball_empty_1 cx rx) /\
  (ball_finite_1 cz rz ->
   ball_finite_1 cx rx /\
   (forall x : R, Rabs (x - val cx) <= val rx ->
    Rabs ((- x) - val cz) <= val rz)) /\
  (forall x : R, in_ball_1 cx rx x -> in_ball_1 cz rz (- x)).

(* ball_neg_2: no fix-up. *)
Definition ball_neg_2_ieee_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_opp : nan1 prec emax),
  (1 <= prec)%Z ->
  forall cx0 cx1 rx : binary_float prec emax,
  ball_2 cx0 cx1 rx ->
  let '(cz0, cz1, rz) := IeeeDraft.ball_neg_2 prec emax nan_opp cx0 cx1 rx in
  ball_2 cz0 cz1 rz /\
  (ball_empty_2 cz0 cz1 rz <-> ball_empty_2 cx0 cx1 rx) /\
  (ball_finite_2 cz0 cz1 rz ->
   ball_finite_2 cx0 cx1 rx /\
   (forall x : R, Rabs (x - (val cx0 + val cx1)) <= val rx ->
    Rabs ((- x) - (val cz0 + val cz1)) <= val rz)) /\
  (forall x : R, in_ball_2 cx0 cx1 rx x -> in_ball_2 cz0 cz1 rz (- x)).
(* add_fast_2_2_full: add_fast_2_2, then the fix-up; t = add(x0, y0). *)
Definition add_fast_2_2_full_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_abs : nan1 prec emax) (nan_mult : nan2 prec emax),
  (2 <= prec)%Z ->
  forall x0 x1 y0 y1 : binary_float prec emax,
  canonical_2 x0 x1 ->
  canonical_2 y0 y1 ->
  let t := IeeeDraft.add prec emax nan_plus x0 y0 in
  let '(w0, w1) := IeeeDraft.add_fast_2_2_full prec emax nan_plus nan_minus nan_abs nan_mult x0 x1 y0 y1 in
  canonical_2 w0 w1 /\
  (finite w0 ->
   finite x0 /\ finite x1 /\ finite y0 /\ finite y1 /\ finite w1 /\
   normalized_2 (ieee_emin prec emax) prec (val w0) (val w1) /\
   Rabs ((val w0 + val w1) - ((val x0 + val x1) + (val y0 + val y1)))
   <= 3 * u prec ^ 2 * (Rabs (val x0 + val x1) + Rabs (val y0 + val y1))) /\
  (finite x0 -> finite y0 ->
   Rabs (val x0 + val x1) <= bpow radix2 (emax - 2) ->
   Rabs (val y0 + val y1) <= bpow radix2 (emax - 2) ->
   finite w0) /\
  (finite x0 -> finite y0 -> ~ finite w0 ->
   w0 = infinity prec emax (Rlt_bool ((val x0 + val x1) + (val y0 + val y1)) 0) /\ w1 = pos_zero prec emax) /\
  (~ (finite x0 /\ finite y0) -> canonical_of t w0 w1).

(* sub_2_2_full: sub_2_2, then the fix-up; t = sub(x0, y0). *)
Definition sub_2_2_full_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_opp nan_abs : nan1 prec emax) (nan_mult : nan2 prec emax),
  (3 <= prec)%Z ->
  forall x0 x1 y0 y1 : binary_float prec emax,
  canonical_2 x0 x1 ->
  canonical_2 y0 y1 ->
  let t := IeeeDraft.sub prec emax nan_minus x0 y0 in
  let '(w0, w1) := IeeeDraft.sub_2_2_full prec emax nan_plus nan_minus nan_opp nan_abs nan_mult x0 x1 y0 y1 in
  canonical_2 w0 w1 /\
  (finite w0 ->
   finite x0 /\ finite x1 /\ finite y0 /\ finite y1 /\ finite w1 /\
   normalized_2 (ieee_emin prec emax) prec (val w0) (val w1) /\
   Rabs ((val w0 + val w1) - ((val x0 + val x1) - (val y0 + val y1)))
   <= (3 / (1 - (4 * u prec))) * u prec ^ 2 * Rabs ((val x0 + val x1) - (val y0 + val y1))) /\
  (finite x0 -> finite y0 ->
   Rabs (val x0 + val x1) <= bpow radix2 (emax - 2) ->
   Rabs (val y0 + val y1) <= bpow radix2 (emax - 2) ->
   finite w0) /\
  (finite x0 -> finite y0 -> ~ finite w0 ->
   w0 = infinity prec emax (Rlt_bool ((val x0 + val x1) - (val y0 + val y1)) 0) /\ w1 = pos_zero prec emax) /\
  (~ (finite x0 /\ finite y0) -> canonical_of t w0 w1).

(* add_2_1_full: add_2_1, then the fix-up; t = add(x0, guard(a)). The operand a is any value of T. *)
Definition add_2_1_full_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_abs : nan1 prec emax) (nan_mult : nan2 prec emax),
  (3 <= prec)%Z ->
  forall x0 x1 a : binary_float prec emax,
  canonical_2 x0 x1 ->
  let t := IeeeDraft.add prec emax nan_plus x0 (IeeeDraft.guard prec emax nan_plus a) in
  let '(w0, w1) := IeeeDraft.add_2_1_full prec emax nan_plus nan_minus nan_abs nan_mult x0 x1 a in
  canonical_2 w0 w1 /\
  (finite w0 ->
   finite x0 /\ finite x1 /\ finite a /\ finite w1 /\
   normalized_2 (ieee_emin prec emax) prec (val w0) (val w1) /\
   Rabs ((val w0 + val w1) - ((val x0 + val x1) + val a))
   <= 2 * u prec ^ 2 * Rabs ((val x0 + val x1) + val a)) /\
  (finite x0 -> finite a ->
   Rabs (val x0 + val x1) <= bpow radix2 (emax - 2) ->
   Rabs (val a) <= bpow radix2 (emax - 2) ->
   finite w0) /\
  (finite x0 -> finite a -> ~ finite w0 ->
   w0 = infinity prec emax (Rlt_bool ((val x0 + val x1) + val a) 0) /\ w1 = pos_zero prec emax) /\
  (~ (finite x0 /\ finite a) -> canonical_of t w0 w1).

(* sub_2_1_full: sub_2_1, then the fix-up; t = sub(x0, guard(a)). *)
Definition sub_2_1_full_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_opp nan_abs : nan1 prec emax) (nan_mult : nan2 prec emax),
  (3 <= prec)%Z ->
  forall x0 x1 a : binary_float prec emax,
  canonical_2 x0 x1 ->
  let t := IeeeDraft.sub prec emax nan_minus x0 (IeeeDraft.guard prec emax nan_plus a) in
  let '(w0, w1) := IeeeDraft.sub_2_1_full prec emax nan_plus nan_minus nan_opp nan_abs nan_mult x0 x1 a in
  canonical_2 w0 w1 /\
  (finite w0 ->
   finite x0 /\ finite x1 /\ finite a /\ finite w1 /\
   normalized_2 (ieee_emin prec emax) prec (val w0) (val w1) /\
   Rabs ((val w0 + val w1) - ((val x0 + val x1) - val a))
   <= 2 * u prec ^ 2 * Rabs ((val x0 + val x1) - val a)) /\
  (finite x0 -> finite a ->
   Rabs (val x0 + val x1) <= bpow radix2 (emax - 2) ->
   Rabs (val a) <= bpow radix2 (emax - 2) ->
   finite w0) /\
  (finite x0 -> finite a -> ~ finite w0 ->
   w0 = infinity prec emax (Rlt_bool ((val x0 + val x1) - val a) 0) /\ w1 = pos_zero prec emax) /\
  (~ (finite x0 /\ finite a) -> canonical_of t w0 w1).

(* sub_1_2_full: sub_1_2, then the fix-up; t = sub(guard(a), y0). *)
Definition sub_1_2_full_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_opp nan_abs : nan1 prec emax) (nan_mult : nan2 prec emax),
  (3 <= prec)%Z ->
  forall a y0 y1 : binary_float prec emax,
  canonical_2 y0 y1 ->
  let t := IeeeDraft.sub prec emax nan_minus (IeeeDraft.guard prec emax nan_plus a) y0 in
  let '(w0, w1) := IeeeDraft.sub_1_2_full prec emax nan_plus nan_minus nan_opp nan_abs nan_mult a y0 y1 in
  canonical_2 w0 w1 /\
  (finite w0 ->
   finite a /\ finite y0 /\ finite y1 /\ finite w1 /\
   normalized_2 (ieee_emin prec emax) prec (val w0) (val w1) /\
   Rabs ((val w0 + val w1) - (val a - (val y0 + val y1)))
   <= 2 * u prec ^ 2 * Rabs (val a - (val y0 + val y1))) /\
  (finite a -> finite y0 ->
   Rabs (val a) <= bpow radix2 (emax - 2) ->
   Rabs (val y0 + val y1) <= bpow radix2 (emax - 2) ->
   finite w0) /\
  (finite a -> finite y0 -> ~ finite w0 ->
   w0 = infinity prec emax (Rlt_bool (val a - (val y0 + val y1)) 0) /\ w1 = pos_zero prec emax) /\
  (~ (finite a /\ finite y0) -> canonical_of t w0 w1).

(* mul_2_1_full: mul_2_1, then the fix-up; t = prod(x0, a). *)
Definition mul_2_1_full_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_opp nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax)
         (nan_mult : nan2 prec emax),
  (2 <= prec)%Z ->
  forall x0 x1 a : binary_float prec emax,
  canonical_2 x0 x1 ->
  let t := IeeeDraft.prod prec emax nan_fma x0 a in
  let '(w0, w1) := IeeeDraft.mul_2_1_full prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_mult x0 x1 a in
  canonical_2 w0 w1 /\
  (finite w0 ->
   finite x0 /\ finite x1 /\ finite a /\ finite w1 /\
   normalized_2 (ieee_emin prec emax) prec (val w0) (val w1) /\
   Rabs ((val w0 + val w1) - ((val x0 + val x1) * val a))
   <= 2 * u prec ^ 2 * Rabs ((val x0 + val x1) * val a) + 1 * eta (ieee_emin prec emax)) /\
  (finite x0 -> finite a ->
   Rabs ((val x0 + val x1) * val a) <= bpow radix2 (emax - 1) ->
   finite w0) /\
  (finite x0 -> finite a -> ~ finite w0 ->
   w0 = infinity prec emax (Rlt_bool ((val x0 + val x1) * val a) 0) /\ w1 = pos_zero prec emax) /\
  (~ (finite x0 /\ finite a) -> canonical_of t w0 w1).

(* mul_pow2_2_full: mul_pow2_2, then the fix-up; t = prod(x0, c). The operand c stays a finite
   power of two. *)
Definition mul_pow2_2_full_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax)
         (nan_mult : nan2 prec emax),
  (2 <= prec)%Z ->
  forall x0 x1 c : binary_float prec emax,
  canonical_2 x0 x1 ->
  finite c ->
  (exists n : Z, val c = bpow radix2 n) ->
  let t := IeeeDraft.prod prec emax nan_fma x0 c in
  let '(w0, w1) := IeeeDraft.mul_pow2_2_full prec emax nan_plus nan_minus nan_abs nan_fma nan_mult x0 x1 c in
  canonical_2 w0 w1 /\
  (finite w0 ->
   finite x0 /\ finite x1 /\ finite w1 /\
   normalized_2 (ieee_emin prec emax) prec (val w0) (val w1) /\
   Rabs ((val w0 + val w1) - ((val x0 + val x1) * val c))
   <= 1 * eta (ieee_emin prec emax)) /\
  (finite x0 ->
   Rabs ((val x0 + val x1) * val c) <= bpow radix2 (emax - 1) ->
   finite w0) /\
  (finite x0 -> ~ finite w0 ->
   w0 = infinity prec emax (Rlt_bool ((val x0 + val x1) * val c) 0) /\ w1 = pos_zero prec emax) /\
  (~ finite x0 -> canonical_of t w0 w1).


(** * The constructor kernels *)

(* make_2: a 2-limb value from one value of T, which may be anything. The result is
   canonical and stands for the same extended real number as a. *)
Definition make_2_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus : nan2 prec emax),
  forall a : binary_float prec emax,
  let '(x0, x1) := IeeeDraft.make_2 prec emax nan_plus a in
  canonical_2 x0 x1 /\
  xval_2 x0 x1 = xval a.

(* make_2_limbs: a 2-limb value from its two limbs, which must be canonical. The result is
   canonical and stands for the same extended real number; when h is finite, each limb
   keeps its value (a zero may change its sign). *)
Definition make_2_limbs_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus : nan2 prec emax),
  forall h l : binary_float prec emax,
  canonical_2 h l ->
  let '(x0, x1) := IeeeDraft.make_2_limbs prec emax nan_plus h l in
  canonical_2 x0 x1 /\
  xval_2 x0 x1 = xval_2 h l /\
  (finite h -> val x0 = val h /\ val x1 = val l).

(** * The kernels that need no fix-up *)

(* On canonical operands these kernels already return what the non-finite layer wants.
   Each statement gives the result as an extended real number (xval, xval_2): for finite
   operands it is the statement of the real model, with a result that leaves the range
   returned as the infinity of its sign; an infinite operand is treated as the infinity
   it is; and a NaN gives a NaN, or false for a comparison. *)

(* neg_2 and abs_2: the result is canonical. *)
Definition neg_2_ieee_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_opp : nan1 prec emax),
  (1 <= prec)%Z ->
  forall x0 x1 : binary_float prec emax,
  canonical_2 x0 x1 ->
  let '(z0, z1) := IeeeDraft.neg_2 prec emax nan_opp x0 x1 in
  canonical_2 z0 z1 /\
  xval_2 z0 z1 = xopp (xval_2 x0 x1).

Definition abs_2_ieee_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_opp : nan1 prec emax),
  (1 <= prec)%Z ->
  forall x0 x1 : binary_float prec emax,
  canonical_2 x0 x1 ->
  let '(z0, z1) := IeeeDraft.abs_2 prec emax nan_opp x0 x1 in
  canonical_2 z0 z1 /\
  xval_2 z0 z1 = xabs (xval_2 x0 x1).

(* The comparisons: that of the two values as extended real numbers. *)
Definition lt_2_2_ieee_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax),
  (1 <= prec)%Z ->
  forall x0 x1 y0 y1 : binary_float prec emax,
  canonical_2 x0 x1 ->
  canonical_2 y0 y1 ->
  let m := IeeeDraft.lt_2_2 prec emax x0 x1 y0 y1 in
  m = xlt (xval_2 x0 x1) (xval_2 y0 y1).

Definition le_2_2_ieee_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax),
  (1 <= prec)%Z ->
  forall x0 x1 y0 y1 : binary_float prec emax,
  canonical_2 x0 x1 ->
  canonical_2 y0 y1 ->
  let m := IeeeDraft.le_2_2 prec emax x0 x1 y0 y1 in
  m = xle (xval_2 x0 x1) (xval_2 y0 y1).

Definition eq_2_2_ieee_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax),
  (1 <= prec)%Z ->
  forall x0 x1 y0 y1 : binary_float prec emax,
  canonical_2 x0 x1 ->
  canonical_2 y0 y1 ->
  let m := IeeeDraft.eq_2_2 prec emax x0 x1 y0 y1 in
  m = xeq (xval_2 x0 x1) (xval_2 y0 y1).

Definition lt_2_1_ieee_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax),
  (1 <= prec)%Z ->
  forall x0 x1 a : binary_float prec emax,
  canonical_2 x0 x1 ->
  let m := IeeeDraft.lt_2_1 prec emax x0 x1 a in
  m = xlt (xval_2 x0 x1) (xval a).

Definition le_2_1_ieee_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax),
  (1 <= prec)%Z ->
  forall x0 x1 a : binary_float prec emax,
  canonical_2 x0 x1 ->
  let m := IeeeDraft.le_2_1 prec emax x0 x1 a in
  m = xle (xval_2 x0 x1) (xval a).

Definition eq_2_1_ieee_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax),
  (1 <= prec)%Z ->
  forall x0 x1 a : binary_float prec emax,
  canonical_2 x0 x1 ->
  let m := IeeeDraft.eq_2_1 prec emax x0 x1 a in
  m = xeq (xval_2 x0 x1) (xval a).

Definition lt_1_2_ieee_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax),
  (1 <= prec)%Z ->
  forall a y0 y1 : binary_float prec emax,
  canonical_2 y0 y1 ->
  let m := IeeeDraft.lt_1_2 prec emax a y0 y1 in
  m = xlt (xval a) (xval_2 y0 y1).

Definition le_1_2_ieee_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax),
  (1 <= prec)%Z ->
  forall a y0 y1 : binary_float prec emax,
  canonical_2 y0 y1 ->
  let m := IeeeDraft.le_1_2 prec emax a y0 y1 in
  m = xle (xval a) (xval_2 y0 y1).

(* The conversions to one limb: the rounding of the value in the sense of T. *)
Definition to_nearest_2_ieee_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax),
  (1 <= prec)%Z ->
  forall x0 x1 : binary_float prec emax,
  canonical_2 x0 x1 ->
  let t := IeeeDraft.to_nearest_2 prec emax x0 x1 in
  xval t = xround emax (RN (ieee_emin prec emax) prec) (xval_2 x0 x1).

Definition to_down_2_ieee_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax),
  (1 <= prec)%Z ->
  forall x0 x1 : binary_float prec emax,
  canonical_2 x0 x1 ->
  let t := IeeeDraft.to_down_2 prec emax x0 x1 in
  xval t = xround emax (RD (ieee_emin prec emax) prec) (xval_2 x0 x1).

Definition to_up_2_ieee_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax),
  (1 <= prec)%Z ->
  forall x0 x1 : binary_float prec emax,
  canonical_2 x0 x1 ->
  let t := IeeeDraft.to_up_2 prec emax x0 x1 in
  xval t = xround emax (RU (ieee_emin prec emax) prec) (xval_2 x0 x1).


(* abs_upper_2: the absolute value of a canonical 2-limb value, rounded up to one limb. *)
Definition abs_upper_2_ieee_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_opp : nan1 prec emax),
  (1 <= prec)%Z ->
  forall x0 x1 : binary_float prec emax,
  canonical_2 x0 x1 ->
  let t := IeeeDraft.abs_upper_2 prec emax nan_opp x0 x1 in
  xval t = xround emax (RU (ieee_emin prec emax) prec) (xabs (xval_2 x0 x1)).

(* radd and rmul, on operands that are nonnegative, +infinity or NaN: the result is of
   that kind too, and when it is finite the operands are finite and the statement of the
   real model holds. (The Ball kernels of the second radius design do not call them.) *)
Definition radd_ieee_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus : nan2 prec emax),
  (2 <= prec)%Z ->
  forall a b : binary_float prec emax,
  nonneg_ext a ->
  nonneg_ext b ->
  let r := IeeeDraft.radd prec emax nan_plus a b in
  nonneg_ext r /\
  (finite r ->
   finite a /\ finite b /\
   (val a + val b) <= val r /\
   val r - (val a + val b)
   <= (3 / 2) * (val r - Ulp.pred radix2 (FLT_exp (ieee_emin prec emax) prec) (val r))).

Definition rmul_ieee_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_fma : nan3 prec emax),
  (2 <= prec)%Z ->
  forall a b : binary_float prec emax,
  nonneg_ext a ->
  nonneg_ext b ->
  let r := IeeeDraft.rmul prec emax nan_fma a b in
  nonneg_ext r /\
  (finite r ->
   finite a /\ finite b /\
   (val a * val b) <= val r /\
   val r - (val a * val b)
   <= (3 / 2) * (val r - Ulp.pred radix2 (FLT_exp (ieee_emin prec emax) prec) (val r))).
