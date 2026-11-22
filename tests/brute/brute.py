#!/usr/bin/env python3
"""The brute-force tier of Kairn's tests (docs/developer/testing.md, tests/brute/README.md).

    python3 tests/brute/brute.py plan    [--bins N]
    python3 tests/brute/brute.py run     --work DIR --budget SECONDS --jobs N [options]
    python3 tests/brute/brute.py collect --work DIR --name NAME --out FILE
    python3 tests/brute/brute.py report  FILE...

Two parts, each a set of pipelines `gen | RUNNER | check` of the oracle (oracle/README.md), the
same pipelines as the quick tier's cross-checks (tests/crosscheck.py, which runs the oracle's two
stages in its own process), only longer:

- compiled: every kernel of gen/claims.json, binary64 and binary32, on random cases of the
  oracle's generator (seed --seed, every stratum), through every runner that the CMake builds
  given by --build produce (kairn-gen-runner* and kairn-gen-packed-runner*: the scalar and the
  packed kernels, under each contraction setting), and the scalar runners of a second build of
  each with the other form of the scalar fix-ups (KAIRN_GEN_FIXUP_CALL; --fixup-forms). The
  cases come in units of --chunk; each
  unit is generated once and judged once per runner, so every runner of a machine judges the
  same cases, and a machine adds units round-robin over the kernels and formats until its
  budget is spent.
- interp: the generator's interpreter on every operand of the toy formats of the plan below, in
  chunks of --interp-chunk enumeration indices.

`run` is restartable: every finished pipeline leaves its summary in the work directory, and a
second `run` on the same directory starts only what is missing. No new pipeline starts after the
budget; the ones running finish. A pipeline that fails (a violated claim, an invalid case, a
suspicious non-finite result where the quick tier fails on one, a broken stream, a runner or
oracle error, a timeout) stops its series (one kernel, format and runner, or one enumeration),
and its finding, with the lines and the command that reproduce it, goes to findings.jsonl.

The driver never leaves processes behind: it kills its pipelines when it is interrupted
(SIGINT, SIGTERM, SIGHUP), on Linux they die with it even if it is killed (PR_SET_PDEATHSIG),
and on Windows they run in a job object that closes with it. --cpus and --nice confine it and
everything it starts.

`collect` merges the summaries with the oracle (check --merge), applies the quick tier's guards
(tests/crosscheck_guards.py) to every merged series and enumeration, and writes one compact JSON
file: totals and statistics per kernel and format, never the case streams. `report` prints
Markdown tables from such files.

Python 3 standard library only; macOS, Linux and Windows.
"""
import argparse
import datetime
import decimal
import glob
import hashlib
import importlib.util
import json
import os
import platform
import re
import shutil
import signal
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
ORACLE = os.path.join(REPO, "oracle", "kairn-oracle")
KAIRN_GEN = os.path.join(REPO, "gen", "kairn-gen")
CLAIMS = os.path.join(REPO, "gen", "claims.json")
GUARDS = os.path.join(REPO, "tests", "crosscheck_guards.py")
WINDOWS = os.name == "nt"
LINUX = sys.platform.startswith("linux")
PY = sys.executable

# Kernels whose intermediate values can overflow for operands far below the largest number, as
# their requirement of no intermediate overflow allows: the quick tier does not fail them on a
# suspicious non-finite result (tests/CMakeLists.txt, _intermediate_overflow), nor does this.
INTERMEDIATE_OVERFLOW = ("split", "two_prod_dekker")

# The product of two one-limb balls at precision 1, where u = 1/2: the factor of its radius,
# up((1+u)^5), is 8 there, above the 4 of the oracle's test of a suspicious non-finite result
# (operands and exact set below a quarter of the largest number). A radius beyond the largest
# number is then no sign of a fault, in any exponent range, and the run does not fail on it;
# tests/brute/widen.py is the exact test in its place (the result is infinite exactly when the
# same computation in a wider exponent range exceeds the largest number).
RADIUS_OVERFLOW = {("ball_mul_1", 1)}


def fails_on_suspicious(kernel, fmt):
    """Whether a suspicious non-finite result of the kernel in the format fails its run."""
    if kernel in INTERMEDIATE_OVERFLOW:
        return False
    return not (fmt.startswith("fp:") and (kernel, parse_fmt(fmt)[0]) in RADIUS_OVERFLOW)

# --- The plan of the interpreter's enumerations ---------------------------------------------------
#
# By the roles of a kernel's inputs, as tests/CMakeLists.txt derives them (1 a limb, 2 a normalized
# pair, r a radius, c a power of two, then _sum or _product; for a kernel of the extended domain,
# after "ext_", with b1 or b2 for a ball): the quick tier's toy format, whose exponent range is
# the base range here, and the formats beyond it. Every kernel also gets the formats of precision
# min_precision and min_precision + 1 in the base range (precision 1, 2 and 3 when min_precision
# is 1; PRECISION_ONE below has the exceptions). For the extended domain every format has the
# shape of the IEEE-model statements, qmin + qmax = 3 - 2p, and the base range is the quick
# tier's number of exponents, qmax - qmin + 1, in that shape. Formats below a kernel's
# min_precision are left out. Sizes: `plan`, from the oracle's gen --exhaustive --total.
SHAPES = {
    "1": ("fp:11:-30:10", ["fp:12:-30:10", "fp:13:-30:10", "fp:13:-60:40"]),
    "1_1_sum": ("fp:5:-7:4", ["fp:6:-7:4", "fp:7:-7:4", "fp:7:-14:2"]),
    "1_1_product": ("fp:5:-12:-1", ["fp:6:-12:-1", "fp:7:-12:-1", "fp:7:-8:4", "fp:7:-20:-6"]),
    "2_1_sum": ("fp:4:-4:2", ["fp:5:-4:2", "fp:6:-4:2", "fp:5:-6:3", "fp:4:-7:4"]),
    "1_2_sum": ("fp:4:-4:2", ["fp:5:-4:2", "fp:6:-4:2", "fp:5:-6:3", "fp:4:-7:4"]),
    "2_1_product": ("fp:4:-8:-2", ["fp:5:-8:-2", "fp:6:-8:-2", "fp:5:-4:2"]),
    "2_2_sum": ("fp:3:-3:2", ["fp:4:-3:2", "fp:5:-3:2", "fp:4:-4:3", "fp:3:-6:4"]),
    "2_2_product": ("fp:4:-7:-3", ["fp:5:-7:-3", "fp:6:-7:-3", "fp:4:-9:-3", "fp:5:-8:-2"]),
    "2_c_product": ("fp:5:-6:2", ["fp:6:-6:2", "fp:7:-6:2", "fp:6:-12:4"]),
    "1_r_1_product": ("fp:3:-5:0", ["fp:4:-5:0", "fp:5:-5:0", "fp:4:-8:2", "fp:3:-8:2"]),
    "2_r_1_product": ("fp:2:-4:1", ["fp:3:-4:1", "fp:4:-4:1", "fp:3:-6:2", "fp:2:-8:3"]),
    "1_r_1_r_sum": ("fp:2:-3:1", ["fp:3:-3:1", "fp:4:-3:1", "fp:3:-4:2", "fp:2:-6:4"]),
    "1_r_1_r_product": ("fp:2:-4:1", ["fp:3:-4:1", "fp:4:-4:1", "fp:3:-6:2", "fp:2:-7:3"]),
    # The scalings of a ball by a power of two (Milestone 2): 0.4 to 3.9 million cases each.
    "1_r_c_product": ("fp:4:-6:1", ["fp:5:-6:1", "fp:6:-6:1", "fp:5:-8:2", "fp:4:-9:3"]),
    "2_r_c_product": ("fp:3:-4:1", ["fp:4:-4:1", "fp:5:-4:1", "fp:4:-6:2", "fp:3:-7:3"]),
    # The extended domain: the quick tier's format with one and two bits more (the same number
    # of exponents), then more exponents.
    "ext_1": ("fp:11:-29:10", ["fp:12:-30:9", "fp:13:-31:8", "fp:13:-61:38"]),
    "ext_2": ("fp:6:-10:1", ["fp:7:-11:0", "fp:8:-12:-1", "fp:8:-16:3"]),
    "ext_r_r_sum": ("fp:6:-10:1", ["fp:7:-11:0", "fp:8:-12:-1", "fp:8:-16:3"]),
    "ext_r_r_product": ("fp:6:-10:1", ["fp:7:-11:0", "fp:8:-12:-1", "fp:8:-16:3"]),
    "ext_1_1_sum": ("fp:5:-7:0", ["fp:6:-8:-1", "fp:7:-9:-2", "fp:7:-13:2"]),
    # The directed products of Milestone 2, as the directed sums.
    "ext_1_1_product": ("fp:5:-7:0", ["fp:6:-8:-1", "fp:7:-9:-2", "fp:7:-13:2"]),
    "ext_2_1_sum": ("fp:4:-5:0", ["fp:5:-6:-1", "fp:6:-7:-2", "fp:5:-8:1", "fp:4:-9:4"]),
    "ext_1_2_sum": ("fp:4:-5:0", ["fp:5:-6:-1", "fp:6:-7:-2", "fp:5:-8:1", "fp:4:-9:4"]),
    "ext_2_1_product": ("fp:4:-5:0", ["fp:5:-6:-1", "fp:6:-7:-2", "fp:5:-8:1", "fp:4:-9:4"]),
    "ext_2_c_product": ("fp:5:-7:0", ["fp:6:-8:-1", "fp:7:-9:-2", "fp:6:-12:3"]),
    "ext_2_2_sum": ("fp:3:-4:1", ["fp:4:-5:0", "fp:5:-6:-1", "fp:3:-6:3", "fp:4:-6:1"]),
    "ext_2_2_product": ("fp:4:-4:-1", ["fp:5:-5:-2", "fp:6:-6:-3", "fp:4:-6:1", "fp:5:-6:-1"]),
    "ext_b1": ("fp:5:-9:2", ["fp:6:-10:1", "fp:7:-11:0", "fp:5:-13:6"]),
    "ext_b2": ("fp:4:-6:1", ["fp:5:-7:0", "fp:6:-8:-1", "fp:4:-8:3"]),
    "ext_b1_b1_sum": ("fp:2:-3:2", ["fp:3:-4:1", "fp:2:-5:4"]),
    # Fourteen exponents too: at two exponents a quarter of the cases end as a finite ball, at
    # ten 42 %, at fourteen about half (estimated on 10 000 indices drawn uniformly).
    "ext_b1_b1_product": ("fp:2:-3:2", ["fp:3:-4:1", "fp:2:-5:4", "fp:2:-7:6"]),
    "ext_b1_1_product": ("fp:3:-4:1", ["fp:4:-5:0", "fp:3:-6:3", "fp:2:-8:7"]),
    "ext_b2_1_product": ("fp:3:-3:0", ["fp:4:-4:-1", "fp:3:-4:1", "fp:2:-4:3"]),
    # The full scalings of a ball by a power of two (Milestone 2): 0.3 to 2.3 million cases each.
    "ext_b1_c_product": ("fp:4:-6:1", ["fp:5:-7:0", "fp:6:-8:-1", "fp:4:-8:3"]),
    "ext_b2_c_product": ("fp:3:-4:1", ["fp:4:-5:0", "fp:5:-6:-1", "fp:3:-6:3"]),
    # The kernels of the folds' stage (Milestone 2): the bounds (a count m, formats with 1/2 and
    # counts past the limit), the steps of the dot products, the finish of two limbs (any limbs).
    "n": ("fp:12:-30:12", ["fp:13:-30:12", "fp:16:-30:14", "fp:20:-50:20"]),
    "1_1_1_product": ("fp:3:-6:-1", ["fp:4:-6:-1", "fp:3:-8:1"]),
    "2_2_2_product": ("fp:4:-3:-2", ["fp:4:-4:-2"]),
    "ext_a2": ("fp:5:-7:0", ["fp:6:-8:-1", "fp:7:-9:-2", "fp:6:-12:3"]),
    # The interval kernels (Milestone 2): an interval of one limb (i1) or two (i2) is one operand,
    # every canonical interval of its bounds. One interval of one limb: 0.2 to 0.9 million cases;
    # two of one limb: 0.7 to 2.6 million; one of two limbs: 0.03 to 0.5 million.
    "ext_i1": ("fp:5:-9:2", ["fp:6:-10:1", "fp:5:-13:6"]),
    "ext_i1_i1_sum": ("fp:2:-3:2", ["fp:2:-5:4", "fp:3:-3:0"]),
    "ext_i1_i1_product": ("fp:2:-3:2", ["fp:2:-5:4", "fp:3:-3:0"]),
    "ext_i2": ("fp:3:-4:1", ["fp:4:-5:0", "fp:3:-5:2", "fp:4:-4:-1"]),
    # The enclosure interface of stage B2: a set and a point (interval_contains_k,
    # ball_contains_point_k); the other kernels of the stage have the shapes above. 0.1 to 2.5
    # million cases each.
    "ext_i1_1_sum": ("fp:3:-4:1", ["fp:4:-5:0", "fp:3:-6:3"]),
    "ext_i2_2_sum": ("fp:2:-2:1", ["fp:3:-3:0", "fp:2:-4:3"]),
    "ext_b1_1_sum": ("fp:3:-4:1", ["fp:4:-5:0", "fp:3:-6:3"]),
    "ext_b2_2_sum": ("fp:3:-3:0", ["fp:4:-4:-1", "fp:3:-4:1"]),
    # The steps of the maps of stage B (the others have the shapes of the kernels they call): a
    # product by a power of two of one limb, the steps of axpy_2_1 (a of one limb).
    "1_c_product": ("fp:7:-14:6", ["fp:8:-14:6", "fp:7:-20:10"]),
    "1_2_2_product": ("fp:3:-5:-3", ["fp:4:-5:-3", "fp:3:-6:-3"]),
    # The kernels of the folds of maxima (m a mask): the maxima of a state and an element, the
    # finishes on every value of the state's limb with the mask both ways.
    "1_m_1_m_sum": ("fp:4:-6:1", ["fp:5:-6:1", "fp:4:-9:4"]),
    "1_m_1_sum": ("fp:5:-7:0", ["fp:6:-7:0", "fp:5:-10:3"]),
    "1_m_2_sum": ("fp:3:-6:2", ["fp:4:-6:2", "fp:3:-8:4"]),
    "ext_1_m_sum": ("fp:11:-29:10", ["fp:12:-30:9", "fp:13:-61:38"]),
    # The kernels of the ball vectors (r a radius, m a mask, c a power of two, n a count): the
    # quick tier's toy formats (tests/CMakeLists.txt), then a bit more and more exponents; the
    # finishes of the extended domain as the finish of a fold of maxima, in the IEEE shape.
    "r_r_r_sum": ("fp:3:-5:3", ["fp:4:-5:3", "fp:4:-8:4"]),
    "r_r_1_sum": ("fp:3:-5:3", ["fp:4:-5:3", "fp:4:-8:4"]),
    "r_m_r_c_sum": ("fp:4:-4:2", ["fp:5:-4:2", "fp:5:-8:4"]),
    "ext_1_m_m_sum": ("fp:11:-29:10", ["fp:12:-30:9", "fp:13:-61:38"]),
    # The accumulator's steps and its radius: 0.05 to 13 million cases each.
    "1_r_1_sum": ("fp:3:-3:1", ["fp:4:-3:1", "fp:4:-6:3"]),
    "2_r_2_sum": ("fp:3:-2:0", ["fp:4:-2:0", "fp:3:-3:1"]),
    "1_r_1_1_product": ("fp:2:-2:1", ["fp:3:-2:1", "fp:3:-4:2"]),
    "r_n_r_r_sum": ("fp:3:-2:0", ["fp:4:-2:0", "fp:4:-4:2"]),
}

# Kernels whose shape's formats do not fit them, each with its own (read before SHAPES and
# EXPLICIT): the merge of two accumulators of two limbs has the shape of the sum of two balls of
# two limbs, whose restrictions name their inputs; its own are those of the quick tier
# (tests/CMakeLists.txt, _toy_kernel_acc_merge_2): the running sums every pair, the sums of
# magnitudes a few values.
_R_ACC_A = "a.in=0x0p+0/0x1p-2/0x1.4p+0/0x1.8p+0"
_R_ACC_C = "c.in=0x0p+0/0x1p-1/0x1.4p+0/0x1.cp+0/0x1.4p+2"
_R_ACC_MUL = "a.in=0x0p+0/0x1p-1/0x1.8p+0"
# conv_radius (seven operands; by the ruling of 2026-11-21 its claim is of finite results,
# and a result that is not finite is +inf or a NaN, judged no further): a few values of each
# operand, ma up to Omega so that ma mb overflows (+inf, and a NaN where g or m is zero), the
# finite results nine tenths of each enumeration (the guards ask three quarters).
_R_CONV = ["ma.in=0x0p+0/0x1p-4/0x1p-1/0x1p+0/0x1.8p+1/0x1.cp+6",
           "mb.in=0x0p+0/0x1p-4/0x1p-1/0x1p+0/0x1.8p+1",
           "rx.in=0x0p+0/0x1p-4/0x1p-2/0x1p+0", "ry.in=0x0p+0/0x1p-4/0x1p-2/0x1p+0",
           "m.in=0x0p+0/0x1p+0/0x1p+1/0x1.8p+1", "g.in=0x0p+0/0x1p-3/0x1p-1/0x1p+0",
           "t.in=0x0p+0/0x1p-4/0x1p+0"]
_R_CONV_WIDE = ["ma.in=0x0p+0/0x1p-5/0x1p-2/0x1p-1/0x1p+0/0x1.8p+1/0x1.8p+2/0x1.cp+7",
                "mb.in=0x0p+0/0x1p-5/0x1p-2/0x1p+0/0x1.8p+1/0x1.8p+2",
                "rx.in=0x0p+0/0x1p-5/0x1p-3/0x1p-1/0x1p+0",
                "ry.in=0x0p+0/0x1p-5/0x1p-3/0x1p-1/0x1p+0",
                "m.in=0x0p+0/0x1p+0/0x1p+1/0x1.8p+1/0x1.4p+2",
                "g.in=0x0p+0/0x1p-5/0x1p-3/0x1p-1/0x1p+0", "t.in=0x0p+0/0x1p-5/0x1p-1/0x1p+1"]
