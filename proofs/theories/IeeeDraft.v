(* DRAFT of the IEEE model of five kernels, written by hand in the form the generator is
   meant to print. Nothing in this file is a proof.

   What it is. proofs/gen/Model.v defines each kernel over the real numbers, in a format
   with no largest number. Here the same kernels are defined over Flocq's type
   binary_float prec emax: the finite numbers of the format with signed zeros, the two
   infinities, and NaN, with Flocq's definitions of the IEEE 754 operations, overflow
   included. Rounding is to nearest, ties to even (mode_NE).

   The format. binary_float prec emax is the IEEE format with precision prec whose
   numbers are below 2^emax in magnitude: the largest one is
   Omega = 2^emax - 2^(emax - prec), and the smallest positive one is 2^emin with
   emin = 3 - emax - prec. Flocq fixes this relation between the two ends of the range,
   as IEEE 754 does. binary64 is prec = 53, emax = 1024; binary32 is prec = 24,
   emax = 128. Flocq requires 0 < prec < emax. So, of the toy formats (p, qmin, qmax) of
   the test tools, this model covers those with qmin + qmax = 3 - 2 p.

   NaN. Which NaN an operation returns (its sign and payload) is not specified here:
   Flocq's operations take it as a function of the operands, and these functions are
   variables of the section below, hence parameters of every definition. No statement
   depends on them. They are not axioms.

   Correspondence with the kernel descriptions (gen/kernels), one operation each:
     add a b      Bplus          a + b
     sub a b      Bminus         a - b
     neg a        Bopp           - a
     fma a b c    Bfma           fma(a, b, c)
     fms a b c    Bfma, Bopp     fma(a, b, -c)
     prod a b     Bfma           fma(a, b, +0.0)
   A call stays a call, as in Model.v, and the names of the values are those of the
   kernel descriptions.

   The second part gives the same five kernels as straight-line programs (Program.v):
   the list of their operations after inlining the calls. This is the form on which the
   relation between the two models is proved (IeeeBridge.v); that each program is its
   kernel is checked there by computation. *)
From Stdlib Require Import ZArith List.
From Flocq Require Import Core Binary.
From Kairn Require Import Program.
Import ListNotations.

Section IeeeKernels.
Variable prec emax : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Context {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}.

Notation float := (binary_float prec emax).
Notation nan_of := {x : float | is_nan prec emax x = true}.

(* The NaN returned by each operation, as a function of its operands. *)
Variable nan_plus : float -> float -> nan_of.
Variable nan_minus : float -> float -> nan_of.
Variable nan_opp : float -> nan_of.
Variable nan_fma : float -> float -> float -> nan_of.

(** * The operations *)

Definition pzero : float := B754_zero prec emax false.

Definition add (a b : float) : float :=
  Bplus prec emax prec_gt_0_ prec_lt_emax_ nan_plus BinarySingleNaN.mode_NE a b.
Definition sub (a b : float) : float :=
  Bminus prec emax prec_gt_0_ prec_lt_emax_ nan_minus BinarySingleNaN.mode_NE a b.
Definition neg (a : float) : float :=
  Bopp prec emax nan_opp a.
Definition fma (a b c : float) : float :=
  Bfma prec emax prec_gt_0_ prec_lt_emax_ nan_fma BinarySingleNaN.mode_NE a b c.
Definition fms (a b c : float) : float := fma a b (neg c).
Definition prod (a b : float) : float := fma a b pzero.

(** * The kernels *)

(* fast_two_sum: Fast2Sum (Dekker 1971). *)
Definition fast_two_sum (a b : float) : float * float :=
  let s := add a b in
  let z := sub s a in
  let e := sub b z in
  (s, e).

(* two_prod: TwoProd with an FMA (folklore; see JMP17). *)
Definition two_prod (a b : float) : float * float :=
  let p := prod a b in
  let e := fms a b p in
  (p, e).

(* two_sum: TwoSum (Knuth, TAOCP vol. 2, 4.2.2; Moller 1965). *)
Definition two_sum (a b : float) : float * float :=
  let s := add a b in
  let bb := sub s a in
  let t0 := sub s bb in
  let t1 := sub a t0 in
  let t2 := sub b bb in
  let e := add t1 t2 in
  (s, e).

