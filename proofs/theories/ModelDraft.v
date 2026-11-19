(* Hand-written draft of the formal model of the first-wave kernels.

   This file stands in for the generated proofs/gen/Model.v until the generator emits it,
   and is written in the form the architecture page prescribes: one definition per kernel
   over the real numbers, every line one rounding, `call`s kept as calls, value names as in
   the kernel listings.

   The arithmetic model: a floating-point format with precision `prec` and gradual
   underflow, whose smallest positive number is 2^emin (Flocq's FLT format; exponents are
   unbounded above, so there is no overflow). `rnd` is rounding to nearest with the tie rule
   `choice` (ties to even is `choice n = negb (Z.even n)`).

     add a b     rnd (a + b)            fma a b c   rnd (a * b + c)
     sub a b     rnd (a - b)            fms a b c   rnd (a * b + - c)
     prod a b    rnd (a * b + 0)   (the product is an FMA with a zero addend)

   Kernels (sources: JMP17 = Joldes, Muller, Popescu, ACM TOMS 44(2), 2017):
     two_sum, fast_two_sum, two_prod   the error-free transformations
     add_2_2    JMP17 Algorithm 6 (AccurateDWPlusDW)
     add_2_1    JMP17 Algorithm 4 (DWPlusFP)
     mul_2_2    JMP17 Algorithm 12 (DWTimesDW3)
     mul_2_1    JMP17 Algorithm 9 (DWTimesFP3) *)
From Stdlib Require Import Reals ZArith.
From Flocq Require Import Core.
Open Scope R_scope.

Section Kernels.
Variable emin prec : Z.
Variable choice : Z -> bool.
Notation rnd := (round radix2 (FLT_exp emin prec) (Znearest choice)).

Definition two_sum (a b : R) : R * R :=
  let s := rnd (a + b) in
  let bb := rnd (s - a) in
  let t0 := rnd (s - bb) in
  let t1 := rnd (a - t0) in
  let t2 := rnd (b - bb) in
  let e := rnd (t1 + t2) in
  (s, e).

Definition fast_two_sum (a b : R) : R * R :=
  let s := rnd (a + b) in
  let z := rnd (s - a) in
  let e := rnd (b - z) in
  (s, e).

Definition two_prod (a b : R) : R * R :=
  let p := rnd (a * b + 0) in
  let e := rnd (a * b + - p) in
  (p, e).

Definition add_2_2 (x0 x1 y0 y1 : R) : R * R :=
  let '(sh, sl) := two_sum x0 y0 in
  let '(th, tl) := two_sum x1 y1 in
  let c := rnd (sl + th) in
  let '(vh, vl) := fast_two_sum sh c in
  let w := rnd (tl + vl) in
  let '(z0, z1) := fast_two_sum vh w in
  (z0, z1).

Definition add_2_1 (x0 x1 a : R) : R * R :=
  let '(sh, sl) := two_sum x0 a in
  let v := rnd (x1 + sl) in
  let '(z0, z1) := fast_two_sum sh v in
  (z0, z1).

Definition mul_2_2 (x0 x1 y0 y1 : R) : R * R :=
  let '(ch, cl1) := two_prod x0 y0 in
  let tl0 := rnd (x1 * y1 + 0) in
  let tl1 := rnd (x0 * y1 + tl0) in
  let cl2 := rnd (x1 * y0 + tl1) in
  let cl3 := rnd (cl1 + cl2) in
  let '(z0, z1) := fast_two_sum ch cl3 in
  (z0, z1).

Definition mul_2_1 (x0 x1 a : R) : R * R :=
  let '(ch, cl1) := two_prod x0 a in
  let cl3 := rnd (x1 * a + cl1) in
  let '(z0, z1) := fast_two_sum ch cl3 in
  (z0, z1).

End Kernels.