KERNEL_FORMATS = {
    # The quick tier's restricted domain (tests/CMakeLists.txt, _toy_kernel_conv_radius), the
    # same one bit more precise, and more values of each operand with two exponents more: 23 040,
    # 23 040 and 120 000 cases.
    "conv_radius": ("fp:3:-4:4", [
        ("fp:3:-4:4", _R_CONV),
        ("fp:4:-4:4", _R_CONV),
        ("fp:3:-5:5", _R_CONV_WIDE),
    ]),
    # The product step of an accumulator of two limbs: three operands of two limbs, the quick
    # tier's restriction (tests/CMakeLists.txt, _toy_2_r_2_2_product), then the running sum's
    # leading limb free, then a format of two exponents complete: 0.1 to 0.3 million cases.
    "acc_mul_2": ("fp:4:-3:-2", [
        ("fp:4:-3:-2", [_R_ACC_MUL, "s.lead=-1:0", "x.lead=-1:0"]),
        ("fp:4:-3:-2", [_R_ACC_MUL, "s.lead=-1:0"]),
        ("fp:3:-2:-1", []),
    ]),
    # And its entry form, acc_mul_2 on the guarded limbs of its factors (rule R3, the factors of a
    # fused operation), which add_product of two limbs calls: the same plan.
    "acc_mul_entry_2": ("fp:4:-3:-2", [
        ("fp:4:-3:-2", [_R_ACC_MUL, "s.lead=-1:0", "x.lead=-1:0"]),
        ("fp:4:-3:-2", [_R_ACC_MUL, "s.lead=-1:0"]),
        ("fp:3:-2:-1", []),
    ]),
    "acc_merge_2": ("fp:3:-2:0", [
        ("fp:3:-2:0", [_R_ACC_A, _R_ACC_C]),
        ("fp:3:-2:-1", []),
        ("fp:4:-3:-1", [_R_ACC_A, _R_ACC_C]),
    ]),
}

# The folds (gen/claims.json, "folds"), by their arrays as tests/CMakeLists.txt names them (_1 a
# sum of one limb, _2 of two, _1_1 and _2_2 dot products): every array of each format up to the
# length given, in every order that differs (gen --exhaustive --max-length), the quick tier's
# first; and the compiled runners on random arrays up to FOLD_LENGTH elements, the scalar ones on
# every order and the packed ones on the lane order of their register.
FOLD_SHAPES = {
    "1": [("fp:3:-3:0", 3), ("fp:4:-4:-1", 3), ("fp:2:-2:1", 4)],
    "2": [("fp:3:-4:1", 2), ("fp:3:-3:0", 2), ("fp:3:-5:2", 2)],
    "1_1": [("fp:2:-1:0", 2), ("fp:2:-2:1", 2), ("fp:3:-3:0", 1)],
    "2_2": [("fp:4:-4:-1", 1), ("fp:4:-5:0", 1)],
    # The maps (map, the scalars: s1 of one limb, s2 of two, sc a power of two; then the arrays),
    # the folds of maxima (max) and the convolutions (conv, both lengths up to the one given).
    "map_1_1": [("fp:2:-1:0", 2), ("fp:2:-2:1", 2), ("fp:3:-3:0", 1)],
    "map_2_2": [("fp:3:-4:1", 1), ("fp:3:-3:0", 1), ("fp:4:-5:0", 1)],
    "map_s1_1_1": [("fp:3:-3:0", 1), ("fp:2:-1:0", 2), ("fp:3:-4:1", 1)],
    "map_s2_2_2": [("fp:4:-3:-2", 1), ("fp:4:-4:-1", 1)],
    "map_s1_2_2": [("fp:3:-2:-1", 1), ("fp:3:-3:0", 1)],
    "map_s1_1": [("fp:3:-3:0", 2), ("fp:5:-7:0", 1), ("fp:2:-2:1", 3)],
    "map_s1_2": [("fp:2:-2:1", 2), ("fp:3:-3:0", 1), ("fp:3:-4:1", 1)],
    "map_sc_1": [("fp:4:-5:0", 2), ("fp:5:-7:0", 2), ("fp:3:-3:0", 3)],
    "map_sc_2": [("fp:3:-3:0", 2), ("fp:3:-4:1", 2), ("fp:4:-5:0", 1)],
    "max_1": [("fp:3:-3:0", 3), ("fp:4:-4:-1", 3), ("fp:2:-2:1", 4)],
    "max_2": [("fp:3:-4:1", 2), ("fp:3:-3:0", 2), ("fp:3:-5:2", 2)],
    "conv_1_1": [("fp:2:-1:0", 2), ("fp:2:-2:1", 2), ("fp:3:-3:0", 1)],
    "conv_2_2": [("fp:4:-4:-1", 1), ("fp:4:-5:0", 1)],
    # The ball vectors, each by its name (kernel_NAME, tests/CMakeLists.txt's
    # _fold_toy_kernel_NAME): the full tier's enumeration first ("-" for none: a product of
    # BallVectors), then formats of binary_float's shape, where V4 is judged (oracle/README.md,
    # "Their folds"): 7 thousand to 140 million requests each.
    "kernel_bv_add_1": [("fp:2:-2:1", 1), ("fp:2:-2:1", 2), ("fp:3:-4:1", 1)],
    "kernel_bv_sub_1": [("fp:2:-2:1", 1), ("fp:2:-2:1", 2), ("fp:3:-4:1", 1)],
    "kernel_bv_add_2": [("fp:3:-2:-1", 1), ("fp:3:-4:1", 1)],
    "kernel_bv_sub_2": [("fp:3:-2:-1", 1), ("fp:3:-4:1", 1)],
    "kernel_bv_scale_1": [("fp:2:-2:1", 2), ("fp:3:-4:1", 1)],
    "kernel_bv_scale_2": [("fp:2:-2:1", 1), ("fp:2:-2:1", 2), ("fp:3:-4:1", 1)],
    # bv_scale_2 on its scalar guarded (rule R3, the factors of a fused operation): the same formats.
    "kernel_bv_scale_2_entry": [("fp:2:-2:1", 1), ("fp:2:-2:1", 2), ("fp:3:-4:1", 1)],
    "kernel_bv_neg_1": [("fp:2:-2:1", 2), ("fp:3:-4:1", 2), ("fp:2:-3:2", 3)],
    "kernel_bv_neg_2": [("fp:2:-2:1", 2), ("fp:3:-4:1", 1)],
    "kernel_bv_mul_pow2_1": [("fp:2:-2:1", 2), ("fp:3:-4:1", 2)],
    "kernel_bv_mul_pow2_2": [("fp:2:-2:1", 2), ("fp:3:-4:1", 1)],
    "kernel_bv_make_1": [("fp:2:-2:1", 2), ("fp:3:-4:1", 2), ("fp:2:-2:1", 3)],
    "kernel_bv_make_2": [("fp:2:-2:1", 2), ("fp:3:-4:1", 1)],
    # bv_make_2 on each limb of each center guarded (rule R3): the same formats.
    "kernel_bv_make_2_entry": [("fp:2:-2:1", 2), ("fp:3:-4:1", 1)],
    "kernel_bv_conv_1": [("-", 0), ("fp:4:-3:-2", 1), ("fp:4:-4:-1", 1)],
    "kernel_bv_conv_2": [("-", 0), ("fp:4:-3:-2", 1), ("fp:4:-4:-1", 1)],
}
FOLD_LENGTH = 4096
FOLD_CHUNK_DIVISOR = 100

# Precision 1 of the one-limb balls with two operands, in place of the base range. There u = 1/2
# and the constants of the radius are large against a format of few exponents: the factor
# up((1+u)^3) of a sum is 4, and its constant H is 8 eta. In the base range moved up until the
# interpreter accepts the constants (fp:1:-2:2 for the sums, largest number 4, H = 2;
# fp:1:-2:3 for the product) 3.8 % of the cases of a sum and 5.3 % of those of the product end
# as a finite ball, and the oracle shows radii that overflow on small operands as suspicious
# (10 of each sum, 423 of the product). With more exponents the sums give a finite ball in half
# of their cases and nothing suspicious; the product in 46 %, and its suspicious results stay
# (RADIUS_OVERFLOW above).
PRECISION_ONE = {
    "1_r_1_r_sum": "fp:1:-5:5",
    "1_r_1_r_product": "fp:1:-6:5",
}

# The two-limb balls with two operands: every operand of their quick-tier format is far too many
# (140 million for ball_add_2 at fp:3:-3:2, 12.4 billion for ball_mul_2 at fp:4:-5:1). They get
# complete enumerations of formats of their min_precision with fewer exponents, and larger
# restricted domains than the quick tier's (gen --restrict), one of them one bit more precise.
#
# The share of the cases that end as a finite ball, estimated on 10 000 enumeration
# indices drawn uniformly (the run reports the exact counts). Since the constant H of the radius
# holds the smallest normal number, a product of balls in a format of few exponents mostly
# overflows: ball_mul_2 at fp:4:-2:0 (numbers 2^-2 to 15, smallest normal 2) gives a finite ball
# in 1.3 % of its cases, and more exponents above do not help (fp:4:-3:0 3.9 %, fp:4:-2:1 1.0 %,
# fp:4:-3:1 2.4 %, 565 million cases), but the same number of exponents lower down does, where
# products of numbers below 1 stay finite: fp:4:-5:-3 (the same size, 15.5 million) 35 %. The
# full product, held to the IEEE shape, gets four exponents (fp:4:-4:-1, 98 million cases, 10 %,
# where fp:4:-3:-2 gives 5.8 %) and a restricted enumeration with six (centers in [1, 2), 54 %).
# The full sums give 18 % at fp:4:-3:-2 and 43 % at fp:3:-3:0, both complete; their quick
# tier's fp:3:-2:-1 gives 6 %.
_R_SUM_QUICK = "0x0p+0/0x1p-3/0x1p-1/0x1.4p+1"
_R_SUM_7 = "0x0p+0/0x1p-3/0x1.8p-2/0x1p-1/0x1.4p+1/0x1.cp+2/0x1.cp+4"
_R_MUL_QUICK = "0x0p+0/0x1p-5/0x1.8p+0"
_R_MUL_5 = "0x0p+0/0x1p-5/0x1p-3/0x1.8p+0/0x1.ep+4"
_R_MUL_P5 = "0x0p+0/0x1p-4/0x1.8p+0"
_R_EXT_MUL_QUICK = "0x0p+0/0x1p-4/0x1p-1/0x1.8p+0"
_R_EXT_MUL_P5 = "0x0p+0/0x1p-5/0x1p-1/0x1.8p+0"
EXPLICIT = {
    "2_r_2_r_sum": ("fp:3:-3:2", [
        ("fp:3:-2:1", []),
        ("fp:3:-3:1", []),
        ("fp:3:-3:2", ["cx.lead=-1:0"]),
        ("fp:3:-3:2", ["rx.in=" + _R_SUM_7, "ry.in=" + _R_SUM_7]),
        ("fp:4:-3:2", ["rx.in=" + _R_SUM_QUICK, "ry.in=" + _R_SUM_QUICK]),
    ]),
    "2_r_2_r_product": ("fp:4:-5:1", [
        ("fp:4:-5:-3", []),
        ("fp:4:-5:1", ["rx.in=" + _R_MUL_QUICK, "ry.in=" + _R_MUL_QUICK]),
        ("fp:4:-5:1", ["rx.in=" + _R_MUL_5, "ry.in=" + _R_MUL_5, "cx.lead=0:0"]),
        ("fp:4:-5:1", ["cx.lead=0:0", "cy.lead=0:0"]),
        ("fp:5:-4:1", ["rx.in=" + _R_MUL_P5, "ry.in=" + _R_MUL_P5, "cx.lead=0:0"]),
    ]),
    # The extended domain, where a ball is one operand (every finite center with every finite
    # radius, the whole line and the empty set) and restrictions shrink its finite part only.
    # The sums are complete in the quick tier (fp:3:-2:-1, two exponents); here complete with one
    # bit more and with four exponents, and restricted with six. The product is restricted in the
    # quick tier (fp:4:-4:-1, radii 0, eta, 1/2, 3/2, cx in [1, 2)); here complete with two and
    # with four exponents, every center with those radii, centers in [1, 2) with six exponents,
    # and restricted with one bit more.
    "ext_b2_b2_sum": ("fp:3:-2:-1", [
        ("fp:4:-3:-2", []),
        ("fp:3:-3:0", []),
        ("fp:3:-4:1", ["rx.in=" + _R_SUM_QUICK, "ry.in=" + _R_SUM_QUICK]),
    ]),
    "ext_b2_b2_product": ("fp:4:-4:-1", [
        ("fp:4:-3:-2", []),
        ("fp:4:-4:-1", ["rx.in=" + _R_EXT_MUL_QUICK, "ry.in=" + _R_EXT_MUL_QUICK]),
        ("fp:4:-4:-1", []),
        ("fp:4:-5:0", ["cx.lead=0:0", "cy.lead=0:0"]),
        ("fp:5:-5:-2", ["rx.in=" + _R_EXT_MUL_P5, "ry.in=" + _R_EXT_MUL_P5, "cx.lead=0:0"]),
    ]),
    # Two intervals of two limbs (the interval kernels): every pair of intervals of a format of two
    # exponents (the quick tier's sums, fp:3:-2:-1, 0.2 million) and of four with one bit more
    # (fp:4:-3:-2, 3.8 million, complete for the product too); restricted ones of more exponents,
    # the bounds of one operand with leading limbs in a few binades; for the hull and the
    # intersection, whose claims hold from precision 1, precision 1 (fp:1:-1:2, 64 516) and 2
    # (fp:2:-2:1, 2.6 million).
    "ext_i2_i2_sum": ("fp:3:-2:-1", [
        ("fp:1:-1:2", []),
        ("fp:2:-2:1", []),
        ("fp:3:-2:-1", []),
        ("fp:4:-3:-2", []),
        ("fp:3:-3:0", ["xl.lead=-1:0", "xu.lead=-1:0"]),
    ]),
    "ext_i2_i2_product": ("fp:4:-3:-2", [
        ("fp:4:-3:-2", []),
        ("fp:4:-4:-1", ["xl.lead=-1:-1", "xu.lead=-1:-1"]),
        ("fp:5:-4:-3", ["xl.lead=-2:-2", "xu.lead=-2:-2"]),
    ]),
}


# The constants of a kernel (the splitter 2^ceil(p/2) + 1 of split and two_prod_dekker, the
# constants up(...) and unit_computed(K) of the Ball kernels) are numbers of the format, or the
# interpreter refuses the kernel in it (kairn-gen interp: "constant ... is not a number of the
# format", or "... overflows the format"): a format where the claims, which assume that nothing
# overflows, say nothing. The plan evaluates every constant of a kernel and of its callees with
# the generator's own code (gen/kairn_gen/consts.py) and replaces a format that one of them does
# not fit by the nearest that every one fits: the same precision and number of exponents, the
# range moved up one exponent at a time (finite domain), or two exponents more at a time in the
# IEEE shape (extended domain).
_GEN = []


def gen_kernels():
    """The generator's modules ir and consts and its kernels, loaded once."""
    if not _GEN:
        sys.path.insert(0, os.path.join(REPO, "gen"))
        from kairn_gen import consts, ir
        _GEN.extend([ir, consts, ir.load_kernels(os.path.join(REPO, "gen", "kernels"))])
    return _GEN


def kernel_constants(name):
    """The constants a kernel names, its callees' included (+inf and NaN are always numbers)."""
    ir, _, ks = gen_kernels()

    def walk(k):
        out = set(ir.constants(k))
        for st in k.body:
            if st.is_call:
                out |= walk(ks[st.op])
        return out
    return sorted(walk(ks[name]) - {"inf", "nan"})


def refusal(name, fmt):
    """Why the interpreter refuses the kernel in the format (a constant of it that is not a
    number of the format), or None."""
    _, consts, ks = gen_kernels()
    p, qmin, qmax = parse_fmt(fmt)
    for c in kernel_constants(name):
        try:
            consts.value(c, ks, p, qmin, qmax)
        except consts.ConstError as e:
            return "constant %s: %s" % (c, e)
    return None


def fitting_format(name, fmt, extended):
    """The format nearest to fmt in which every constant of the kernel is a number (see above),
    or None if there is none within 64 steps."""
    p, qmin, qmax = parse_fmt(fmt)
    for i in range(1, 65):
        f = (ieee_shaped(p, qmax - qmin + 1 + 2 * i) if extended
             else "fp:%d:%d:%d" % (p, qmin + i, qmax + i))
        if refusal(name, f) is None:
            return f
    return None


def not_yet_cross_checked():
    """The kernels the oracle does not judge yet: the list KAIRN_NOT_YET_CROSS_CHECKED of
    tests/CMakeLists.txt, the one place that says which (the folds' stage of Milestone 2)."""
    with open(os.path.join(REPO, "tests", "CMakeLists.txt"), encoding="utf-8") as f:
        m = re.search(r"^set\(KAIRN_NOT_YET_CROSS_CHECKED\s([^)]*)\)", f.read(), re.M)
    return set(m.group(1).split()) if m else set()


def load_claims():
    """The kernels of gen/claims.json that the oracle judges: every one, but those of
    not_yet_cross_checked()."""
    skip = not_yet_cross_checked()
    with open(CLAIMS, encoding="utf-8") as f:
        return [k for k in json.load(f)["kernels"] if k["name"] not in skip]


def not_yet_cross_checked_folds():
    """The folds the oracle does not judge yet: KAIRN_NOT_YET_CROSS_CHECKED_FOLDS of
    tests/CMakeLists.txt."""
    with open(os.path.join(REPO, "tests", "CMakeLists.txt"), encoding="utf-8") as f:
        m = re.search(r"^set\(KAIRN_NOT_YET_CROSS_CHECKED_FOLDS\s([^)]*)\)", f.read(), re.M)
    return set(m.group(1).split()) if m else set()


def load_folds():
    """The folds of gen/claims.json that the oracle judges."""
    skip = not_yet_cross_checked_folds()
    with open(CLAIMS, encoding="utf-8") as f:
        return [k for k in json.load(f).get("folds", []) if k["name"] not in skip]


def fold_shape(f):
    """The shape of a fold's toy formats, as tests/CMakeLists.txt names it: the limbs of its
    arrays; for a map first its scalars (s1, s2, sc for a power of two), and map, conv or max for
    a map, a convolution and a fold of maxima."""
    shape = "_".join(str(a.get("limbs", 1)) for a in f.get("arrays", []))
    if f.get("bv") or f.get("bv_conv"):
        return "kernel_" + f["name"]
    if f.get("map"):
        req = [r.replace(" ", "") for r in f.get("requires", [])]
        sc = ["sc" if "power_of_two(%s)" % s.get("name") in req else "s%d" % s.get("limbs", 1)
              for s in f.get("scalars", [])]
        return "_".join(["map"] + sc + [shape])
    if f.get("conv"):
        return "conv_" + shape
    if any(e.get("kind") == "upper" for e in f.get("ensures", [])):
        return "max_" + shape
    return shape