(* add_2_2: JMP17 Alg. 6 (AccurateDWPlusDW); bound from MR22. *)
Definition add_2_2 (x0 x1 y0 y1 : float) : float * float :=
  let '(sh, sl) := two_sum x0 y0 in
  let '(th, tl) := two_sum x1 y1 in
  let c := add sl th in
  let '(vh, vl) := fast_two_sum sh c in
  let w := add tl vl in
  let '(z0, z1) := fast_two_sum vh w in
  (z0, z1).

(* mul_2_2: JMP17 Alg. 12 (DWTimesDW3); bound from MR22. *)
Definition mul_2_2 (x0 x1 y0 y1 : float) : float * float :=
  let '(ch, cl1) := two_prod x0 y0 in
  let tl0 := prod x1 y1 in
  let tl1 := fma x0 y1 tl0 in
  let cl2 := fma x1 y0 tl1 in
  let cl3 := add cl1 cl2 in
  let '(z0, z1) := fast_two_sum ch cl3 in
  (z0, z1).

End IeeeKernels.

(** * The same kernels as straight-line programs *)

(* Positions: the inputs are numbered from 0 in the order of the kernel's arguments, and
   each instruction defines the next position. The comment of each line gives the
   position and the name of the value in the kernel description. *)

(* inputs: 0 a, 1 b *)
Definition fast_two_sum_prog : list instr :=
  [ Iadd 0 1     (*  2 s *)
  ; Isub 2 0     (*  3 z *)
  ; Isub 1 3     (*  4 e *)
  ].

(* inputs: 0 a, 1 b *)
Definition two_prod_prog : list instr :=
  [ Iprod 0 1    (*  2 p *)
  ; Ifms 0 1 2   (*  3 e *)
  ].

(* inputs: 0 a, 1 b *)
Definition two_sum_prog : list instr :=
  [ Iadd 0 1     (*  2 s *)
  ; Isub 2 0     (*  3 bb *)
  ; Isub 2 3     (*  4 t0 *)
  ; Isub 0 4     (*  5 t1 *)
  ; Isub 1 3     (*  6 t2 *)
  ; Iadd 5 6     (*  7 e *)
  ].

(* inputs: 0 x0, 1 x1, 2 y0, 3 y1 *)
Definition add_2_2_prog : list instr :=
  [ Iadd 0 2     (*  4 sh      two_sum(x0, y0) *)
  ; Isub 4 0     (*  5 bb *)
  ; Isub 4 5     (*  6 t0 *)
  ; Isub 0 6     (*  7 t1 *)
  ; Isub 2 5     (*  8 t2 *)
  ; Iadd 7 8     (*  9 sl *)
  ; Iadd 1 3     (* 10 th      two_sum(x1, y1) *)
  ; Isub 10 1    (* 11 bb *)
  ; Isub 10 11   (* 12 t0 *)
  ; Isub 1 12    (* 13 t1 *)
  ; Isub 3 11    (* 14 t2 *)
  ; Iadd 13 14   (* 15 tl *)
  ; Iadd 9 10    (* 16 c *)
  ; Iadd 4 16    (* 17 vh      fast_two_sum(sh, c) *)
  ; Isub 17 4    (* 18 z *)
  ; Isub 16 18   (* 19 vl *)
  ; Iadd 15 19   (* 20 w *)
  ; Iadd 17 20   (* 21 z0      fast_two_sum(vh, w) *)
  ; Isub 21 17   (* 22 z *)
  ; Isub 20 22   (* 23 z1 *)
  ].

(* inputs: 0 x0, 1 x1, 2 y0, 3 y1 *)
Definition mul_2_2_prog : list instr :=
  [ Iprod 0 2    (*  4 ch      two_prod(x0, y0) *)
  ; Ifms 0 2 4   (*  5 cl1 *)
  ; Iprod 1 3    (*  6 tl0 *)
  ; Ifma 0 3 6   (*  7 tl1 *)
  ; Ifma 1 2 7   (*  8 cl2 *)
  ; Iadd 5 8     (*  9 cl3 *)
  ; Iadd 4 9     (* 10 z0      fast_two_sum(ch, cl3) *)
  ; Isub 10 4    (* 11 z *)
  ; Isub 9 11    (* 12 z1 *)
  ].
