#!/usr/bin/env python3
"""The brute-force tier of Kairn's tests (docs/developer/testing.md, tests/brute/README.md).

    python3 tests/brute/brute.py plan    [--bins N]
    python3 tests/brute/brute.py run     --work DIR --budget SECONDS --jobs N [options]
    python3 tests/brute/brute.py collect --work DIR --name NAME --out FILE
    python3 tests/brute/brute.py report  FILE...

Two parts, each a set of pipelines `gen | RUNNER | check` of the oracle (oracle/README.md), the
same pipelines as the quick tier's cross-checks (tests/crosscheck.cmake), only longer:

- compiled: every kernel of gen/claims.json, binary64 and binary32, on random cases of the
  oracle's generator (seed --seed, every stratum), through every runner that the CMake builds
  given by --build produce (kairn-gen-runner* and kairn-gen-packed-runner*: the scalar and the
  packed kernels, under each contraction setting). The cases come in units of --chunk; each
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

# --- The plan of the interpreter's enumerations ---------------------------------------------------
#
# By the roles of a kernel's inputs, as tests/CMakeLists.txt derives them (1 a limb, 2 a normalized
# pair, r a radius, c a power of two, then _sum or _product): the quick tier's toy format, whose
# exponent range is the base range here, and the formats beyond it. Every kernel also gets the
# formats of precision min_precision and min_precision + 1 in the base range (precision 2 and 3
# when min_precision is 1: the oracle reads no format of precision 1). Formats below a kernel's
# min_precision are left out. Sizes: `plan`, from the oracle's gen --exhaustive --total.
SHAPES = {
    "1": ("fp:11:-30:10", ["fp:12:-30:10", "fp:13:-30:10", "fp:13:-60:40"]),
    "1_1_sum": ("fp:5:-7:4", ["fp:6:-7:4", "fp:7:-7:4", "fp:7:-14:2"]),
    "1_1_product": ("fp:5:-12:-1", ["fp:6:-12:-1", "fp:7:-12:-1", "fp:7:-8:4", "fp:7:-20:-6"]),
    "r_r_sum": ("fp:6:-8:4", ["fp:7:-8:4", "fp:8:-8:4", "fp:8:-14:2"]),
    "r_r_product": ("fp:6:-13:-2", ["fp:7:-13:-2", "fp:8:-13:-2", "fp:8:-8:4"]),
    "2": ("fp:6:-8:4", ["fp:7:-8:4", "fp:8:-8:4", "fp:8:-20:2"]),
    "2_1_sum": ("fp:4:-4:2", ["fp:5:-4:2", "fp:6:-4:2", "fp:5:-6:3", "fp:4:-7:4"]),
    "1_2_sum": ("fp:4:-4:2", ["fp:5:-4:2", "fp:6:-4:2", "fp:5:-6:3", "fp:4:-7:4"]),
    "2_1_product": ("fp:4:-8:-2", ["fp:5:-8:-2", "fp:6:-8:-2", "fp:5:-4:2"]),
    "2_2_sum": ("fp:3:-3:2", ["fp:4:-3:2", "fp:5:-3:2", "fp:4:-4:3", "fp:3:-6:4"]),
    "2_2_product": ("fp:4:-7:-3", ["fp:5:-7:-3", "fp:6:-7:-3", "fp:4:-9:-3", "fp:5:-8:-2"]),
    "2_c_product": ("fp:5:-6:2", ["fp:6:-6:2", "fp:7:-6:2", "fp:6:-12:4"]),
    "1_r_sum": ("fp:5:-7:4", ["fp:6:-7:4", "fp:7:-7:4", "fp:7:-14:2"]),
    "2_r_sum": ("fp:4:-4:2", ["fp:5:-4:2", "fp:6:-4:2", "fp:5:-8:4"]),
    "1_r_1_product": ("fp:3:-5:0", ["fp:4:-5:0", "fp:5:-5:0", "fp:4:-8:2", "fp:3:-8:2"]),
    "2_r_1_product": ("fp:2:-4:1", ["fp:3:-4:1", "fp:4:-4:1", "fp:3:-6:2", "fp:2:-8:3"]),
    "1_r_1_r_sum": ("fp:2:-3:1", ["fp:3:-3:1", "fp:4:-3:1", "fp:3:-4:2", "fp:2:-6:4"]),
    "1_r_1_r_product": ("fp:2:-4:0", ["fp:3:-4:0", "fp:4:-4:0", "fp:3:-6:2", "fp:2:-7:3"]),
}

# The two-limb balls with two operands: every operand of their quick-tier format is far too many
# (140 million for ball_add_2 at fp:3:-3:2, 12.4 billion for ball_mul_2 at fp:4:-5:1). They get
# complete enumerations of formats of their min_precision with fewer exponents, and larger
# restricted domains than the quick tier's (gen --restrict), one of them one bit more precise.
_R_SUM_QUICK = "0x0p+0/0x1p-3/0x1p-1/0x1.4p+1"
_R_SUM_7 = "0x0p+0/0x1p-3/0x1.8p-2/0x1p-1/0x1.4p+1/0x1.cp+2/0x1.cp+4"
_R_MUL_QUICK = "0x0p+0/0x1p-5/0x1.8p+0"
_R_MUL_5 = "0x0p+0/0x1p-5/0x1p-3/0x1.8p+0/0x1.ep+4"
_R_MUL_P5 = "0x0p+0/0x1p-4/0x1.8p+0"
EXPLICIT = {
    "2_r_2_r_sum": ("fp:3:-3:2", [
        ("fp:3:-2:1", []),
        ("fp:3:-3:1", []),
        ("fp:3:-3:2", ["cx.lead=-1:0"]),
        ("fp:3:-3:2", ["rx.in=" + _R_SUM_7, "ry.in=" + _R_SUM_7]),
        ("fp:4:-3:2", ["rx.in=" + _R_SUM_QUICK, "ry.in=" + _R_SUM_QUICK]),
    ]),
    "2_r_2_r_product": ("fp:4:-5:1", [
        ("fp:4:-2:0", []),
        ("fp:4:-5:1", ["rx.in=" + _R_MUL_QUICK, "ry.in=" + _R_MUL_QUICK]),
        ("fp:4:-5:1", ["rx.in=" + _R_MUL_5, "ry.in=" + _R_MUL_5, "cx.lead=0:0"]),
        ("fp:4:-5:1", ["cx.lead=0:0", "cy.lead=0:0"]),
        ("fp:5:-4:1", ["rx.in=" + _R_MUL_P5, "ry.in=" + _R_MUL_P5, "cx.lead=0:0"]),
    ]),
}


def load_claims():
    with open(CLAIMS, encoding="utf-8") as f:
        return json.load(f)["kernels"]


def shape_of(k):
    """The roles of the inputs and the operation, as tests/CMakeLists.txt derives them."""
    requires = [r.replace(" ", "") for r in k.get("requires", [])]
    roles = []
    for i in k["inputs"]:
        if i.get("type") == "mask":
            roles.append("m")
        elif i.get("limbs", 1) != 1:
            roles.append(str(i["limbs"]))
        elif "nonneg(%s)" % i["name"] in requires:
            roles.append("r")
        elif "power_of_two(%s)" % i["name"] in requires:
            roles.append("c")
        else:
            roles.append("1")
    s = "_".join(roles)
    if len(k["inputs"]) > 1:
        s += "_product" if "*" in (k.get("value") or "") else "_sum"
    return s


def parse_fmt(name):
    m = re.match(r"^fp:(\d+):(-?\d+):(-?\d+)$", name)
    if not m:
        raise ValueError("not a toy format: %s" % name)
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def interp_plan(kernels, only=None):
    """[{kernel, format, restrict, why}] and [errors]: what the interpreter enumerates."""
    plan, errors = [], []
    for k in kernels:
        name = k["name"]
        if only and name not in only:
            continue
        shape = shape_of(k)
        pmin = k.get("min_precision")
        if not isinstance(pmin, int):
            errors.append("%s: min_precision is %r, so no format can be chosen" % (name, pmin))
            continue
        entries = []
        if shape in EXPLICIT:
            quick, listed = EXPLICIT[shape]
            for fmt, restrict in listed:
                entries.append((fmt, restrict, None))
        elif shape in SHAPES:
            quick, extra = SHAPES[shape]
            _, qmin, qmax = parse_fmt(quick)
            p0 = max(pmin, 2)
            for p in (p0, p0 + 1):
                entries.append(("fp:%d:%d:%d" % (p, qmin, qmax), [], None))
            for fmt in extra:
                entries.append((fmt, [], None))
        else:
            errors.append("%s: no toy formats are planned for its inputs (%s): add them to "
                          "SHAPES in tests/brute/brute.py" % (name, shape.replace("_", " ")))
            continue
        qp = parse_fmt(quick)[0]
        seen = set()
        for fmt, restrict, _ in entries:
            p, qmin, qmax = parse_fmt(fmt)
            if p < pmin or (fmt, tuple(restrict)) in seen:
                continue
            seen.add((fmt, tuple(restrict)))
            why = []
            if p == pmin:
                why.append("p = min_precision")
            elif p <= max(pmin, 2) + 1:
                why.append("p = min_precision + %d" % (p - pmin))
            if (qmin, qmax) == parse_fmt(quick)[1:]:
                if p == qp:
                    why.append("the quick tier's format")
                elif p > qp:
                    why.append("quick tier + %d bit%s" % (p - qp, "s" if p - qp > 1 else ""))
                else:
                    why.append("the quick tier's exponent range")
            else:
                why.append("another exponent range")
            if restrict:
                why.append("restricted")
            plan.append({"kernel": name, "format": fmt, "restrict": list(restrict),
                         "why": ", ".join(why)})
    return plan, errors


def enum_key(e):
    key = "%s__%s" % (e["kernel"], e["format"].replace(":", "_"))
    if e["restrict"]:
        key += "__r" + hashlib.sha1(",".join(e["restrict"]).encode()).hexdigest()[:10]
    return key


def gen_total(e):
    cmd = [PY, ORACLE, "gen", e["kernel"], e["format"], "--exhaustive", "--total"]
    for r in e["restrict"]:
        cmd += ["--restrict", r]
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


def bins_of(plan, n):
    """A deterministic split of the enumerations into n bins of about equal size (largest first,
    each into the lightest bin), so that machines can share the plan."""
    load = [0] * n
    out = {}
    for e in sorted(plan, key=lambda e: (-e["total"], enum_key(e))):
        b = min(range(n), key=lambda i: (load[i], i))
        load[b] += e["total"]
        out[enum_key(e)] = b
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


def build(work, specs, generator, cmake_args, jobs, env):
    """Configure (once) and build each --build NAME=CXX; return the runners they produce."""
    runners = []
    os.makedirs(os.path.join(work, "logs"), exist_ok=True)
    for spec in specs:
        name, _, cxx = spec.partition("=")
        if not name or not cxx or safe(name) != name:
            sys.exit("brute: --build wants NAME=COMPILER, NAME of letters, digits, . _ -: %r"
                     % spec)
        bdir = os.path.join(work, "builds", name)
        if not os.path.exists(os.path.join(bdir, "CMakeCache.txt")):
            cmd = ["cmake", "-S", REPO, "-B", bdir, "-DCMAKE_BUILD_TYPE=Release",
                   "-DCMAKE_CXX_COMPILER=" + cxx, "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON"]
            if generator:
                cmd += ["-G", generator]
            cmd += cmake_args
            log("configure %s: %s" % (name, " ".join(cmd[1:2] + cmd[5:])))
            run_step("configure " + name, cmd, env, 900,
                     os.path.join(work, "logs", "configure-%s.log" % name))
        log("build %s" % name)
        cmd = ["cmake", "--build", bdir, "--parallel", str(max(1, jobs))]
        if cache_value(bdir, "CMAKE_CONFIGURATION_TYPES"):
            cmd += ["--config", "Release"]
        run_step("build " + name, cmd, env, 3600, os.path.join(work, "logs", "build-%s.log" % name))
        runners += discover(name, bdir)
    if not runners:
        sys.exit("brute: the builds produced no runner")
    return runners


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
        m = re.match(r"^kairn-gen-(packed-)?runner(?:-(.+))?$", target)
        if not m or not os.path.isfile(path) or (not WINDOWS and not os.access(path, os.X_OK)):
            continue
        kind = "packed" if m.group(1) else "scalar"
        label = (backend if kind == "packed" else "cxx") + ("-" + m.group(2) if m.group(2) else "")
        out.append({"id": "%s/%s" % (name, label), "build": name, "label": label, "kind": kind,
                    "backend": backend if kind == "packed" else "scalar", "target": target,
                    "setting": m.group(2) or "the build's flags", "compiler": compiler,
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
        _, err = self.errlog("gen-%s-%s-%d" % (u.kernel, u.format, u.start))
        self.procs = [popen([PY, ORACLE, "gen", u.kernel, u.format, "--seed", self.s.seed,
                             "--start", str(u.start), "--count", str(u.count)],
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
        if u.kernel not in INTERMEDIATE_OVERFLOW:
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
                                                 u.kernel not in INTERMEDIATE_OVERFLOW)
            why += more
            if rc_c not in (0, 1) or (rc_c == 1 and not more):
                why.append("check exited with %d" % rc_c)
        if why:
            self.s.finding("compiled", why, examples, kernel=u.kernel, format=u.format,
                           runner=r["id"], seed=self.s.seed, start=u.start, count=u.count,
                           reproduce=reproduce_random(u.kernel, u.format, self.s.seed, r))
            self.s.stopped.add((u.kernel, u.format, r["id"]))
            if os.path.exists(self.tmp):
                os.replace(self.tmp, self.out + ".failed")
            return why
        os.replace(self.tmp, self.out)
        return []


class InterpTask(Task):
    """One chunk of an enumeration through the generator's interpreter."""
    weight = 2

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
               "--start", str(self.start_i), "--count", str(self.count)]
        for r in e["restrict"]:
            gen += ["--restrict", r]
        check = [PY, ORACLE, "check", "--json", self.tmp, "--quiet"]
        if e["kernel"] not in INTERMEDIATE_OVERFLOW:
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
            more, examples, _ = summary_problems(summary, e["kernel"] not in INTERMEDIATE_OVERFLOW)
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