def fold_plan(folds, only=None):
    """[{kernel, format, restrict, maxlen, why}] and [errors]: every array of the formats of
    FOLD_SHAPES up to their lengths, for each fold at or above its min_precision."""
    plan, errors = [], []
    for f in folds:
        name = f["name"]
        if only and name not in only:
            continue
        shape = fold_shape(f)
        if shape not in FOLD_SHAPES:
            errors.append("%s: no toy formats are planned for its arrays (%s): add them to "
                          "FOLD_SHAPES in tests/brute/brute.py" % (name, shape.replace("_", " ")))
            continue
        for i, (fmt, L) in enumerate(FOLD_SHAPES[shape]):
            if fmt == "-":
                continue        # no enumeration in the full tier's format
            if parse_fmt(fmt)[0] < (f.get("min_precision") or 1):
                continue
            plan.append({"kernel": name, "format": fmt, "restrict": [], "maxlen": L,
                         "why": ("the full tier's format" if i == 0 else "another format") +
                                ", every array up to %d elements" % L})
    return plan, errors


def packed_lanes(fold_name, fmt, backend):
    """W of the packed form of a fold for a format and backend (its claims), or None."""
    with open(CLAIMS, encoding="utf-8") as f:
        for k in json.load(f).get("folds", []):
            if k["name"] == fold_name:
                return (k.get("packed_lanes") or {}).get(fmt, {}).get(backend)
    return None


def shape_of(k):
    """The roles of the inputs and the operation, as tests/CMakeLists.txt derives them."""
    requires = [r.replace(" ", "") for r in k.get("requires", [])]
    balls = dict(m.groups() for m in (re.match(r"^ball\(([^,]+),([^)]+)\)$", r) for r in requires)
                 if m)
    # An interval (the interval kernels): its lower bound stands for it, its upper is left out.
    intervals = dict(m.groups() for m in (re.match(r"^interval\(([^,]+),([^)]+)\)$", r)
                                          for r in requires) if m)
    roles = []
    for i in k["inputs"]:
        if i["name"] in balls.values() or i["name"] in intervals.values():
            continue
        if i.get("type") == "mask":
            roles.append("m")
        elif i["name"] in balls:
            roles.append("b%d" % i.get("limbs", 1))
        elif i["name"] in intervals:
            roles.append("i%d" % i.get("limbs", 1))
        elif (i.get("limbs", 1) != 1 and k.get("domain") == "extended"
              and "canonical(%s)" % i["name"] not in requires):
            roles.append("a%d" % i["limbs"])       # several limbs of any values
        elif i.get("limbs", 1) != 1:
            roles.append(str(i["limbs"]))
        elif "count(%s)" % i["name"] in requires:
            roles.append("n")
        elif "nonneg(%s)" % i["name"] in requires:
            roles.append("r")
        elif "power_of_two(%s)" % i["name"] in requires:
            roles.append("c")
        else:
            roles.append("1")
    s = "_".join(roles)
    if len(roles) > 1:
        # A kernel without a value (an interval kernel) is a product when the set of an entry is.
        product = ("*" in k["value"] if k.get("value") is not None else
                   any("*" in str(e.get("set") or "") for e in k.get("ensures", [])))
        s += "_product" if product else "_sum"
    if k.get("domain") == "extended":
        s = "ext_" + s
    return s


def parse_fmt(name):
    m = re.match(r"^fp:(\d+):(-?\d+):(-?\d+)$", name)
    if not m:
        raise ValueError("not a toy format: %s" % name)
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def ieee_shaped(p, exponents):
    """The format of precision p with that many exponents and qmin + qmax = 3 - 2p, the shape of
    binary64, binary32 and the IEEE-model statements (exponents is even in that shape)."""
    qmin = 2 - p - exponents // 2
    return "fp:%d:%d:%d" % (p, qmin, 3 - 2 * p - qmin)


def interp_plan(kernels, only=None):
    """[{kernel, format, restrict, why}] and [errors]: what the interpreter enumerates."""
    plan, errors = [], []
    for k in kernels:
        name = k["name"]
        if only and name not in only:
            continue
        shape = shape_of(k)
        extended = k.get("domain") == "extended"
        pmin = k.get("min_precision")
        if not isinstance(pmin, int):
            errors.append("%s: min_precision is %r, so no format can be chosen" % (name, pmin))
            continue
        entries = []
        if name in KERNEL_FORMATS or shape in EXPLICIT:
            quick, listed = KERNEL_FORMATS.get(name) or EXPLICIT[shape]
            for fmt, restrict in listed:
                entries.append((fmt, restrict, None))
        elif shape in SHAPES:
            quick, extra = SHAPES[shape]
            _, qmin, qmax = parse_fmt(quick)
            # Precision 1 too, which the oracle reads since commit 2bfe39d; and 2 and 3 then.
            p0 = max(pmin, 2)
            for p in ([1] if pmin == 1 else []) + [p0, p0 + 1]:
                if p == 1 and shape in PRECISION_ONE:
                    entries.append((PRECISION_ONE[shape], [], None))
                elif extended:
                    entries.append((ieee_shaped(p, qmax - qmin + 1), [], None))
                else:
                    entries.append(("fp:%d:%d:%d" % (p, qmin, qmax), [], None))
            for fmt in extra:
                entries.append((fmt, [], None))
        else:
            errors.append("%s: no toy formats are planned for its inputs (%s): add them to "
                          "SHAPES in tests/brute/brute.py" % (name, shape.replace("_", " ")))
            continue
        qp, qmin0, qmax0 = parse_fmt(quick)
        seen = set()
        for fmt, restrict, _ in entries:
            p, qmin, qmax = parse_fmt(fmt)
            if p < pmin:
                continue
            refused = refusal(name, fmt)
            if refused:
                replaced = fitting_format(name, fmt, extended)
                if replaced is None:
                    errors.append("%s: the interpreter refuses %s (%s), and no format of the "
                                  "same precision with its exponents moved up accepts it"
                                  % (name, fmt, refused))
                    continue
                fmt, refused = replaced, "replaces %s, where %s" % (fmt, refused.split(": ")[0]
                                                                    + " is not a number")
                p, qmin, qmax = parse_fmt(fmt)
            if (fmt, tuple(restrict)) in seen:
                continue
            if extended and qmin + qmax != 3 - 2 * p:
                errors.append("%s: %s is not of the shape qmin + qmax = 3 - 2p of the extended "
                              "domain" % (name, fmt))
                continue
            seen.add((fmt, tuple(restrict)))
            why = []
            if p == pmin:
                why.append("p = min_precision")
            elif p <= max(pmin, 2) + 1:
                why.append("p = min_precision + %d" % (p - pmin))
            # The exponent range, or in the extended domain the number of exponents.
            if (qmax - qmin if extended else (qmin, qmax)) == (
                    qmax0 - qmin0 if extended else (qmin0, qmax0)):
                if p == qp:
                    why.append("the quick tier's format")
                elif p > qp:
                    why.append("quick tier + %d bit%s" % (p - qp, "s" if p - qp > 1 else ""))
                else:
                    why.append("the quick tier's " + ("number of exponents" if extended
                                                       else "exponent range"))
            else:
                why.append("another " + ("number of exponents" if extended else "exponent range"))
            if restrict:
                why.append("restricted")
            if refused:
                why.append(refused)
            plan.append({"kernel": name, "format": fmt, "restrict": list(restrict),
                         "why": ", ".join(why),
                         "domain": "extended" if extended else "finite"})
    return plan, errors


def enum_key(e):
    key = "%s__%s" % (e["kernel"], e["format"].replace(":", "_"))
    if e["restrict"]:
        key += "__r" + hashlib.sha1(",".join(e["restrict"]).encode()).hexdigest()[:10]
    if e.get("maxlen") is not None:
        key += "__L%d" % e["maxlen"]
    return key


def gen_extra(e):
    """The arguments of gen for an enumeration beyond its kernel and format: the restrictions,
    and for a fold the largest length."""
    out = []
    for r in e["restrict"]:
        out += ["--restrict", r]
    if e.get("maxlen") is not None:
        out += ["--max-length", str(e["maxlen"])]
    return out


def gen_total(e):
    cmd = [PY, ORACLE, "gen", e["kernel"], e["format"], "--exhaustive", "--total"] + gen_extra(e)
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    m = re.match(r"(\d+) enumeration indices", out.stdout)
    if out.returncode != 0 or not m:
        raise RuntimeError("gen --total failed for %s: %s" % (" ".join(cmd[2:]),
                                                             (out.stderr or out.stdout).strip()))
    return int(m.group(1))


def sized_plan(plan, cache_path=None):
    cache = {}
    if cache_path and os.path.exists(cache_path):
        with open(cache_path, encoding="utf-8") as f:
            cache = json.load(f)
    for e in plan:
        k = enum_key(e)
        if k not in cache:
            cache[k] = gen_total(e)
        e["total"] = cache[k]
    if cache_path:
        write_json(cache_path, cache)
    return plan


# --- The plan of the emulated part (begin) --------------------------------------------------------
#
# The kernels printed for the emulated limb type (tests/emulated/runner.cpp: the C++ of the scalar
# kernels on an integer arithmetic of the format), judged by the oracle against gen/claims.json in
# the formats of the statements (architecture.md, "The formats of the statements": qmax >= 1, qmin =
# 3 - qmax - 2p) of precision 8 to 11 with the smallest exponent range, qmax = 1: fp:8:-14:1,
# fp:9:-16:1, fp:10:-18:1, fp:11:-20:1 (the bounds of two-limb folds, whose counts must reach the
# limit of their mask, about 2^(2p-2), in qmax = 16: EMULATED_QMAX). Every operand where the
# enumeration has at most EMULATED_EXHAUSTIVE indices: every kernel that reads one limb, at every
# precision; at precision 8 every kernel of two limbs (two numbers, 19 million; a pair, an interval
# or a ball of one limb, 2 to 10 million). EMULATED_CASES random cases of every stratum of the
# oracle's generator otherwise (gen --seed), and EMULATED_FOLD_CASES random arrays of up to
# EMULATED_FOLD_LENGTH elements of each fold, in every order. Only those enumerations are sized
# (gen --exhaustive --total, which counts the pairs one by one: 11 seconds at precision 8 on the
# Linux machine, 60 at precision 9, about five times more per bit): two numbers at precision 9 are
# 95 million cases, a kernel of three limbs at precision 8 more than 4 353^2 x 2 177 = 4 x 10^10.
# The pairs of precision 9 (12 million) would fit the threshold and are left to random cases, the
# price of sizing them. The guards of the emulated tier hold every series
# (crosscheck_guards.py --emulated). The sizes and rates are in docs/developer/testing.md, "The
# emulated formats".
EMULATED_PRECISIONS = (8, 9, 10, 11)
EMULATED_QMAX = {"bound_sum_2": 16, "bound_dot_2": 16}
EMULATED_EXHAUSTIVE = 20_000_000
EMULATED_CASES = 500_000
EMULATED_FOLD_CASES = 20_000
EMULATED_FOLD_LENGTH = 256


def emulated_format(name, p):
    qmax = EMULATED_QMAX.get(name, 1)
    return "fp:%d:%d:%d" % (p, 3 - qmax - 2 * p, qmax)


def input_limbs(k):
    """The limbs of a kernel's inputs that are not masks."""
    return sum(i.get("limbs", 1) for i in k.get("inputs", []) if i.get("type") != "mask")


def emulated_plan(kernels, folds, only=None, cache_path=None, match=None):
    """[{kernel, format, restrict, mode, total, why, domain, part}]: the emulated part, each entry
    exhaustive (total the enumeration's indices) or random (total its cases), sized with the
    oracle's gen --exhaustive --total (cached in CACHE_PATH) for the kernels of at most two limbs;
    with MATCH, only the entries whose 'KERNEL FORMAT' it matches (re.search)."""
    cache = {}
    if cache_path and os.path.exists(cache_path):
        cache = read_json(cache_path)
    plan = []
    for k in kernels:
        name = k["name"]
        if only and name not in only:
            continue
        limbs = input_limbs(k)
        for p in EMULATED_PRECISIONS:
            if (k.get("min_precision") or 1) > p:
                continue
            fmt = emulated_format(name, p)
            if match and not re.search(match, "%s %s" % (name, fmt)):
                continue
            e = {"part": "emulated", "kernel": name, "format": fmt, "restrict": [],
                 "domain": k.get("domain") or "finite"}
            total = None
            if limbs == 1 or (limbs == 2 and p == EMULATED_PRECISIONS[0]):
                key = enum_key(e)
                if key not in cache:
                    cache[key] = gen_total(e)
                total = cache[key]
            if total is not None and total <= EMULATED_EXHAUSTIVE:
                e.update(mode="exhaustive", total=total, why="every operand (%s)" % (
                    "one limb" if limbs == 1 else "%s indices" % "{:,}".format(total)))
            else:
                e.update(mode="random", total=EMULATED_CASES, why="random cases, every stratum (%s)" % (
                    "%d limbs" % limbs if total is None else "%s indices" % "{:,}".format(total)))
            plan.append(e)
    for f in folds:
        name = f["name"]
        if only and name not in only:
            continue
        for p in EMULATED_PRECISIONS:
            if (f.get("min_precision") or 1) > p or (
                    match and not re.search(match, "%s %s" % (name, emulated_format(name, p)))):
                continue
            plan.append({"part": "emulated", "kernel": name, "format": emulated_format(name, p),
                         "restrict": [], "domain": f.get("domain") or "finite", "mode": "random",
                         "total": EMULATED_FOLD_CASES, "maxlen": EMULATED_FOLD_LENGTH,
                         "why": "random arrays up to %d elements, every order" % EMULATED_FOLD_LENGTH})
    if cache_path:
        write_json(cache_path, cache)
    return plan


def emu_key(e):
    """The key of an entry of the emulated part (its directory under WORK/emulated)."""
    return "emulated__%s__%s" % (enum_key(e), e["mode"])


def emulated_gen(e, seed, start, count):
    """The oracle's gen for a chunk of an entry of the emulated part."""
    cmd = [PY, ORACLE, "gen", e["kernel"], e["format"]]
    if e["mode"] == "exhaustive":
        cmd.append("--exhaustive")
    else:
        cmd += ["--seed", seed]
    cmd += ["--start", str(start), "--count", str(count)]
    if e.get("maxlen") is not None:
        cmd += ["--max-length", str(e["maxlen"])]
    return cmd


def emulated_runner(a, work, env):
    """The emulated runner of a run: --emulated-runner, or kairn-emulated-runner built in the first
    --build (with the fix-ups inline: the full tier runs both forms and compares their bytes)."""
    if a.emulated_runner:
        return os.path.abspath(a.emulated_runner)
    if not a.build:
        sys.exit("brute: the emulated part needs --emulated-runner PATH or a --build NAME=COMPILER")
    name, _, cxx = a.build[0].partition("=")
    bdir = os.path.join(work, "builds", name)
    build_one(work, name, bdir, cxx, a.generator, a.cmake_arg or [], a.jobs, env, ["kairn-emulated-runner"])
    exe = ".exe" if WINDOWS else ""
    found = sorted(glob.glob(os.path.join(bdir, "tests", "**", "kairn-emulated-runner" + exe), recursive=True))
    if not found:
        sys.exit("brute: no kairn-emulated-runner in %s" % bdir)
    return found[0]
# --- The plan of the emulated part (end) ----------------------------------------------------------


def bins_of(plan, n, key=enum_key):
    """A deterministic split of the enumerations into n bins of about equal size (largest first,
    each into the lightest bin), so that machines can share the plan."""
    load = [0] * n
    out = {}
    for e in sorted(plan, key=lambda e: (-e["total"], key(e))):
        b = min(range(n), key=lambda i: (load[i], i))
        load[b] += e["total"]
        out[key(e)] = b
    return out, load


def parse_ranges(text, n=None):
    """'0-5,7' -> {0,1,2,3,4,5,7}."""
    s = set()
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            s.update(range(int(a), int(b) + 1))
        else:
            s.add(int(part))
    if n is not None and any(i < 0 or i >= n for i in s):
        raise ValueError("%s is not within 0-%d" % (text, n - 1))
    return s


# --- Small helpers ---------------------------------------------------------------------------------

def write_json(path, data, compact=False):
    tmp = path + ".tmp%d" % os.getpid()
    with open(tmp, "w", encoding="utf-8") as f:
        if compact:
            json.dump(data, f, separators=(",", ":"), sort_keys=False)
        else:
            json.dump(data, f, indent=1, sort_keys=False)
        f.write("\n")
    os.replace(tmp, path)


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


def log(msg):
    print("[%s] %s" % (time.strftime("%H:%M:%S"), msg), flush=True)


def safe(name):
    return re.sub(r"[^A-Za-z0-9_.-]", "_", name)


def frac_gt(a, b):
    """a > b for fractions given as (num, den) with den > 0."""
    return a[0] * b[1] > b[0] * a[1]


def frac_dec(r, digits=10):
    if r is None:
        return None
    n, d = int(r[0]), int(r[1])
    if n == 0:
        return "0"
    ctx = decimal.Context(prec=digits)
    return format(ctx.divide(decimal.Decimal(n), decimal.Decimal(d)), "g")


def as_frac(v):
    return None if v is None else (int(v[0]), int(v[1]))


# --- The machine -----------------------------------------------------------------------------------

def cpu_name():
    try:
        if LINUX:
            with open("/proc/cpuinfo", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("model name"):
                        return line.split(":", 1)[1].strip()
        elif sys.platform == "darwin":
            return subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"],
                                  capture_output=True, text=True, timeout=30).stdout.strip()
        elif WINDOWS:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as k:
                return winreg.QueryValueEx(k, "ProcessorNameString")[0].strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return platform.processor() or "unknown"


def machine_info(cpus):
    return {"system": platform.system(), "release": platform.release(),
            "machine": platform.machine(), "cpu": cpu_name(),
            "logical_cpus": os.cpu_count(), "cpus_used": cpus,
            "python": platform.python_version()}


def confine(cpus, nice):
    """Pin this process (and so everything it starts) to the CPUs, at a lower priority."""
    if cpus:
        ids = sorted(parse_ranges(cpus))
        if LINUX:
            os.sched_setaffinity(0, ids)
        elif WINDOWS:
            import ctypes
            k32 = ctypes.WinDLL("kernel32", use_last_error=True)
            k32.GetCurrentProcess.restype = ctypes.c_void_p
            mask = sum(1 << i for i in ids)
            if not k32.SetProcessAffinityMask(ctypes.c_void_p(k32.GetCurrentProcess()),
                                              ctypes.c_size_t(mask)):
                sys.exit("brute: SetProcessAffinityMask failed (%d)" % ctypes.get_last_error())
        else:
            sys.exit("brute: --cpus is not supported on this system")
    if nice:
        if WINDOWS:
            import ctypes
            k32 = ctypes.WinDLL("kernel32", use_last_error=True)
            k32.GetCurrentProcess.restype = ctypes.c_void_p
            # BELOW_NORMAL_PRIORITY_CLASS, which the processes it starts inherit.
            k32.SetPriorityClass(ctypes.c_void_p(k32.GetCurrentProcess()), 0x4000)
        else:
            os.nice(nice)


