# MR22: formalization of double-word arithmetic (Muller, Rideau)

Rocq proofs accompanying J.-M. Muller and L. Rideau, *Formalization of double-word arithmetic,
and comments on "Tight and rigorous error bounds for basic building blocks of double-word
arithmetic"*, ACM TOMS 48(1), 2022 ([hal-02972245](https://hal.science/hal-02972245)).

- Origin: the release archive `double-double_arithmetic-submitted_paper_release` of
  `https://gitlab.inria.fr/lrg/double-double_arithmetic` (the repository named in the archive's
  own opam file). SHA-256 of the downloaded archive:
  `786ae0b8c0bb53c6df4ea9004a8722f04a7b329993aa6e068ebdd708bec498f7`.
- License: MIT, copyright 2020 Jean-Michel Muller and Laurence Rideau. The archive states it in
  its `LICENSE` file, reproduced here unchanged, and in its opam file (`license: "MIT"`). The
  source files also carry the header line "Copyright (c) Inria. All rights reserved." (ENS de
  Lyon and Inria in `Bayleyaux.v`), which is kept as it is.
- Written for Coq 8.12, Flocq 3.3 and mathcomp-ssreflect 1.11. Built here with Rocq 9.0.1 and
  Flocq 4.2.2, without mathcomp.

## What is here

Five of the archive's ten files: `DWPlus.v` (the additions of JMP17, Algorithms 4 to 6) and the
four files it depends on (`Bayleyaux.v`, `F2SumFLT.v`, `F2SumFLX.v`, `F2Sum.v`). Kairn uses, in
`proofs/theories/Add22.v` and `Add21.v`:

- `DWPlusDW_relerr_bound` and `DWPlusDW_relerr_bound_pre` (AccurateDWPlusDW);
- `DWPlusFP_correct` (DWPlusFP);
- the definitions `double_word`, `TwoSum`, `Fast2Sum`, `DWPlusFP` and the lemmas about them
  (`TwoSum_correct`, `TwoSum_sumE`, `TwoSumC`, `TwoSum_asym`, `TwoSumS`, `Fast2Sum0f`,
  `Fast2Sum_asym`, `Fast2SumS`, `F2Sum_correct_abs`, `F2Sum_correct_DW'`, `DW_TwoSum`,
  `DW_asym`, `DW_S`, `dw_ulp`, `scale_generic_12`, `boundDWDW_ge_0`, `round_bpow`).

Not included: `DWTimesFP.v`, `DWTimesDW.v`, `DWTimesDW_original.v`, `DWDivFP.v`, `DWDivDW.v`.
Kairn's product proofs (`Mul22.v`, `Mul21.v`) do not use them: they follow the case analysis of
`DWTimesDW12_correct` for one of their four cases, and are written from scratch for a format
with underflow. (`DWTimesFP.v` declares `Parameter TwoProd`, which Kairn's axiom audit would
reject.)

## Modifications

No statement is changed, and no proof script except in the places listed below for
`Bayleyaux.v` and `DWPlus.v`.

All five files:

- `Require Import mathcomp.ssreflect.ssreflect.` is replaced by
  `From Stdlib Require Import ssreflect.` followed by the three settings that mathcomp's file
  made global and that the proof scripts rely on, here local to each file:
  `Set SsrOldRewriteGoalsOrder`, `Set Asymmetric Patterns`, `Set Bullet Behavior "None"`.
- One more local setting, `Set Warnings "-deprecated-syntactic-definition"`: the scripts use
  standard-library names that are now deprecated aliases (`Rabs_Rinv`, `double`).
- The standard library is imported with its `From Stdlib` prefix, and `ZArith` and `Reals` are
  imported explicitly, before Flocq, so that Flocq's lemma names (`Zeven_ex`) are not shadowed
  (`Require Import Reals Psatz.` or `Require Import Psatz.` becomes
  `From Stdlib Require Import ZArith Reals Psatz.`).

`Bayleyaux.v`:

- `Zpower` (removed from the standard library) is written `Z.pow`, in four places (lemmas
  `r1pu` and `r1mu2`).
- `rewrite -Zodd_even_bool` (removed) is written `rewrite Z.negb_even`, in `r1mu2`.

`DWPlus.v`:

- In `part_case_ulp`, `split =>//.` is written `move=> x; split =>//.`: the script used the name
  that Coq 8.12 gave automatically to an introduced hypothesis.