def reproduce_random(kernel, fmt, seed, runner):
    check = "python3 oracle/kairn-oracle check"
    if kernel not in INTERMEDIATE_OVERFLOW:
        check += " --fail-on-suspicious"
    return ("python3 oracle/kairn-oracle gen %s %s --seed %s --start INDEX --count 1 | "
            "BUILD/tests/%s | %s   (BUILD: the build %s, runner %s; INDEX from the line's tag)"
            % (kernel, fmt, seed, runner["target"], check, runner["build"], runner["id"]))


def reproduce_exhaustive(e):
    restrict = "".join(" --restrict %s" % r for r in e["restrict"])
    check = "python3 oracle/kairn-oracle check"
    if e["kernel"] not in INTERMEDIATE_OVERFLOW:
        check += " --fail-on-suspicious"
    return ("python3 oracle/kairn-oracle gen %s %s --exhaustive%s --start INDEX --count 1 | "
            "python3 gen/kairn-gen interp | %s   (INDEX from the line's tag)"
            % (e["kernel"], e["format"], restrict, check))


class Unit:
    def __init__(self, work, kernel, fmt, start, count):
        self.kernel, self.format, self.start, self.count = kernel, fmt, start, count
        self.dir = os.path.join(work, "compiled", kernel, fmt)
        self.req = os.path.join(work, "streams", "%s-%s-%012d.req" % (kernel, fmt, start))
        self.generated = False
        self.pending = []           # runners still to judge it

    def result(self, rid):
        return os.path.join(self.dir, safe(rid), "u%012d.json" % self.start)