_JOB = None


def windows_job():
    """Put this process into a job object that kills every process in it when its last handle
    closes, that is when this process ends however it ends; the processes it starts inherit it."""
    global _JOB
    import ctypes
    from ctypes import wintypes
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)

    class Basic(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64),
                    ("PerJobUserTimeLimit", ctypes.c_int64), ("LimitFlags", wintypes.DWORD),
                    ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t),
                    ("ActiveProcessLimit", wintypes.DWORD), ("Affinity", ctypes.c_size_t),
                    ("PriorityClass", wintypes.DWORD), ("SchedulingClass", wintypes.DWORD)]

    class Io(ctypes.Structure):
        _fields_ = [(n, ctypes.c_uint64) for n in (
            "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
            "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

    class Extended(ctypes.Structure):
        _fields_ = [("BasicLimitInformation", Basic), ("IoInfo", Io),
                    ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                    ("PeakProcessMemoryUsed", ctypes.c_size_t),
                    ("PeakJobMemoryUsed", ctypes.c_size_t)]

    k32.CreateJobObjectW.restype = wintypes.HANDLE
    k32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    k32.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p,
                                            wintypes.DWORD]
    k32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    k32.GetCurrentProcess.restype = wintypes.HANDLE
    job = k32.CreateJobObjectW(None, None)
    if not job:
        sys.exit("brute: CreateJobObject failed (%d)" % ctypes.get_last_error())
    info = Extended()
    info.BasicLimitInformation.LimitFlags = 0x2000          # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not k32.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info)):
        sys.exit("brute: SetInformationJobObject failed (%d)" % ctypes.get_last_error())
    if not k32.AssignProcessToJobObject(job, k32.GetCurrentProcess()):
        sys.exit("brute: AssignProcessToJobObject failed (%d)" % ctypes.get_last_error())
    _JOB = job


def _pdeathsig():
    import ctypes
    libc = ctypes.CDLL(None, use_errno=True)
    libc.prctl(1, signal.SIGKILL)                           # PR_SET_PDEATHSIG


LIVE = set()


def popen(args, **kw):
    if LINUX:
        kw["preexec_fn"] = _pdeathsig
    p = subprocess.Popen(args, **kw)
    LIVE.add(p)
    return p


def kill_all():
    for p in list(LIVE):
        if p.poll() is None:
            try:
                p.kill()
            except OSError:
                pass
    for p in list(LIVE):
        try:
            p.wait(timeout=30)
        except subprocess.TimeoutExpired:
            pass
        LIVE.discard(p)


STOP = []


def _on_signal(signum, _frame):
    STOP.append(signum)


def run_step(name, cmd, env, timeout, logpath):
    """One build step, with a timeout; on a timeout the step's process is killed."""
    with open(logpath, "w", encoding="utf-8", errors="replace") as f:
        p = popen(cmd, stdout=f, stderr=subprocess.STDOUT, env=env, cwd=REPO)
        t0 = time.time()
        while p.poll() is None:
            if STOP:
                kill_all()
                sys.exit("brute: interrupted during %s" % name)
            if time.time() - t0 > timeout:
                kill_all()
                sys.exit("brute: %s timed out after %d s; see %s" % (name, timeout, logpath))
            time.sleep(0.2)
        LIVE.discard(p)
    if p.returncode != 0:
        with open(logpath, encoding="utf-8", errors="replace") as f:
            tail = f.read()[-4000:]
        sys.exit("brute: %s failed (%d):\n%s" % (name, p.returncode, tail))


def env_from_script(script):
    """The environment after a batch file such as vcvars64.bat (Windows) or a shell script."""
    if WINDOWS:
        out = subprocess.run('cmd /d /c "call "%s" >nul && set"' % script, capture_output=True,
                             text=True, timeout=300)
    else:
        out = subprocess.run(["sh", "-c", '. "$0" >/dev/null && env', script],
                             capture_output=True, text=True, timeout=300)
    env = {}
    for line in out.stdout.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            env[k] = v
    if out.returncode != 0 or not env:
        sys.exit("brute: the environment script %s failed: %s" % (script, out.stderr[-2000:]))
    return env


# --- Builds and runners ----------------------------------------------------------------------------

FLAG = re.compile(r"^(-O\w*|-std[=:]\S+|-m\S+|-f\S+|-D\S+|-g\S*|-W\S*|-pedantic|"
                  r"/O\w+|/fp:\S+|/arch:\S+|/std:\S+|/EH\w+|/M[DT]d?|/GR-?|/D\S+|/W\d|/permissive-|"
                  r"/Z\w+|/utf-8|/clang:\S+|--gcc-install-dir=\S+)$")


def build_flags(command):
    """The options of a compile command that matter, without any path."""
    words = command.split() if isinstance(command, str) else command
    keep = []
    for w in words:
        if FLAG.match(w) and "/" not in w[1:] and "\\" not in w:
            keep.append(w)
        elif w.startswith("--gcc-install-dir="):
            keep.append("--gcc-install-dir=(GCC's)")
    return " ".join(keep)


def runner_target(target):
    """(packed, suffix) for the target name of a runner of the library, None for any other name.

    The runners are kairn-gen-runner and kairn-gen-packed-runner, each with an optional suffix
    naming its flags. A target whose suffix ends in "fault" is not one of them: it is a runner
    built with a kernel that is wrong on purpose (tests/CMakeLists.txt:
    kairn-gen-packed-runner-lane-fault, for crosscheck.lanes.fault.*), which an enumeration must
    never take for the library."""
    m = re.match(r"^kairn-gen-(packed-)?runner(?:-(.+))?$", target)
    if not m or (m.group(2) and re.search(r"(^|-)fault$", m.group(2))):
        return None
    return bool(m.group(1)), m.group(2)


def compiler_of(builddir):
    for f in glob.glob(os.path.join(builddir, "CMakeFiles", "*", "CMakeCXXCompiler.cmake")):
        with open(f, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        cid = re.search(r'set\(CMAKE_CXX_COMPILER_ID "([^"]*)"', text)
        ver = re.search(r'set\(CMAKE_CXX_COMPILER_VERSION "([^"]*)"', text)
        return "%s %s" % (cid.group(1) if cid else "?", ver.group(1) if ver else "?")
    return "unknown"


def cache_value(builddir, name):
    path = os.path.join(builddir, "CMakeCache.txt")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith(name + ":"):
                return line.split("=", 1)[1].strip()
    return None


def default_fixup_call(compiler):
    """KAIRN_GEN_FIXUP_CALL as include/kairn/gen/prelude.hpp sets it when nothing defines it:
    1 (the fix-up of a scalar full kernel a function of its own) with Clang on AArch64, 0
    (inline) elsewhere. The builds are native, so the target is this machine."""
    clang = compiler.split()[0] in ("Clang", "AppleClang")
    return 1 if clang and platform.machine().lower() in ("arm64", "aarch64") else 0


def build(work, specs, generator, cmake_args, jobs, env, fixup_forms="both"):
    """Configure (once) and build each --build NAME=CXX; return the runners they produce.

    The quick tier's runners have the compiler's own form of the scalar fix-ups
    (KAIRN_GEN_FIXUP_CALL, prelude.hpp). With fixup_forms "both", each build NAME has a second
    one, NAME-fixup-call or NAME-fixup-inline, configured with the other form defined
    (CXXFLAGS=-DKAIRN_GEN_FIXUP_CALL=0 or 1), of which only the scalar runners are built and
    run: the packed kernels have no such branch (gen/kairn_gen/cpp.py)."""
    runners = []
    os.makedirs(os.path.join(work, "logs"), exist_ok=True)
    for spec in specs:
        name, _, cxx = spec.partition("=")
        if not name or not cxx or safe(name) != name:
            sys.exit("brute: --build wants NAME=COMPILER, NAME of letters, digits, . _ -: %r"
                     % spec)
        bdir = os.path.join(work, "builds", name)
        build_one(work, name, bdir, cxx, generator, cmake_args, jobs, env, None)
        main = discover(name, bdir)
        dflt = default_fixup_call(main[0]["compiler"])
        for r in main:
            if r["kind"] == "scalar":
                r["fixup"] = "call" if dflt else "inline"
                r["fixup_default"] = True
        runners += main
        if fixup_forms != "both":
            continue
        other = 1 - dflt
        oname = "%s-fixup-%s" % (name, "call" if other else "inline")
        odir = os.path.join(work, "builds", oname)
        oenv = dict(env)
        oenv["CXXFLAGS"] = (env.get("CXXFLAGS", "") + " -DKAIRN_GEN_FIXUP_CALL=%d" % other).strip()
        targets = [r["target"] for r in main if r["kind"] == "scalar"]
        build_one(work, oname, odir, cxx, generator, cmake_args, jobs, oenv, targets)
        extra = [r for r in discover(oname, odir) if r["kind"] == "scalar"]
        for r in extra:
            r["fixup"] = "call" if other else "inline"
            r["fixup_default"] = False
            if "-DKAIRN_GEN_FIXUP_CALL=%d" % other not in r["flags"].split():
                sys.exit("brute: the runner %s was not compiled with -DKAIRN_GEN_FIXUP_CALL=%d "
                         "(its flags: %s)" % (r["id"], other, r["flags"]))
        runners += extra
    if not runners:
        sys.exit("brute: the builds produced no runner")
    return runners


def build_one(work, name, bdir, cxx, generator, cmake_args, jobs, env, targets):
    if not os.path.exists(os.path.join(bdir, "CMakeCache.txt")):
        cmd = ["cmake", "-S", REPO, "-B", bdir, "-DCMAKE_BUILD_TYPE=Release",
               "-DCMAKE_CXX_COMPILER=" + cxx, "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON"]
        if generator:
            cmd += ["-G", generator]
        cmd += cmake_args
        log("configure %s: %s%s" % (name, " ".join(cmd[1:2] + cmd[5:]),
                                    " (CXXFLAGS=%s)" % env["CXXFLAGS"] if env.get("CXXFLAGS")
                                    else ""))
        run_step("configure " + name, cmd, env, 900,
                 os.path.join(work, "logs", "configure-%s.log" % name))
    log("build %s" % name)
    cmd = ["cmake", "--build", bdir, "--parallel", str(max(1, jobs))]
    if cache_value(bdir, "CMAKE_CONFIGURATION_TYPES"):
        cmd += ["--config", "Release"]
    if targets:
        cmd += ["--target"] + targets
    run_step("build " + name, cmd, env, 3600, os.path.join(work, "logs", "build-%s.log" % name))


def discover(name, bdir):
    backend = "neon" if cache_value(bdir, "KAIRN_TESTS_NEON") in ("1", "TRUE", "ON") else "avx2"
    commands = {}
    cc = os.path.join(bdir, "compile_commands.json")
    if os.path.exists(cc):
        for e in read_json(cc):
            text = e.get("command") or " ".join(e.get("arguments", []))
            m = re.search(r"CMakeFiles[/\\]([^/\\]+)\.dir[/\\]", e.get("output", "") or text)
            if m:
                commands[m.group(1)] = text
    compiler = compiler_of(bdir)
    out = []
    exe = ".exe" if WINDOWS else ""
    for path in sorted(glob.glob(os.path.join(bdir, "tests", "**", "kairn-gen-*runner*" + exe),
                                 recursive=True)):
        target = os.path.basename(path)[:len(os.path.basename(path)) - len(exe)]
        named = runner_target(target)
        if not named or not os.path.isfile(path) or (not WINDOWS and not os.access(path, os.X_OK)):
            continue
        kind = "packed" if named[0] else "scalar"
        label = (backend if kind == "packed" else "cxx") + ("-" + named[1] if named[1] else "")
        out.append({"id": "%s/%s" % (name, label), "build": name, "label": label, "kind": kind,
                    "backend": backend if kind == "packed" else "scalar", "target": target,
                    "setting": named[1] or "the build's flags", "compiler": compiler,
                    "flags": build_flags(commands.get(target, "")), "path": path})
    if not out:
        sys.exit("brute: no runner in %s" % bdir)
    return out


# --- Tasks -----------------------------------------------------------------------------------------

class Task:
    weight = 1

    def __init__(self, sched):
        self.s = sched
        self.procs = []
        self.files = []
        self.t0 = None

    def start(self):
        self.t0 = time.time()

    def done(self):
        return all(p.poll() is not None for p in self.procs)

    def kill(self):
        for p in self.procs:
            if p.poll() is None:
                try:
                    p.kill()
                except OSError:
                    pass
        for p in self.procs:
            p.wait()
        self.close()

    def close(self):
        for f in self.files:
            try:
                f.close()
            except OSError:
                pass
        self.files = []
        for p in self.procs:
            LIVE.discard(p)
        for path in getattr(self, "logs", []):
            if os.path.exists(path) and os.path.getsize(path) == 0:
                os.remove(path)

    def errlog(self, name):
        path = os.path.join(self.s.work, "logs", safe(name) + ".err")
        f = open(path, "w", encoding="utf-8", errors="replace")
        self.files.append(f)
        self.logs = getattr(self, "logs", []) + [path]
        return path, f


def summary_problems(summary, fail_on_suspicious):
    """Everything in an oracle summary that makes the run a finding, and examples of it."""
    t = {}
    examples = []
    for k in summary.get("keys", []):
        for name, n in k["stats"]["counts"].items():
            t[name] = t.get(name, 0) + n
        for kind in ("failure", "invalid", "suspicious"):
            for line, why in k["stats"]["examples"].get(kind, []):
                if kind != "suspicious" or fail_on_suspicious:
                    examples.append({"kind": kind, "line": line, "why": why})
    why = []
    if t.get("failed"):
        why.append("%d cases failed a claim" % t["failed"])
    if t.get("invalid"):
        why.append("%d invalid cases" % t["invalid"])
    if fail_on_suspicious and t.get("suspicious"):
        why.append("%d suspicious non-finite results" % t["suspicious"])
    if t.get("out_of_scope"):
        why.append("%d cases out of scope" % t["out_of_scope"])
    for e in summary.get("stream_errors", []):
        why.append("stream error: %s" % e)
    for e in summary.get("claims_errors", []):
        why.append("claims error: %s" % e)
    return why, examples[:10], t


class GenTask(Task):
    """One unit of random cases, written to a file that every runner then reads."""

    def __init__(self, sched, unit):
        super().__init__(sched)
        self.unit = unit

    def start(self):
        super().start()
        u = self.unit
        self.tmp = u.req + ".tmp"
        out = open(self.tmp, "wb")
        self.files.append(out)
        _, err = self.errlog("gen-%s-%s%s-%d" % (u.kernel, u.format, u.group, u.start))
        self.procs = [popen([PY, ORACLE, "gen", u.kernel, u.format, "--seed", self.s.seed,
                             "--start", str(u.start), "--count", str(u.count)]
                            + fold_stream_args(u),
                            stdout=out, stderr=err, cwd=REPO)]

    def finish(self):
        self.close()
        rc = self.procs[0].returncode
        if rc != 0:
            return ["gen exited with %d" % rc]
        os.replace(self.tmp, self.unit.req)
        self.unit.generated = True
        return []


class CheckTask(Task):
    """One runner on one unit, judged by the oracle."""

    def __init__(self, sched, unit, runner):
        super().__init__(sched)
        self.unit, self.runner = unit, runner

    def start(self):
        super().start()
        u, r = self.unit, self.runner
        self.out = u.result(r["id"])
        os.makedirs(os.path.dirname(self.out), exist_ok=True)
        self.tmp = self.out + ".tmp"
        if os.path.exists(self.tmp):
            os.remove(self.tmp)
        inp = open(u.req, "rb")
        self.files.append(inp)
        _, err = self.errlog("check-%s-%s-%d-%s" % (u.kernel, u.format, u.start, r["id"]))
        check = [PY, ORACLE, "check", "--json", self.tmp, "--quiet"]
        if fails_on_suspicious(u.kernel, u.format):
            check.append("--fail-on-suspicious")
        run = popen([r["path"]], stdin=inp, stdout=subprocess.PIPE, stderr=err)
        chk = popen(check, stdin=run.stdout, stdout=subprocess.DEVNULL, stderr=err, cwd=REPO)
        run.stdout.close()
        self.procs = [run, chk]

    def finish(self):
        self.close()
        rc_r, rc_c = self.procs[0].returncode, self.procs[1].returncode
        u, r = self.unit, self.runner
        why = []
        if rc_r != 0:
            why.append("runner exited with %d" % rc_r)
        try:
            summary = read_json(self.tmp)
        except (OSError, ValueError) as ex:
            summary = None
            why.append("no summary from check (exit %d): %s" % (rc_c, ex))
        examples = []
        if summary is not None:
            more, examples, _ = summary_problems(summary,
                                                 fails_on_suspicious(u.kernel, u.format))
            why += more
            if rc_c not in (0, 1) or (rc_c == 1 and not more):
                why.append("check exited with %d" % rc_c)
        if why:
            self.s.finding("compiled", why, examples, kernel=u.kernel, format=u.format,
                           runner=r["id"], seed=self.s.seed, start=u.start, count=u.count,
                           reproduce=reproduce_random(u.kernel, u.format, self.s.seed, r,
                                                      fold_stream_args(u)))
            self.s.stopped.add((u.kernel, u.format, r["id"]))
            if os.path.exists(self.tmp):
                os.replace(self.tmp, self.out + ".failed")
            return why
        os.replace(self.tmp, self.out)
        return []


class InterpTask(Task):
    """One chunk of an enumeration through the generator's interpreter."""
    weight = 2
    part = "interp"

    def __init__(self, sched, enum, start, count):
        super().__init__(sched)
        self.e, self.start_i, self.count = enum, start, count

    def start(self):
        super().start()
        e = self.e
        d = os.path.join(self.s.work, "interp", enum_key(e))
        os.makedirs(d, exist_ok=True)
        self.out = os.path.join(d, "c%012d.json" % self.start_i)
        self.tmp = self.out + ".tmp"
        if os.path.exists(self.tmp):
            os.remove(self.tmp)
        _, err = self.errlog("interp-%s-%d" % (enum_key(e), self.start_i))
        gen = [PY, ORACLE, "gen", e["kernel"], e["format"], "--exhaustive",
               "--start", str(self.start_i), "--count", str(self.count)] + gen_extra(e)
        check = [PY, ORACLE, "check", "--json", self.tmp, "--quiet"]
        if fails_on_suspicious(e["kernel"], e["format"]):
            check.append("--fail-on-suspicious")
        g = popen(gen, stdout=subprocess.PIPE, stderr=err, cwd=REPO)
        i = popen([PY, KAIRN_GEN, "interp"], stdin=g.stdout, stdout=subprocess.PIPE, stderr=err,
                  cwd=REPO)
        g.stdout.close()
        c = popen(check, stdin=i.stdout, stdout=subprocess.DEVNULL, stderr=err, cwd=REPO)
        i.stdout.close()
        self.procs = [g, i, c]

    def finish(self):
        self.close()
        rc = [p.returncode for p in self.procs]
        e = self.e
        why = []
        if rc[0] != 0:
            why.append("gen exited with %d" % rc[0])
        if rc[1] != 0:
            why.append("the interpreter exited with %d" % rc[1])
        examples = []
        try:
            summary = read_json(self.tmp)
        except (OSError, ValueError) as ex:
            summary = None
            why.append("no summary from check (exit %d): %s" % (rc[2], ex))
        if summary is not None:
            more, examples, _ = summary_problems(summary,
                                                 fails_on_suspicious(e["kernel"], e["format"]))
            why += more
            if rc[2] not in (0, 1) or (rc[2] == 1 and not more):
                why.append("check exited with %d" % rc[2])
        if why:
            self.s.finding("interp", why, examples, kernel=e["kernel"], format=e["format"],
                           restrict=e["restrict"], start=self.start_i, count=self.count,
                           reproduce=reproduce_exhaustive(e))
            self.s.stopped_enums.add(enum_key(e))
            if os.path.exists(self.tmp):
                os.replace(self.tmp, self.out + ".failed")
            return why
        os.replace(self.tmp, self.out)
        return []


class EmulatedTask(InterpTask):
    """One chunk of an entry of the emulated part: the oracle's gen (every operand, or random cases
    of the run's seed), the emulated runner, the oracle's check."""
    part = "emulated"

    def start(self):
        Task.start(self)
        e = self.e
        d = os.path.join(self.s.work, "emulated", emu_key(e))
        os.makedirs(d, exist_ok=True)
        self.out = os.path.join(d, "c%012d.json" % self.start_i)
        self.tmp = self.out + ".tmp"
        if os.path.exists(self.tmp):
            os.remove(self.tmp)
        _, err = self.errlog("emulated-%s-%d" % (emu_key(e), self.start_i))
        check = [PY, ORACLE, "check", "--json", self.tmp, "--quiet"]
        if fails_on_suspicious(e["kernel"], e["format"]):
            check.append("--fail-on-suspicious")
        g = popen(emulated_gen(e, self.s.seed, self.start_i, self.count), stdout=subprocess.PIPE,
                  stderr=err, cwd=REPO)
        r = popen([self.s.emulated_runner], stdin=g.stdout, stdout=subprocess.PIPE, stderr=err)
        g.stdout.close()
        c = popen(check, stdin=r.stdout, stdout=subprocess.DEVNULL, stderr=err, cwd=REPO)
        r.stdout.close()
        self.procs = [g, r, c]

    def finish(self):
        self.close()
        rc = [p.returncode for p in self.procs]
        e = self.e
        why = []
        if rc[0] != 0:
            why.append("gen exited with %d" % rc[0])
        if rc[1] != 0:
            why.append("the emulated runner exited with %d" % rc[1])
        examples = []
        try:
            summary = read_json(self.tmp)
        except (OSError, ValueError) as ex:
            summary = None
            why.append("no summary from check (exit %d): %s" % (rc[2], ex))
        if summary is not None:
            more, examples, _ = summary_problems(summary, fails_on_suspicious(e["kernel"], e["format"]))
            why += more
            if rc[2] not in (0, 1) or (rc[2] == 1 and not more):
                why.append("check exited with %d" % rc[2])
        if why:
            gen = " ".join(emulated_gen(e, self.s.seed, "INDEX", 1)[1:]).replace(ORACLE, "oracle/kairn-oracle")
            self.s.finding("emulated", why, examples, key=emu_key(e), kernel=e["kernel"],
                           format=e["format"], mode=e["mode"], start=self.start_i, count=self.count,
                           reproduce="python3 %s | %s | python3 oracle/kairn-oracle check%s   (INDEX from the "
                                     "line's tag; RUNNER the emulated runner, kairn-emulated-runner)"
                                     % (gen, "RUNNER", " --fail-on-suspicious" if fails_on_suspicious(
                                         e["kernel"], e["format"]) else ""))
            self.s.stopped_enums.add(emu_key(e))
            if os.path.exists(self.tmp):
                os.replace(self.tmp, self.out + ".failed")
            return why
        os.replace(self.tmp, self.out)
        return []


def reproduce_random(kernel, fmt, seed, runner, extra=()):
    check = "python3 oracle/kairn-oracle check"
    if fails_on_suspicious(kernel, fmt):
        check += " --fail-on-suspicious"
    return ("python3 oracle/kairn-oracle gen %s %s --seed %s%s --start INDEX --count 1 | "
            "BUILD/tests/%s | %s   (BUILD: the build %s, runner %s; INDEX from the line's tag)"
            % (kernel, fmt, seed, "".join(" " + w for w in extra), runner["target"], check,
               runner["build"], runner["id"]))


def fold_stream_args(unit):
    """gen's arguments of a fold's unit beyond seed and indices: its orders and largest length."""
    out = []
    if unit.orders:
        out += ["--orders", unit.orders]
    if unit.fold:
        out += ["--max-length", str(FOLD_LENGTH)]
    return out


def reproduce_exhaustive(e):
    restrict = "".join(" " + w for w in gen_extra(e))
    check = "python3 oracle/kairn-oracle check"
    if fails_on_suspicious(e["kernel"], e["format"]):
        check += " --fail-on-suspicious"
    return ("python3 oracle/kairn-oracle gen %s %s --exhaustive%s --start INDEX --count 1 | "
            "python3 gen/kairn-gen interp | %s   (INDEX from the line's tag)"
            % (e["kernel"], e["format"], restrict, check))


class Unit:
    def __init__(self, work, kernel, fmt, start, count, fold=False, group="", orders=None):
        self.kernel, self.format, self.start, self.count = kernel, fmt, start, count
        # A fold's unit is for one group of runners: the scalar ones (every order), or the
        # packed ones of a backend (the lane order of their register, orders lanes:W).
        self.fold, self.group, self.orders = fold, group, orders
        self.dir = os.path.join(work, "compiled", kernel, fmt)
        self.req = os.path.join(work, "streams", "%s-%s%s-%012d.req" % (
            kernel, fmt, "-" + group if group else "", start))
        self.generated = False
        self.pending = []           # runners still to judge it

    def result(self, rid):
        return os.path.join(self.dir, safe(rid), "u%012d.json" % self.start)


class Scheduler:
    def __init__(self, a, work, runners, enums, emus=(), emulated_runner=None):
        self.a = a
        self.work = work
        self.seed = a.seed
        self.runners = runners
        self.enums = enums
        self.emus = list(emus)
        self.emulated_runner = emulated_runner
        self.jobs = a.jobs
        self.stopped = set()
        self.stopped_enums = set()
        self.findings_path = os.path.join(work, "findings.jsonl")
        self.times = open(os.path.join(work, "times.jsonl"), "a", encoding="utf-8")
        self.n_findings = 0
        if os.path.exists(self.findings_path):
            with open(self.findings_path, encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        x = json.loads(line)
                        self.n_findings += 1
                        if x["part"] == "compiled":
                            self.stopped.add((x["kernel"], x["format"], x["runner"]))
                        else:
                            self.stopped_enums.add(x.get("key") or enum_key(x))
        self.folds = set(getattr(a, "fold_names", []))
        self.pairs = [(k, f) for k in list(a.kernel_names) + sorted(self.folds)
                      for f in ("binary64", "binary32")]
        self.stats = {"tasks": 0, "judged_cases": 0, "interp_cases": 0, "emulated_cases": 0}

    def timing(self, t, why):
        """The wall time of a finished pipeline, for the cases per second of the report."""
        x = {"s": round(time.time() - t.t0, 3)}
        if isinstance(t, InterpTask):
            x.update(part=t.part, enum=emu_key(t.e) if t.part == "emulated" else enum_key(t.e),
                     count=t.count)
        else:
            x.update(part="gen" if isinstance(t, GenTask) else "check", kernel=t.unit.kernel,
                     format=t.unit.format, count=t.unit.count)
            if isinstance(t, CheckTask):
                x["runner"] = t.runner["id"]
        if why:
            x["failed"] = True
        self.times.write(json.dumps(x, separators=(",", ":")) + "\n")
        self.times.flush()

    def finding(self, part, why, examples, **fields):
        x = dict(part=part, why=why, examples=examples, time=now_iso(), **fields)
        with open(self.findings_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(x) + "\n")
        self.n_findings += 1
        log("FINDING (%s): %s %s %s: %s" % (part, fields.get("kernel"), fields.get("format"),
                                            fields.get("runner") or ",".join(
                                                fields.get("restrict") or []), "; ".join(why)))
        for e in examples[:3]:
            log("    %s: %s" % (e["kind"], e["line"]))

    # The compiled part: units round-robin over (kernel, format), up to --cases per pair.
    def units(self):
        u = 0
        while True:
            start = u * self.a.chunk
            if self.a.cases is not None and start >= self.a.cases:
                return
            if all(all((k, f, r["id"]) in self.stopped for r in self.runners)
                   for k, f in self.pairs):
                return
            count = self.a.chunk if self.a.cases is None else min(self.a.chunk,
                                                                  self.a.cases - start)
            # A fold's case is an array of 265 elements on average: its units are a hundredth of
            # a kernel's, cases and cap alike, so that one unit takes about as long.
            fchunk = max(1, self.a.chunk // FOLD_CHUNK_DIVISOR)
            fstart = u * fchunk
            fcount = fchunk if self.a.cases is None else max(
                0, min(fchunk, self.a.cases // FOLD_CHUNK_DIVISOR - fstart))
            for k, f in self.pairs:
                if k in self.folds and fcount == 0:
                    continue
                if k not in self.folds:
                    groups = [(Unit(self.work, k, f, start, count), self.runners)]
                else:
                    groups = []
                    scalar = [r for r in self.runners if r["kind"] == "scalar"]
                    if scalar:
                        groups.append((Unit(self.work, k, f, fstart, fcount, True, "scalar"),
                                       scalar))
                    for be in sorted({r["backend"] for r in self.runners if r["kind"] == "packed"}):
                        W = packed_lanes(k, f, be)
                        rs = [r for r in self.runners if r["kind"] == "packed" and r["backend"] == be]
                        if W:
                            groups.append((Unit(self.work, k, f, fstart, fcount, True, be,
                                                "lanes:%d" % W), rs))
                for unit, rs in groups:
                    unit.pending = [r for r in rs if (k, f, r["id"]) not in self.stopped
                                    and not os.path.exists(unit.result(r["id"]))]
                    if unit.pending:
                        yield unit
            u += 1

    def release(self, unit, runner, open_units):
        """The runner is done with the unit; the unit's file goes when every runner is."""
        if runner in unit.pending:
            unit.pending.remove(runner)
        if not unit.pending and unit in open_units:
            open_units.remove(unit)
            if os.path.exists(unit.req):
                os.remove(unit.req)

    def interp_tasks(self):
        for e in self.enums:
            if enum_key(e) in self.stopped_enums:
                continue
            d = os.path.join(self.work, "interp", enum_key(e))
            for s in range(0, e["total"], self.a.interp_chunk):
                if enum_key(e) in self.stopped_enums:
                    break
                if os.path.exists(os.path.join(d, "c%012d.json" % s)):
                    continue
                yield InterpTask(self, e, s, min(self.a.interp_chunk, e["total"] - s))
        # The emulated part, after the interpreter's enumerations: chunks of --emulated-chunk
        # indices or cases (a hundredth of it for the arrays of a fold).
        for e in self.emus:
            if emu_key(e) in self.stopped_enums:
                continue
            d = os.path.join(self.work, "emulated", emu_key(e))
            chunk = self.a.emulated_chunk if e.get("maxlen") is None else \
                max(1, self.a.emulated_chunk // FOLD_CHUNK_DIVISOR)
            for s in range(0, e["total"], chunk):
                if emu_key(e) in self.stopped_enums:
                    break
                if os.path.exists(os.path.join(d, "c%012d.json" % s)):
                    continue
                yield EmulatedTask(self, e, s, min(chunk, e["total"] - s))

    def run(self, deadline):
        running = []
        used = 0
        unit_iter = self.units() if self.a.compiled else iter(())
        interp_iter = self.interp_tasks() if self.a.interp or self.a.emulated else iter(())
        next_interp = next(interp_iter, None)
        open_units = []             # generated or generating, with runners pending
        checks = []                 # CheckTasks ready to start
        last_report = time.time()
        t_start = time.time()
        while True:
            if STOP:
                log("interrupted (signal %s): killing %d running pipelines"
                    % (STOP[0], len(running)))
                for t in running:
                    t.kill()
                return 2
            # Reap.
            for t in [t for t in running if t.done()]:
                running.remove(t)
                used -= t.weight
                self.stats["tasks"] += 1
                if isinstance(t, CheckTask):
                    self.stats["judged_cases"] += t.unit.count
                if isinstance(t, InterpTask):
                    self.stats[t.part + "_cases"] += t.count
                why = t.finish()
                self.timing(t, why)
                if isinstance(t, GenTask):
                    if why:
                        self.finding("compiled", why, [], kernel=t.unit.kernel,
                                     format=t.unit.format, runner="(gen)", seed=self.seed,
                                     start=t.unit.start, count=t.unit.count, reproduce="")
                        for r in list(t.unit.pending):
                            self.stopped.add((t.unit.kernel, t.unit.format, r["id"]))
                            self.release(t.unit, r, open_units)
                    else:
                        for r in t.unit.pending:
                            checks.append(CheckTask(self, t.unit, r))
                elif isinstance(t, CheckTask):
                    self.release(t.unit, t.runner, open_units)
            # Timeouts: the pipeline is killed, and its series stopped.
            for t in [t for t in running if time.time() - t.t0 > self.a.task_timeout]:
                t.kill()
                running.remove(t)
                used -= t.weight
                why = ["timed out after %d s" % self.a.task_timeout]
                if isinstance(t, InterpTask):
                    key = emu_key(t.e) if t.part == "emulated" else enum_key(t.e)
                    self.finding(t.part, why, [], key=key, kernel=t.e["kernel"], format=t.e["format"],
                                 restrict=t.e["restrict"], start=t.start_i, count=t.count,
                                 reproduce="" if t.part == "emulated" else reproduce_exhaustive(t.e))
                    self.stopped_enums.add(key)
                    continue
                u = t.unit
                rid = t.runner["id"] if isinstance(t, CheckTask) else "(gen)"
                self.finding("compiled", why, [], kernel=u.kernel, format=u.format, runner=rid,
                             seed=self.seed, start=u.start, count=u.count, reproduce="")
                for r in ([t.runner] if isinstance(t, CheckTask) else list(u.pending)):
                    self.stopped.add((u.kernel, u.format, r["id"]))
                    self.release(u, r, open_units)
            # Start. A unit is generated while the runners still judge the ones before it, so
            # that no slot waits for a generator: when fewer checks are queued or coming than
            # there are slots, a generator goes first.
            before = deadline is None or time.time() < deadline
            # Generating a case can take three times as long as judging one (the comparisons),
            # so up to three units per round of the runners are generated at a time.
            n_r = max(1, len(self.runners))
            max_gens = max(2, -(-3 * self.jobs // n_r))
            max_open = max_gens + 2 + (-(-self.jobs // n_r))
            while used < self.jobs:
                task = None
                if before and next_interp is None:
                    gens = [t for t in running if isinstance(t, GenTask)]
                    coming = len(checks) + sum(len(t.unit.pending) for t in gens)
                    if len(gens) < max_gens and coming < self.jobs and len(open_units) < max_open:
                        unit = next(unit_iter, None)
                        if unit is not None:
                            open_units.append(unit)
                            task = GenTask(self, unit)
                # Judge what is generated: it frees the disk.
                while task is None and checks:
                    c = checks.pop(0)
                    if (c.unit.kernel, c.unit.format, c.runner["id"]) in self.stopped:
                        self.release(c.unit, c.runner, open_units)
                        continue
                    task = c
                    break
                if task is None and before and next_interp is not None:
                    if used + next_interp.weight <= self.jobs or not running:
                        task, next_interp = next_interp, next(interp_iter, None)
                    else:
                        break
                if task is None and before and next_interp is None and len(open_units) < max_open:
                    unit = next(unit_iter, None)
                    if unit is not None:
                        open_units.append(unit)
                        task = GenTask(self, unit)
                if task is None:
                    break
                task.start()
                running.append(task)
                used += task.weight
            if not running and not checks:
                break
            if time.time() - last_report > self.a.report_every:
                last_report = time.time()
                log("%d s: %d pipelines running (%d slots of %d), %d finished; %d unit-runner "
                    "cases judged, %d enumeration indices, %d emulated cases; %d findings"
                    % (time.time() - t_start, len(running), used, self.jobs, self.stats["tasks"],
                       self.stats["judged_cases"], self.stats["interp_cases"],
                       self.stats["emulated_cases"], self.n_findings))
            time.sleep(0.1)
        return 0


def cmd_run(a):
    work = os.path.abspath(a.work)
    os.makedirs(work, exist_ok=True)
    for d in ("logs", "streams", "compiled", "interp", "emulated"):
        os.makedirs(os.path.join(work, d), exist_ok=True)
    # Request files of a previous run are rewritten: the generator is deterministic.
    for f in glob.glob(os.path.join(work, "streams", "*")):
        os.remove(f)
    if WINDOWS:
        windows_job()
    else:
        for s in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            signal.signal(s, _on_signal)
    if WINDOWS:
        signal.signal(signal.SIGINT, _on_signal)
        signal.signal(signal.SIGBREAK, _on_signal)
    confine(a.cpus, a.nice)
    env = dict(os.environ)
    if a.env_script:
        env = env_from_script(a.env_script)
        os.environ.clear()
        os.environ.update(env)
    parts = set(a.part.split(","))
    a.compiled, a.interp, a.emulated = "compiled" in parts, "interp" in parts, "emulated" in parts
    code_commit = a.commit or git_commit(CODE_PATHS)
    driver_commit = a.driver_commit or git_commit(DRIVER_PATHS)
    if not code_commit or not driver_commit:
        sys.exit("brute: no git history to name the commit of the code under test and of the "
                 "driver: give --commit and --driver-commit")
    kernels = load_claims()
    folds = load_folds()
    only = set(a.kernels.split(",")) if a.kernels else None
    a.kernel_names = [k["name"] for k in kernels if not only or k["name"] in only]
    a.fold_names = [k["name"] for k in folds if not only or k["name"] in only]
    started = now_iso()
    t0 = time.time()
    runners = []
    if a.compiled:
        if not a.build:
            sys.exit("brute: the compiled part needs at least one --build NAME=COMPILER")
        runners = build(work, a.build, a.generator, a.cmake_arg or [], a.jobs, env,
                        a.fixup_forms)
        write_json(os.path.join(work, "runners.json"), runners)
        log("%d runners: %s" % (len(runners), ", ".join(r["id"] for r in runners)))
    enums = []
    if a.interp:
        plan, errors = interp_plan(kernels, only)
        fplan, ferrors = fold_plan(folds, only)
        plan += fplan
        errors += ferrors
        for e in errors:
            log("PLAN ERROR: %s" % e)
        if errors:
            return 1
        if a.interp_match:
            plan = [e for e in plan if re.search(a.interp_match, "%s %s" % (e["kernel"], e["format"]))]
        plan = sized_plan(plan, os.path.join(work, "sizes.json"))
        if a.interp_bins:
            which, load = bins_of(plan, a.interp_bins)
            take = parse_ranges(a.interp_take, a.interp_bins)
            plan = [e for e in plan if which[enum_key(e)] in take]
        plan.sort(key=lambda e: (-e["total"], enum_key(e)))
        enums = plan
        write_json(os.path.join(work, "interp-plan.json"), enums)
        log("%d enumerations, %d indices" % (len(enums), sum(e["total"] for e in enums)))
    emus, emulated_exe = [], None
    if a.emulated:
        emus = emulated_plan(kernels, folds, only, os.path.join(work, "emulated-sizes.json"),
                             a.emulated_match)
        if a.emulated_bins:
            which, _ = bins_of(emus, a.emulated_bins, emu_key)
            take = parse_ranges(a.emulated_take, a.emulated_bins)
            emus = [e for e in emus if which[emu_key(e)] in take]
        emus.sort(key=lambda e: (-e["total"], emu_key(e)))
        write_json(os.path.join(work, "emulated-plan.json"), emus)
        emulated_exe = emulated_runner(a, work, env)
        log("the emulated part: %d entries, %d indices or cases, runner %s"
            % (len(emus), sum(e["total"] for e in emus), emulated_exe))
    record = {"started": started, "budget": a.budget, "jobs": a.jobs, "parts": sorted(parts),
              "seed": a.seed, "chunk": a.chunk, "interp_chunk": a.interp_chunk,
              "cases_cap": a.cases, "kernels": a.kernel_names + a.fold_names, "cpus": a.cpus,
              "nice": a.nice,
              "commit": code_commit, "driver_commit": driver_commit,
              "driver_sha256": file_sha256(__file__),
              "fixup_forms": a.fixup_forms, "machine": machine_info(a.cpus),
              "interp_bins": a.interp_bins, "interp_take": a.interp_take,
              "interp_match": a.interp_match,
              "emulated_bins": a.emulated_bins, "emulated_take": a.emulated_take,
              "emulated_match": a.emulated_match, "emulated_chunk": a.emulated_chunk,
              "emulated_runner": emulated_exe,
              "builds": [{"name": b, "compiler": compiler_of(os.path.join(work, "builds", b))}
                         for b in sorted({r["build"] for r in runners})]}
    with open(os.path.join(work, "runs.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
    deadline = time.time() + a.budget if a.budget else None
    sched = Scheduler(a, work, runners, enums, emus, emulated_exe)
    try:
        status = sched.run(deadline)
    finally:
        kill_all()
        for f in glob.glob(os.path.join(work, "streams", "*")):
            try:
                os.remove(f)
            except OSError:
                pass
    end = {"finished": now_iso(), "started": started, "wall": round(time.time() - t0, 1),
           "status": status, "tasks": sched.stats["tasks"], "findings": sched.n_findings}
    with open(os.path.join(work, "runs.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(end) + "\n")
    log("done in %.0f s: %d pipelines, %d findings%s"
        % (time.time() - t0, sched.stats["tasks"], sched.n_findings,
           " (see %s)" % sched.findings_path if sched.n_findings else ""))
    return status or (1 if sched.n_findings else 0)


# The code under test: the kernels and their claims, the generator and its interpreter, the
# headers, the proofs and the oracle; and the driver. In a checkout, the last commit that changed
# each is what `run` records unless --commit and --driver-commit say otherwise (a copy made with
# git archive has no history: give both).
CODE_PATHS = ("include", "gen", "proofs", "oracle")
DRIVER_PATHS = ("tests/brute",)


def git_commit(paths=()):
    try:
        cmd = ["git", "-C", REPO, "log", "-1", "--format=%H"]
        if paths:
            cmd += ["--"] + list(paths)
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def file_sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read().replace(b"\r\n", b"\n")).hexdigest()


# --- Collect ---------------------------------------------------------------------------------------

def load_guards():
    spec = importlib.util.spec_from_file_location("crosscheck_guards", GUARDS)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


MERGE_FAN_IN = 48


def run_merges(jobs_list, jobs):
    """[(files, out)] merged by the oracle (check --merge), at most `jobs` at a time; a long list
    is merged in groups first, so that no command line gets long."""
    failed = []
    made = []
    for level in range(4):
        rounds, final = [], []
        for files, out in jobs_list:
            if len(files) <= MERGE_FAN_IN:
                rounds.append((files, out))
            else:
                parts = []
                for i in range(0, len(files), MERGE_FAN_IN):
                    part = "%s.part%d-%d.json" % (out, level, i // MERGE_FAN_IN)
                    rounds.append((files[i:i + MERGE_FAN_IN], part))
                    parts.append(part)
                made += parts
                final.append((parts, out))
        failed += _merge_round(rounds, jobs)
        if not final or failed:
            break
        jobs_list = final
    for f in made:
        if os.path.exists(f):
            os.remove(f)
    return failed


def _merge_round(jobs_list, jobs):
    pending = list(jobs_list)
    running = []
    failed = []
    while pending or running:
        while pending and len(running) < jobs:
            files, out = pending.pop(0)
            cmd = [PY, ORACLE, "check", "--merge", "--json", out, "--quiet"] + files
            running.append((popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                  cwd=REPO), out))
        for p, out in list(running):
            if p.poll() is not None:
                err = p.stderr.read().decode(errors="replace")
                p.stderr.close()
                LIVE.discard(p)
                running.remove((p, out))
                if p.returncode not in (0, 1) or not os.path.exists(out):
                    failed.append("%s: %s" % (os.path.basename(out), err.strip()[-500:]))
        time.sleep(0.05)
    return failed


def entry_stats(keys, p):
    """One kernel and format of a merged summary: its ensures entries over every tag."""
    out = []
    first = keys[0]["stats"]["entries"]
    for j, e0 in enumerate(first):
        es = [k["stats"]["entries"][j] for k in keys]
        x = {"label": e0["label"], "kind": e0["kind"],
             "applicable": sum(e["applicable"] for e in es),
             "failures": sum(e["failures"] for e in es)}
        best = None
        if e0["kind"] == "error":
            best = None
            a_best = None
            b_best = None
            for e in es:
                r = as_frac(e["max_ratio"])
                if r is not None and (best is None or frac_gt(r, best[0])):
                    best = (r, e["max_ratio_case"])
                for d, (rr, case) in e["profile"].items():
                    rr = as_frac(rr)
                    if int(d) >= p and rr is not None and (a_best is None or
                                                           frac_gt(rr, a_best[0])):
                        a_best = (rr, case)
                b = as_frac(e["b_max"])
                if b is not None and (b_best is None or frac_gt(b, b_best[0])):
                    b_best = (b, e["b_case"])
            x["max_ratio"] = best and [frac_dec(best[0]), best[1]]
            x["observed_c"] = a_best and [frac_dec(a_best[0]), a_best[1]]
            x["observed_t"] = b_best and [frac_dec(b_best[0]), b_best[1]]
        maxima, minima, counts = {}, {}, {}
        for e in es:
            for name, (r, case) in e.get("maxima", {}).items():
                r = as_frac(r)
                if name not in maxima or frac_gt(r, maxima[name][0]):
                    maxima[name] = (r, case)
            for name, (r, case) in e.get("minima", {}).items():
                r = as_frac(r)
                if name not in minima or frac_gt(minima[name][0], r):
                    minima[name] = (r, case)
            for name, n in e.get("counts", {}).items():
                # The histogram of r_z / r_min - 1 by powers of two has a bin per binade of
                # binary64; its extremes are kept below, its bins are not.
                if not name.startswith("ratio - 1 in ["):
                    counts[name] = counts.get(name, 0) + n
        if maxima:
            x["maxima"] = {n: [frac_dec(r), c] for n, (r, c) in sorted(maxima.items())}
        if minima:
            x["minima"] = {n: [frac_dec(r), c] for n, (r, c) in sorted(minima.items())}
        if counts:
            x["counts"] = dict(sorted(counts.items()))
        # Whether the extreme is the claim itself, decided exactly: an error equal to its bound,
        # an upper bound exceeding the value by exactly the claimed number of gaps.
        if e0["kind"] == "error" and best is not None:
            x["attains_claim"] = best[0][0] == best[0][1]
        elif e0["kind"] == "upper" and "excess in gaps" in maxima:
            g = re.search(r"gaps=(\d+)(?:/(\d+))?", e0["label"])
            if g:
                gn, gd = int(g.group(1)), int(g.group(2) or 1)
                r = maxima["excess in gaps"][0]
                x["attains_claim"] = r[0] * gd == gn * r[1]
        out.append(x)
    return out


def read_times(path):
    """Seconds of the finished pipelines (times.jsonl), summed by (part, kernel or enumeration,
    format, runner)."""
    out = {}
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            x = json.loads(line)
            if x.get("failed"):
                continue
            if x["part"] in ("interp", "emulated"):
                key = (x["part"], x["enum"], None, None)
            else:
                key = (x["part"], x["kernel"], x["format"], x.get("runner"))
            out[key] = out.get(key, 0.0) + x["s"]
    return out


def key_counts(keys):
    t = {}
    for k in keys:
        for name, n in k["stats"]["counts"].items():
            t[name] = t.get(name, 0) + n
    return t


def coverage_of(summary):
    cov = summary.get("coverage", [])
    if len(cov) != 1:
        return None, None
    return cov[0]["desc"], cov[0]["ranges"]


def headline(entries):
    """Per runner, the one number of each entry that says how close the claim came."""
    h = []
    for x in entries:
        if x["kind"] == "error":
            h.append(x["max_ratio"][0] if x.get("max_ratio") else None)
        elif x["kind"] == "upper":
            h.append(x.get("maxima", {}).get("excess in gaps", [None])[0])
        elif x["kind"] == "encloses":
            h.append(x.get("minima", {}).get("slack in gaps of the radius", [None])[0])
        else:
            h.append(None)
    return h


def cmd_collect(a):
    confine(a.cpus, a.nice)
    work = os.path.abspath(a.work)
    guards = load_guards()
    merged_dir = os.path.join(work, "merged")
    runs = []
    with open(os.path.join(work, "runs.jsonl"), encoding="utf-8") as f:
        for line in f:
            if line.strip():
                runs.append(json.loads(line))
    starts = [r for r in runs if "budget" in r]
    ends = [r for r in runs if "finished" in r]
    if not starts:
        sys.exit("brute: no run recorded in %s" % work)
    seeds = sorted({r["seed"] for r in starts if "compiled" in r["parts"]})
    if len(seeds) > 1:
        sys.exit("brute: the runs in %s used different seeds: %s" % (work, seeds))
    seed = seeds[0] if seeds else None
    findings = []
    fpath = os.path.join(work, "findings.jsonl")
    if os.path.exists(fpath):
        with open(fpath, encoding="utf-8") as f:
            findings = [json.loads(l) for l in f if l.strip()]
    runners = read_json(os.path.join(work, "runners.json")) \
        if os.path.exists(os.path.join(work, "runners.json")) else []
    domain = {k["name"]: k.get("domain") or "finite" for k in load_claims() + load_folds()}
    fold_names = {k["name"] for k in load_folds()}
    times = read_times(os.path.join(work, "times.jsonl"))
    merges = []
    series = []
    for kdir in sorted(glob.glob(os.path.join(work, "compiled", "*", "*"))):
        kernel, fmt = os.path.basename(os.path.dirname(kdir)), os.path.basename(kdir)
        for rdir in sorted(glob.glob(os.path.join(kdir, "*"))):
            files = sorted(glob.glob(os.path.join(rdir, "u*.json")))
            if not files:
                continue
            rid = next((r["id"] for r in runners if safe(r["id"]) == os.path.basename(rdir)),
                       os.path.basename(rdir))
            out = os.path.join(merged_dir, "compiled", kernel, fmt, os.path.basename(rdir) + ".json")
            os.makedirs(os.path.dirname(out), exist_ok=True)
            merges.append((files, out))
            series.append((kernel, fmt, rid, out, len(files)))
    plan = read_json(os.path.join(work, "interp-plan.json")) \
        if os.path.exists(os.path.join(work, "interp-plan.json")) else []
    enum_out = []
    for e in plan:
        files = sorted(glob.glob(os.path.join(work, "interp", enum_key(e), "c*.json")))
        out = os.path.join(merged_dir, "interp", enum_key(e) + ".json")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        if files:
            merges.append((files, out))
        enum_out.append((e, out, len(files)))
    # The emulated part: each entry's chunks, merged.
    emu_plan = read_json(os.path.join(work, "emulated-plan.json")) \
        if os.path.exists(os.path.join(work, "emulated-plan.json")) else []
    emu_seeds = sorted({r["seed"] for r in starts if "emulated" in r["parts"]})
    if len(emu_seeds) > 1:
        sys.exit("brute: the emulated runs in %s used different seeds: %s" % (work, emu_seeds))
    emu_out = []
    for e in emu_plan:
        files = sorted(glob.glob(os.path.join(work, "emulated", emu_key(e), "c*.json")))
        out = os.path.join(merged_dir, "emulated", emu_key(e) + ".json")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        if files:
            merges.append((files, out))
        emu_out.append((e, out, len(files)))
    log("merging %d series, %d enumerations and %d entries of the emulated part"
        % (len(series), len(enum_out), len(emu_out)))
    failed = run_merges(merges, a.jobs)
    if failed:
        sys.exit("brute: merges failed:\n" + "\n".join(failed))

    compiled = {}
    totals = {}
    for kernel, fmt, rid, out, nfiles in series:
        s = read_json(out)
        keys = [k for k in s["keys"] if (k["kernel"], k["format"]) == (kernel, fmt)]
        desc, ranges = coverage_of(s)
        covered = sum(b - a for a, b in ranges) if ranges else 0
        ns = argparse.Namespace(kernel=kernel, format=fmt, exhaustive=False, restrict="",
                                count=covered, seed=seed)
        if kernel in fold_names:
            # A fold's stream: every order for the scalar runners, the lane order of the register
            # for the packed ones; arrays up to FOLD_LENGTH elements.
            rr = next((r for r in runners if r["id"] == rid), {})
            ns.max_length = str(FOLD_LENGTH)
            ns.orders = (None if rr.get("kind") != "packed" else
                         "lanes:%s" % packed_lanes(kernel, fmt, rr.get("backend")))
        problems = list(guards.problems(s, ns))
        more, examples, _ = summary_problems(s, fails_on_suspicious(kernel, fmt))
        problems += more
        counts = key_counts(keys)
        p = keys[0]["stats"]["p"] if keys else None
        entries = entry_stats(keys, p) if keys else []
        slot = compiled.setdefault(kernel, {}).setdefault(fmt, {"runners": {}})
        slot["runners"][rid] = {"counts": counts, "entries": entries, "units": nfiles,
                                "covered": ranges, "guards": problems or "ok",
                                "strata": {k["tag"]: [k["stats"]["counts"].get("cases", 0),
                                                      k["stats"]["counts"].get("judged", 0)]
                                           for k in keys},
                                "seconds": times.get(("check", kernel, fmt, rid), 0.0)}
        for n, v in counts.items():
            totals[n] = totals.get(n, 0) + v
    # Per kernel and format: the counts over the runners, and each entry's extreme over them.
    for kernel, fmts in compiled.items():
        for fmt, slot in fmts.items():
            rs = slot["runners"]
            agg = {}
            for r in rs.values():
                for n, v in r["counts"].items():
                    agg[n] = agg.get(n, 0) + v
            slot["counts"] = agg
            slot["entries"] = combine_entries([(rid, r["entries"]) for rid, r in rs.items()])
            slot["guards"] = "ok" if all(r["guards"] == "ok" for r in rs.values()) else \
                {rid: r["guards"] for rid, r in rs.items() if r["guards"] != "ok"}
            slot["cases_per_runner"] = sorted({r["counts"].get("cases", 0) for r in rs.values()})
            slot["domain"] = domain.get(kernel, "unknown")
            # Per stratum: the cases of the machine's stream (the most any runner judged: they
            # all judge the same stream) and the judged results summed over the runners.
            strata = {}
            for r in rs.values():
                for tag, (nc, nj) in r["strata"].items():
                    x = strata.setdefault(tag, [0, 0])
                    x[0] = max(x[0], nc)
                    x[1] += nj
            slot["strata"] = dict(sorted(strata.items()))
            # Wall seconds of the pipelines: generating the cases, and judging them, summed over
            # the runners.
            slot["seconds"] = {"gen": round(times.get(("gen", kernel, fmt, None), 0.0), 1),
                               "check": round(sum(r["seconds"] for r in rs.values()), 1)}
            slot["runners"] = {rid: [r["counts"].get(n, 0) for n in RUNNER_COUNTS] +
                               [headline(r["entries"])] for rid, r in sorted(rs.items())}
    interp = []
    itotals = {}
    for e, out, nfiles in enum_out:
        rec = {"kernel": e["kernel"], "format": e["format"], "restrict": e["restrict"],
               "why": e["why"], "total": e["total"], "chunks": nfiles,
               "domain": domain.get(e["kernel"], "unknown"),
               "seconds": round(times.get(("interp", enum_key(e), None, None), 0.0), 1)}
        if not nfiles:
            rec["guards"] = ["not run"]
            interp.append(rec)
            continue
        s = read_json(out)
        keys = [k for k in s["keys"] if (k["kernel"], k["format"]) == (e["kernel"], e["format"])]
        desc, ranges = coverage_of(s)
        ns = argparse.Namespace(kernel=e["kernel"], format=e["format"], exhaustive=True,
                                restrict=",".join(e["restrict"]), count=None, seed=None,
                                max_length=e.get("maxlen"))
        problems = list(guards.problems(s, ns))
        more, examples, _ = summary_problems(s, fails_on_suspicious(e["kernel"], e["format"]))
        problems += more
        rec["covered"] = sum(b - a for a, b in ranges) if ranges else 0
        rec["complete"] = ranges == [[0, e["total"]]]
        rec["counts"] = key_counts(keys)
        rec["entries"] = entry_stats(keys, keys[0]["stats"]["p"]) if keys else []
        rec["guards"] = problems or "ok"
        for n, v in rec["counts"].items():
            itotals[n] = itotals.get(n, 0) + v
        interp.append(rec)
    emulated = []
    etotals = {}
    for e, out, nfiles in emu_out:
        rec = {"kernel": e["kernel"], "format": e["format"], "mode": e["mode"], "why": e["why"],
               "total": e["total"], "chunks": nfiles, "domain": domain.get(e["kernel"], "unknown"),
               "seconds": round(times.get(("emulated", emu_key(e), None, None), 0.0), 1)}
        if not nfiles:
            rec["guards"] = ["not run"]
            emulated.append(rec)
            continue
        s = read_json(out)
        keys = [k for k in s["keys"] if (k["kernel"], k["format"]) == (e["kernel"], e["format"])]
        desc, ranges = coverage_of(s)
        exhaustive = e["mode"] == "exhaustive"
        ns = argparse.Namespace(kernel=e["kernel"], format=e["format"], exhaustive=exhaustive,
                                restrict="", count=None if exhaustive else e["total"],
                                seed=None if exhaustive else (emu_seeds[0] if emu_seeds else None),
                                max_length=None if e.get("maxlen") is None else str(e["maxlen"]),
                                orders=None, emulated=True)
        problems = list(guards.problems(s, ns)) + list(guards.emulated_problems(s, ns))
        more, examples, _ = summary_problems(s, fails_on_suspicious(e["kernel"], e["format"]))
        problems += more
        rec["covered"] = sum(b - a for a, b in ranges) if ranges else 0
        rec["complete"] = ranges == [[0, e["total"]]]
        rec["counts"] = key_counts(keys)
        rec["entries"] = entry_stats(keys, keys[0]["stats"]["p"]) if keys else []
        rec["guards"] = problems or "ok"
        for n, v in rec["counts"].items():
            etotals[n] = etotals.get(n, 0) + v
        emulated.append(rec)
    machine = starts[-1]["machine"]
    result = {
        "kairn_brute_summary": 1,
        "name": a.name,
        "machine": machine,
        # The code under test and the driver: every commit a run of this work directory named
        # (one each, unless it was restarted with another driver), and the driver of collect.
        "commit": sorted({r["commit"] for r in starts if r.get("commit")}),
        "driver_commit": sorted({r["driver_commit"] for r in starts if r.get("driver_commit")}),
        "driver_sha256": sorted({r["driver_sha256"] for r in starts if r.get("driver_sha256")}),
        "collect_driver_sha256": file_sha256(__file__),
        "fixup_forms": sorted({r.get("fixup_forms", "default") for r in starts
                               if "compiled" in r["parts"]}),
        "runs": [{"started": r["started"], "budget": r["budget"], "jobs": r["jobs"],
                  "parts": r["parts"], "cpus": r["cpus"], "nice": r["nice"],
                  "interp_bins": r.get("interp_bins"), "interp_take": r.get("interp_take"),
                  "interp_match": r.get("interp_match")}
                 for r in starts],
        "ends": [{"started": r["started"], "finished": r["finished"], "wall": r["wall"],
                  "status": r["status"], "findings": r["findings"]} for r in ends],
        "seed": seed,
        "chunk": starts[-1]["chunk"],
        "interp_chunk": starts[-1]["interp_chunk"],
        "runners": {r["id"]: {"kind": r["kind"], "backend": r["backend"], "setting": r["setting"],
                              "compiler": r["compiler"], "flags": r["flags"],
                              "build": r["build"], "fixup": r.get("fixup"),
                              "fixup_default": r.get("fixup_default")} for r in runners},
        "runner_columns": list(RUNNER_COUNTS) + ["headline per entry"],
        "compiled": {"totals": totals, "kernels": compiled},
        "interp": {"totals": itotals, "enumerations": interp},
        "emulated": {"totals": etotals, "entries": emulated,
                     "seed": emu_seeds[0] if emu_seeds else None},
        "findings": findings,
    }
    write_json(a.out, result, compact=True)
    ok_c = all(s["guards"] == "ok" for f in compiled.values() for s in f.values())
    ok_i = all(r["guards"] == "ok" for r in interp)
    ok_e = all(r["guards"] == "ok" for r in emulated)
    log("wrote %s (%d bytes): compiled %s judged in %d series%s; interp %s cases in %d "
        "enumerations%s; emulated %s cases in %d entries%s; %d findings"
        % (a.out, os.path.getsize(a.out), "{:,}".format(totals.get("judged", 0)), len(series),
           "" if ok_c else " (GUARDS FAILED)", "{:,}".format(itotals.get("cases", 0)), len(interp),
           "" if ok_i else " (GUARDS FAILED or not complete)", "{:,}".format(etotals.get("cases", 0)),
           len(emulated), "" if ok_e else " (GUARDS FAILED or not complete)", len(findings)))
    return 0 if ok_c and ok_i and ok_e and not findings else 1


RUNNER_COUNTS = ("cases", "judged", "failed", "invalid", "nonfinite", "suspicious")


def combine_entries(per_runner):
    """Each entry's extreme statistics over the runners, with the runner that attains it."""
    if not per_runner:
        return []
    base = per_runner[0][1]
    out = []
    for j, e0 in enumerate(base):
        x = {"label": e0["label"], "kind": e0["kind"],
             "applicable": sum(es[j]["applicable"] for _, es in per_runner),
             "failures": sum(es[j]["failures"] for _, es in per_runner)}
        for field in ("max_ratio", "observed_c", "observed_t"):
            best = None
            for rid, es in per_runner:
                v = es[j].get(field)
                if v and (best is None or decimal.Decimal(v[0]) > decimal.Decimal(best[0])):
                    best = v + [rid]
            if best:
                x[field] = best
        for field, sign in (("maxima", 1), ("minima", -1)):
            agg = {}
            for rid, es in per_runner:
                for name, v in es[j].get(field, {}).items():
                    cur = agg.get(name)
                    if cur is None or sign * (decimal.Decimal(v[0]) - decimal.Decimal(cur[0])) > 0:
                        agg[name] = v + [rid]
            if agg:
                x[field] = agg
        counts = {}
        for _, es in per_runner:
            for name, n in es[j].get("counts", {}).items():
                counts[name] = counts.get(name, 0) + n
        if counts:
            x["counts"] = counts
        if any("attains_claim" in es[j] for _, es in per_runner):
            x["attains_claim"] = any(es[j].get("attains_claim") for _, es in per_runner)
        out.append(x)
    return out


# --- Report ----------------------------------------------------------------------------------------
#
# Markdown for docs/developer/results/: the machines, then one table per kernel, with a row per
# format of the compiled runners (every machine and runner together) and per enumeration of the
# interpreter, and the lines that attain the extremes.

def fmt_int(n):
    return "{:,}".format(n).replace(",", " ")


def short(dec, digits=6):
    if dec is None:
        return "-"
    d = decimal.Decimal(dec)
    if d == 0:
        return "0"
    text = format(decimal.Context(prec=digits).create_decimal(d), "g")
    if d != 1 and decimal.Decimal(text) == 1:
        text = format(decimal.Context(prec=10).create_decimal(d), "g")
    return text


def near_one(dec, attains):
    """A ratio that rounds to 1 at ten digits without being 1: say so rather than print 1."""
    return (not attains and dec is not None and decimal.Decimal(dec) <= 1
            and decimal.Decimal(dec) >= decimal.Decimal("0.99999999995"))


B4_APPLIES = "B4 applies: finite operands, every finite_when condition holds"


def headline_columns(entries):
    """(column title, extractor, better) for the entries of a kernel that have one."""
    cols = []
    for j, e in enumerate(entries):
        lab = e["label"]
        if e["kind"] == "error":
            several = sum(x["kind"] == "error" for x in entries) > 1
            cols.append(("largest error / bound" + (" (%s)" % lab.split("form ", 1)[1][3:]
                                                    if several else ""),
                         j, "max_ratio", None, 1))
            cols.append(("observed c", j, "observed_c", None, 1))
        elif e["kind"] == "upper":
            cols.append(("largest excess, gaps (claim %s)" % lab.split("gaps=")[1].split()[0],
                         j, "maxima", "excess in gaps", 1))
        elif e["kind"] == "encloses":
            cols.append(("smallest radius slack, gaps", j, "minima",
                         "slack in gaps of the radius", -1))
            cols.append(("smallest radius / enclosing", j, "minima",
                         "radius / smallest enclosing radius", -1))
            # B4 (a finite ball from finite operands under the claim's finite_when condition):
            # the cases the oracle applied it to, where the claim has such a condition.
            if B4_APPLIES in e.get("counts", {}):
                cols.append(("B4 applied to", j, "count", B4_APPLIES, 0))
        elif e["kind"] in ("rounded", "predicate"):
            cols.append(("outcomes" if e["kind"] == "predicate" else "cases by rounding",
                         j, "counts", None, 0))
    return cols


def col_value(entry, field, name):
    """[decimal, line, runner?] or None."""
    v = entry.get(field)
    if v is None:
        return None
    if name is not None:
        v = v.get(name)
    return v


def best_of(values, sign):
    best = None
    for v in values:
        if v and (best is None or sign * (decimal.Decimal(v[0]) - decimal.Decimal(best[0])) > 0):
            best = v
    return best


def exact_claim(label):
    """An error entry whose bound is zero: the claim is that the result is exact."""
    return bool(re.search(r"\bc=0, k=\d+, t=0\b", label))


def counts_text(counts):
    order = ["true", "false", "exact", "inexact", "tie", "inexact, = RN", "inexact, != RN"]
    names = sorted(counts, key=lambda c: (order.index(c) if c in order else 99, c))
    return "; ".join("%s %s" % (c.replace("inexact, != RN", "differs from RN")
                               .replace("inexact, = RN", "inexact, as RN"), fmt_int(counts[c]))
                     for c in names)


def cmd_report(a):
    docs = [read_json(f) for f in a.files]
    out = []
    w = out.append
    w("| Machine | Compilers | Runners | Seed | Cases per kernel and format | Judged (compiled) "
      "| Enumerated (interpreter) |")
    w("|---|---|---|---|---|---|---|")
    for d in docs:
        m = d["machine"]
        cpr = sorted({c for k in d["compiled"]["kernels"].values() for s in k.values()
                      for c in s["cases_per_runner"]})
        comp = sorted({r["compiler"] for r in d["runners"].values()})
        w("| %s: %s %s, %s | %s | %d | `%s` | %s | %s | %s |"
          % (d["name"], m["system"], m["machine"], m["cpu"], ", ".join(comp) or "-",
             len(d["runners"]), d["seed"] or "-",
             ("%s to %s" % (fmt_int(cpr[0]), fmt_int(cpr[-1])) if len(cpr) > 1 else
              fmt_int(cpr[0])) if cpr else "-",
             fmt_int(d["compiled"]["totals"].get("judged", 0)),
             fmt_int(d["interp"]["totals"].get("cases", 0))))
    report_throughput(docs, w)
    report_aim(docs, w)
    report_agreement(docs, w)
    report_backends(docs, w)
    report_balls(docs, w)
    kernels = []
    for d in docs:
        for k in list(d["compiled"]["kernels"]) + [r["kernel"] for r in
                                                   d["interp"]["enumerations"]]:
            if k not in kernels:
                kernels.append(k)
    # How close each bound came: the extreme of each error, upper and encloses entry over the
    # compiled runs and over the interpreter's, every kernel in one table, closest first.
    rank = []
    for k in kernels:
        per = {}
        for d in docs:
            for fmt, s in d["compiled"]["kernels"].get(k, {}).items():
                for e in s["entries"]:
                    per.setdefault(e["label"], {"kind": e["kind"], "c": [], "i": []})["c"].append(e)
            for r in d["interp"]["enumerations"]:
                if r["kernel"] == k:
                    for e in r.get("entries", []):
                        per.setdefault(e["label"], {"kind": e["kind"], "c": [], "i": []})[
                            "i"].append(dict(e, _fmt=r["format"]))
        for label, x in per.items():
            if x["kind"] == "error":
                get, sign = (lambda e: e.get("max_ratio")), 1
            elif x["kind"] == "upper":
                get, sign = (lambda e: e.get("maxima", {}).get("excess in gaps")), 1
            elif x["kind"] == "encloses":
                get, sign = (lambda e: e.get("minima", {}).get("slack in gaps of the radius")), -1
            else:
                continue
            c = best_of([get(e) for e in x["c"]], sign)
            i = best_of([get(e) and get(e)[:2] + [e["_fmt"]] for e in x["i"]], sign)
            ca = any(e.get("attains_claim") for e in x["c"])
            ia = any(e.get("attains_claim") for e in x["i"])
            rank.append((x["kind"], k, label, c and c + [ca], i and i + [ia]))
    for kind, title, note in (
            ("error", "Largest error over its bound", "1 is the bound"),
            ("upper", "Largest excess of an upper bound, in gaps",
             "the claim is the `gaps=` of the entry"),
            ("encloses", "Smallest slack of a Ball radius, in gaps of the radius",
             "below 1, a radius one unit in the last place smaller would not enclose")):
        rs = [r for r in rank if r[0] == kind]
        if not rs:
            continue
        sign = -1 if kind == "encloses" else 1
        rs.sort(key=lambda r: -sign * max(
            [decimal.Decimal(v[0]) * sign for v in (r[3], r[4]) if v] or [decimal.Decimal(0)]))
        w("")
        w("<!-- %s: %s -->" % (title, note))
        w("| Kernel | Claim | Compiled | Interpreter (format) |")
        w("|---|---|---|---|")
        for _, k, label, c, i in rs:
            if kind == "error" and exact_claim(label):
                w("| `%s` | `%s` | %s | %s |" % (k, label.replace("|", "\\|"),
                                                "0 (exact)" if c else "-",
                                                ("0 (exact; `%s`)" % i[2]) if i else "-"))
                continue
            ctext = "-"
            if c:
                ctext = ("1 - ε, ε < 10⁻⁹" if kind == "error" and near_one(c[0], c[-1]) else
                         short(c[0]) + (" (the claim)" if c[-1] else ""))
            w("| `%s` | `%s` | %s | %s |" % (
                k, label.replace("|", "\\|"), ctext,
                ("%s (`%s`)%s" % (short(i[0]), i[2], " (the claim)" if i[-1] else "")) if i
                else "-"))
    for k in kernels:
        rows = []           # (title, counts, entries, guards)
        for fmt in ("binary64", "binary32"):
            slots = [(d["name"], d["compiled"]["kernels"][k][fmt]) for d in docs
                     if fmt in d["compiled"]["kernels"].get(k, {})]
            if not slots:
                continue
            counts = {}
            for _, s in slots:
                for n, v in s["counts"].items():
                    counts[n] = counts.get(n, 0) + v
            nrun = sum(len(s["runners"]) for _, s in slots)
            merged = []
            for j, e0 in enumerate(slots[0][1]["entries"]):
                x = {"label": e0["label"], "kind": e0["kind"]}
                for field in ("max_ratio", "observed_c"):
                    vs = [s["entries"][j].get(field) for n, s in slots]
                    vs = [v + [n] if v else None for v, (n, _) in zip(vs, slots)]
                    x[field] = best_of(vs, 1)
                for field, sign in (("maxima", 1), ("minima", -1)):
                    names = {nm for _, s in slots for nm in s["entries"][j].get(field, {})}
                    x[field] = {nm: best_of([s["entries"][j].get(field, {}).get(nm, None) and
                                             s["entries"][j][field][nm] + [n]
                                             for n, s in slots], sign) for nm in names}
                cs = {}
                for _, s in slots:
                    for c, m in s["entries"][j].get("counts", {}).items():
                        cs[c] = cs.get(c, 0) + m
                x["counts"] = cs
                if any("attains_claim" in s["entries"][j] for _, s in slots):
                    x["attains_claim"] = any(s["entries"][j].get("attains_claim")
                                             for _, s in slots)
                merged.append(x)
            ok = all(s["guards"] == "ok" for _, s in slots)
            rows.append(("`%s`, %d runners on %d machine%s" % (fmt, nrun, len(slots),
                                                               "s" if len(slots) > 1 else ""),
                         counts, merged, ok, True))
        for d in docs:
            for r in d["interp"]["enumerations"]:
                if r["kernel"] != k:
                    continue
                title = "`%s`%s (%s)" % (r["format"], (", restricted: " + ", ".join(
                    "`%s`" % x for x in r["restrict"])) if r["restrict"] else ", every operand",
                    r["why"].replace(", restricted", ""))
                found = [f for f in d.get("findings", []) if f["part"] == "interp" and
                         (f["kernel"], f["format"], f.get("restrict", [])) ==
                         (r["kernel"], r["format"], r["restrict"])]
                if found:
                    title += " (**stopped by a finding**: %s)" % found[0]["why"][0]
                rows.append((title, r.get("counts", {}), r.get("entries", []),
                             r["guards"] == "ok" and r.get("complete") or bool(found), False))
        if not rows:
            continue
        w("")
        w("### `%s`" % k)
        w("")
        entries0 = next((r[2] for r in rows if r[2]), [])
        w("Claims: " + "; ".join("`%s`" % e["label"] for e in entries0) + ".")
        w("")
        cols = headline_columns(entries0)
        w("| " + " | ".join(["Run", "Cases", "Judged", "Failed"] + [c[0] for c in cols]) + " |")
        w("|---|---|---|---|" + "---|" * len(cols))
        lines = []
        for title, counts, entries, ok, compiled in rows:
            cells = []
            for name, j, field, sub, sign in cols:
                if j >= len(entries):
                    cells.append("-")
                    continue
                e = entries[j]
                if field == "counts":
                    cells.append(counts_text(e.get("counts", {})))
                    continue
                if field == "count":
                    cells.append(fmt_int(e.get("counts", {}).get(sub, 0)))
                    continue
                v = col_value(e, field, sub)
                mark = " (the claim)" if (e.get("attains_claim") and field in ("max_ratio",
                                                                                "maxima")) else ""
                if v and field in ("max_ratio", "observed_c") and exact_claim(e["label"]) \
                        and decimal.Decimal(v[0]) == 0:
                    cells.append("0 (exact)" if field == "max_ratio" else "0")
                    continue
                if v and field == "max_ratio" and near_one(v[0], e.get("attains_claim")):
                    cells.append("1 - ε, ε < 10⁻⁹")
                    lines.append((title, name, v))
                    continue
                cells.append(short(v[0]) + mark if v else "-")
                if v and field != "observed_c" and not (sub and "enclosing" in sub):
                    lines.append((title, name, v))
            w("| " + " | ".join([title + ("" if ok else " (**INCOMPLETE or guard failed**)"),
                                 fmt_int(counts.get("cases", 0)), fmt_int(counts.get("judged", 0)),
                                 fmt_int(counts.get("failed", 0))] + cells) + " |")
        # The line of the extreme of each headline column, over the compiled rows and over the
        # interpreter's.
        picks = []
        for name, j, field, sub, sign in cols:
            if field in ("counts", "count", "observed_c") or (sub and "enclosing" in sub):
                continue
            for compiled in (True, False):
                vs = [(v, t) for t, nm, v in lines if nm == name and
                      any(r[0] == t and r[4] == compiled for r in rows)]
                best = None
                for v, t in vs:
                    if best is None or sign * (decimal.Decimal(v[0]) -
                                               decimal.Decimal(best[0][0])) > 0:
                        best = (v, t)
                if best:
                    picks.append((name, compiled, best))
        strata_lines = []
        for fmt in ("binary64", "binary32"):
            st = {}
            for d in docs:
                for tag, (nc, nj) in d["compiled"]["kernels"].get(k, {}).get(fmt, {}).get(
                        "strata", {}).items():
                    x = st.setdefault(tag, [0, 0])
                    x[0] += nc
                    x[1] += nj
            if st:
                strata_lines.append("`%s`: %s" % (fmt, ", ".join(
                    "%s %s" % (tag, fmt_int(nc)) for tag, (nc, nj) in sorted(st.items()))))
        if strata_lines:
            w("")
            w("Distinct random cases per stratum, summed over the machines (each judged by every "
              "runner of its machine): " + "; ".join(strata_lines) + ".")
        if picks:
            w("")
            w("Where the extremes are attained (the line as the oracle reports it):")
            w("")
            w("```")
            for name, compiled, (v, t) in picks:
                where = (" (%s)" % ", ".join(v[2:])) if len(v) > 2 else ""
                if not compiled:
                    # The enumeration, restrictions included: the tag's index is within it.
                    where = " (%s)" % re.sub(r" \((p =|quick|another|the quick).*$", "",
                                             t.replace("`", ""))
                value = short(v[0])
                if name.startswith("largest error") and v[0] != "1" and near_one(v[0], False):
                    value = "1 - ε, ε < 10⁻⁹"
                w("%s, %s %s%s:" % (name, "compiled" if compiled else "interpreter", value,
                                    where))
                w("  " + v[1])
            w("```")
    print("\n".join(out))
    return 0


def wall_of(d):
    return sum(e["wall"] for e in d.get("ends", []))


def report_throughput(docs, w):
    """Cases per second: of each machine over its wall time, and of one pipeline."""
    w("")
    w("<!-- Throughput: wall time of the runs (builds included); per second of it, the results "
      "judged by the compiled runners and the cases enumerated; per second of one pipeline, the "
      "cases one oracle check of a compiled runner, one generator of random cases and one "
      "interpreter pipeline get through (summed over the kernels) -->")
    w("| Machine | Wall time | Judged per second | Enumerated per second | One check pipeline, "
      "cases/s | One generator, cases/s | One interpreter pipeline, cases/s |")
    w("|---|---|---|---|---|---|---|")
    for d in docs:
        wall = wall_of(d)
        kern = d["compiled"]["kernels"]
        cases_chk = sum(s["counts"].get("cases", 0) for f in kern.values() for s in f.values())
        sec_chk = sum(s.get("seconds", {}).get("check", 0) for f in kern.values()
                      for s in f.values())
        cases_gen = sum(max(s["cases_per_runner"] or [0]) for f in kern.values()
                        for s in f.values())
        sec_gen = sum(s.get("seconds", {}).get("gen", 0) for f in kern.values() for s in f.values())
        en = d["interp"]["enumerations"]
        cases_i = sum(r.get("counts", {}).get("cases", 0) for r in en)
        sec_i = sum(r.get("seconds", 0) for r in en)

        def rate(n, t):
            return fmt_int(int(round(n / t))) if t else "-"
        w("| %s | %s | %s | %s | %s | %s | %s |" % (
            d["name"], "%.0f s (%.2f h)" % (wall, wall / 3600) if wall else "-",
            rate(d["compiled"]["totals"].get("judged", 0), wall),
            rate(d["interp"]["totals"].get("cases", 0), wall),
            rate(cases_chk, sec_chk), rate(cases_gen, sec_gen), rate(cases_i, sec_i)))


AIM = 10 ** 8


def report_aim(docs, w):
    """Cases per kernel and format summed over the machines and runners, against 10^8."""
    per = {}
    for d in docs:
        for k, fmts in d["compiled"]["kernels"].items():
            for fmt, s in fmts.items():
                x = per.setdefault((k, fmt), [0, 0, 0])
                x[0] += s["counts"].get("cases", 0)
                x[1] += s["counts"].get("judged", 0)
                x[2] += max(s["cases_per_runner"] or [0])
    if not per:
        return
    cases = sorted(v[0] for v in per.values())
    judged = sorted(v[1] for v in per.values())
    distinct = sorted(v[2] for v in per.values())
    below = sorted((v[0], k, f) for (k, f), v in per.items() if v[0] < AIM)
    below_j = sorted((v[1], k, f) for (k, f), v in per.items() if v[1] < AIM)
    w("")
    w("<!-- The aim: 10^8 cases per kernel and format, summed over the machines and their "
      "runners -->")
    w("Per kernel and format, summed over the machines and their runners: %s to %s cases "
      "(median %s), of which %s to %s judged (a finite result, or any result in the extended "
      "domain), from %s to %s distinct cases. %d of %d kernel and format pairs reach $10^8$ "
      "cases%s." % (fmt_int(cases[0]), fmt_int(cases[-1]), fmt_int(cases[len(cases) // 2]),
                    fmt_int(judged[0]), fmt_int(judged[-1]), fmt_int(distinct[0]),
                    fmt_int(distinct[-1]), len(per) - len(below), len(per),
                    ("; the fewest: " + ", ".join("`%s` `%s` %s" % (k, f, fmt_int(n))
                                                  for n, k, f in below[:5])) if below else ""))
    w("")
    w("%d of %d reach $10^8$ judged results%s." % (
        len(per) - len(below_j), len(per),
        ("; below it: " + ", ".join("`%s` `%s` %s" % (k, f, fmt_int(n)) for n, k, f in below_j))
        if below_j else ""))


def report_agreement(docs, w):
    """Whether every runner of a machine gave the same counts and extremes, per kernel and
    format; the exceptions."""
    diff = []
    n = 0
    for d in docs:
        for k, fmts in sorted(d["compiled"]["kernels"].items()):
            for fmt, s in sorted(fmts.items()):
                n += 1
                rows = {rid: (tuple(v[:len(RUNNER_COUNTS)]), json.dumps(v[-1]))
                        for rid, v in s["runners"].items()}
                if len(set(rows.values())) > 1:
                    groups = {}
                    for rid, v in sorted(rows.items()):
                        groups.setdefault(v, []).append(rid)
                    diff.append((d["name"], k, fmt, groups))
    w("")
    w("<!-- Agreement of the runners of a machine (they judge the same cases) -->")
    if not diff:
        w("On each machine, every runner gave the same counts and the same extremes, for every "
          "kernel and format (%d series of runners compared)." % n)
        return
    w("Runners of one machine that disagree on the counts or the extremes (%d of %d kernel and "
      "format pairs):" % (len(diff), n))
    w("")
    for name, k, fmt, groups in diff:
        parts = []
        for (counts, head), rids in groups.items():
            parts.append("%s: counts %s, extremes %s" % (", ".join(rids), list(counts), head))
        w("- %s `%s` `%s`: %s" % (name, k, fmt, "; ".join(parts)))


def backend_of(r):
    if r["kind"] == "packed":
        return r["backend"].upper().replace("AVX2", "AVX2").replace("NEON", "NEON")
    return "scalar"


def report_backends(docs, w):
    """The largest error over its bound per kernel (operation and limb counts), format and
    backend: scalar (both forms of the fix-ups), AVX2, NEON; over every machine and compiler."""
    cols = []
    for d in docs:
        for r in d["runners"].values():
            b = backend_of(r)
            if b not in cols:
                cols.append(b)
    cols.sort(key=lambda b: (b != "scalar", b))
    table = {}
    labels = {}
    for d in docs:
        for k, fmts in d["compiled"]["kernels"].items():
            for fmt, s in fmts.items():
                kinds = [e["kind"] for e in s["entries"]]
                for rid, v in s["runners"].items():
                    b = backend_of(d["runners"][rid])
                    for j, h in enumerate(v[-1]):
                        if kinds[j] != "error" or h is None or exact_claim(
                                s["entries"][j]["label"]):
                            continue
                        key = (k, s["entries"][j]["label"])
                        labels[key] = s["entries"][j]["label"]
                        cur = table.setdefault(key, {}).get((fmt, b))
                        if cur is None or decimal.Decimal(h) > decimal.Decimal(cur):
                            table[key][(fmt, b)] = h
    if not table:
        return
    heads = ["%s %s" % (f, b) for f in ("binary64", "binary32") for b in cols]
    w("")
    w("<!-- Largest error over its bound per kernel, format and backend (every machine and "
      "compiler; scalar: both forms of the fix-ups) -->")
    w("| Kernel | Claim | " + " | ".join(heads) + " |")
    w("|---|---|" + "---|" * len(heads))

    def cell(v):
        # A ratio of exactly 1 is printed "1" by frac_dec; one that only rounds to 1 at ten
        # digits keeps its zeros ("1.000000000").
        if v is None:
            return "-"
        if v == "1":
            return "1 (the claim)"
        if near_one(v, False):
            return "1 - ε, ε < 10⁻⁹"
        return short(v)
    for key in sorted(table, key=lambda key: -max(decimal.Decimal(v)
                                                   for v in table[key].values())):
        w("| `%s` | `%s` | %s |" % (key[0], labels[key].replace("|", "\\|"), " | ".join(
            cell(table[key].get((f, b))) for f in ("binary64", "binary32") for b in cols)))


def report_balls(docs, w):
    """The share of the cases of each enumeration of a Ball kernel whose result is a finite ball:
    in the finite domain the judged ones (the others are non-finite), in the extended domain the
    count "result: finite ball" of the encloses entry."""
    rows = []
    for d in docs:
        for r in d["interp"]["enumerations"]:
            if not r["kernel"].startswith("ball_") or not r.get("counts"):
                continue
            cases = r["counts"].get("cases", 0)
            if r.get("domain") == "extended":
                fin = sum(e.get("counts", {}).get("result: finite ball", 0)
                          for e in r.get("entries", []) if e["kind"] == "encloses")
                if not any(e["kind"] == "encloses" for e in r.get("entries", [])):
                    continue
            else:
                fin = r["counts"].get("judged", 0)
            rows.append((r["kernel"], r["format"], r["restrict"], cases, fin))
    if not rows:
        return
    w("")
    w("<!-- Ball enumerations: the cases whose result is a finite ball -->")
    w("| Kernel | Enumeration | Cases | Finite ball | Share |")
    w("|---|---|---|---|---|")
    for k, f, rs, cases, fin in sorted(rows):
        w("| `%s` | `%s`%s | %s | %s | %s |" % (
            k, f, (", restricted: " + ", ".join("`%s`" % x for x in rs)) if rs else "",
            fmt_int(cases), fmt_int(fin), ("%.1f %%" % (100.0 * fin / cases)) if cases else "-"))


# --- Plan ------------------------------------------------------------------------------------------

def cmd_plan(a):
    kernels = load_claims()
    only = set(a.kernels.split(",")) if a.kernels else None
    plan, errors = interp_plan(kernels, only)
    fplan, ferrors = fold_plan(load_folds(), only)
    plan += fplan
    errors += ferrors
    for e in errors:
        print("PLAN ERROR: %s" % e)
    plan = sized_plan(plan, a.sizes) if a.part != "emulated" else []
    which, load = bins_of(plan, a.bins) if a.bins else ({}, [])
    total = 0
    for e in plan:
        total += e["total"]
        print("%-16s %-14s %14s  %s%s%s" % (
            e["kernel"], e["format"], "{:,}".format(e["total"]), e["why"],
            ("  [" + ",".join(e["restrict"]) + "]") if e["restrict"] else "",
            ("  bin %d" % which[enum_key(e)]) if which else ""))
    print("%d enumerations, %s indices" % (len(plan), "{:,}".format(total)))
    if load:
        print("bins: " + ", ".join("%d: %s" % (i, "{:,}".format(n)) for i, n in enumerate(load)))
    if a.part in ("all", "emulated"):
        # The emulated part (above, "The plan of the emulated part").
        emus = emulated_plan(kernels, load_folds(), only, a.sizes)
        which, load = bins_of(emus, a.bins, emu_key) if a.bins else ({}, [])
        for e in emus:
            print("emulated %-16s %-13s %-10s %14s  %s%s" % (
                e["kernel"], e["format"], e["mode"], "{:,}".format(e["total"]), e["why"],
                ("  bin %d" % which[emu_key(e)]) if which else ""))
        ex = [e for e in emus if e["mode"] == "exhaustive"]
        rn = [e for e in emus if e["mode"] == "random"]
        print("the emulated part: %d entries, %d enumerations of %s indices (at most %s each), %d random "
              "series of %s cases or arrays" % (
                  len(emus), len(ex), "{:,}".format(sum(e["total"] for e in ex)),
                  "{:,}".format(EMULATED_EXHAUSTIVE), len(rn), "{:,}".format(sum(e["total"] for e in rn))))
        for p in EMULATED_PRECISIONS:
            names = sorted(e["kernel"] for e in ex if parse_fmt(e["format"])[0] == p)
            print("  every operand at precision %d: %d kernels" % (p, len(names)))
        if load:
            print("emulated bins: " + ", ".join("%d: %s" % (i, "{:,}".format(n)) for i, n in enumerate(load)))
    return 1 if errors else 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="brute.py", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan", help="the interpreter's enumerations and their sizes")
    p.add_argument("--bins", type=int, default=0)
    p.add_argument("--kernels")
    p.add_argument("--part", choices=("all", "interp", "emulated"), default="all",
                   help="the interpreter's enumerations, the emulated part, or both (default)")
    p.add_argument("--sizes", help="a JSON file of the sizes of the enumerations, read and written "
                                   "(the oracle's gen --total of each, which takes minutes in all)")
    p.set_defaults(func=cmd_plan)

    r = sub.add_parser("run", help="build, run, and keep the summaries in the work directory")
    r.add_argument("--work", required=True, help="work directory (restartable)")
    r.add_argument("--budget", type=float, required=True,
                   help="seconds: no new pipeline starts after this")
    r.add_argument("--jobs", type=int, required=True,
                   help="busy processes at a time: a compiled pipeline counts 1, an interpreter's 2")
    r.add_argument("--part", default="compiled,interp",
                   help="compiled, interp, emulated, comma-separated (default compiled,interp)")
    r.add_argument("--emulated-runner", help="the emulated part: the runner of the emulated kernels "
                                             "(default: kairn-emulated-runner built in the first --build)")
    r.add_argument("--emulated-chunk", type=int, default=1000000,
                   help="enumeration indices or random cases per pipeline of the emulated part")
    r.add_argument("--emulated-bins", type=int, default=0,
                   help="split the emulated part into this many bins of about equal size ...")
    r.add_argument("--emulated-take", default="", help="... and run these bins (e.g. 0-6)")
    r.add_argument("--emulated-match", help="only the entries of the emulated part whose "
                                            "'KERNEL FORMAT' matches this regular expression")
    r.add_argument("--build", action="append", metavar="NAME=COMPILER",
                   help="a CMake build of the runners with this compiler (repeatable)")
    r.add_argument("--generator", help="CMake generator (default: CMake's)")
    r.add_argument("--cmake-arg", action="append", help="extra configure argument (repeatable)")
    r.add_argument("--env-script", help="run in the environment this script sets up "
                                        "(vcvars64.bat on Windows)")
    r.add_argument("--seed", default="brute", help="seed of the random cases (no spaces or =)")
    r.add_argument("--chunk", type=int, default=200000, help="random cases per unit")
    r.add_argument("--cases", type=int, help="at most this many random cases per kernel and "
                                             "format (default: as many as the budget allows)")
    r.add_argument("--interp-chunk", type=int, default=500000,
                   help="enumeration indices per pipeline")
    r.add_argument("--interp-bins", type=int, default=0,
                   help="split the plan into this many bins of about equal size ...")
    r.add_argument("--interp-take", default="", help="... and run these bins (e.g. 0-6)")
    r.add_argument("--kernels", help="only these kernels (comma-separated)")
    r.add_argument("--interp-match", help="only the enumerations whose 'KERNEL FORMAT' matches this "
                                          "regular expression (before --interp-bins)")
    r.add_argument("--cpus", help="CPU numbers to run on, e.g. 0-31,64-95 (Linux, Windows)")
    r.add_argument("--nice", type=int, default=0, help="lower the priority (POSIX nice; on "
                                                       "Windows, below normal)")
    r.add_argument("--task-timeout", type=float, default=1800,
                   help="seconds before a pipeline is killed and reported")
    r.add_argument("--report-every", type=float, default=60)
    r.add_argument("--commit", help="the commit of the code under test (default: the last that "
                                    "changed include, gen, proofs or oracle)")
    r.add_argument("--driver-commit", help="the commit of this driver (default: the last that "
                                           "changed tests/brute)")
    r.add_argument("--fixup-forms", choices=("both", "default"), default="both",
                   help="both forms of the scalar fix-ups (KAIRN_GEN_FIXUP_CALL; default), or "
                        "only the compiler's own, as in the quick tier")
    r.set_defaults(func=cmd_run)

    c = sub.add_parser("collect", help="merge, guard and write the compact summary")
    c.add_argument("--work", required=True)
    c.add_argument("--name", required=True)
    c.add_argument("--out", required=True)
    c.add_argument("--jobs", type=int, default=4)
    c.add_argument("--cpus", help="as for run")
    c.add_argument("--nice", type=int, default=0, help="as for run")
    c.set_defaults(func=cmd_collect)

    t = sub.add_parser("report", help="Markdown tables from compact summaries")
    t.add_argument("files", nargs="+")
    t.set_defaults(func=cmd_report)
    a = ap.parse_args(argv)
    if a.cmd == "run" and (a.interp_bins and not a.interp_take):
        ap.error("--interp-bins needs --interp-take")
    if a.cmd == "run" and (a.emulated_bins and not a.emulated_take):
        ap.error("--emulated-bins needs --emulated-take")
    if a.cmd == "run" and (" " in a.seed or "=" in a.seed or not a.seed):
        ap.error("--seed must be non-empty, without spaces or '='")
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