class Scheduler:
    def __init__(self, a, work, runners, enums):
        self.a = a
        self.work = work
        self.seed = a.seed
        self.runners = runners
        self.enums = enums
        self.jobs = a.jobs
        self.stopped = set()
        self.stopped_enums = set()
        self.findings_path = os.path.join(work, "findings.jsonl")
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
                            self.stopped_enums.add(enum_key(x))
        self.pairs = [(k, f) for k in a.kernel_names for f in ("binary64", "binary32")]
        self.stats = {"tasks": 0, "judged_cases": 0, "interp_cases": 0}

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
            for k, f in self.pairs:
                unit = Unit(self.work, k, f, start, count)
                unit.pending = [r for r in self.runners if (k, f, r["id"]) not in self.stopped
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

    def run(self, deadline):
        running = []
        used = 0
        unit_iter = self.units() if self.a.compiled else iter(())
        interp_iter = self.interp_tasks() if self.a.interp else iter(())
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
                    self.stats["interp_cases"] += t.count
                why = t.finish()
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
                    self.finding("interp", why, [], kernel=t.e["kernel"], format=t.e["format"],
                                 restrict=t.e["restrict"], start=t.start_i, count=t.count,
                                 reproduce=reproduce_exhaustive(t.e))
                    self.stopped_enums.add(enum_key(t.e))
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
            n_r = max(1, len(self.runners))
            max_gens = max(1, self.jobs // n_r)
            max_open = 2 + 2 * (-(-self.jobs // n_r))
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
                    "cases judged, %d enumeration indices; %d findings"
                    % (time.time() - t_start, len(running), used, self.jobs, self.stats["tasks"],
                       self.stats["judged_cases"], self.stats["interp_cases"], self.n_findings))
            time.sleep(0.1)
        return 0


def cmd_run(a):
    work = os.path.abspath(a.work)
    os.makedirs(work, exist_ok=True)
    for d in ("logs", "streams", "compiled", "interp"):
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
    a.compiled, a.interp = "compiled" in parts, "interp" in parts
    kernels = load_claims()
    only = set(a.kernels.split(",")) if a.kernels else None
    a.kernel_names = [k["name"] for k in kernels if not only or k["name"] in only]
    started = now_iso()
    t0 = time.time()
    runners = []
    if a.compiled:
        if not a.build:
            sys.exit("brute: the compiled part needs at least one --build NAME=COMPILER")
        runners = build(work, a.build, a.generator, a.cmake_arg or [], a.jobs, env)
        write_json(os.path.join(work, "runners.json"), runners)
        log("%d runners: %s" % (len(runners), ", ".join(r["id"] for r in runners)))
    enums = []
    if a.interp:
        plan, errors = interp_plan(kernels, only)
        for e in errors:
            log("PLAN ERROR: %s" % e)
        if errors:
            return 1
        plan = sized_plan(plan, os.path.join(work, "sizes.json"))
        if a.interp_bins:
            which, load = bins_of(plan, a.interp_bins)
            take = parse_ranges(a.interp_take, a.interp_bins)
            plan = [e for e in plan if which[enum_key(e)] in take]
        plan.sort(key=lambda e: (-e["total"], enum_key(e)))
        enums = plan
        write_json(os.path.join(work, "interp-plan.json"), enums)
        log("%d enumerations, %d indices" % (len(enums), sum(e["total"] for e in enums)))
    record = {"started": started, "budget": a.budget, "jobs": a.jobs, "parts": sorted(parts),
              "seed": a.seed, "chunk": a.chunk, "interp_chunk": a.interp_chunk,
              "cases_cap": a.cases, "kernels": a.kernel_names, "cpus": a.cpus, "nice": a.nice,
              "commit": a.commit or git_commit(), "machine": machine_info(a.cpus),
              "interp_bins": a.interp_bins, "interp_take": a.interp_take,
              "builds": [{"name": s.split("=", 1)[0],
                          "compiler": compiler_of(os.path.join(work, "builds",
                                                               s.split("=", 1)[0]))}
                         for s in (a.build or [])] if a.compiled else []}
    with open(os.path.join(work, "runs.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
    deadline = time.time() + a.budget if a.budget else None
    sched = Scheduler(a, work, runners, enums)
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


def git_commit():
    try:
        out = subprocess.run(["git", "-C", REPO, "rev-parse", "HEAD"], capture_output=True,
                             text=True, timeout=30)
        if out.returncode == 0:
            return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return None


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
    rmap = {r["id"]: r for r in runners}
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
    log("merging %d series and %d enumerations" % (len(series), len(enum_out)))
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
        problems = list(guards.problems(s, ns))
        more, examples, _ = summary_problems(s, kernel not in INTERMEDIATE_OVERFLOW)
        problems += more
        counts = key_counts(keys)
        p = keys[0]["stats"]["p"] if keys else None
        entries = entry_stats(keys, p) if keys else []
        slot = compiled.setdefault(kernel, {}).setdefault(fmt, {"runners": {}})
        slot["runners"][rid] = {"counts": counts, "entries": entries, "units": nfiles,
                                "covered": ranges, "guards": problems or "ok"}
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
            slot["runners"] = {rid: [r["counts"].get(n, 0) for n in RUNNER_COUNTS] +
                               [headline(r["entries"])] for rid, r in sorted(rs.items())}
    interp = []
    itotals = {}
    for e, out, nfiles in enum_out:
        rec = {"kernel": e["kernel"], "format": e["format"], "restrict": e["restrict"],
               "why": e["why"], "total": e["total"], "chunks": nfiles}
        if not nfiles:
            rec["guards"] = ["not run"]
            interp.append(rec)
            continue
        s = read_json(out)
        keys = [k for k in s["keys"] if (k["kernel"], k["format"]) == (e["kernel"], e["format"])]
        desc, ranges = coverage_of(s)
        ns = argparse.Namespace(kernel=e["kernel"], format=e["format"], exhaustive=True,
                                restrict=",".join(e["restrict"]), count=None, seed=None)
        problems = list(guards.problems(s, ns))
        more, examples, _ = summary_problems(s, e["kernel"] not in INTERMEDIATE_OVERFLOW)
        problems += more
        rec["covered"] = sum(b - a for a, b in ranges) if ranges else 0
        rec["complete"] = ranges == [[0, e["total"]]]
        rec["counts"] = key_counts(keys)
        rec["entries"] = entry_stats(keys, keys[0]["stats"]["p"]) if keys else []
        rec["guards"] = problems or "ok"
        for n, v in rec["counts"].items():
            itotals[n] = itotals.get(n, 0) + v
        interp.append(rec)
    machine = starts[-1]["machine"]
    result = {
        "kairn_brute_summary": 1,
        "name": a.name,
        "machine": machine,
        "commit": sorted({r["commit"] for r in starts if r.get("commit")}),
        "runs": [{"started": r["started"], "budget": r["budget"], "jobs": r["jobs"],
                  "parts": r["parts"], "cpus": r["cpus"], "nice": r["nice"],
                  "interp_bins": r.get("interp_bins"), "interp_take": r.get("interp_take")}
                 for r in starts],
        "ends": [{"started": r["started"], "finished": r["finished"], "wall": r["wall"],
                  "status": r["status"], "findings": r["findings"]} for r in ends],
        "seed": seed,
        "chunk": starts[-1]["chunk"],
        "interp_chunk": starts[-1]["interp_chunk"],
        "runners": {r["id"]: {"kind": r["kind"], "backend": r["backend"], "setting": r["setting"],
                              "compiler": r["compiler"], "flags": r["flags"]} for r in runners},
        "runner_columns": list(RUNNER_COUNTS) + ["headline per entry"],
        "compiled": {"totals": totals, "kernels": compiled},
        "interp": {"totals": itotals, "enumerations": interp},
        "findings": findings,
    }
    write_json(a.out, result, compact=True)
    ok_c = all(s["guards"] == "ok" for f in compiled.values() for s in f.values())
    ok_i = all(r["guards"] == "ok" for r in interp)
    log("wrote %s (%d bytes): compiled %s judged in %d series%s; interp %s cases in %d "
        "enumerations%s; %d findings"
        % (a.out, os.path.getsize(a.out), "{:,}".format(totals.get("judged", 0)), len(series),
           "" if ok_c else " (GUARDS FAILED)", "{:,}".format(itotals.get("cases", 0)), len(interp),
           "" if ok_i else " (GUARDS FAILED or not complete)", len(findings)))
    return 0 if ok_c and ok_i and not findings else 1


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
    return format(decimal.Context(prec=digits).create_decimal(d), "g")


def headline_columns(entries):
    """(column title, extractor, better) for the entries of a kernel that have one."""
    cols = []
    for j, e in enumerate(entries):
        lab = e["label"]
        if e["kind"] == "error":
            cols.append(("largest error / bound" + (" (%s)" % lab.split(")")[0].split("(")[1]
                                                    if sum(x["kind"] == "error" for x in entries)
                                                    > 1 else ""),
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


def counts_text(counts):
    order = ["true", "false", "exact", "inexact", "tie", "inexact, = RN", "inexact, != RN"]
    names = sorted(counts, key=lambda c: (order.index(c) if c in order else 99, c))
    return ", ".join("%s %s" % (c.replace("inexact, != RN", "differs from RN")
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
            w("| `%s` | `%s` | %s | %s |" % (
                k, label.replace("|", "\\|"),
                (short(c[0]) + (" (the claim)" if c[-1] else "")) if c else "-",
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
                title = "`%s`%s" % (r["format"], (", restricted: " + ", ".join(
                    "`%s`" % x for x in r["restrict"])) if r["restrict"] else ", every operand")
                rows.append((title, r.get("counts", {}), r.get("entries", []),
                             r["guards"] == "ok" and r.get("complete"), False))
        if not rows:
            continue
        w("")
        w("### `%s`" % k)
        w("")
        entries0 = next((r[2] for r in rows if r[2]), [])
        w("Claims: " + "; ".join("`%s`" % e["label"] for e in entries0) + ".")
        w("")
        cols = headline_columns(entries0)
        w("| Run | Cases | Judged | Failed | " + " | ".join(c[0] for c in cols) + " |")
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
                    cells.append(counts_text(e.get("counts", {})) if compiled else "")
                    continue
                v = col_value(e, field, sub)
                mark = " (the claim)" if (e.get("attains_claim") and field in ("max_ratio",
                                                                                "maxima")) else ""
                cells.append(short(v[0]) + mark if v else "-")
                if v and field != "observed_c" and not (sub and "enclosing" in sub):
                    lines.append((title, name, v))
            w("| %s%s | %s | %s | %s | %s |" % (
                title, "" if ok else " (**INCOMPLETE or guard failed**)",
                fmt_int(counts.get("cases", 0)), fmt_int(counts.get("judged", 0)),
                fmt_int(counts.get("failed", 0)), " | ".join(cells)))
        # The line of the extreme of each headline column, over the compiled rows and over the
        # interpreter's.
        picks = []
        for name, j, field, sub, sign in cols:
            if field in ("counts", "observed_c") or (sub and "enclosing" in sub):
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
        if picks:
            w("")
            w("Where the extremes are attained (the line as the oracle reports it):")
            w("")
            w("```")
            for name, compiled, (v, t) in picks:
                where = (" (%s)" % ", ".join(v[2:])) if len(v) > 2 else ""
                w("%s, %s %s%s:" % (name, "compiled" if compiled else "interpreter", short(v[0]),
                                    where))
                w("  " + v[1])
            w("```")
    print("\n".join(out))
    return 0


# --- Plan ------------------------------------------------------------------------------------------

def cmd_plan(a):
    kernels = load_claims()
    only = set(a.kernels.split(",")) if a.kernels else None
    plan, errors = interp_plan(kernels, only)
    for e in errors:
        print("PLAN ERROR: %s" % e)
    plan = sized_plan(plan)
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
    return 1 if errors else 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="brute.py", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan", help="the interpreter's enumerations and their sizes")
    p.add_argument("--bins", type=int, default=0)
    p.add_argument("--kernels")
    p.set_defaults(func=cmd_plan)

    r = sub.add_parser("run", help="build, run, and keep the summaries in the work directory")
    r.add_argument("--work", required=True, help="work directory (restartable)")
    r.add_argument("--budget", type=float, required=True,
                   help="seconds: no new pipeline starts after this")
    r.add_argument("--jobs", type=int, required=True,
                   help="busy processes at a time: a compiled pipeline counts 1, an interpreter's 2")
    r.add_argument("--part", default="compiled,interp", help="compiled, interp, or both")
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
    r.add_argument("--cpus", help="CPU numbers to run on, e.g. 0-31,64-95 (Linux, Windows)")
    r.add_argument("--nice", type=int, default=0, help="lower the priority (POSIX nice; on "
                                                       "Windows, below normal)")
    r.add_argument("--task-timeout", type=float, default=1800,
                   help="seconds before a pipeline is killed and reported")
    r.add_argument("--report-every", type=float, default=60)
    r.add_argument("--commit", help="the commit the tree is from (default: git rev-parse HEAD)")
    r.set_defaults(func=cmd_run)

    c = sub.add_parser("collect", help="merge, guard and write the compact summary")
    c.add_argument("--work", required=True)
    c.add_argument("--name", required=True)
    c.add_argument("--out", required=True)
    c.add_argument("--jobs", type=int, default=4)
    c.set_defaults(func=cmd_collect)

    t = sub.add_parser("report", help="Markdown tables from compact summaries")
    t.add_argument("files", nargs="+")
    t.set_defaults(func=cmd_report)
    a = ap.parse_args(argv)
    if a.cmd == "run" and (a.interp_bins and not a.interp_take):
        ap.error("--interp-bins needs --interp-take")
    if a.cmd == "run" and (" " in a.seed or "=" in a.seed or not a.seed):
        ap.error("--seed must be non-empty, without spaces or '='")
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
